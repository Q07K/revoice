from typing import Annotated

from fastapi import APIRouter, Depends, Form, UploadFile
from fastapi.responses import FileResponse

from app.features.covers.models import CoverJob
from app.features.covers.schemas import CoverRead, WaveformRead
from app.features.covers.service import CoverService, get_cover_service

router = APIRouter(prefix="/covers", tags=["covers"])

ServiceDep = Annotated[CoverService, Depends(get_cover_service)]


@router.post("", response_model=CoverRead, status_code=202)
def create_cover(
    song: UploadFile,
    voice_id: Annotated[int, Form()],
    service: ServiceDep,
    transpose: Annotated[int, Form(ge=-24, le=24)] = 0,
) -> CoverJob:
    return service.create(voice_id, transpose, song)


@router.get("", response_model=list[CoverRead])
def list_covers(service: ServiceDep, voice_id: int | None = None) -> list[CoverJob]:
    return list(service.list_all(voice_id))


@router.get("/{cover_id}", response_model=CoverRead)
def get_cover(cover_id: int, service: ServiceDep) -> CoverJob:
    return service.get(cover_id)


@router.post("/{cover_id}/retry", response_model=CoverRead, status_code=202)
def retry_cover(cover_id: int, service: ServiceDep) -> CoverJob:
    return service.retry(cover_id)


@router.get("/{cover_id}/audio")
def download_cover_audio(cover_id: int, service: ServiceDep) -> FileResponse:
    result_path, download_name = service.get_result(cover_id)
    return FileResponse(path=result_path, filename=download_name)


@router.get("/{cover_id}/waveform", response_model=WaveformRead)
def get_cover_waveform(cover_id: int, service: ServiceDep) -> WaveformRead:
    return WaveformRead(peaks=service.get_waveform(cover_id))
