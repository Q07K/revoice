"""Fake engines that exercise the full pipeline instantly, for dev without a GPU."""

import shutil
import time
from pathlib import Path

from app.engines.base import (
    ConversionSpec,
    ProgressCallback,
    SeparationResult,
    TrainingSpec,
)


class MockTrainer:
    def __init__(self, steps: int = 10, step_seconds: float = 0.05) -> None:
        self._steps = steps
        self._step_seconds = step_seconds

    def train(self, spec: TrainingSpec, on_progress: ProgressCallback) -> Path:
        spec.output_dir.mkdir(parents=True, exist_ok=True)
        for step in range(1, self._steps + 1):
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
    def mix(self, vocals: Path, instrumental: Path, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(vocals, output_path)
        return output_path
