import codecs
import os
import re
import signal
import subprocess
import time
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class EngineError(RuntimeError):
    """Raised when an underlying audio engine (training, separation, ...) fails."""


class CommandCancelled(Exception):
    """Raised when a streaming command is stopped via its should_cancel callback."""


class ProgressCallback(Protocol):
    def __call__(self, progress: float) -> None: ...


class CancelCheck(Protocol):
    def __call__(self) -> bool: ...


def _kill_process_tree(process: "subprocess.Popen[bytes]") -> None:
    """Terminate a process and all of its descendants.

    Applio's trainer spawns its own worker processes, so killing only the
    top-level process would orphan them (leaving GPU memory pinned). On Windows
    `taskkill /T` walks the whole tree; on POSIX the child is launched in its own
    session (see run_command_streaming), so signalling the process group reaches
    every descendant.
    """
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            capture_output=True,
            check=False,
        )
        return
    try:
        pgid = os.getpgid(process.pid)
    except ProcessLookupError:
        return
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=5)
            return
        except subprocess.TimeoutExpired:
            continue


@dataclass(frozen=True)
class TrainingSpec:
    dataset_dir: Path
    output_dir: Path
    model_name: str
    epochs: int
    sample_rate: int


@dataclass(frozen=True)
class ConversionSpec:
    source_vocals: Path
    model_path: Path
    output_path: Path
    transpose: int
    # RVC 추론 품질 옵션 (Applio infer로 전달). 기본값은 무난한 출발점.
    index_rate: float = 0.5
    protect: float = 0.33
    volume_envelope: float = 1.0


@dataclass(frozen=True)
class SeparationResult:
    vocals: Path
    instrumental: Path


@dataclass(frozen=True)
class VideoSpec:
    audio_path: Path
    output_path: Path
    aspect: str  # "16:9" | "9:16"
    visual: str  # "image" | "wave" | "spectrum"
    image_path: Path | None
    title: str
    subtitle: str


class VoiceTrainer(Protocol):
    def train(
        self, spec: TrainingSpec, on_progress: ProgressCallback, should_cancel: CancelCheck
    ) -> Path: ...


class VoiceConverter(Protocol):
    def convert(self, spec: ConversionSpec) -> Path: ...


class VocalSeparator(Protocol):
    def separate(
        self, song_path: Path, output_dir: Path, on_progress: ProgressCallback
    ) -> SeparationResult: ...


class Dereverber(Protocol):
    def dereverb(self, vocals: Path, output_dir: Path) -> Path:
        """Strip reverb/echo from a vocal stem, returning the dry vocal file."""
        ...


class KaraokeSplitter(Protocol):
    def split(self, vocals: Path, output_dir: Path) -> tuple[Path, Path]:
        """Split a vocal stem into (lead vocal, backing vocals)."""
        ...


class PitchAnalyzer(Protocol):
    def median_f0(self, audio_paths: Sequence[Path]) -> float | None:
        """Median voiced f0 (Hz) across the given files; None when unmeasurable."""
        ...


class AudioMixer(Protocol):
    def mix(
        self,
        vocals: Path,
        instrumental: Path,
        output_path: Path,
        vocal_gain: float,
        instrumental_gain: float,
    ) -> Path: ...

    def merge(self, inputs: Sequence[Path], output_path: Path) -> Path:
        """Sum tracks at unity gain (e.g. instrumental + backing vocals)."""
        ...


class VideoRenderer(Protocol):
    def render(self, spec: VideoSpec) -> Path: ...


def subprocess_env() -> dict[str, str]:
    # Child tools print UTF-8; without this, decoding fails on Korean Windows (cp949).
    return {**os.environ, "PYTHONIOENCODING": "utf-8"}


def run_command(args: Sequence[str], cwd: Path | None = None) -> str:
    """Run an external tool, raising EngineError with its tail output on failure."""
    result = subprocess.run(
        list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=subprocess_env(),
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout)[-2000:]
        raise EngineError(f"Command failed ({args[0]}): {detail}")
    return result.stdout


_LINE_BREAKS = re.compile(r"[\r\n]")


def run_command_streaming(
    args: Sequence[str],
    cwd: Path | None,
    on_line: Callable[[str], None],
    should_cancel: CancelCheck | None = None,
) -> str:
    """Run a long-lived tool, forwarding each output line as it appears.

    Splits on carriage returns as well so tqdm-style progress bars stream live.
    Returns the tail of the combined output for diagnostics. Exit codes are not
    checked here: some tools (Applio's trainer) exit non-zero by design, so
    callers must verify expected output files instead.

    If should_cancel() turns true between output chunks, the process tree is
    killed and CommandCancelled is raised.
    """
    process = subprocess.Popen(
        list(args),
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=subprocess_env(),
        # POSIX: run in a fresh session so the whole spawned tree (Applio's
        # trainer forks workers) shares one process group we can signal on cancel.
        start_new_session=os.name != "nt",
    )
    tail: deque[str] = deque(maxlen=60)

    def emit(line: str) -> None:
        if line.strip():
            tail.append(line)
            on_line(line)

    stream = process.stdout
    if stream is not None:
        # read1 returns as soon as any bytes are available, so tqdm-style
        # \r updates stream in near real time instead of in 4 KB bursts.
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        buffer = ""
        while True:
            if should_cancel is not None and should_cancel():
                _kill_process_tree(process)
                raise CommandCancelled()
            chunk = stream.read1(4096)
            if not chunk:
                break
            buffer += decoder.decode(chunk)
            *lines, buffer = _LINE_BREAKS.split(buffer)
            for line in lines:
                emit(line)
        buffer += decoder.decode(b"", final=True)
        emit(buffer)
    process.wait()
    return "\n".join(tail)


_MEAN_VOLUME = re.compile(r"mean_volume:\s*(-?[\d.]+)\s*dB")


def mean_volume_db(path: Path) -> float | None:
    """Mean level via ffmpeg volumedetect; None when unmeasurable."""
    result = subprocess.run(
        ["ffmpeg", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=subprocess_env(),
    )
    match = _MEAN_VOLUME.search(result.stderr)
    return float(match.group(1)) if match else None


def audio_duration_seconds(path: Path) -> float | None:
    """Media duration via ffprobe; None when it cannot be determined."""
    try:
        output = run_command(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ]
        )
        return float(output.strip())
    except (EngineError, ValueError, OSError):
        return None


def throttled(callback: ProgressCallback, min_interval: float = 0.6) -> ProgressCallback:
    """Rate-limit progress writes by time, not by value delta.

    A value-delta throttle collapses per-batch progress into epoch-sized steps
    when the epoch count is low (e.g. 20 epochs -> ~5% jumps). Sampling by time
    keeps the bar smooth regardless of how many epochs were requested, while
    still bounding DB writes. The terminal 1.0 always gets through.
    """
    last_time = float("-inf")
    last_value = -1.0

    def wrapper(progress: float) -> None:
        nonlocal last_time, last_value
        now = time.monotonic()
        if progress >= 1.0 or (progress > last_value and now - last_time >= min_interval):
            last_time = now
            last_value = progress
            callback(progress)

    return wrapper
