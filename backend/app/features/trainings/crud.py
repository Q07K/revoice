from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.features.trainings.models import TrainingJob, TrainingStatus


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def create_job(db: Session, voice_id: int, epochs: int) -> TrainingJob:
    job = TrainingJob(voice_id=voice_id, epochs=epochs)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, job_id: int) -> TrainingJob | None:
    return db.get(TrainingJob, job_id)


def list_jobs(db: Session, voice_id: int | None = None) -> Sequence[TrainingJob]:
    query = select(TrainingJob).order_by(TrainingJob.id.desc())
    if voice_id is not None:
        query = query.where(TrainingJob.voice_id == voice_id)
    return db.scalars(query).all()


def set_running(db: Session, job_id: int) -> None:
    job = db.get(TrainingJob, job_id)
    if job is None:
        return
    job.status = TrainingStatus.RUNNING
    job.started_at = _utcnow()
    db.commit()


def set_progress(
    db: Session, job_id: int, progress: float, eta_seconds: float | None
) -> None:
    job = db.get(TrainingJob, job_id)
    if job is None:
        return
    job.progress = min(max(progress, 0.0), 1.0)
    job.eta_seconds = eta_seconds
    db.commit()


def set_completed(db: Session, job_id: int) -> None:
    job = db.get(TrainingJob, job_id)
    if job is None:
        return
    job.status = TrainingStatus.COMPLETED
    job.progress = 1.0
    job.eta_seconds = None
    job.finished_at = _utcnow()
    db.commit()


def set_failed(db: Session, job_id: int, error: str) -> None:
    job = db.get(TrainingJob, job_id)
    if job is None:
        return
    job.status = TrainingStatus.FAILED
    job.error = error
    job.eta_seconds = None
    job.finished_at = _utcnow()
    db.commit()


def set_cancelled(db: Session, job_id: int) -> None:
    job = db.get(TrainingJob, job_id)
    if job is None:
        return
    job.status = TrainingStatus.CANCELLED
    job.eta_seconds = None
    job.finished_at = _utcnow()
    db.commit()


def reset_for_requeue(db: Session, job_id: int) -> None:
    job = db.get(TrainingJob, job_id)
    if job is None:
        return
    job.status = TrainingStatus.PENDING
    job.progress = 0.0
    job.eta_seconds = None
    job.error = None
    job.started_at = None
    job.finished_at = None
    db.commit()
