"""SignatureReferenceProfile domain entity for enrolled forensic reference samples."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from veritrace.domain.exceptions.base import InvalidIdentifierError, ValidationError
from veritrace.domain.value_objects.identifiers import (
    ORG_PREFIX,
    SIGREF_PREFIX,
    SUBJ_PREFIX,
    ensure_utc,
    generate_id,
    utc_now,
    validate_id,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(slots=True)
class SignatureReferenceProfile:
    """Enrolled reference signature sample maintained under strict chain-of-custody.

    INVARIANT: Reference signatures require verified legal provenance, written signatory
    consent, and RBAC governance. Machine similarity does NOT prove legal authorship.
    """

    id: str
    subject_id: str
    organization_id: str
    crop_image_path: str
    sha256_hash: str
    source_document_ref: str
    consent_mandate_ref: str
    enrollment_date: datetime
    embedding_vector: bytes | None = None
    retention_expiry_date: datetime | None = None
    access_role_required: str = "FORENSIC_INVESTIGATOR"
    provenance_json: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        # Support sigref_ prefix (and legacy sig_ if present)
        if self.id.startswith(SIGREF_PREFIX):
            self.id = validate_id(self.id, SIGREF_PREFIX, "SignatureReferenceProfile.id")
        elif self.id.startswith("sig_"):
            self.id = validate_id(self.id, "sig_", "SignatureReferenceProfile.id")
        else:
            raise InvalidIdentifierError(
                f"SignatureReferenceProfile.id must start with '{SIGREF_PREFIX}', got '{self.id}'"
            )

        self.subject_id = validate_id(
            self.subject_id, SUBJ_PREFIX, "SignatureReferenceProfile.subject_id"
        )
        self.organization_id = validate_id(
            self.organization_id, ORG_PREFIX, "SignatureReferenceProfile.organization_id"
        )

        if not self.crop_image_path or not self.crop_image_path.strip():
            raise ValidationError("crop_image_path must not be empty")

        clean_hash = self.sha256_hash.strip().lower()
        if not _SHA256_PATTERN.match(clean_hash):
            raise ValidationError(
                f"sha256_hash must be a 64-char hex digest, got '{self.sha256_hash}'"
            )
        self.sha256_hash = clean_hash

        if not self.source_document_ref or not self.source_document_ref.strip():
            raise ValidationError("source_document_ref must not be empty")

        # Mandatory chain-of-custody consent mandate
        if not self.consent_mandate_ref or not self.consent_mandate_ref.strip():
            raise ValidationError(
                "consent_mandate_ref must not be empty; enrollment requires mandate"
            )

        self.enrollment_date = ensure_utc(
            self.enrollment_date, "SignatureReferenceProfile.enrollment_date"
        )

        if self.retention_expiry_date is not None:
            self.retention_expiry_date = ensure_utc(
                self.retention_expiry_date,
                "SignatureReferenceProfile.retention_expiry_date",
            )
            if self.retention_expiry_date <= self.enrollment_date:
                raise ValidationError(
                    f"retention_expiry ({self.retention_expiry_date}) "
                    f"must be after enrollment ({self.enrollment_date})"
                )

    def is_expired(self, as_of: datetime | None = None) -> bool:
        """Check if profile has exceeded its mandatory retention expiration date."""
        if self.retention_expiry_date is None:
            return False
        reference_time = ensure_utc(as_of) if as_of else utc_now()
        return reference_time >= self.retention_expiry_date

    def is_authorized_for_role(self, user_role: str) -> bool:
        """Check if user role meets the RBAC access tier required for this profile."""
        role_hierarchy = {
            "VIEWER": 0,
            "DOCUMENT_ANALYST": 1,
            "FORENSIC_INVESTIGATOR": 2,
            "LEAD_AUDITOR": 3,
            "ADMIN": 4,
        }
        required_level = role_hierarchy.get(self.access_role_required, 2)
        user_level = role_hierarchy.get(user_role, 0)
        return user_level >= required_level

    @classmethod
    def create(
        cls,
        subject_id: str,
        organization_id: str,
        crop_image_path: str,
        sha256_hash: str,
        source_document_ref: str,
        consent_mandate_ref: str,
        profile_id: str | None = None,
        enrollment_date: datetime | None = None,
        retention_expiry_date: datetime | None = None,
        embedding_vector: bytes | None = None,
        access_role_required: str = "FORENSIC_INVESTIGATOR",
        provenance_json: dict[str, Any] | None = None,
    ) -> SignatureReferenceProfile:
        """Factory method creating an enrolled SignatureReferenceProfile entity."""
        pid = profile_id or generate_id(SIGREF_PREFIX)
        ts = enrollment_date or utc_now()
        return cls(
            id=pid,
            subject_id=subject_id,
            organization_id=organization_id,
            crop_image_path=crop_image_path.strip(),
            sha256_hash=sha256_hash.strip().lower(),
            source_document_ref=source_document_ref.strip(),
            consent_mandate_ref=consent_mandate_ref.strip(),
            enrollment_date=ts,
            embedding_vector=embedding_vector,
            retention_expiry_date=retention_expiry_date,
            access_role_required=access_role_required,
            provenance_json=provenance_json,
        )
