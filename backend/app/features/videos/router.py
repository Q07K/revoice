from typing import Annotated

from fastapi import APIRouter, Depends, Form, UploadFile
from fastapi.responses import FileResponse

from app.features.videos.models import VideoAspect, VideoJob, VideoVisual
from app.features.videos.schemas import VideoRead
from app.features.videos.service import VideoService, get_video_service

router = APIRouter(prefix="/videos", tags=["videos"])

ServiceDep = Annotated[VideoService, Depends(get_video_service)]


@router.post("", response_model=VideoRead, status_code=202)
def create_video(
    service: ServiceDep,
    cover_id: Annotated[int, Form()],
    title: Annotated[str, Form()],
    subtitle: Annotated[str, Form()] = "",
    visual: Annotated[VideoVisual, Form()] = VideoVisual.WAVE,
    aspect: Annotated[VideoAspect, Form()] = VideoAspect.WIDE,
    image: UploadFile | None = None,
) -> VideoJob:
    return service.create(cover_id, title, subtitle, visual, aspect, image)


@router.get("", response_model=list[VideoRead])
def list_videos(service: ServiceDep, cover_id: int | None = None) -> list[VideoJob]:
    return list(service.list_all(cover_id))


@router.get("/{job_id}", response_model=VideoRead)
def get_video(job_id: int, service: ServiceDep) -> VideoJob:
    return service.get(job_id)


@router.delete("/{job_id}", status_code=204)
def delete_video(job_id: int, service: ServiceDep) -> None:
    service.delete(job_id)


@router.get("/{job_id}/download")
def download_video(job_id: int, service: ServiceDep) -> FileResponse:
    path, download_name = service.get_result(job_id)
    return FileResponse(path=path, filename=download_name, media_type="video/mp4")
