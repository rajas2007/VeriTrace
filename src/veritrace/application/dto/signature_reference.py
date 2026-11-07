"""Data Transfer Objects for Signature Reference Profiles and Authorized Subjects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AuthorizedSubjectCreateDTO:
    """Request DTO to register an authorized enterprise signatory."""

    organization_id: str
    full_name: str
    designation: str
    id_reference: str


@dataclass(frozen=True)
class AuthorizedSubjectDTO:
    """Response DTO representing an authorized signatory."""

    id: str
    organization_id: str
    full_name: str
    designation: str
    id_reference: str
    created_at: datetime


@dataclass(frozen=True)
class SignatureReferenceEnrollDTO:
    """Request DTO to enroll a reference signature under chain-of-custody governance."""

    organization_id: str
    subject_id: str
    crop_image_path: str
    source_document_ref: str
    consent_mandate_ref: str
    investigation_id: str | None = None
    retention_expiry_date: datetime | None = None
    access_role_required: str = "FORENSIC_INVESTIGATOR"


@dataclass(frozen=True)
class SignatureReferenceDTO:
    """Response DTO for an enrolled signature reference profile."""

    id: str
    subject_id: str
    organization_id: str
    crop_image_path: str
    sha256_hash: str
    source_document_ref: str
    consent_mandate_ref: str
    enrollment_date: datetime
    retention_expiry_date: datetime | None = None
    has_embedding: bool = False
    access_role_required: str = "FORENSIC_INVESTIGATOR"
