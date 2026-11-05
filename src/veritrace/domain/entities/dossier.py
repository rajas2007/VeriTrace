"""Dossier domain entity representing a compiled investigation report."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from veritrace.domain.exceptions.base import ValidationError
from veritrace.domain.value_objects.identifiers import (
    DOS_PREFIX,
    INV_PREFIX,
    ensure_utc,
    generate_id,
    utc_now,
    validate_id,
)

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(slots=True)
class Dossier:
    """Permanent record of compiled investigation dossier reports with cryptographic output hash."""

    id: str
    investigation_id: str
    dossier_data: dict[str, Any]
    pdf_storage_path: str
    pdf_hash_sha256: str
    generated_at: datetime

    def __post_init__(self) -> None:
        self.id = validate_id(self.id, DOS_PREFIX, "Dossier.id")
        self.investigation_id = validate_id(
            self.investigation_id, INV_PREFIX, "Dossier.investigation_id"
        )
        if not self.pdf_storage_path or not self.pdf_storage_path.strip():
            raise ValidationError("Dossier.pdf_storage_path must not be empty")

        clean_hash = self.pdf_hash_sha256.strip().lower()
        if not _SHA256_PATTERN.match(clean_hash):
            raise ValidationError(
                f"pdf_hash_sha256 must be a 64-character hex digest: '{self.pdf_hash_sha256}'"
            )
        self.pdf_hash_sha256 = clean_hash
        self.generated_at = ensure_utc(self.generated_at, "Dossier.generated_at")

    @property
    def dossier_json(self) -> dict[str, Any]:
        """Structured PS-2 JSON report payload."""
        return self.dossier_data

    @classmethod
    def create(
        cls,
        investigation_id: str,
        dossier_data: dict[str, Any],
        pdf_storage_path: str,
        pdf_hash_sha256: str,
        dossier_id: str | None = None,
        generated_at: datetime | None = None,
    ) -> Dossier:
        """Factory method creating a Dossier entity."""
        did = dossier_id or generate_id(DOS_PREFIX)
        ts = generated_at or utc_now()
        return cls(
            id=did,
            investigation_id=investigation_id,
            dossier_data=dossier_data,
            pdf_storage_path=pdf_storage_path.strip(),
            pdf_hash_sha256=pdf_hash_sha256.strip().lower(),
            generated_at=ts,
        )
