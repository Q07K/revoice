"""Fake engines that exercise the full pipeline instantly, for dev without a GPU."""

import shutil
import time
from collections.abc import Sequence
from pathlib import Path

from app.engines.base import (
    CancelCheck,
    CommandCancelled,
    ConversionSpec,
    ProgressCallback,
    SeparationResult,
    TrainingSpec,
    VideoSpec,
)


class MockTrainer:
    def __init__(self, steps: int = 10, step_seconds: float = 0.05) -> None:
        self._steps = steps
        self._step_seconds = step_seconds

    def train(
        self, spec: TrainingSpec, on_progress: ProgressCallback, should_cancel: CancelCheck
    ) -> Path:
        spec.output_dir.mkdir(parents=True, exist_ok=True)
        for step in range(1, self._steps + 1):
            if should_cancel():
                raise CommandCancelled()
            time.sleep(self._step_seconds)
            on_progress(step / self._steps)
        model_path = spec.output_dir / f"{spec.model_name}.pth"
        model_path.write_bytes(b"mock-rvc-model")
        return model_path


class MockConverter:
    def convert(self, spec: ConversionSpec) -> Path:
        spec.output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(spec.source_vocals, spec.output_path)
        return spec.output_path


class MockSeparator:
    def separate(
        self, song_path: Path, output_dir: Path, on_progress: ProgressCallback
    ) -> SeparationResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        vocals = output_dir / "vocals.wav"
        instrumental = output_dir / "instrumental.wav"
        shutil.copyfile(song_path, vocals)
        on_progress(0.5)
        shutil.copyfile(song_path, instrumental)
        on_progress(1.0)
        return SeparationResult(vocals=vocals, instrumental=instrumental)


class MockMixer:
    def mix(
        self,
        vocals: Path,
        instrumental: Path,
        output_path: Path,
        vocal_gain: float,
        instrumental_gain: float,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(vocals, output_path)
        return output_path

    def merge(self, inputs: Sequence[Path], output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(inputs[0], output_path)
        return output_path


class MockKaraokeSplitter:
    def split(self, vocals: Path, output_dir: Path) -> tuple[Path, Path]:
        target_dir = output_dir / "karaoke"
        target_dir.mkdir(parents=True, exist_ok=True)
        lead = target_dir / "lead.wav"
        backing = target_dir / "backing.wav"
        shutil.copyfile(vocals, lead)
        shutil.copyfile(vocals, backing)
        return lead, backing


class MockDereverber:
    def dereverb(self, vocals: Path, output_dir: Path) -> Path:
        target_dir = output_dir / "dereverb"
        target_dir.mkdir(parents=True, exist_ok=True)
        dry = target_dir / "dry_vocals.wav"
        shutil.copyfile(vocals, dry)
        return dry


class MockPitchAnalyzer:
    """Register measurement needs librosa (Applio venv); the mock reports
    unknown so auto key matching resolves to no shift."""

    def median_f0(self, audio_paths: Sequence[Path]) -> float | None:
        return None


class MockVideoRenderer:
    def render(self, spec: VideoSpec) -> Path:
        spec.output_path.parent.mkdir(parents=True, exist_ok=True)
        spec.output_path.write_bytes(b"mock-mp4")
        return spec.output_path
