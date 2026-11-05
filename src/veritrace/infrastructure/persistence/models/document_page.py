"""SQLAlchemy model for DocumentPage entity."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from veritrace.infrastructure.persistence.base import Base

if TYPE_CHECKING:
    from veritrace.infrastructure.persistence.models.document import DocumentModel
    from veritrace.infrastructure.persistence.models.evidence import EvidenceModel
    from veritrace.infrastructure.persistence.models.extracted_field import (
        ExtractedFieldModel,
    )


class DocumentPageModel(Base):
    """Represents a single rasterized page of an ingested document."""

    __tablename__ = "document_pages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    width_pixels: Mapped[int] = mapped_column(Integer, nullable=False)
    height_pixels: Mapped[int] = mapped_column(Integer, nullable=False)
    dpi: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    image_storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    has_digital_text: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    text_layer_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="SCANNED_RASTER"
    )
    primary_language: Mapped[str] = mapped_column(String(16), nullable=False, default="eng")
    primary_script: Mapped[str] = mapped_column(String(32), nullable=False, default="Latn")
    languages_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    document: Mapped[DocumentModel] = relationship(
        "DocumentModel",
        back_populates="pages",
    )
    extracted_fields: Mapped[list[ExtractedFieldModel]] = relationship(
        "ExtractedFieldModel",
        back_populates="page",
        cascade="all, delete-orphan",
    )
    # INVARIANT: Evidence is physical visual anchor and must not be silently cascade-deleted
    evidence_items: Mapped[list[EvidenceModel]] = relationship(
        "EvidenceModel",
        back_populates="page",
        passive_deletes="all",
    )

    __table_args__ = (
        UniqueConstraint("document_id", "page_number", name="uq_document_pages_doc_num"),
        Index("idx_document_pages_doc_id", "document_id"),
    )
