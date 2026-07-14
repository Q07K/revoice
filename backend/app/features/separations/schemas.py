from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.features.separations.models import SeparationStatus


class SeparationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    status: SeparationStatus
    progress: float
    eta_seconds: float | None
    has_vocals: bool
    has_instrumental: bool
    has_dry_vocals: bool
    error: str | None
    created_at: datetime
    finished_at: datetime | None
