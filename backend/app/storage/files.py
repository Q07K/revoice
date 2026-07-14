import shutil
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import get_settings


class FileStorage:
    """Filesystem layout for datasets, trained models, songs, and rendered covers."""

    def __init__(self, root: Path) -> None:
        # Engine subprocesses run with a different cwd (e.g. the Applio checkout),
        # so every path handed to them must be absolute.
        self._root = root.resolve()

    def dataset_dir(self, voice_id: int) -> Path:
        return self._ensure(self._root / "datasets" / str(voice_id))

    def model_dir(self, voice_id: int) -> Path:
        return self._ensure(self._root / "models" / str(voice_id))

    def songs_dir(self) -> Path:
        return self._ensure(self._root / "songs")

    def cover_dir(self, cover_id: int) -> Path:
        return self._ensure(self._root / "covers" / str(cover_id))

    def separation_dir(self, job_id: int) -> Path:
        return self._ensure(self._root / "separations" / str(job_id))

    def video_dir(self, job_id: int) -> Path:
        return self._ensure(self._root / "videos" / str(job_id))

    def save_upload(self, upload: UploadFile, target_dir: Path) -> Path:
        suffix = Path(upload.filename or "").suffix.lower()
        destination = target_dir / f"{uuid4().hex}{suffix}"
        with destination.open("wb") as out:
            shutil.copyfileobj(upload.file, out)
        return destination

    def remove_voice_data(self, voice_id: int) -> None:
        shutil.rmtree(self._root / "datasets" / str(voice_id), ignore_errors=True)
        shutil.rmtree(self._root / "models" / str(voice_id), ignore_errors=True)

    def remove_cover_data(self, cover_id: int, song_path: Path | None) -> None:
        shutil.rmtree(self._root / "covers" / str(cover_id), ignore_errors=True)
        if song_path is not None:
            song_path.unlink(missing_ok=True)

    def remove_separation_data(self, job_id: int) -> None:
        shutil.rmtree(self._root / "separations" / str(job_id), ignore_errors=True)

    def remove_video_data(self, job_id: int) -> None:
        shutil.rmtree(self._root / "videos" / str(job_id), ignore_errors=True)

    @staticmethod
    def _ensure(path: Path) -> Path:
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_file_storage() -> FileStorage:
    return FileStorage(root=get_settings().storage_dir)
