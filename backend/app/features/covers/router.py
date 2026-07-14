from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Form, UploadFile
from fastapi.responses import FileResponse

from app.features.covers.models import CoverJob
from app.features.covers.schemas import (
    INDEX_RATE_DEFAULT,
    INDEX_RATE_MAX,
    INDEX_RATE_MIN,
    PROTECT_DEFAULT,
    PROTECT_MAX,
    PROTECT_MIN,
    VOCAL_GAIN_MAX,
    VOCAL_GAIN_MIN,
    VOLUME_ENVELOPE_DEFAULT,
    VOLUME_ENVELOPE_MAX,
    VOLUME_ENVELOPE_MIN,
    BatchDeleteRequest,
    BatchDeleteResult,
    CoverRead,
    RemixRequest,
    WaveformRead,
)
from app.features.covers.service import CoverService, get_cover_service

router = APIRouter(prefix="/covers", tags=["covers"])

ServiceDep = Annotated[CoverService, Depends(get_cover_service)]


@router.post("", response_model=CoverRead, status_code=202)
def create_cover(
    song: UploadFile,
    voice_id: Annotated[int, Form()],
    service: ServiceDep,
    transpose: Annotated[int, Form(ge=-24, le=24)] = 0,
    auto_transpose: Annotated[bool, Form()] = False,
    vocal_gain: Annotated[float, Form(ge=VOCAL_GAIN_MIN, le=VOCAL_GAIN_MAX)] = 1.5,
    index_rate: Annotated[
        float, Form(ge=INDEX_RATE_MIN, le=INDEX_RATE_MAX)
    ] = INDEX_RATE_DEFAULT,
    protect: Annotated[float, Form(ge=PROTECT_MIN, le=PROTECT_MAX)] = PROTECT_DEFAULT,
    volume_envelope: Annotated[
        float, Form(ge=VOLUME_ENVELOPE_MIN, le=VOLUME_ENVELOPE_MAX)
    ] = VOLUME_ENVELOPE_DEFAULT,
) -> CoverJob:
    return service.create(
        voice_id, transpose, auto_transpose, vocal_gain, index_rate, protect, volume_envelope, song
    )


@router.get("", response_model=list[CoverRead])
def list_covers(service: ServiceDep, voice_id: int | None = None) -> list[CoverJob]:
    return list(service.list_all(voice_id))


@router.get("/{cover_id}", response_model=CoverRead)
def get_cover(cover_id: int, service: ServiceDep) -> CoverJob:
    return service.get(cover_id)


@router.delete("/{cover_id}", status_code=204)
def delete_cover(cover_id: int, service: ServiceDep) -> None:
    service.delete(cover_id)


@router.post("/batch-delete", response_model=BatchDeleteResult)
def batch_delete_covers(body: BatchDeleteRequest, service: ServiceDep) -> BatchDeleteResult:
    deleted, skipped = service.delete_many(body.ids)
    return BatchDeleteResult(deleted=deleted, skipped=skipped)


@router.post("/{cover_id}/retry", response_model=CoverRead, status_code=202)
def retry_cover(cover_id: int, service: ServiceDep) -> CoverJob:
    return service.retry(cover_id)


@router.post("/{cover_id}/remix", response_model=CoverRead)
def remix_cover(cover_id: int, body: RemixRequest, service: ServiceDep) -> CoverJob:
    return service.remix(cover_id, body.vocal_gain)


@router.get("/{cover_id}/audio")
def download_cover_audio(cover_id: int, service: ServiceDep) -> FileResponse:
    result_path, download_name = service.get_result(cover_id)
    return FileResponse(path=result_path, filename=download_name)


@router.get("/{cover_id}/export.mp3")
def export_cover_mp3(cover_id: int, service: ServiceDep) -> FileResponse:
    path, download_name = service.get_export(cover_id)
    return FileResponse(path=path, filename=download_name)


@router.get("/{cover_id}/stems/{kind}/audio")
def get_cover_stem(
    cover_id: int,
    kind: Literal["vocal", "instrumental"],
    service: ServiceDep,
) -> FileResponse:
    path = service.get_stem(cover_id, kind)
    return FileResponse(path=path, media_type="audio/wav")


@router.get("/{cover_id}/waveform", response_model=WaveformRead)
def get_cover_waveform(cover_id: int, service: ServiceDep) -> WaveformRead:
    return WaveformRead(peaks=service.get_waveform(cover_id))
