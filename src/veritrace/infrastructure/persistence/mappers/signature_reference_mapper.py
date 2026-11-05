"""Bidirectional mapper for SignatureReferenceProfile persistence."""

from __future__ import annotations

from veritrace.domain.entities.signature_reference import SignatureReferenceProfile
from veritrace.infrastructure.persistence.mappers.converters import to_utc
from veritrace.infrastructure.persistence.models.signature_reference import (
    SignatureReferenceProfileModel,
)


class SignatureReferenceMapper:
    """Maps between SignatureReferenceProfile domain entity and SQLAlchemy model."""

    @staticmethod
    def to_model(
        entity: SignatureReferenceProfile,
    ) -> SignatureReferenceProfileModel:
        """Convert SignatureReferenceProfile domain entity to SQLAlchemy model."""
        return SignatureReferenceProfileModel(
            id=entity.id,
            subject_id=entity.subject_id,
            organization_id=entity.organization_id,
            crop_image_path=entity.crop_image_path,
            sha256_hash=entity.sha256_hash,
            embedding_vector=entity.embedding_vector,
            enrollment_date=to_utc(entity.enrollment_date),
            source_document_ref=entity.source_document_ref,
            consent_mandate_ref=entity.consent_mandate_ref,
            retention_expiry_date=to_utc(entity.retention_expiry_date),
            access_role_required=entity.access_role_required,
            provenance_json=entity.provenance_json,
        )

    @staticmethod
    def to_entity(
        model: SignatureReferenceProfileModel,
    ) -> SignatureReferenceProfile:
        """Convert SQLAlchemy model to SignatureReferenceProfile domain entity."""
        enrollment_date = to_utc(model.enrollment_date)
        assert enrollment_date is not None
        return SignatureReferenceProfile(
            id=model.id,
            subject_id=model.subject_id,
            organization_id=model.organization_id,
            crop_image_path=model.crop_image_path,
            sha256_hash=model.sha256_hash,
            embedding_vector=model.embedding_vector,
            enrollment_date=enrollment_date,
            source_document_ref=model.source_document_ref,
            consent_mandate_ref=model.consent_mandate_ref,
            retention_expiry_date=to_utc(model.retention_expiry_date),
            access_role_required=model.access_role_required,
            provenance_json=model.provenance_json,
        )
