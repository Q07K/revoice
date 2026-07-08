from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.features.trainings.models import TrainingStatus


class TrainingCreate(BaseModel):
    voice_id: int
    # RVC v2는 과적합이 빠르다. 개발자 권장 상한이 ~200이고 데이터가 많을수록
    # 더 일찍 과적합하므로, 소량 데이터 기준 안전한 100을 기본값으로 둔다.
    epochs: int = Field(default=100, ge=1, le=500)


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
