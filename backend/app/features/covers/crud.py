from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.features.covers.models import CoverJob, CoverStatus


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def create_cover(
    db: Session,
    voice_id: int,
    title: str,
    song_path: str,
    transpose: int,
    vocal_gain: float,
) -> CoverJob:
    cover = CoverJob(
        voice_id=voice_id,
        title=title,
        song_path=song_path,
        transpose=transpose,
        vocal_gain=vocal_gain,
    )
    db.add(cover)
    db.commit()
    db.refresh(cover)
    return cover


def set_vocal_gain(db: Session, cover_id: int, vocal_gain: float) -> None:
    cover = db.get(CoverJob, cover_id)
    if cover is None:
        return
    cover.vocal_gain = vocal_gain
    db.commit()


def delete_cover(db: Session, cover: CoverJob) -> None:
    db.delete(cover)
    db.commit()


def get_cover(db: Session, cover_id: int) -> CoverJob | None:
    return db.get(CoverJob, cover_id)


def list_covers(db: Session, voice_id: int | None = None) -> Sequence[CoverJob]:
    query = select(CoverJob).order_by(CoverJob.id.desc())
    if voice_id is not None:
        query = query.where(CoverJob.voice_id == voice_id)
    return db.scalars(query).all()


def set_stage(
    db: Session,
    cover_id: int,
    status: CoverStatus,
    progress: float,
    eta_seconds: float | None,
) -> None:
    cover = db.get(CoverJob, cover_id)
    if cover is None:
        return
    cover.status = status
    cover.progress = min(max(progress, 0.0), 1.0)
    cover.eta_seconds = eta_seconds
    db.commit()


def set_completed(db: Session, cover_id: int, result_path: str) -> None:
    cover = db.get(CoverJob, cover_id)
    if cover is None:
        return
    cover.status = CoverStatus.COMPLETED
    cover.progress = 1.0
    cover.eta_seconds = None
    cover.result_path = result_path
    cover.finished_at = _utcnow()
    db.commit()


def set_failed(db: Session, cover_id: int, error: str) -> None:
    cover = db.get(CoverJob, cover_id)
    if cover is None:
        return
    cover.status = CoverStatus.FAILED
    cover.eta_seconds = None
    cover.error = error
    cover.finished_at = _utcnow()
    db.commit()


def reset_for_retry(db: Session, cover_id: int) -> None:
    cover = db.get(CoverJob, cover_id)
    if cover is None:
        return
    cover.status = CoverStatus.PENDING
    cover.progress = 0.0
    cover.eta_seconds = None
    cover.error = None
    cover.result_path = None
    cover.finished_at = None
    db.commit()
