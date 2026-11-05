"""SQLAlchemy model for InvestigationJob entity."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from veritrace.infrastructure.persistence.base import Base

if TYPE_CHECKING:
    from veritrace.infrastructure.persistence.models.investigation import InvestigationModel


class InvestigationJobModel(Base):
    """Manages persistent asynchronous job lifecycle, progress, and failure recovery."""

    __tablename__ = "investigation_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    investigation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    current_stage: Mapped[str] = mapped_column(String(64), nullable=False)
    progress_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stage_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    can_resume: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    investigation: Mapped[InvestigationModel] = relationship(
        "InvestigationModel",
        back_populates="jobs",
    )

    __table_args__ = (
        Index("idx_investigation_jobs_inv_id", "investigation_id"),
        Index("idx_investigation_jobs_status", "status"),
    )
