from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.features.videos.models import VideoAspect, VideoJob, VideoStatus, VideoVisual


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def create_job(
    db: Session,
    cover_id: int,
    title: str,
    subtitle: str,
    visual: VideoVisual,
    aspect: VideoAspect,
    image_path: str | None,
) -> VideoJob:
    job = VideoJob(
        cover_id=cover_id,
        title=title,
        subtitle=subtitle,
        visual=visual,
        aspect=aspect,
        image_path=image_path,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, job_id: int) -> VideoJob | None:
    return db.get(VideoJob, job_id)


def list_jobs(db: Session, cover_id: int | None = None) -> Sequence[VideoJob]:
    query = select(VideoJob).order_by(VideoJob.id.desc())
    if cover_id is not None:
        query = query.where(VideoJob.cover_id == cover_id)
    return db.scalars(query).all()


def delete_job(db: Session, job: VideoJob) -> None:
    db.delete(job)
    db.commit()


def set_stage(
    db: Session, job_id: int, progress: float, eta_seconds: float | None
) -> None:
    job = db.get(VideoJob, job_id)
    if job is None:
        return
    job.status = VideoStatus.RENDERING
    job.progress = min(max(progress, 0.0), 1.0)
    job.eta_seconds = eta_seconds
    db.commit()


def set_completed(db: Session, job_id: int, result_path: str) -> None:
    job = db.get(VideoJob, job_id)
    if job is None:
        return
    job.status = VideoStatus.COMPLETED
    job.progress = 1.0
    job.eta_seconds = None
    job.result_path = result_path
    job.finished_at = _utcnow()
    db.commit()


def set_failed(db: Session, job_id: int, error: str) -> None:
    job = db.get(VideoJob, job_id)
    if job is None:
        return
    job.status = VideoStatus.FAILED
    job.eta_seconds = None
    job.error = error
    job.finished_at = _utcnow()
    db.commit()


def reset_for_requeue(db: Session, job_id: int) -> None:
    job = db.get(VideoJob, job_id)
    if job is None:
        return
    job.status = VideoStatus.PENDING
    job.progress = 0.0
    job.eta_seconds = None
    job.error = None
    job.result_path = None
    job.finished_at = None
    db.commit()
