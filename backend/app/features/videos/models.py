from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class VideoStatus(StrEnum):
    PENDING = "pending"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoVisual(StrEnum):
    IMAGE = "image"
    WAVE = "wave"
    SPECTRUM = "spectrum"


class VideoAspect(StrEnum):
    WIDE = "16:9"
    VERTICAL = "9:16"


class VideoJob(Base):
    """A YouTube-ready mp4 rendered from a finished cover."""

    __tablename__ = "video_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    cover_id: Mapped[int] = mapped_column(
        ForeignKey("cover_jobs.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    subtitle: Mapped[str] = mapped_column(String(255), default="")
    visual: Mapped[VideoVisual] = mapped_column(
        Enum(VideoVisual, native_enum=False, length=20), default=VideoVisual.WAVE
    )
    aspect: Mapped[VideoAspect] = mapped_column(
        Enum(VideoAspect, native_enum=False, length=10), default=VideoAspect.WIDE
    )
    image_path: Mapped[str | None] = mapped_column(String(500), default=None)
    status: Mapped[VideoStatus] = mapped_column(
        Enum(VideoStatus, native_enum=False, length=20), default=VideoStatus.PENDING
    )
    progress: Mapped[float] = mapped_column(default=0.0)
    eta_seconds: Mapped[float | None] = mapped_column(default=None)
    result_path: Mapped[str | None] = mapped_column(String(500), default=None)
    error: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
