"""Bidirectional mapper between DocumentPage domain entity and DocumentPageModel."""

from __future__ import annotations

from veritrace.domain.entities.document_page import DocumentPage
from veritrace.domain.enums.document import TextLayerType
from veritrace.domain.value_objects.geometry import PageDimensions
from veritrace.infrastructure.persistence.mappers.converters import (
    dict_to_language_profile,
    language_profile_to_dict,
)
from veritrace.infrastructure.persistence.models.document_page import DocumentPageModel


class DocumentPageMapper:
    """Maps between DocumentPage domain entity and SQLAlchemy DocumentPageModel."""

    @staticmethod
    def to_model(entity: DocumentPage) -> DocumentPageModel:
        """Convert DocumentPage domain entity to SQLAlchemy model."""
        return DocumentPageModel(
            id=entity.id,
            document_id=entity.document_id,
            page_number=entity.page_number,
            width_pixels=entity.width_pixels,
            height_pixels=entity.height_pixels,
            dpi=entity.dpi,
            image_storage_path=entity.image_storage_path,
            has_digital_text=entity.has_digital_text,
            text_layer_type=entity.text_layer_type.value,
            primary_language=entity.primary_language,
            primary_script=entity.primary_script,
            languages_json=language_profile_to_dict(entity.language_profile),
        )

    @staticmethod
    def to_entity(model: DocumentPageModel) -> DocumentPage:
        """Convert SQLAlchemy DocumentPageModel to DocumentPage domain entity."""
        dimensions = PageDimensions(
            width_pixels=model.width_pixels,
            height_pixels=model.height_pixels,
            dpi=model.dpi,
        )
        return DocumentPage(
            id=model.id,
            document_id=model.document_id,
            page_number=model.page_number,
            dimensions=dimensions,
            image_storage_path=model.image_storage_path,
            has_digital_text=model.has_digital_text,
            text_layer_type=TextLayerType(model.text_layer_type),
            primary_language=model.primary_language,
            primary_script=model.primary_script,
            language_profile=dict_to_language_profile(model.languages_json),
        )

    to_domain = to_entity
