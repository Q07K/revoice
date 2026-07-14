from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CoverStatus(StrEnum):
    PENDING = "pending"
    SEPARATING = "separating"
    CONVERTING = "converting"
    MIXING = "mixing"
    COMPLETED = "completed"
    FAILED = "failed"


class CoverJob(Base):
    __tablename__ = "cover_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    voice_id: Mapped[int] = mapped_column(
        ForeignKey("voices.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    song_path: Mapped[str] = mapped_column(String(500))
    transpose: Mapped[int] = mapped_column(default=0)
    # 키 자동 매칭 여부. True면 잡 실행 중 계산된 옥타브 시프트가 transpose에
    # 기록된다 (완료 후 transpose = 실제 적용된 키).
    auto_transpose: Mapped[bool] = mapped_column(default=False)
    # 반주 대비 변환 보컬의 볼륨 배수 (1.0 = 원본, >1 = 보컬 강조).
    vocal_gain: Mapped[float] = mapped_column(default=1.5)
    # RVC 추론 품질 옵션 (커버 생성 시 고정, 표시/재현용으로 저장).
    index_rate: Mapped[float] = mapped_column(default=0.5)
    protect: Mapped[float] = mapped_column(default=0.33)
    volume_envelope: Mapped[float] = mapped_column(default=1.0)
    status: Mapped[CoverStatus] = mapped_column(
        Enum(CoverStatus, native_enum=False, length=20), default=CoverStatus.PENDING
    )
    progress: Mapped[float] = mapped_column(default=0.0)
    eta_seconds: Mapped[float | None] = mapped_column(default=None)
    error: Mapped[str | None] = mapped_column(Text, default=None)
    result_path: Mapped[str | None] = mapped_column(String(500), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
