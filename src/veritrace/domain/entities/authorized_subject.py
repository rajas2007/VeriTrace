"""AuthorizedSubject domain entity representing an authorized enterprise signatory."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from veritrace.domain.exceptions.base import ValidationError
from veritrace.domain.value_objects.identifiers import (
    ORG_PREFIX,
    SUBJ_PREFIX,
    ensure_utc,
    generate_id,
    utc_now,
    validate_id,
)


@dataclass(slots=True)
class AuthorizedSubject:
    """Designated signer profile authorized to execute, endorse, or verify enterprise documents."""

    id: str
    organization_id: str
    full_name: str
    designation: str
    id_reference: str
    created_at: datetime

    def __post_init__(self) -> None:
        self.id = validate_id(self.id, SUBJ_PREFIX, "AuthorizedSubject.id")
        self.organization_id = validate_id(
            self.organization_id, ORG_PREFIX, "AuthorizedSubject.organization_id"
        )
        if not self.full_name or not self.full_name.strip():
            raise ValidationError("AuthorizedSubject.full_name must not be empty")
        if not self.designation or not self.designation.strip():
            raise ValidationError("AuthorizedSubject.designation must not be empty")
        if not self.id_reference or not self.id_reference.strip():
            raise ValidationError("AuthorizedSubject.id_reference must not be empty")
        self.created_at = ensure_utc(self.created_at, "AuthorizedSubject.created_at")

    def belongs_to_organization(self, organization_id: str) -> bool:
        """Check if this authorized subject belongs to the specified organization."""
        return self.organization_id == organization_id

    @classmethod
    def create(
        cls,
        organization_id: str,
        full_name: str,
        designation: str,
        id_reference: str,
        subject_id: str | None = None,
        created_at: datetime | None = None,
    ) -> AuthorizedSubject:
        """Factory method creating an AuthorizedSubject entity."""
        sid = subject_id or generate_id(SUBJ_PREFIX)
        ts = created_at or utc_now()
        return cls(
            id=sid,
            organization_id=organization_id,
            full_name=full_name.strip(),
            designation=designation.strip(),
            id_reference=id_reference.strip(),
            created_at=ts,
        )
