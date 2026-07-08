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
    status: Mapped[CoverStatus] = mapped_column(
        Enum(CoverStatus, native_enum=False, length=20), default=CoverStatus.PENDING
    )
    progress: Mapped[float] = mapped_column(default=0.0)
    eta_seconds: Mapped[float | None] = mapped_column(default=None)
    error: Mapped[str | None] = mapped_column(Text, default=None)
    result_path: Mapped[str | None] = mapped_column(String(500), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
