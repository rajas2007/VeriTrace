"""SQLAlchemy model for Entity aggregate child."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from veritrace.infrastructure.persistence.base import Base

if TYPE_CHECKING:
    from veritrace.infrastructure.persistence.models.extracted_field import (
        ExtractedFieldModel,
    )
    from veritrace.infrastructure.persistence.models.investigation import (
        InvestigationModel,
    )


class EntityModel(Base):
    """Canonical real-world identity or factual claim reconciled across multiple documents."""

    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    investigation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    canonical_value: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    investigation: Mapped[InvestigationModel] = relationship(
        "InvestigationModel",
        back_populates="entities",
    )
    extracted_fields: Mapped[list[ExtractedFieldModel]] = relationship(
        "ExtractedFieldModel",
        back_populates="entity",
    )

    __table_args__ = (Index("idx_entities_inv_id", "investigation_id"),)
