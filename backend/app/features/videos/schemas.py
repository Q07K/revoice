from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.features.videos.models import VideoAspect, VideoStatus, VideoVisual


class VideoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cover_id: int
    title: str
    subtitle: str
    visual: VideoVisual
    aspect: VideoAspect
    status: VideoStatus
    progress: float
    eta_seconds: float | None
    error: str | None
    created_at: datetime
    finished_at: datetime | None
