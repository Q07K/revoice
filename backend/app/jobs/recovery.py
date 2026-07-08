"""Startup recovery: jobs that were running when the server stopped can never
finish (their worker threads died with the process), so mark them failed and
settle the owning voice's status.
"""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.features.covers import crud as covers_crud
from app.features.covers.models import CoverJob, CoverStatus
from app.features.trainings import crud as trainings_crud
from app.features.trainings.models import TrainingJob, TrainingStatus
from app.features.voices import crud as voices_crud
from app.features.voices.models import VoiceStatus

logger = logging.getLogger(__name__)

_INTERRUPTED_MESSAGE = "서버가 재시작되어 작업이 중단됐어요. 다시 시작해주세요."

_ACTIVE_TRAINING = (TrainingStatus.PENDING, TrainingStatus.RUNNING)
_ACTIVE_COVER = (
    CoverStatus.PENDING,
    CoverStatus.SEPARATING,
    CoverStatus.CONVERTING,
    CoverStatus.MIXING,
)


def fail_interrupted_jobs() -> None:
    with SessionLocal() as db:
        trainings = db.scalars(
            select(TrainingJob).where(TrainingJob.status.in_(_ACTIVE_TRAINING))
        ).all()
        for job in trainings:
            trainings_crud.set_failed(db, job.id, _INTERRUPTED_MESSAGE)
            _settle_voice_status(db, job.voice_id)
            logger.warning("Marked interrupted training job %s as failed.", job.id)

        covers = db.scalars(
            select(CoverJob).where(CoverJob.status.in_(_ACTIVE_COVER))
        ).all()
        for cover in covers:
            covers_crud.set_failed(db, cover.id, _INTERRUPTED_MESSAGE)
            logger.warning("Marked interrupted cover job %s as failed.", cover.id)


def _settle_voice_status(db: Session, voice_id: int) -> None:
    voice = voices_crud.get_voice(db, voice_id)
    if voice is None:
        return
    # A voice that finished an earlier training still has a usable model.
    status = VoiceStatus.READY if voice.model_path is not None else VoiceStatus.FAILED
    voices_crud.set_voice_status(db, voice_id, status)
