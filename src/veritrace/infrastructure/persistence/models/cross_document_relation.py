"""SQLAlchemy model for CrossDocumentRelation entity."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from veritrace.infrastructure.persistence.base import Base

if TYPE_CHECKING:
    from veritrace.infrastructure.persistence.models.document import DocumentModel
    from veritrace.infrastructure.persistence.models.finding import FindingModel
    from veritrace.infrastructure.persistence.models.investigation import (
        InvestigationModel,
    )


class CrossDocumentRelationModel(Base):
    """Represents a directional semantic relationship across two distinct documents."""

    __tablename__ = "cross_document_relations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    investigation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    relation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    finding_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("findings.id", ondelete="SET NULL"),
        nullable=True,
    )
    similarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    investigation: Mapped[InvestigationModel] = relationship(
        "InvestigationModel",
        back_populates="relations",
        foreign_keys=[investigation_id],
    )
    source_document: Mapped[DocumentModel] = relationship(
        "DocumentModel",
        foreign_keys=[source_document_id],
        back_populates="source_relations",
    )
    target_document: Mapped[DocumentModel] = relationship(
        "DocumentModel",
        foreign_keys=[target_document_id],
        back_populates="target_relations",
    )
    finding: Mapped[FindingModel | None] = relationship(
        "FindingModel",
        back_populates="cross_document_relations",
    )

    __table_args__ = (
        Index("idx_cross_document_relations_inv_id", "investigation_id"),
        Index("idx_cross_document_relations_source_doc", "source_document_id"),
        Index("idx_cross_document_relations_target_doc", "target_document_id"),
    )
