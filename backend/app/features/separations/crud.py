from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.features.separations.models import SeparationJob, SeparationStatus


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def create_job(db: Session, title: str, source_path: str) -> SeparationJob:
    job = SeparationJob(title=title, source_path=source_path)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, job_id: int) -> SeparationJob | None:
    return db.get(SeparationJob, job_id)


def list_jobs(db: Session) -> Sequence[SeparationJob]:
    return db.scalars(select(SeparationJob).order_by(SeparationJob.id.desc())).all()


def delete_job(db: Session, job: SeparationJob) -> None:
    db.delete(job)
    db.commit()


def set_stage(
    db: Session, job_id: int, progress: float, eta_seconds: float | None
) -> None:
    job = db.get(SeparationJob, job_id)
    if job is None:
        return
    job.status = SeparationStatus.SEPARATING
    job.progress = min(max(progress, 0.0), 1.0)
    job.eta_seconds = eta_seconds
    db.commit()


def set_completed(
    db: Session,
    job_id: int,
    vocals_path: str,
    instrumental_path: str,
    dry_vocals_path: str | None,
) -> None:
    job = db.get(SeparationJob, job_id)
    if job is None:
        return
    job.status = SeparationStatus.COMPLETED
    job.progress = 1.0
    job.eta_seconds = None
    job.vocals_path = vocals_path
    job.instrumental_path = instrumental_path
    job.dry_vocals_path = dry_vocals_path
    job.finished_at = _utcnow()
    db.commit()


def set_failed(db: Session, job_id: int, error: str) -> None:
    job = db.get(SeparationJob, job_id)
    if job is None:
        return
    job.status = SeparationStatus.FAILED
    job.eta_seconds = None
    job.error = error
    job.finished_at = _utcnow()
    db.commit()


def reset_for_requeue(db: Session, job_id: int) -> None:
    job = db.get(SeparationJob, job_id)
    if job is None:
        return
    job.status = SeparationStatus.PENDING
    job.progress = 0.0
    job.eta_seconds = None
    job.error = None
    job.vocals_path = None
    job.instrumental_path = None
    job.dry_vocals_path = None
    job.finished_at = None
    db.commit()
