"""Real engines: Applio (RVC v2) for training/inference, audio-separator for
vocal isolation, and ffmpeg for the final mixdown.

Requires a local Applio checkout (https://github.com/IAHispano/Applio) at
`settings.applio_dir` with its own venv (`settings.applio_python`), plus the
`audio-separator` CLI and `ffmpeg`.

Applio's core.py always exits 0 (it swallows exceptions and its trainer even
exits non-zero on success by design), so every stage verifies its expected
output files instead of trusting exit codes.
"""

import logging
import os
import re
import shutil
from pathlib import Path

from app.engines.base import (
    ConversionSpec,
    EngineError,
    ProgressCallback,
    SeparationResult,
    TrainingSpec,
    run_command,
    run_command_streaming,
    throttled,
)

logger = logging.getLogger(__name__)

_EPOCH_LINE = re.compile(r"epoch=(\d+)")
_TQDM_COUNTER = re.compile(r"(\d+)/(\d+) \[")

# Progress budget: preprocess+extract 0~0.1, training 0.1~0.95, index/collect rest.
_TRAIN_PROGRESS_START = 0.1
_TRAIN_PROGRESS_SPAN = 0.85


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

    def _logs_dir(self, model_name: str) -> Path:
        return self._applio_dir / "logs" / model_name


class ApplioTrainer(_ApplioCli):
    """Runs the Applio preprocess -> extract -> train -> index pipeline."""

    def __init__(self, applio_dir: Path, python_bin: str, batch_size: int) -> None:
        super().__init__(applio_dir, python_bin)
        self._batch_size = batch_size

    def train(self, spec: TrainingSpec, on_progress: ProgressCallback) -> Path:
        self._ensure_assets_config()
        self._preprocess(spec)
        on_progress(0.05)
        self._extract(spec)
        on_progress(_TRAIN_PROGRESS_START)
        self._train(spec, on_progress)
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

    def _preprocess(self, spec: TrainingSpec) -> None:
        self._run_core(
            [
                "preprocess",
                "--model_name", spec.model_name,
                "--dataset_path", str(spec.dataset_dir),
                "--sample_rate", str(spec.sample_rate),
                "--cpu_cores", str(_worker_count()),
                "--cut_preprocess", "Automatic",
            ]
        )
        _require_files(self._logs_dir(spec.model_name) / "sliced_audios", "*.wav", "Preprocess")

    def _extract(self, spec: TrainingSpec) -> None:
        self._run_core(
            [
                "extract",
                "--model_name", spec.model_name,
                "--f0_method", "rmvpe",
                "--sample_rate", str(spec.sample_rate),
                "--include_mutes", "2",
                "--cpu_cores", str(_worker_count()),
                "--gpu", "-",
            ]
        )
        _require_files(self._logs_dir(spec.model_name) / "extracted", "*.npy", "Feature extraction")

    def _train(self, spec: TrainingSpec, on_progress: ProgressCallback) -> None:
        command = self._core_command(
            [
                "train",
                "--model_name", spec.model_name,
                "--sample_rate", str(spec.sample_rate),
                "--total_epoch", str(spec.epochs),
                "--save_every_epoch", str(min(spec.epochs, 50)),
                "--save_only_latest", "True",
                "--save_every_weights", "False",
                "--batch_size", str(self._batch_size),
                "--index_algorithm", "Auto",
            ]
        )

        tracker = _EpochTracker(spec.epochs, on_progress)
        tail = run_command_streaming(command, self._applio_dir, tracker.observe)
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
    def convert(self, spec: ConversionSpec) -> Path:
        index = next(iter(spec.model_path.parent.glob("*.index")), None)
        if index is None:
            raise EngineError(
                f"No .index file next to {spec.model_path}. Re-train the voice to generate one."
            )
        spec.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._run_core(
            [
                "infer",
                "--pitch", str(spec.transpose),
                "--f0_method", "rmvpe",
                "--input_path", str(spec.source_vocals),
                "--output_path", str(spec.output_path),
                "--pth_path", str(spec.model_path),
                "--index_path", str(index),
            ]
        )
        if not spec.output_path.exists():
            raise EngineError("Voice conversion produced no output file. Check backend logs.")
        return spec.output_path


class CliVocalSeparator:
    """Separates vocals/instrumental with the `audio-separator` CLI (RoFormer models)."""

    def __init__(self, separator_bin: str, model_filename: str) -> None:
        self._separator_bin = separator_bin
        self._model_filename = model_filename

    def separate(
        self, song_path: Path, output_dir: Path, on_progress: ProgressCallback
    ) -> SeparationResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        report = throttled(on_progress)

        def observe(line: str) -> None:
            match = _TQDM_COUNTER.search(line)
            if match is not None and int(match.group(2)) > 0:
                report(int(match.group(1)) / int(match.group(2)))

        tail = run_command_streaming(
            [
                self._separator_bin, str(song_path),
                "--model_filename", self._model_filename,
                "--output_dir", str(output_dir),
                "--output_format", "wav",
            ],
            None,
            observe,
        )
        try:
            return SeparationResult(
                vocals=_find_output(output_dir, "(Vocals)"),
                instrumental=_find_output(output_dir, "(Instrumental)"),
            )
        except EngineError as error:
            raise EngineError(f"{error} Last output:\n{tail[-1000:]}") from error


class FfmpegMixer:
    def mix(self, vocals: Path, instrumental: Path, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        run_command(
            [
                "ffmpeg", "-y",
                "-i", str(vocals),
                "-i", str(instrumental),
                "-filter_complex", "amix=inputs=2:duration=longest:normalize=0",
                str(output_path),
            ]
        )
        return output_path


def _find_output(output_dir: Path, marker: str) -> Path:
    for candidate in output_dir.glob("*.wav"):
        if marker.lower() in candidate.name.lower():
            return candidate
    raise EngineError(f"Separator output containing '{marker}' not found in {output_dir}.")
