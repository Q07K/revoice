from typing import Annotated

from fastapi import APIRouter, Depends

from app.features.trainings.models import TrainingJob
from app.features.trainings.schemas import TrainingCreate, TrainingRead
from app.features.trainings.service import TrainingService, get_training_service

router = APIRouter(prefix="/trainings", tags=["trainings"])

ServiceDep = Annotated[TrainingService, Depends(get_training_service)]


@router.post("", response_model=TrainingRead, status_code=202)
def start_training(data: TrainingCreate, service: ServiceDep) -> TrainingJob:
    return service.start(data)


@router.get("", response_model=list[TrainingRead])
def list_trainings(service: ServiceDep, voice_id: int | None = None) -> list[TrainingJob]:
    return list(service.list_all(voice_id))


@router.get("/{job_id}", response_model=TrainingRead)
def get_training(job_id: int, service: ServiceDep) -> TrainingJob:
    return service.get(job_id)


@router.post("/{job_id}/cancel", response_model=TrainingRead, status_code=202)
def cancel_training(job_id: int, service: ServiceDep) -> TrainingJob:
    return service.cancel(job_id)
