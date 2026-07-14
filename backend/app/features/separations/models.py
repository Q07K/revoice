from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SeparationStatus(StrEnum):
    PENDING = "pending"
    SEPARATING = "separating"
    COMPLETED = "completed"
    FAILED = "failed"


class SeparationJob(Base):
    """A standalone vocal/instrumental split — the same RoFormer separator the
    cover pipeline uses, exposed as its own tool (e.g. to prep clean vocals for
    a training dataset)."""

    __tablename__ = "separation_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    source_path: Mapped[str] = mapped_column(String(500))
    status: Mapped[SeparationStatus] = mapped_column(
        Enum(SeparationStatus, native_enum=False, length=20),
        default=SeparationStatus.PENDING,
    )
    progress: Mapped[float] = mapped_column(default=0.0)
    eta_seconds: Mapped[float | None] = mapped_column(default=None)
    vocals_path: Mapped[str | None] = mapped_column(String(500), default=None)
    instrumental_path: Mapped[str | None] = mapped_column(String(500), default=None)
    # 보컬에서 리버브/에코까지 제거한 드라이 보컬 (디리버브 모델이 꺼져 있으면 None).
    dry_vocals_path: Mapped[str | None] = mapped_column(String(500), default=None)
    error: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    @property
    def has_vocals(self) -> bool:
        return self.vocals_path is not None

    @property
    def has_instrumental(self) -> bool:
        return self.instrumental_path is not None

    @property
    def has_dry_vocals(self) -> bool:
        return self.dry_vocals_path is not None
