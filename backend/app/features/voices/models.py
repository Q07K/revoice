from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class VoiceStatus(StrEnum):
    DRAFT = "draft"
    TRAINING = "training"
    READY = "ready"
    FAILED = "failed"


class Voice(Base):
    __tablename__ = "voices"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[VoiceStatus] = mapped_column(
        Enum(VoiceStatus, native_enum=False, length=20), default=VoiceStatus.DRAFT
    )
    model_path: Mapped[str | None] = mapped_column(String(500), default=None)
    # 데이터셋에서 측정한 목소리 음역(유성음 f0 중앙값, Hz). 커버 자동 키 매칭에
    # 사용하며, 첫 자동 키 커버 때 계산해 캐시한다.
    median_f0_hz: Mapped[float | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    dataset_files: Mapped[list["DatasetFile"]] = relationship(
        back_populates="voice", cascade="all, delete-orphan"
    )


class DatasetFile(Base):
    __tablename__ = "dataset_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    voice_id: Mapped[int] = mapped_column(
        ForeignKey("voices.id", ondelete="CASCADE"), index=True
    )
    original_name: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(500))
    size_bytes: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    voice: Mapped[Voice] = relationship(back_populates="dataset_files")
