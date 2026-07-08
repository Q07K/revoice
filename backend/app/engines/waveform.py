"""Waveform peak extraction for UI display (drawn as bars on the frontend)."""

import subprocess
from pathlib import Path

from app.engines.base import EngineError, subprocess_env

_ANALYSIS_SAMPLE_RATE = 4000


def compute_waveform_peaks(path: Path, buckets: int = 160) -> list[float]:
    """Downmix to mono PCM and reduce to `buckets` normalized peak values (0~1)."""
    samples = _decode_mono_pcm(path).cast("h")
    if len(samples) == 0:
        return [0.0] * buckets
    bucket_size = max(1, len(samples) // buckets)
    peaks: list[float] = []
    for index in range(buckets):
        chunk = samples[index * bucket_size : (index + 1) * bucket_size]
        peak = max((abs(value) for value in chunk), default=0)
        peaks.append(peak / 32768)
    highest = max(peaks)
    if highest > 0:
        peaks = [round(peak / highest, 4) for peak in peaks]
    return peaks


def _decode_mono_pcm(path: Path) -> memoryview:
    result = subprocess.run(
        [
            "ffmpeg", "-v", "error",
            "-i", str(path),
            "-ac", "1",
            "-ar", str(_ANALYSIS_SAMPLE_RATE),
            "-f", "s16le",
            "-",
        ],
        capture_output=True,
        env=subprocess_env(),
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace")[-500:]
        raise EngineError(f"Could not decode audio for waveform: {detail}")
    payload = result.stdout
    # s16le samples are 2 bytes each; drop a trailing odd byte if ffmpeg was cut off.
    if len(payload) % 2 == 1:
        payload = payload[:-1]
    return memoryview(payload)
