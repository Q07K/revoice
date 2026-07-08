from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.features.covers.models import CoverStatus

# 보컬 볼륨 배수 허용 범위 (라우터·재믹싱 공용).
VOCAL_GAIN_MIN = 0.5
VOCAL_GAIN_MAX = 2.5


class WaveformRead(BaseModel):
    peaks: list[float]


class RemixRequest(BaseModel):
    vocal_gain: float = Field(ge=VOCAL_GAIN_MIN, le=VOCAL_GAIN_MAX)


class CoverRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    voice_id: int
    title: str
    transpose: int
    vocal_gain: float
    status: CoverStatus
    progress: float
    eta_seconds: float | None
    error: str | None
    created_at: datetime
    finished_at: datetime | None
