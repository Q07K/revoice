from typing import Annotated, Literal

from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import FileResponse

from app.features.separations.models import SeparationJob
from app.features.separations.schemas import SeparationRead
from app.features.separations.service import (
    SeparationService,
    get_separation_service,
)

router = APIRouter(prefix="/separations", tags=["separations"])

ServiceDep = Annotated[SeparationService, Depends(get_separation_service)]


@router.post("", response_model=SeparationRead, status_code=202)
def create_separation(song: UploadFile, service: ServiceDep) -> SeparationJob:
    return service.create(song)


@router.get("", response_model=list[SeparationRead])
def list_separations(service: ServiceDep) -> list[SeparationJob]:
    return list(service.list_all())


@router.get("/{job_id}", response_model=SeparationRead)
def get_separation(job_id: int, service: ServiceDep) -> SeparationJob:
    return service.get(job_id)


@router.delete("/{job_id}", status_code=204)
def delete_separation(job_id: int, service: ServiceDep) -> None:
    service.delete(job_id)


@router.get("/{job_id}/audio")
def download_stem(
    job_id: int,
    service: ServiceDep,
    stem: Literal["vocals", "instrumental", "dry_vocals"] = "vocals",
) -> FileResponse:
    path, download_name = service.get_stem(job_id, stem)
    return FileResponse(path=path, filename=download_name)
