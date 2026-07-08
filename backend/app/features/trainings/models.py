from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TrainingStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TrainingJob(Base):
    __tablename__ = "training_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    voice_id: Mapped[int] = mapped_column(
        ForeignKey("voices.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[TrainingStatus] = mapped_column(
        Enum(TrainingStatus, native_enum=False, length=20), default=TrainingStatus.PENDING
    )
    epochs: Mapped[int] = mapped_column(default=200)
    progress: Mapped[float] = mapped_column(default=0.0)
    eta_seconds: Mapped[float | None] = mapped_column(default=None)
    error: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
