"""SQLAlchemy model for Evidence entity."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from veritrace.infrastructure.persistence.base import Base
from veritrace.infrastructure.persistence.models.finding_evidence import (
    finding_evidence_map,
)

if TYPE_CHECKING:
    from veritrace.infrastructure.persistence.models.document_page import (
        DocumentPageModel,
    )
    from veritrace.infrastructure.persistence.models.finding import FindingModel


class EvidenceModel(Base):
    """Pixel-level visual crop and coordinate anchor that supports one or more findings."""

    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    page_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("document_pages.id", ondelete="RESTRICT"),
        nullable=False,
    )
    crop_image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    normalized_bbox: Mapped[Any] = mapped_column(JSON, nullable=False)
    pixel_x: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pixel_y: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pixel_width: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pixel_height: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    heatmap_image_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    grounding_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    page: Mapped[DocumentPageModel] = relationship(
        "DocumentPageModel",
        back_populates="evidence_items",
    )
    findings: Mapped[list[FindingModel]] = relationship(
        "FindingModel",
        secondary=finding_evidence_map,
        back_populates="evidence",
    )

    __table_args__ = (Index("idx_evidence_page_id", "page_id"),)
