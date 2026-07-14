from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.features.covers.models import CoverStatus

# 보컬 볼륨 배수 허용 범위 (라우터·재믹싱 공용).
VOCAL_GAIN_MIN = 0.5
VOCAL_GAIN_MAX = 2.5

# RVC 추론 품질 옵션 허용 범위 + 기본값 (Applio infer 규약 기준).
INDEX_RATE_MIN, INDEX_RATE_MAX, INDEX_RATE_DEFAULT = 0.0, 1.0, 0.5
PROTECT_MIN, PROTECT_MAX, PROTECT_DEFAULT = 0.0, 0.5, 0.33
VOLUME_ENVELOPE_MIN, VOLUME_ENVELOPE_MAX, VOLUME_ENVELOPE_DEFAULT = 0.0, 1.0, 1.0


class WaveformRead(BaseModel):
    peaks: list[float]


class RemixRequest(BaseModel):
    vocal_gain: float = Field(ge=VOCAL_GAIN_MIN, le=VOCAL_GAIN_MAX)


class BatchDeleteRequest(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=500)


class BatchDeleteResult(BaseModel):
    deleted: int
    # 진행 중이거나 이미 없는 커버는 건너뛴다.
    skipped: int


class CoverRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    voice_id: int
    title: str
    transpose: int
    auto_transpose: bool
    vocal_gain: float
    index_rate: float
    protect: float
    volume_envelope: float
    status: CoverStatus
    progress: float
    eta_seconds: float | None
    error: str | None
    created_at: datetime
    finished_at: datetime | None
