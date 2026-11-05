"""SQLAlchemy model for ExtractedField entity."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from veritrace.infrastructure.persistence.base import Base

if TYPE_CHECKING:
    from veritrace.infrastructure.persistence.models.document_page import (
        DocumentPageModel,
    )
    from veritrace.infrastructure.persistence.models.entity import EntityModel


class ExtractedFieldModel(Base):
    """Stores granular OCR tokens and parsed key-values with provenance and verbatim raw text."""

    __tablename__ = "extracted_fields"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    page_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("document_pages.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("entities.id", ondelete="SET NULL"),
        nullable=True,
    )
    field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    field_value: Mapped[str] = mapped_column(Text, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    field_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    script: Mapped[str | None] = mapped_column(String(32), nullable=True)
    lang_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    normalized_bbox: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    extraction_source: Mapped[str] = mapped_column(
        String(32), nullable=False, default="DIGITAL_TEXT"
    )
    ocr_engine: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ocr_model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Relationships
    page: Mapped[DocumentPageModel] = relationship(
        "DocumentPageModel",
        back_populates="extracted_fields",
    )
    entity: Mapped[EntityModel | None] = relationship(
        "EntityModel",
        back_populates="extracted_fields",
    )

    __table_args__ = (
        Index("idx_extracted_fields_page_id", "page_id"),
        Index("idx_extracted_fields_entity_id", "entity_id"),
        Index("idx_extracted_fields_name", "field_name"),
    )
