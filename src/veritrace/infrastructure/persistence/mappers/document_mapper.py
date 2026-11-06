"""Bidirectional mapper between Document domain entity and DocumentModel."""

from __future__ import annotations

from veritrace.domain.entities.document import Document
from veritrace.domain.enums.document import (
    DocumentStatus,
    DocumentType,
    QualityStatus,
)
from veritrace.infrastructure.persistence.mappers.converters import (
    dict_to_language_profile,
    language_profile_to_dict,
    to_utc,
)
from veritrace.infrastructure.persistence.models.document import DocumentModel


class DocumentMapper:
    """Maps between Document domain entity and SQLAlchemy DocumentModel."""

    @staticmethod
    def to_model(entity: Document) -> DocumentModel:
        """Convert Document domain entity to SQLAlchemy model."""
        return DocumentModel(
            id=entity.id,
            investigation_id=entity.investigation_id,
            original_filename=entity.original_filename,
            file_hash_sha256=entity.file_hash_sha256,
            mime_type=entity.mime_type,
            document_type=entity.document_type.value,
            primary_language=entity.primary_language,
            primary_script=entity.primary_script,
            languages_json=language_profile_to_dict(entity.language_profile),
            classification_confidence=entity.classification_confidence,
            page_count=entity.page_count,
            file_size_bytes=entity.file_size_bytes,
            storage_path=entity.storage_path,
            quality_status=entity.quality_status.value,
            structured_content=entity.structured_content,
            metadata_json=entity.metadata_json,
            status=entity.status.value,
            created_at=to_utc(entity.created_at),
        )

    @staticmethod
    def to_entity(model: DocumentModel) -> Document:
        """Convert SQLAlchemy DocumentModel to Document domain entity."""
        created_at = to_utc(model.created_at)
        assert created_at is not None
        return Document(
            id=model.id,
            investigation_id=model.investigation_id,
            original_filename=model.original_filename,
            file_hash_sha256=model.file_hash_sha256,
            mime_type=model.mime_type,
            created_at=created_at,
            document_type=DocumentType(model.document_type),
            primary_language=model.primary_language,
            primary_script=model.primary_script,
            language_profile=dict_to_language_profile(model.languages_json),
            classification_confidence=model.classification_confidence,
            page_count=model.page_count,
            file_size_bytes=model.file_size_bytes,
            storage_path=model.storage_path,
            quality_status=QualityStatus(model.quality_status),
            structured_content=model.structured_content,
            metadata_json=model.metadata_json,
            status=DocumentStatus(model.status),
        )

    to_domain = to_entity
