"""Organization domain entity representing an enterprise workspace aggregate."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from veritrace.domain.enums.audit import IndustrySector
from veritrace.domain.exceptions.base import ValidationError
from veritrace.domain.value_objects.identifiers import (
    ORG_PREFIX,
    ensure_utc,
    generate_id,
    utc_now,
    validate_id,
)


@dataclass(slots=True)
class Organization:
    """Enterprise workspace aggregate grouping investigations and authorized personnel."""

    id: str
    name: str
    industry_sector: IndustrySector
    created_at: datetime

    def __post_init__(self) -> None:
        self.id = validate_id(self.id, ORG_PREFIX, "Organization.id")
        if not self.name or not self.name.strip():
            raise ValidationError("Organization.name must not be empty")
        self.created_at = ensure_utc(self.created_at, "Organization.created_at")

    @classmethod
    def create(
        cls,
        name: str,
        industry_sector: IndustrySector,
        organization_id: str | None = None,
        created_at: datetime | None = None,
    ) -> Organization:
        """Factory method creating a valid Organization entity."""
        oid = organization_id or generate_id(ORG_PREFIX)
        ts = created_at or utc_now()
        return cls(
            id=oid,
            name=name.strip(),
            industry_sector=industry_sector,
            created_at=ts,
        )
