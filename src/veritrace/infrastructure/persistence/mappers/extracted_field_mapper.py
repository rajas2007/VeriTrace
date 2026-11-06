"""Bidirectional mapper between ExtractedField domain entity and ExtractedFieldModel."""

from __future__ import annotations

from veritrace.domain.entities.extracted_field import ExtractedField
from veritrace.domain.enums.document import ExtractionSourceType
from veritrace.infrastructure.persistence.mappers.converters import (
    bbox_to_dict,
    dict_to_bbox,
)
from veritrace.infrastructure.persistence.models.extracted_field import (
    ExtractedFieldModel,
)


class ExtractedFieldMapper:
    """Maps between ExtractedField domain entity and SQLAlchemy ExtractedFieldModel."""

    @staticmethod
    def to_model(entity: ExtractedField) -> ExtractedFieldModel:
        """Convert ExtractedField domain entity to SQLAlchemy model."""
        return ExtractedFieldModel(
            id=entity.id,
            page_id=entity.page_id,
            entity_id=entity.entity_id,
            field_name=entity.field_name,
            field_value=entity.field_value,
            raw_text=entity.raw_text,
            confidence=entity.confidence,
            field_type=entity.field_type,
            language=entity.language,
            script=entity.script,
            lang_confidence=entity.lang_confidence,
            normalized_bbox=bbox_to_dict(entity.normalized_bbox),
            extraction_source=entity.extraction_source.value,
            ocr_engine=entity.ocr_engine,
            ocr_model_version=entity.ocr_model_version,
        )

    @staticmethod
    def to_entity(model: ExtractedFieldModel) -> ExtractedField:
        """Convert SQLAlchemy ExtractedFieldModel to ExtractedField domain entity."""
        return ExtractedField(
            id=model.id,
            page_id=model.page_id,
            field_name=model.field_name,
            field_value=model.field_value,
            raw_text=model.raw_text,
            confidence=model.confidence,
            field_type=model.field_type,
            entity_id=model.entity_id,
            language=model.language,
            script=model.script,
            lang_confidence=model.lang_confidence,
            normalized_bbox=dict_to_bbox(model.normalized_bbox),
            extraction_source=ExtractionSourceType(model.extraction_source),
            ocr_engine=model.ocr_engine,
            ocr_model_version=model.ocr_model_version,
        )

    to_domain = to_entity
