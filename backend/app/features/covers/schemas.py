from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.features.covers.models import CoverStatus


class WaveformRead(BaseModel):
    peaks: list[float]


class CoverRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    voice_id: int
    title: str
    transpose: int
    status: CoverStatus
    progress: float
    eta_seconds: float | None
    error: str | None
    created_at: datetime
    finished_at: datetime | None
