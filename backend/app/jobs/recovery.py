"""Startup recovery: jobs that were running when the server stopped can never
finish (their worker threads died with the process), so re-queue them from the
start. Every job type renders into its own work dir from persisted inputs, so
a fresh run is safe; only jobs whose inputs are gone are marked failed.
"""

import logging
from functools import partial

from sqlalchemy import select

from app.core.database import SessionLocal
from app.features.covers import crud as covers_crud
from app.features.covers.models import CoverJob, CoverStatus
from app.features.separations import crud as separations_crud
from app.features.separations.models import SeparationJob, SeparationStatus
from app.features.trainings import crud as trainings_crud
from app.features.trainings.models import TrainingJob, TrainingStatus
from app.features.videos import crud as videos_crud
from app.features.videos.models import VideoJob, VideoStatus
from app.jobs.runner import get_job_runner

logger = logging.getLogger(__name__)

_ACTIVE_TRAINING = (TrainingStatus.PENDING, TrainingStatus.RUNNING)
_ACTIVE_COVER = (
    CoverStatus.PENDING,
    CoverStatus.SEPARATING,
    CoverStatus.CONVERTING,
    CoverStatus.MIXING,
)
_ACTIVE_SEPARATION = (SeparationStatus.PENDING, SeparationStatus.SEPARATING)
_ACTIVE_VIDEO = (VideoStatus.PENDING, VideoStatus.RENDERING)


def resume_interrupted_jobs() -> None:
    # Imported lazily: the service modules pull in the engine stack, which the
    # crud/model imports above must not depend on at import time.
    from app.features.covers.service import execute_cover
    from app.features.separations.service import execute_separation
    from app.features.trainings.service import execute_training
    from app.features.videos.service import execute_video

    runner = get_job_runner()
    with SessionLocal() as db:
        trainings = db.scalars(
            select(TrainingJob).where(TrainingJob.status.in_(_ACTIVE_TRAINING))
        ).all()
        for job in trainings:
            trainings_crud.reset_for_requeue(db, job.id)
            runner.submit(partial(execute_training, job.id))
            logger.warning("Re-queued interrupted training job %s.", job.id)

        covers = db.scalars(
            select(CoverJob).where(CoverJob.status.in_(_ACTIVE_COVER))
        ).all()
        for cover in covers:
            covers_crud.reset_for_retry(db, cover.id)
            runner.submit(partial(execute_cover, cover.id))
            logger.warning("Re-queued interrupted cover job %s.", cover.id)

        separations = db.scalars(
            select(SeparationJob).where(SeparationJob.status.in_(_ACTIVE_SEPARATION))
        ).all()
        for job in separations:
            separations_crud.reset_for_requeue(db, job.id)
            runner.submit(partial(execute_separation, job.id))
            logger.warning("Re-queued interrupted separation job %s.", job.id)

        videos = db.scalars(
            select(VideoJob).where(VideoJob.status.in_(_ACTIVE_VIDEO))
        ).all()
        for job in videos:
            videos_crud.reset_for_requeue(db, job.id)
            runner.submit(partial(execute_video, job.id))
            logger.warning("Re-queued interrupted video job %s.", job.id)
