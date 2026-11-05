"""SQLAlchemy model for Dossier entity."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from veritrace.infrastructure.persistence.base import Base

if TYPE_CHECKING:
    from veritrace.infrastructure.persistence.models.investigation import (
        InvestigationModel,
    )


class DossierModel(Base):
    """Permanent record of compiled investigation dossier reports with cryptographic hash."""

    __tablename__ = "dossiers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    investigation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
    )
    dossier_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    pdf_storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    pdf_hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    investigation: Mapped[InvestigationModel] = relationship(
        "InvestigationModel",
        back_populates="dossiers",
    )

    __table_args__ = (Index("idx_dossiers_inv_id", "investigation_id"),)
