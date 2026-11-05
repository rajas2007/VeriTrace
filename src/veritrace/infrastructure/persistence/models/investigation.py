"""SQLAlchemy model for Investigation aggregate root."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from veritrace.infrastructure.persistence.base import Base

if TYPE_CHECKING:
    from veritrace.infrastructure.persistence.models.audit_event import AuditEventModel
    from veritrace.infrastructure.persistence.models.cross_document_relation import (
        CrossDocumentRelationModel,
    )
    from veritrace.infrastructure.persistence.models.document import DocumentModel
    from veritrace.infrastructure.persistence.models.dossier import DossierModel
    from veritrace.infrastructure.persistence.models.entity import EntityModel
    from veritrace.infrastructure.persistence.models.finding import FindingModel
    from veritrace.infrastructure.persistence.models.investigation_job import (
        InvestigationJobModel,
    )
    from veritrace.infrastructure.persistence.models.organization import OrganizationModel


class InvestigationModel(Base):
    """Root aggregate representing an industrial multi-document forensic investigation case."""

    __tablename__ = "investigations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    reference_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    risk_classification: Mapped[str] = mapped_column(
        String(32), nullable=False, default="UNDETERMINED"
    )
    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    organization: Mapped[OrganizationModel] = relationship(
        "OrganizationModel",
        back_populates="investigations",
    )
    documents: Mapped[list[DocumentModel]] = relationship(
        "DocumentModel",
        back_populates="investigation",
        cascade="all, delete-orphan",
    )
    jobs: Mapped[list[InvestigationJobModel]] = relationship(
        "InvestigationJobModel",
        back_populates="investigation",
        cascade="all, delete-orphan",
    )
    entities: Mapped[list[EntityModel]] = relationship(
        "EntityModel",
        back_populates="investigation",
        cascade="all, delete-orphan",
    )
    findings: Mapped[list[FindingModel]] = relationship(
        "FindingModel",
        back_populates="investigation",
        cascade="all, delete-orphan",
    )
    relations: Mapped[list[CrossDocumentRelationModel]] = relationship(
        "CrossDocumentRelationModel",
        back_populates="investigation",
        cascade="all, delete-orphan",
        foreign_keys="CrossDocumentRelationModel.investigation_id",
    )
    dossiers: Mapped[list[DossierModel]] = relationship(
        "DossierModel",
        back_populates="investigation",
        cascade="all, delete-orphan",
    )
    # INVARIANT: audit_events are immutable and append-only; never cascade-deleted
    audit_events: Mapped[list[AuditEventModel]] = relationship(
        "AuditEventModel",
        back_populates="investigation",
        passive_deletes="all",
    )

    __table_args__ = (
        Index("idx_investigations_reference_code", "reference_code", unique=True),
        Index("idx_investigations_status", "status"),
        Index("idx_investigations_org_id", "organization_id"),
    )
