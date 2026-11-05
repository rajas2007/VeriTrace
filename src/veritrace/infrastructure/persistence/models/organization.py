"""SQLAlchemy model for Organization aggregate."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from veritrace.infrastructure.persistence.base import Base

if TYPE_CHECKING:
    from veritrace.infrastructure.persistence.models.authorized_subject import (
        AuthorizedSubjectModel,
    )
    from veritrace.infrastructure.persistence.models.investigation import InvestigationModel
    from veritrace.infrastructure.persistence.models.signature_reference import (
        SignatureReferenceProfileModel,
    )


class OrganizationModel(Base):
    """Multi-tenant industrial workspace grouping investigations and authorized subjects."""

    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry_sector: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships (Protected against uncontrolled cascades)
    investigations: Mapped[list[InvestigationModel]] = relationship(
        "InvestigationModel",
        back_populates="organization",
        passive_deletes="all",
    )
    authorized_subjects: Mapped[list[AuthorizedSubjectModel]] = relationship(
        "AuthorizedSubjectModel",
        back_populates="organization",
        passive_deletes="all",
    )
    signature_references: Mapped[list[SignatureReferenceProfileModel]] = relationship(
        "SignatureReferenceProfileModel",
        back_populates="organization",
        passive_deletes="all",
    )
