import logging
import threading
import time
from collections.abc import Sequence
from functools import partial
from pathlib import Path
from types import TracebackType

from fastapi import Depends, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal, get_db
from app.core.exceptions import ConflictError, NotFoundError
from app.engines.base import audio_duration_seconds
from app.engines.factory import get_engine_set
from app.features.separations import crud
from app.features.separations.models import SeparationJob, SeparationStatus
from app.features.voices.service import validate_audio_filename
from app.jobs.runner import JobRunner, get_job_runner
from app.storage.files import FileStorage, get_file_storage

logger = logging.getLogger(__name__)

_IN_PROGRESS = frozenset({SeparationStatus.PENDING, SeparationStatus.SEPARATING})
_STAGE_OVERHEAD_S = 20.0
_TICK_INTERVAL_S = 2.0


class SeparationService:
    def __init__(self, db: Session, storage: FileStorage, runner: JobRunner) -> None:
        self._db = db
        self._storage = storage
        self._runner = runner

    def create(self, song: UploadFile) -> SeparationJob:
        title = validate_audio_filename(song.filename)
        # Create the row first so the upload can live under the job's own dir,
        # keeping every file for a job together for a clean delete.
        job = crud.create_job(self._db, title, "")
        source = self._storage.save_upload(song, self._storage.separation_dir(job.id))
        job.source_path = str(source)
        self._db.commit()
        self._db.refresh(job)
        self._runner.submit(partial(execute_separation, job.id))
        return job

    def get(self, job_id: int) -> SeparationJob:
        job = crud.get_job(self._db, job_id)
        if job is None:
            raise NotFoundError(f"Separation {job_id} not found.")
        return job

    def list_all(self) -> Sequence[SeparationJob]:
        return crud.list_jobs(self._db)

    def delete(self, job_id: int) -> None:
        job = self.get(job_id)
        if job.status in _IN_PROGRESS:
            raise ConflictError("진행 중인 작업은 삭제할 수 없어요. 완료되면 삭제해주세요.")
        self._storage.remove_separation_data(job_id)
        crud.delete_job(self._db, job)

    def get_stem(self, job_id: int, stem: str) -> tuple[Path, str]:
        """Return (file path, download filename) for the requested stem."""
        job = self.get(job_id)
        if job.status is not SeparationStatus.COMPLETED:
            raise ConflictError("분리가 아직 끝나지 않았어요.")
        path_str, label = {
            "vocals": (job.vocals_path, "보컬"),
            "instrumental": (job.instrumental_path, "반주"),
            "dry_vocals": (job.dry_vocals_path, "보컬_리버브제거"),
        }[stem]
        if path_str is None or not Path(path_str).exists():
            raise NotFoundError("요청한 트랙이 없어요.")
        download_name = f"{Path(job.title).stem}_{label}{Path(path_str).suffix}"
        return Path(path_str), download_name


class _ProgressTicker:
    """audio-separator emits no parseable progress on the pipe, so advance a
    time-based estimate in a background thread (same approach as covers)."""

    def __init__(self, job_id: int, estimate_seconds: float | None) -> None:
        self._job_id = job_id
        self._estimate = estimate_seconds
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def __enter__(self) -> "_ProgressTicker":
        _set_stage(self._job_id, 0.02, self._estimate)
        self._thread.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._stop.set()
        self._thread.join(timeout=_TICK_INTERVAL_S * 3)

    def _run(self) -> None:
        estimate = self._estimate
        if estimate is None or estimate <= 0:
            return
        started = time.monotonic()
        while not self._stop.wait(_TICK_INTERVAL_S):
            elapsed = time.monotonic() - started
            fraction = min(elapsed / estimate, 0.97)
            eta = max(estimate - elapsed, 2.0)
            _set_stage(self._job_id, 0.02 + 0.96 * fraction, eta)


def execute_separation(job_id: int) -> None:
    """Background entrypoint: split the source into vocals + instrumental, then
    strip reverb from the vocal for a third, dry stem (dataset-ready)."""
    with SessionLocal() as db:
        job = crud.get_job(db, job_id)
        if job is None:
            return
        source = Path(job.source_path)
    work_dir = get_file_storage().separation_dir(job_id)
    engines = get_engine_set()
    estimate = _estimate_seconds(source)
    if estimate is not None and engines.dereverber is not None:
        # The de-reverb pass is a second separator-grade model over the vocal.
        estimate *= 2
    dry_vocals: Path | None = None
    try:
        with _ProgressTicker(job_id, estimate):
            result = engines.separator.separate(source, work_dir, _ignore_progress)
            if engines.dereverber is not None:
                try:
                    dry_vocals = engines.dereverber.dereverb(result.vocals, work_dir)
                except Exception:  # noqa: BLE001 - 2-스템 결과만으로도 완료 처리
                    logger.exception("De-reverb failed for separation %s.", job_id)
    except Exception as exc:  # noqa: BLE001 - surfaced to the user via the job row
        logger.exception("Separation job %s failed.", job_id)
        with SessionLocal() as db:
            crud.set_failed(db, job_id, str(exc))
        return
    with SessionLocal() as db:
        crud.set_completed(
            db,
            job_id,
            str(result.vocals),
            str(result.instrumental),
            None if dry_vocals is None else str(dry_vocals),
        )


def _estimate_seconds(source: Path) -> float | None:
    duration = audio_duration_seconds(source)
    if duration is None:
        return None
    return _STAGE_OVERHEAD_S + duration * get_settings().separation_speed_factor


def _ignore_progress(progress: float) -> None:
    """Progress is time-estimated by _ProgressTicker instead."""


def _set_stage(job_id: int, progress: float, eta_seconds: float | None) -> None:
    with SessionLocal() as db:
        crud.set_stage(db, job_id, progress, eta_seconds)


def get_separation_service(db: Session = Depends(get_db)) -> SeparationService:
    return SeparationService(db=db, storage=get_file_storage(), runner=get_job_runner())
