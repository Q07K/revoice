from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile

from app.features.voices.models import DatasetFile, Voice
from app.features.voices.schemas import (
    DatasetFileRead,
    VoiceCreate,
    VoiceDetail,
    VoiceRead,
    VoiceUpdate,
)
from app.features.voices.service import VoiceService, get_voice_service

router = APIRouter(prefix="/voices", tags=["voices"])

ServiceDep = Annotated[VoiceService, Depends(get_voice_service)]


@router.post("", response_model=VoiceRead, status_code=201)
def create_voice(data: VoiceCreate, service: ServiceDep) -> Voice:
    return service.create(data)


@router.get("", response_model=list[VoiceRead])
def list_voices(service: ServiceDep) -> list[Voice]:
    return list(service.list_all())


@router.get("/{voice_id}", response_model=VoiceDetail)
def get_voice(voice_id: int, service: ServiceDep) -> Voice:
    return service.get(voice_id)


@router.patch("/{voice_id}", response_model=VoiceRead)
def update_voice(voice_id: int, data: VoiceUpdate, service: ServiceDep) -> Voice:
    return service.update(voice_id, data)


@router.delete("/{voice_id}", status_code=204)
def delete_voice(voice_id: int, service: ServiceDep) -> None:
    service.delete(voice_id)


@router.post("/{voice_id}/dataset", response_model=list[DatasetFileRead], status_code=201)
def upload_dataset_files(
    voice_id: int, files: list[UploadFile], service: ServiceDep
) -> list[DatasetFile]:
    return service.add_dataset_files(voice_id, files)
