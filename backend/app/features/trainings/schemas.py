from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.features.trainings.models import TrainingStatus


class TrainingCreate(BaseModel):
    voice_id: int
    epochs: int = Field(default=200, ge=1, le=2000)


class TrainingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    voice_id: int
    status: TrainingStatus
    epochs: int
    progress: float
    eta_seconds: float | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
