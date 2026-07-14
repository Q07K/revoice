import logging
import shutil
import tempfile
import threading
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import replace
from functools import partial
from pathlib import Path

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal, get_db
from app.core.exceptions import ConflictError, InvalidInputError, NotFoundError
from app.engines.base import (
    CancelCheck,
    CommandCancelled,
    ProgressCallback,
    TrainingSpec,
    audio_duration_seconds,
)
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


# Progress slice reserved for dataset cleanup before the trainer's own budget
# (which is rescaled into the remaining 8~100%). The frontend stage bar mirrors
# these boundaries (TrainingProgress.tsx).
_CLEANUP_END = 0.08


def execute_training(job_id: int) -> None:
    """Background entrypoint: cleans the dataset, runs the trainer, and
    persists the outcome (including the voice register for auto key)."""
    with SessionLocal() as db:
        job = crud.get_job(db, job_id)
        if job is None:
            return
        voice_id = job.voice_id
        spec = _build_spec(voice_id, job.epochs)
        crud.set_running(db, job_id)
    should_cancel = partial(cancellation.is_cancel_requested, job_id)
    write_progress = _progress_writer(job_id)

    def trainer_progress(progress: float) -> None:
        write_progress(_CLEANUP_END + (1.0 - _CLEANUP_END) * progress)

    try:
        with tempfile.TemporaryDirectory(prefix="revoice_clean_") as staging:
            if get_settings().training_dataset_cleanup:
                cleaned_dir = _clean_dataset(
                    spec.dataset_dir, Path(staging), write_progress, should_cancel
                )
                spec = replace(spec, dataset_dir=cleaned_dir)
            write_progress(_CLEANUP_END)
            model_path = get_engine_set().trainer.train(
                spec, trainer_progress, should_cancel
            )
            # The cleaned vocals are the best material to measure the voice
            # register (auto key matching) from — raw uploads may carry BGM.
            median_f0 = get_engine_set().pitch_analyzer.median_f0(
                [path for path in sorted(spec.dataset_dir.iterdir()) if path.is_file()]
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
        if median_f0 is not None:
            voices_crud.set_median_f0(db, voice_id, median_f0)


@contextmanager
def _ticking(
    on_progress: ProgressCallback, start: float, end: float, estimate_seconds: float
) -> Iterator[None]:
    """Advance progress by elapsed/estimate while a silent external tool runs
    (audio-separator prints nothing parseable on pipes), capped just short of
    the slice end so the bar never claims a step it hasn't finished."""
    stop = threading.Event()

    def run() -> None:
        began = time.monotonic()
        while not stop.wait(2.0):
            fraction = min((time.monotonic() - began) / estimate_seconds, 0.97)
            on_progress(start + (end - start) * fraction)

    thread = threading.Thread(target=run, daemon=True)
    if estimate_seconds > 0:
        thread.start()
    try:
        yield
    finally:
        stop.set()
        if thread.is_alive():
            thread.join(timeout=6.0)


# Cleanup runs two separator-grade passes per file (vocals + de-reverb), plus
# per-invocation model-load overhead.
_CLEANUP_OVERHEAD_S = 20.0
_FALLBACK_DURATION_S = 240.0


def _clean_dataset(
    dataset_dir: Path,
    staging_dir: Path,
    on_progress: ProgressCallback,
    should_cancel: CancelCheck,
) -> Path:
    """Run each dataset file through vocal separation (+ de-reverb) so training
    sees dry, accompaniment-free vocals even when the user uploaded karaoke or
    phone recordings with background music.

    A file whose cleanup fails is used as-is — training on raw audio beats
    failing the whole job. Returns the directory the trainer should read.
    """
    engines = get_engine_set()
    files = [path for path in sorted(dataset_dir.iterdir()) if path.is_file()]
    cleaned = staging_dir / "cleaned"
    cleaned.mkdir(parents=True, exist_ok=True)
    passes = 1 if engines.dereverber is None else 2
    durations = [audio_duration_seconds(path) or _FALLBACK_DURATION_S for path in files]
    total_duration = sum(durations) or 1.0
    completed = 0.0
    for position, (path, duration) in enumerate(zip(files, durations)):
        if should_cancel():
            raise CommandCancelled()
        slice_start = _CLEANUP_END * completed / total_duration
        slice_end = _CLEANUP_END * (completed + duration) / total_duration
        estimate = (
            _CLEANUP_OVERHEAD_S * passes
            + duration * get_settings().separation_speed_factor * passes
        )
        work = staging_dir / f"work_{position}"
        with _ticking(on_progress, slice_start, slice_end, estimate):
            try:
                separated = engines.separator.separate(path, work, _ignore_progress)
                vocals = separated.vocals
                if engines.dereverber is not None:
                    vocals = engines.dereverber.dereverb(vocals, work)
                shutil.copyfile(vocals, cleaned / f"{path.stem}_clean.wav")
            except Exception:  # noqa: BLE001 — per-file fallback, never fail the job here
                logger.exception("Dataset cleanup failed for %s; using the raw file.", path)
                shutil.copyfile(path, cleaned / path.name)
        # Free the stems as we go: datasets can be long and disk-heavy.
        shutil.rmtree(work, ignore_errors=True)
        completed += duration
        on_progress(slice_end)
    return cleaned


def _ignore_progress(progress: float) -> None:
    """Cleanup progress advances per file instead."""


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
