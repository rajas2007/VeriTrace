"""SQLAlchemy model for Document entity."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from veritrace.infrastructure.persistence.base import Base

if TYPE_CHECKING:
    from veritrace.infrastructure.persistence.models.cross_document_relation import (
        CrossDocumentRelationModel,
    )
    from veritrace.infrastructure.persistence.models.document_page import (
        DocumentPageModel,
    )
    from veritrace.infrastructure.persistence.models.investigation import (
        InvestigationModel,
    )


class DocumentModel(Base):
    """Represents an individual physical or digital file uploaded to an investigation."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    investigation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False, default="UNCLASSIFIED")
    primary_language: Mapped[str] = mapped_column(String(16), nullable=False, default="eng")
    primary_script: Mapped[str] = mapped_column(String(32), nullable=False, default="Latn")
    languages_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    classification_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    quality_status: Mapped[str] = mapped_column(String(32), nullable=False, default="UNVERIFIED")
    structured_content: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="UPLOADED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    investigation: Mapped[InvestigationModel] = relationship(
        "InvestigationModel",
        back_populates="documents",
    )
    pages: Mapped[list[DocumentPageModel]] = relationship(
        "DocumentPageModel",
        back_populates="document",
        cascade="all, delete-orphan",
    )
    source_relations: Mapped[list[CrossDocumentRelationModel]] = relationship(
        "CrossDocumentRelationModel",
        foreign_keys="CrossDocumentRelationModel.source_document_id",
        back_populates="source_document",
        cascade="all, delete-orphan",
    )
    target_relations: Mapped[list[CrossDocumentRelationModel]] = relationship(
        "CrossDocumentRelationModel",
        foreign_keys="CrossDocumentRelationModel.target_document_id",
        back_populates="target_document",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_documents_inv_id", "investigation_id"),
        Index("idx_documents_hash", "file_hash_sha256"),
    )
