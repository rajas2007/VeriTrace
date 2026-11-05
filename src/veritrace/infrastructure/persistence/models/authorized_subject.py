"""SQLAlchemy model for AuthorizedSubject entity."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from veritrace.infrastructure.persistence.base import Base

if TYPE_CHECKING:
    from veritrace.infrastructure.persistence.models.organization import OrganizationModel
    from veritrace.infrastructure.persistence.models.signature_reference import (
        SignatureReferenceProfileModel,
    )


class AuthorizedSubjectModel(Base):
    """Designated signer profile authorized to endorse or inspect enterprise documents."""

    __tablename__ = "authorized_subjects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    designation: Mapped[str] = mapped_column(String(128), nullable=False)
    id_reference: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships (Protected against uncontrolled cascades)
    organization: Mapped[OrganizationModel] = relationship(
        "OrganizationModel",
        back_populates="authorized_subjects",
    )
    signature_references: Mapped[list[SignatureReferenceProfileModel]] = relationship(
        "SignatureReferenceProfileModel",
        back_populates="subject",
        passive_deletes="all",
    )

    __table_args__ = (Index("idx_authorized_subjects_org_id", "organization_id"),)
