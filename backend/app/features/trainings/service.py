import logging
import time
from collections.abc import Sequence
from functools import partial

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal, get_db
from app.core.exceptions import ConflictError, InvalidInputError, NotFoundError
from app.engines.base import CommandCancelled, ProgressCallback, TrainingSpec
from app.engines.factory import get_engine_set
from app.features.trainings import crud
from app.features.trainings.models import TrainingJob, TrainingStatus
from app.features.trainings.schemas import TrainingCreate
from app.features.voices import crud as voices_crud
from app.features.voices.models import VoiceStatus
from app.jobs import cancellation
from app.jobs.runner import JobRunner, get_job_runner
from app.storage.files import get_file_storage

logger = logging.getLogger(__name__)


class TrainingService:
    def __init__(self, db: Session, runner: JobRunner) -> None:
        self._db = db
        self._runner = runner

    def start(self, data: TrainingCreate) -> TrainingJob:
        voice = voices_crud.get_voice(self._db, data.voice_id)
        if voice is None:
            raise NotFoundError(f"Voice {data.voice_id} not found.")
        if voice.status is VoiceStatus.TRAINING:
            raise ConflictError("This voice is already being trained.")
        if not voice.dataset_files:
            raise InvalidInputError("Upload at least one dataset audio file before training.")
        job = crud.create_job(self._db, voice.id, data.epochs)
        voices_crud.set_voice_status(self._db, voice.id, VoiceStatus.TRAINING)
        self._runner.submit(partial(execute_training, job.id))
        return job

    def get(self, job_id: int) -> TrainingJob:
        job = crud.get_job(self._db, job_id)
        if job is None:
            raise NotFoundError(f"Training job {job_id} not found.")
        return job

    def list_all(self, voice_id: int | None = None) -> Sequence[TrainingJob]:
        return crud.list_jobs(self._db, voice_id)

    def cancel(self, job_id: int) -> TrainingJob:
        job = self.get(job_id)
        if job.status not in (TrainingStatus.PENDING, TrainingStatus.RUNNING):
            raise ConflictError("진행 중인 학습만 중단할 수 있어요.")
        cancellation.request_cancel(job_id)
        return job


def execute_training(job_id: int) -> None:
    """Background entrypoint: runs the trainer and persists the outcome."""
    with SessionLocal() as db:
        job = crud.get_job(db, job_id)
        if job is None:
            return
        voice_id = job.voice_id
        spec = _build_spec(voice_id, job.epochs)
        crud.set_running(db, job_id)
    should_cancel = partial(cancellation.is_cancel_requested, job_id)
    try:
        model_path = get_engine_set().trainer.train(
            spec, _progress_writer(job_id), should_cancel
        )
    except CommandCancelled:
        logger.info("Training job %s cancelled by user.", job_id)
        with SessionLocal() as db:
            crud.set_cancelled(db, job_id)
            # Cancelling isn't a failure: keep an earlier trained model usable,
            # otherwise drop back to draft so the voice can be trained again.
            voice = voices_crud.get_voice(db, voice_id)
            settled = (
                VoiceStatus.READY
                if voice is not None and voice.model_path is not None
                else VoiceStatus.DRAFT
            )
            voices_crud.set_voice_status(db, voice_id, settled)
        return
    except Exception as exc:
        logger.exception("Training job %s failed.", job_id)
        with SessionLocal() as db:
            crud.set_failed(db, job_id, str(exc))
            voices_crud.set_voice_status(db, voice_id, VoiceStatus.FAILED)
        return
    finally:
        cancellation.clear(job_id)
    with SessionLocal() as db:
        crud.set_completed(db, job_id)
        voices_crud.set_voice_status(db, voice_id, VoiceStatus.READY, str(model_path))


def _build_spec(voice_id: int, epochs: int) -> TrainingSpec:
    storage = get_file_storage()
    return TrainingSpec(
        dataset_dir=storage.dataset_dir(voice_id),
        output_dir=storage.model_dir(voice_id),
        model_name=f"voice_{voice_id}",
        epochs=epochs,
        sample_rate=get_settings().training_sample_rate,
    )


def _progress_writer(job_id: int) -> ProgressCallback:
    anchor: dict[str, float] = {}

    def write(progress: float) -> None:
        eta_seconds = _estimate_eta(anchor, progress)
        with SessionLocal() as db:
            crud.set_progress(db, job_id, progress, eta_seconds)

    return write


def _estimate_eta(anchor: dict[str, float], progress: float) -> float | None:
    """Linear remaining-time estimate from the rate since the first progress report.

    Early estimates are rough (they include preprocessing time) and converge as
    training advances. Returns None until there is a measurable rate.
    """
    now = time.monotonic()
    if "time" not in anchor:
        anchor["time"] = now
        anchor["progress"] = progress
        return None
    elapsed = now - anchor["time"]
    gained = progress - anchor["progress"]
    if elapsed <= 0 or gained <= 0.001:
        return None
    return (1.0 - progress) * elapsed / gained


def get_training_service(db: Session = Depends(get_db)) -> TrainingService:
    return TrainingService(db=db, runner=get_job_runner())
