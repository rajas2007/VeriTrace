"""SQLAlchemy model for SignatureReferenceProfile entity."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from veritrace.infrastructure.persistence.base import Base

if TYPE_CHECKING:
    from veritrace.infrastructure.persistence.models.authorized_subject import (
        AuthorizedSubjectModel,
    )
    from veritrace.infrastructure.persistence.models.finding import FindingModel
    from veritrace.infrastructure.persistence.models.organization import OrganizationModel


class SignatureReferenceProfileModel(Base):
    """Enrolled reference signature sample maintained under strict chain-of-custody.

    SECURITY NOTE: Reference crops and embedding vectors are not encrypted via
    application-layer cryptography (host-level volume encryption is relied upon).
    """

    __tablename__ = "signature_references"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    subject_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("authorized_subjects.id", ondelete="RESTRICT"),
        nullable=False,
    )
    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    crop_image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_vector: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    enrollment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_document_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    consent_mandate_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    retention_expiry_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    access_role_required: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="FORENSIC_INVESTIGATOR",
    )
    provenance_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    subject: Mapped[AuthorizedSubjectModel] = relationship(
        "AuthorizedSubjectModel",
        back_populates="signature_references",
    )
    organization: Mapped[OrganizationModel] = relationship(
        "OrganizationModel",
        back_populates="signature_references",
    )
    findings: Mapped[list[FindingModel]] = relationship(
        "FindingModel",
        back_populates="signature_reference",
    )

    __table_args__ = (
        Index("idx_signature_references_subject_id", "subject_id"),
        Index("idx_signature_references_org_id", "organization_id"),
        Index("uq_signature_references_subject_hash", "subject_id", "sha256_hash", unique=True),
    )
