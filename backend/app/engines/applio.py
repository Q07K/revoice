"""Real engines: Applio (RVC v2) for training/inference, audio-separator for
vocal isolation, and ffmpeg for the final mixdown.

Requires a local Applio checkout (https://github.com/IAHispano/Applio) at
`settings.applio_dir` with its own venv (`settings.applio_python`), plus the
`audio-separator` CLI and `ffmpeg`.

Applio's core.py always exits 0 (it swallows exceptions and its trainer even
exits non-zero on success by design), so every stage verifies its expected
output files instead of trusting exit codes.
"""

import json
import logging
import math
import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path

from app.core.config import get_settings
from app.engines.base import (
    CancelCheck,
    CommandCancelled,
    ConversionSpec,
    EngineError,
    ProgressCallback,
    SeparationResult,
    TrainingSpec,
    run_command,
    run_command_streaming,
    subprocess_env,
    throttled,
)
from app.engines.separator_client import get_separator_daemon

logger = logging.getLogger(__name__)


def _raise_if_cancelled(should_cancel: CancelCheck) -> None:
    if should_cancel():
        raise CommandCancelled()


# Applio's preprocessor only picks up these extensions and silently ignores the
# rest (rvc/train/preprocess/preprocess.py), so anything else (phone recordings
# are usually .m4a) must be transcoded to WAV before training.
_APPLIO_AUDIO_EXTS = frozenset({".wav", ".mp3", ".flac", ".ogg"})


@contextmanager
def _prepared_dataset(dataset_dir: Path) -> Iterator[Path]:
    """Yield a dataset directory Applio can read, transcoding unsupported files.

    If every file already has an Applio-supported extension the original
    directory is used as-is. Otherwise a temporary directory is populated with
    the supported files (copied) and the rest transcoded to WAV via ffmpeg, and
    cleaned up when training's preprocess stage finishes.
    """
    files = [path for path in sorted(dataset_dir.iterdir()) if path.is_file()]
    if all(path.suffix.lower() in _APPLIO_AUDIO_EXTS for path in files):
        yield dataset_dir
        return
    with tempfile.TemporaryDirectory(prefix="revoice_dataset_") as tmp:
        staged = Path(tmp)
        for path in files:
            if path.suffix.lower() in _APPLIO_AUDIO_EXTS:
                shutil.copy2(path, staged / path.name)
            else:
                # -vn drops any video/cover-art stream so ffmpeg emits pure PCM.
                run_command(["ffmpeg", "-y", "-i", str(path), "-vn", str(staged / f"{path.stem}.wav")])
        yield staged


_EPOCH_LINE = re.compile(r"epoch=(\d+)")
_TQDM_COUNTER = re.compile(r"(\d+)/(\d+) \[")

# Progress budget per stage (absolute, 0~1). The UI derives the current stage
# (preprocess / extract / train / finalize) from these boundaries, so each stage
# streams its own tqdm within its slice for a smooth, gap-free bar. Preprocess
# and extract stop just shy of their upper bound so the bar never briefly reads
# as the next stage while the current one is still finishing.
_PREPROCESS_SPAN = (0.0, 0.049)
_EXTRACT_SPAN = (0.05, 0.098)
_TRAIN_PROGRESS_START = 0.1
_TRAIN_PROGRESS_SPAN = 0.85
_FINALIZE_START = 0.95


def _tqdm_reporter(
    on_progress: ProgressCallback, start: float, end: float
) -> "Callable[[str], None]":
    """Map a stage's tqdm counter (n/total) onto the [start, end] progress slice.

    throttled() drops decreasing values, so a stage that prints more than one bar
    (extract runs f0 then embeddings) pauses rather than snapping backwards.
    """
    report = throttled(on_progress)

    def observe(line: str) -> None:
        match = _TQDM_COUNTER.search(line)
        if match is not None and int(match.group(2)) > 0:
            report(start + (end - start) * int(match.group(1)) / int(match.group(2)))

    return observe


class _EpochTracker:
    """Turns Applio's train output (epoch records + per-batch tqdm) into progress."""

    def __init__(self, total_epochs: int, on_progress: ProgressCallback) -> None:
        self._total = max(total_epochs, 1)
        self._on_progress = throttled(on_progress)
        self._completed_epochs = 0

    def observe(self, line: str) -> None:
        epoch_match = _EPOCH_LINE.search(line)
        if epoch_match is not None:
            self._completed_epochs = min(int(epoch_match.group(1)), self._total)
            self._report(0.0)
            return
        batch_match = _TQDM_COUNTER.search(line)
        if batch_match is not None and int(batch_match.group(2)) > 0:
            self._report(int(batch_match.group(1)) / int(batch_match.group(2)))

    def _report(self, current_epoch_fraction: float) -> None:
        epochs_done = min(self._completed_epochs + current_epoch_fraction, self._total)
        ratio = epochs_done / self._total
        self._on_progress(_TRAIN_PROGRESS_START + _TRAIN_PROGRESS_SPAN * ratio)


def _worker_count() -> int:
    return max(1, min(os.cpu_count() or 2, 8))


def _require_files(directory: Path, pattern: str, stage: str) -> None:
    if next(iter(directory.glob(pattern)), None) is None:
        raise EngineError(
            f"{stage} produced no output in {directory}. "
            "Check the backend logs for the Applio output."
        )


class _ApplioCli:
    def __init__(self, applio_dir: Path, python_bin: str) -> None:
        self._applio_dir = applio_dir
        self._python_bin = python_bin

    def _core_command(self, args: list[str]) -> list[str]:
        return [self._python_bin, str(self._applio_dir / "core.py"), *args]

    def _run_core(self, args: list[str]) -> None:
        output = run_command(self._core_command(args), cwd=self._applio_dir)
        logger.debug("applio %s: %s", args[0], output[-500:])

    def _run_core_streaming(
        self,
        args: list[str],
        on_line: Callable[[str], None],
        should_cancel: CancelCheck | None = None,
    ) -> str:
        return run_command_streaming(
            self._core_command(args), self._applio_dir, on_line, should_cancel
        )

    def _logs_dir(self, model_name: str) -> Path:
        return self._applio_dir / "logs" / model_name


class ApplioTrainer(_ApplioCli):
    """Runs the Applio preprocess -> extract -> train -> index pipeline."""

    def __init__(
        self,
        applio_dir: Path,
        python_bin: str,
        batch_size: int,
        gpu_device: str = "0",
        pretrained_g: Path | None = None,
        pretrained_d: Path | None = None,
        overtraining_threshold: int = 0,
    ) -> None:
        super().__init__(applio_dir, python_bin)
        self._batch_size = batch_size
        # Applio core.py --gpu 규약: "0"=첫 GPU, "-"=CPU, "0-1"=다중 GPU.
        self._gpu_device = gpu_device
        # Custom pretrained needs both halves; fall back to Applio's default
        # pretrained when either file is missing.
        self._custom_pretrained = (
            (pretrained_g, pretrained_d)
            if pretrained_g is not None
            and pretrained_d is not None
            and pretrained_g.exists()
            and pretrained_d.exists()
            else None
        )
        self._overtraining_threshold = overtraining_threshold

    def train(
        self, spec: TrainingSpec, on_progress: ProgressCallback, should_cancel: CancelCheck
    ) -> Path:
        self._ensure_assets_config()
        # Applio resumes from logs/<model>/{G,D}_*.pth when they exist, which
        # would silently continue a previous run's weights (wrong dataset,
        # wrong pretrained). Every train request starts from scratch.
        shutil.rmtree(self._logs_dir(spec.model_name), ignore_errors=True)
        _raise_if_cancelled(should_cancel)
        with _prepared_dataset(spec.dataset_dir) as dataset_dir:
            self._preprocess(spec, dataset_dir, on_progress, should_cancel)
        _raise_if_cancelled(should_cancel)
        self._extract(spec, on_progress, should_cancel)
        on_progress(_TRAIN_PROGRESS_START)
        self._train(spec, on_progress, should_cancel)
        on_progress(_FINALIZE_START)
        self._build_index(spec.model_name)
        on_progress(0.98)
        return self._collect_artifacts(spec)

    def _ensure_assets_config(self) -> None:
        """Applio's UI normally creates assets/config.json on first launch; without
        it the final weight extraction fails silently, so create it ourselves."""
        config = self._applio_dir / "assets" / "config.json"
        template = self._applio_dir / "assets" / "config_template.json"
        if not config.exists() and template.exists():
            shutil.copy2(template, config)

    def _preprocess(
        self,
        spec: TrainingSpec,
        dataset_dir: Path,
        on_progress: ProgressCallback,
        should_cancel: CancelCheck,
    ) -> None:
        self._run_core_streaming(
            [
                "preprocess",
                "--model_name", spec.model_name,
                "--dataset_path", str(dataset_dir),
                "--sample_rate", str(spec.sample_rate),
                "--cpu_cores", str(_worker_count()),
                "--cut_preprocess", "Automatic",
            ],
            _tqdm_reporter(on_progress, *_PREPROCESS_SPAN),
            should_cancel,
        )
        _require_files(self._logs_dir(spec.model_name) / "sliced_audios", "*.wav", "Preprocess")

    def _extract(
        self, spec: TrainingSpec, on_progress: ProgressCallback, should_cancel: CancelCheck
    ) -> None:
        self._run_core_streaming(
            [
                "extract",
                "--model_name", spec.model_name,
                "--f0_method", "rmvpe",
                "--sample_rate", str(spec.sample_rate),
                "--include_mutes", "2",
                "--cpu_cores", str(_worker_count()),
                "--gpu", self._gpu_device,
            ],
            _tqdm_reporter(on_progress, *_EXTRACT_SPAN),
            should_cancel,
        )
        _require_files(self._logs_dir(spec.model_name) / "extracted", "*.npy", "Feature extraction")

    def _train(
        self, spec: TrainingSpec, on_progress: ProgressCallback, should_cancel: CancelCheck
    ) -> None:
        args = [
            "train",
            "--model_name", spec.model_name,
            "--sample_rate", str(spec.sample_rate),
            "--total_epoch", str(spec.epochs),
            "--save_every_epoch", str(min(spec.epochs, 50)),
            "--save_only_latest", "True",
            "--save_every_weights", "False",
            "--batch_size", str(self._batch_size),
            "--index_algorithm", "Auto",
            "--gpu", self._gpu_device,
        ]
        if self._custom_pretrained is not None:
            generator, discriminator = self._custom_pretrained
            args += [
                "--custom_pretrained", "True",
                "--g_pretrained_path", str(generator),
                "--d_pretrained_path", str(discriminator),
            ]
        if self._overtraining_threshold > 0:
            args += [
                "--overtraining_detector", "True",
                "--overtraining_threshold", str(self._overtraining_threshold),
            ]
        command = self._core_command(args)

        tracker = _EpochTracker(spec.epochs, on_progress)
        tail = run_command_streaming(
            command, self._applio_dir, tracker.observe, should_cancel
        )
        weight_pattern = f"{spec.model_name}_*e_*s.pth"
        if next(iter(self._logs_dir(spec.model_name).glob(weight_pattern)), None) is None:
            raise EngineError(f"Training produced no model weight. Last output:\n{tail[-1500:]}")

    def _build_index(self, model_name: str) -> None:
        # core.py skips index generation after training (the trainer's exit code
        # trips its own success check), so run it explicitly.
        self._run_core(["index", "--model_name", model_name, "--index_algorithm", "Auto"])

    def _collect_artifacts(self, spec: TrainingSpec) -> Path:
        logs_dir = self._logs_dir(spec.model_name)
        weights = sorted(
            logs_dir.glob(f"{spec.model_name}_*e_*s.pth"),
            key=lambda path: path.stat().st_mtime,
        )
        if not weights:
            raise EngineError(f"Trained weight not found in {logs_dir}.")
        spec.output_dir.mkdir(parents=True, exist_ok=True)
        model_path = spec.output_dir / weights[-1].name
        shutil.copy2(weights[-1], model_path)

        index_file = logs_dir / f"{spec.model_name}.index"
        if index_file.exists():
            shutil.copy2(index_file, spec.output_dir / index_file.name)
        else:
            logger.warning("Index file missing for %s; conversion will fail.", spec.model_name)
        return model_path


class ApplioConverter(_ApplioCli):
    def __init__(
        self,
        applio_dir: Path,
        python_bin: str,
        split_audio: bool = True,
        clean_strength: float = 0.0,
        reverb: bool = False,
    ) -> None:
        super().__init__(applio_dir, python_bin)
        self._split_audio = split_audio
        # Applio's --clean_strength only accepts tenths (0.0~1.0); 0 disables.
        self._clean_strength = round(clean_strength, 1)
        self._reverb = reverb

    def convert(self, spec: ConversionSpec) -> Path:
        index = next(iter(spec.model_path.parent.glob("*.index")), None)
        if index is None:
            raise EngineError(
                f"No .index file next to {spec.model_path}. Re-train the voice to generate one."
            )
        spec.output_path.parent.mkdir(parents=True, exist_ok=True)
        args = [
            "infer",
            "--pitch", str(spec.transpose),
            "--f0_method", "rmvpe",
            "--index_rate", str(spec.index_rate),
            "--protect", str(spec.protect),
            "--volume_envelope", str(spec.volume_envelope),
            # Split on silence so long songs convert in stable chunks instead of
            # drifting over a single multi-minute pass.
            "--split_audio", str(self._split_audio),
            "--input_path", str(spec.source_vocals),
            "--output_path", str(spec.output_path),
            "--pth_path", str(spec.model_path),
            "--index_path", str(index),
        ]
        if self._clean_strength > 0:
            args += ["--clean_audio", "True", "--clean_strength", f"{self._clean_strength:.1f}"]
        if self._reverb:
            # A gentle Freeverb (pedalboard) restores the ambience the dereverb
            # pass stripped, so the converted vocal doesn't sound bone-dry.
            args += [
                "--post_process", "True",
                "--reverb", "True",
                "--reverb_room_size", "0.35",
                "--reverb_damping", "0.6",
                "--reverb_wet_gain", "0.15",
                "--reverb_dry_gain", "0.85",
                "--reverb_width", "1.0",
                "--reverb_freeze_mode", "0",
            ]
        self._run_core(args)
        if not spec.output_path.exists():
            raise EngineError("Voice conversion produced no output file. Check backend logs.")
        return spec.output_path


class ApplioPitchAnalyzer:
    """Measures a vocal register (median voiced f0) for auto key matching.

    librosa lives in the Applio venv, not the backend venv, so the measurement
    runs scripts/median_f0.py with the Applio interpreter. Inputs are first
    transcoded to short mono 16 kHz WAVs so pyin stays fast regardless of the
    source format/length. Returns None on any failure — callers fall back to
    no key shift rather than failing the cover.
    """

    _MAX_FILES = 4
    _MAX_SECONDS_PER_FILE = 90

    def __init__(self, python_bin: str) -> None:
        self._python_bin = python_bin
        self._script = Path(__file__).parent / "scripts" / "median_f0.py"

    def median_f0(self, audio_paths: Sequence[Path]) -> float | None:
        paths = list(audio_paths)[: self._MAX_FILES]
        if not paths:
            return None
        with tempfile.TemporaryDirectory(prefix="revoice_f0_") as tmp:
            staged: list[str] = []
            for position, path in enumerate(paths):
                target = Path(tmp) / f"{position}.wav"
                try:
                    run_command(
                        [
                            "ffmpeg", "-y",
                            "-t", str(self._MAX_SECONDS_PER_FILE),
                            "-i", str(path),
                            "-vn", "-ac", "1", "-ar", "16000",
                            str(target),
                        ]
                    )
                except EngineError as error:
                    logger.warning("f0 staging failed for %s: %s", path, error)
                    continue
                staged.append(str(target))
            if not staged:
                return None
            try:
                output = run_command([self._python_bin, str(self._script), *staged])
            except EngineError as error:
                logger.warning("median f0 measurement failed: %s", error)
                return None
        try:
            value = float(output.strip().splitlines()[-1])
        except (ValueError, IndexError):
            return None
        return value if value > 0 and not math.isnan(value) else None


def _run_separator(
    separator_bin: str, model_filename: str, input_path: Path, output_dir: Path
) -> str:
    """Run one separation pass, returning the output tail for diagnostics.

    Prefers the persistent daemon (models stay loaded between passes); any
    daemon problem falls back to the one-shot CLI.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    settings = get_settings()
    if settings.separator_daemon:
        python_bin = settings.separator_python or _sibling_python(separator_bin)
        if python_bin is not None:
            try:
                get_separator_daemon(python_bin).separate(
                    model_filename, input_path, output_dir
                )
                return ""
            except EngineError as error:
                logger.warning("Separator daemon failed; falling back to CLI. (%s)", error)
    return run_command_streaming(
        [
            separator_bin, str(input_path),
            "--model_filename", model_filename,
            "--output_dir", str(output_dir),
            "--output_format", "wav",
        ],
        None,
        lambda line: None,
    )


def _sibling_python(separator_bin: str) -> str | None:
    """The daemon must run in the separator venv: use the python next to the CLI."""
    candidate = Path(separator_bin).parent / "python"
    return str(candidate) if candidate.exists() else None


class CliVocalSeparator:
    """Separates vocals/instrumental with the `audio-separator` CLI (RoFormer models)."""

    def __init__(self, separator_bin: str, model_filename: str) -> None:
        self._separator_bin = separator_bin
        self._model_filename = model_filename

    def separate(
        self, song_path: Path, output_dir: Path, on_progress: ProgressCallback
    ) -> SeparationResult:
        tail = _run_separator(self._separator_bin, self._model_filename, song_path, output_dir)
        try:
            return SeparationResult(
                vocals=_find_output(output_dir, _VOCAL_MARKERS),
                instrumental=_find_output(output_dir, _INSTRUMENTAL_MARKERS),
            )
        except EngineError as error:
            raise EngineError(f"{error} Last output:\n{tail[-1000:]}") from error


class CliKaraokeSplitter:
    """Splits a vocal stem into lead vs backing vocals (karaoke model).

    Converting a stacked chorus through RVC smears the voices together, so
    only the lead goes to conversion; the backing vocals are merged back into
    the accompaniment untouched.
    """

    def __init__(self, separator_bin: str, model_filename: str) -> None:
        self._separator_bin = separator_bin
        self._model_filename = model_filename

    def split(self, vocals: Path, output_dir: Path) -> tuple[Path, Path]:
        target_dir = output_dir / "karaoke"
        tail = _run_separator(self._separator_bin, self._model_filename, vocals, target_dir)
        try:
            # The input filename already contains "(vocals)" from the first
            # separation pass, so marker-match the unambiguous backing stem
            # ("instrumental" for karaoke models) and take the other file as
            # the lead.
            backing = _find_output(target_dir, _INSTRUMENTAL_MARKERS)
            lead = next(
                (path for path in target_dir.glob("*.wav") if path != backing), None
            )
            if lead is None:
                raise EngineError(f"Karaoke lead stem not found in {target_dir}.")
            return lead, backing
        except EngineError as error:
            raise EngineError(f"{error} Last output:\n{tail[-1000:]}") from error


class CliDereverber:
    """Removes reverb/echo from a vocal stem with an audio-separator model.

    Reverb in the source vocal is the biggest RVC artifact source (smeared,
    metallic output), so the vocal gets a second separation pass before
    conversion. Outputs land in their own subdirectory so retry runs never
    confuse the dry stem with the first-pass separation outputs.
    """

    def __init__(self, separator_bin: str, model_filename: str) -> None:
        self._separator_bin = separator_bin
        self._model_filename = model_filename

    def dereverb(self, vocals: Path, output_dir: Path) -> Path:
        target_dir = output_dir / "dereverb"
        tail = _run_separator(self._separator_bin, self._model_filename, vocals, target_dir)
        try:
            return _find_output(target_dir, _DRY_MARKERS)
        except EngineError as error:
            raise EngineError(f"{error} Last output:\n{tail[-1000:]}") from error


class FfmpegMixer:
    """Mixes the converted vocal over the instrumental with a light vocal chain
    (high-pass, gentle compression, short ambience) plus two-pass loudness
    normalization to -14 LUFS, so every cover comes out at a consistent,
    streaming-friendly level. Two-pass (measure, then linear gain) avoids the
    pumping that single-pass dynamic loudnorm causes on music."""

    _LOUDNORM_TARGET = "loudnorm=I=-14:TP=-1.2:LRA=11"

    def mix(
        self,
        vocals: Path,
        instrumental: Path,
        output_path: Path,
        vocal_gain: float,
        instrumental_gain: float,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        measured = self._measure_loudness(vocals, instrumental, vocal_gain, instrumental_gain)
        if measured is None:
            # Measurement failed (e.g. exotic input): keep the mix usable with
            # the plain limiter chain instead of failing the job.
            final = "alimiter=limit=0.97"
        else:
            final = (
                f"{self._LOUDNORM_TARGET}"
                f":measured_I={measured['input_i']}"
                f":measured_TP={measured['input_tp']}"
                f":measured_LRA={measured['input_lra']}"
                f":measured_thresh={measured['input_thresh']}"
                f":offset={measured['target_offset']}"
                # loudnorm resamples to 192 kHz internally; bring it back down.
                ":linear=true,aresample=48000"
            )
        run_command(
            [
                "ffmpeg", "-y",
                "-i", str(vocals),
                "-i", str(instrumental),
                "-filter_complex", self._filter(vocal_gain, instrumental_gain, final),
                str(output_path),
            ]
        )
        return output_path

    @staticmethod
    def _filter(vocal_gain: float, instrumental_gain: float, final_stage: str) -> str:
        # Vocal chain: cut low-end rumble and tame dynamics so quiet lines stay
        # audible over the track. Ambience comes from the pedalboard reverb the
        # converter applies (conversion_reverb), not from the mixer. Per-track
        # gain applies after the compressor so it doesn't change its drive.
        return (
            "[0:a]highpass=f=85,"
            "acompressor=threshold=0.1:ratio=2.5:attack=15:release=200:makeup=1.4,"
            f"volume={vocal_gain:.3f}[v];"
            f"[1:a]volume={instrumental_gain:.3f}[i];"
            f"[v][i]amix=inputs=2:duration=longest:normalize=0,{final_stage}"
        )

    def merge(self, inputs: Sequence[Path], output_path: Path) -> Path:
        """Unity-gain sum, written as float WAV so the intermediate can't clip
        (levels are settled later by the final mix's loudness normalization)."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        args = ["ffmpeg", "-y"]
        for path in inputs:
            args += ["-i", str(path)]
        args += [
            "-filter_complex",
            f"amix=inputs={len(inputs)}:duration=longest:normalize=0",
            "-c:a", "pcm_f32le",
            str(output_path),
        ]
        run_command(args)
        return output_path

    def _measure_loudness(
        self, vocals: Path, instrumental: Path, vocal_gain: float, instrumental_gain: float
    ) -> dict[str, str] | None:
        """First loudnorm pass: render the same mix to the null muxer and parse
        the measured loudness stats loudnorm prints (JSON on stderr)."""
        first_pass = f"{self._LOUDNORM_TARGET}:print_format=json"
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(vocals),
                "-i", str(instrumental),
                "-filter_complex", self._filter(vocal_gain, instrumental_gain, first_pass),
                "-f", "null", "-",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=subprocess_env(),
        )
        if result.returncode != 0:
            logger.warning("loudnorm measurement failed: %s", result.stderr[-500:])
            return None
        match = re.search(r"\{[^{}]+\}\s*$", result.stderr, re.DOTALL)
        if match is None:
            logger.warning("loudnorm stats not found in ffmpeg output.")
            return None
        try:
            stats: dict[str, str] = json.loads(match.group(0))
            required = ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")
            # A silent mix measures "-inf", which the second pass can't parse.
            if any(not math.isfinite(float(stats[key])) for key in required):
                return None
        except (json.JSONDecodeError, KeyError, ValueError):
            return None
        return stats


# audio-separator names stems by the parenthesised label the model defines. The
# vocal stem is always "(Vocals)", but the backing track varies by model: the
# classic 4-stem/instrumental models emit "(Instrumental)", while 2-stem vocal
# models (e.g. vocals_mel_band_roformer) emit "(other)" / "(No Vocals)".
_VOCAL_MARKERS = ("(vocals)",)
_INSTRUMENTAL_MARKERS = ("(instrumental)", "(no vocals)", "(other)", "(inst)")
# Dry-stem labels across dereverb model families: RoFormer models emit
# "(noreverb)", VR DeEcho/DeReverb "(no reverb)"/"(no echo)", MDX23C "(dry)".
_DRY_MARKERS = ("(noreverb)", "(no reverb)", "(no echo)", "(dry)")


def _find_output(output_dir: Path, markers: tuple[str, ...]) -> Path:
    for marker in markers:
        for candidate in output_dir.glob("*.wav"):
            if marker in candidate.name.lower():
                return candidate
    raise EngineError(
        f"Separator output for {markers} not found in {output_dir}."
    )
