import logging
import threading
import time
from collections.abc import Sequence
from functools import partial
from pathlib import Path
from types import TracebackType

from fastapi import Depends, UploadFile
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.exceptions import ConflictError, NotFoundError
from app.engines.base import VideoSpec, audio_duration_seconds
from app.engines.factory import get_engine_set
from app.features.covers import crud as covers_crud
from app.features.covers.models import CoverStatus
from app.features.videos import crud
from app.features.videos.models import VideoAspect, VideoJob, VideoStatus, VideoVisual
from app.jobs.runner import JobRunner, get_job_runner
from app.storage.files import FileStorage, get_file_storage

logger = logging.getLogger(__name__)

_IN_PROGRESS = frozenset({VideoStatus.PENDING, VideoStatus.RENDERING})
_OVERHEAD_S = 10.0
_RENDER_FACTOR = 0.6  # ffmpeg render time ≈ this × audio seconds (rough)
_TICK_INTERVAL_S = 1.5
_IMAGE_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".webp"})


class VideoService:
    def __init__(self, db: Session, storage: FileStorage, runner: JobRunner) -> None:
        self._db = db
        self._storage = storage
        self._runner = runner

    def create(
        self,
        cover_id: int,
        title: str,
        subtitle: str,
        visual: VideoVisual,
        aspect: VideoAspect,
        image: UploadFile | None,
    ) -> VideoJob:
        cover = covers_crud.get_cover(self._db, cover_id)
        if cover is None:
            raise NotFoundError(f"Cover {cover_id} not found.")
        if cover.status is not CoverStatus.COMPLETED or cover.result_path is None:
            raise ConflictError("완성된 커버만 영상으로 만들 수 있어요.")

        job = crud.create_job(self._db, cover_id, title, subtitle, visual, aspect, None)
        image_path: str | None = None
        if image is not None and image.filename:
            suffix = Path(image.filename).suffix.lower()
            if suffix not in _IMAGE_SUFFIXES:
                allowed = ", ".join(sorted(_IMAGE_SUFFIXES))
                raise ConflictError(f"지원하지 않는 이미지 형식이에요. 허용: {allowed}")
            saved = self._storage.save_upload(image, self._storage.video_dir(job.id))
            image_path = str(saved)
            job.image_path = image_path
            self._db.commit()
            self._db.refresh(job)
        self._runner.submit(partial(execute_video, job.id))
        return job

    def get(self, job_id: int) -> VideoJob:
        job = crud.get_job(self._db, job_id)
        if job is None:
            raise NotFoundError(f"Video {job_id} not found.")
        return job

    def list_all(self, cover_id: int | None = None) -> Sequence[VideoJob]:
        return crud.list_jobs(self._db, cover_id)

    def delete(self, job_id: int) -> None:
        job = self.get(job_id)
        if job.status in _IN_PROGRESS:
            raise ConflictError("렌더링 중인 영상은 삭제할 수 없어요. 완료되면 삭제해주세요.")
        self._storage.remove_video_data(job_id)
        crud.delete_job(self._db, job)

    def get_result(self, job_id: int) -> tuple[Path, str]:
        job = self.get(job_id)
        if job.status is not VideoStatus.COMPLETED or job.result_path is None:
            raise ConflictError("영상 렌더링이 아직 끝나지 않았어요.")
        download_name = f"{Path(job.title).stem or 'revoice'}_cover.mp4"
        return Path(job.result_path), download_name


class _ProgressTicker:
    """ffmpeg emits progress on the pipe, but we run it via run_command (no
    stream), so advance a time-based estimate like the other silent stages."""

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
            _set_stage(self._job_id, 0.02 + 0.96 * fraction, max(estimate - elapsed, 2.0))


def execute_video(job_id: int) -> None:
    """Background entrypoint: render the cover's audio into an mp4."""
    with SessionLocal() as db:
        job = crud.get_job(db, job_id)
        if job is None:
            return
        cover = covers_crud.get_cover(db, job.cover_id)
        if cover is None or cover.result_path is None:
            crud.set_failed(db, job_id, "커버 오디오를 찾을 수 없어요.")
            return
        audio_path = Path(cover.result_path)
        spec = VideoSpec(
            audio_path=audio_path,
            output_path=get_file_storage().video_dir(job_id) / "video.mp4",
            aspect=job.aspect.value,
            visual=job.visual.value,
            image_path=Path(job.image_path) if job.image_path else None,
            title=job.title,
            subtitle=job.subtitle,
        )
    estimate = _estimate_seconds(audio_path)
    try:
        with _ProgressTicker(job_id, estimate):
            result = get_engine_set().video_renderer.render(spec)
    except Exception as exc:  # noqa: BLE001 - surfaced to the user via the job row
        logger.exception("Video job %s failed.", job_id)
        with SessionLocal() as db:
            crud.set_failed(db, job_id, str(exc))
        return
    with SessionLocal() as db:
        crud.set_completed(db, job_id, str(result))


def _estimate_seconds(audio_path: Path) -> float | None:
    duration = audio_duration_seconds(audio_path)
    if duration is None:
        return None
    return _OVERHEAD_S + duration * _RENDER_FACTOR


def _set_stage(job_id: int, progress: float, eta_seconds: float | None) -> None:
    with SessionLocal() as db:
        crud.set_stage(db, job_id, progress, eta_seconds)


def get_video_service(db: Session = Depends(get_db)) -> VideoService:
    return VideoService(db=db, storage=get_file_storage(), runner=get_job_runner())
