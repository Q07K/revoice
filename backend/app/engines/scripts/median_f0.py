"""Print the median voiced f0 (Hz) of the given audio files, one float on stdout.

Runs inside the Applio venv (the backend venv has no librosa/torch). Callers
pre-transcode inputs to short mono WAVs, so loading here is cheap. Prints "nan"
when no voiced frames are found.
"""

import sys

import librosa
import numpy as np


def main(paths: list[str]) -> None:
    voiced: list[np.ndarray] = []
    for path in paths:
        audio, sr = librosa.load(path, sr=16000, mono=True)
        if audio.size == 0:
            continue
        f0, _, _ = librosa.pyin(
            audio, fmin=65.0, fmax=1000.0, sr=sr, frame_length=1024
        )
        f0 = f0[np.isfinite(f0)]
        if f0.size:
            voiced.append(f0)
    if voiced:
        print(float(np.median(np.concatenate(voiced))))
    else:
        print("nan")


if __name__ == "__main__":
    main(sys.argv[1:])
