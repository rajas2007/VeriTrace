"""SQLAlchemy model for Finding entity."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from veritrace.infrastructure.persistence.base import Base
from veritrace.infrastructure.persistence.models.finding_evidence import (
    finding_evidence_map,
)

if TYPE_CHECKING:
    from veritrace.infrastructure.persistence.models.cross_document_relation import (
        CrossDocumentRelationModel,
    )
    from veritrace.infrastructure.persistence.models.evidence import EvidenceModel
    from veritrace.infrastructure.persistence.models.investigation import (
        InvestigationModel,
    )
    from veritrace.infrastructure.persistence.models.review_decision import (
        ReviewDecisionModel,
    )
    from veritrace.infrastructure.persistence.models.signature_reference import (
        SignatureReferenceProfileModel,
    )


class FindingModel(Base):
    """Standardized forensic conclusion categorized under the Three-Tier Epistemic Ontology."""

    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    investigation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    epistemic_tier: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    narrative_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    investigator_guidance: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING_REVIEW")
    signature_reference_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("signature_references.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    investigation: Mapped[InvestigationModel] = relationship(
        "InvestigationModel",
        back_populates="findings",
    )
    signature_reference: Mapped[SignatureReferenceProfileModel | None] = relationship(
        "SignatureReferenceProfileModel",
        back_populates="findings",
    )
    evidence: Mapped[list[EvidenceModel]] = relationship(
        "EvidenceModel",
        secondary=finding_evidence_map,
        back_populates="findings",
    )
    # INVARIANT: Review decisions represent authoritative human adjudication;
    # protected against uncontrolled cascade deletion.
    review_decisions: Mapped[list[ReviewDecisionModel]] = relationship(
        "ReviewDecisionModel",
        back_populates="finding",
        passive_deletes="all",
    )
    cross_document_relations: Mapped[list[CrossDocumentRelationModel]] = relationship(
        "CrossDocumentRelationModel",
        back_populates="finding",
    )

    __table_args__ = (
        Index("idx_findings_inv_id", "investigation_id"),
        Index("idx_findings_tier", "epistemic_tier"),
        Index("idx_findings_severity", "severity"),
        Index("idx_findings_sigref_id", "signature_reference_id"),
    )
