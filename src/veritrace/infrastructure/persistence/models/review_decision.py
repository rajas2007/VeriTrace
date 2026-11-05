"""SQLAlchemy model for ReviewDecision entity."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from veritrace.infrastructure.persistence.base import Base

if TYPE_CHECKING:
    from veritrace.infrastructure.persistence.models.finding import FindingModel


class ReviewDecisionModel(Base):
    """Authoritative sign-off, dismissal, or annotation decision made by an investigator."""

    __tablename__ = "review_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    finding_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("findings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reviewer_id: Mapped[str] = mapped_column(String(64), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    finding: Mapped[FindingModel] = relationship(
        "FindingModel",
        back_populates="review_decisions",
    )

    __table_args__ = (Index("idx_review_decisions_finding_id", "finding_id"),)
