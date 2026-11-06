"""Bidirectional mapper between Evidence domain entity and EvidenceModel."""

from __future__ import annotations

from veritrace.domain.entities.evidence import Evidence
from veritrace.infrastructure.persistence.mappers.converters import (
    bbox_to_dict,
    dict_to_bbox,
)
from veritrace.infrastructure.persistence.models.evidence import EvidenceModel


class EvidenceMapper:
    """Maps between Evidence domain entity and SQLAlchemy EvidenceModel."""

    @staticmethod
    def to_model(entity: Evidence) -> EvidenceModel:
        """Convert Evidence domain entity to SQLAlchemy model."""
        return EvidenceModel(
            id=entity.id,
            page_id=entity.page_id,
            crop_image_path=entity.crop_image_path,
            normalized_bbox=bbox_to_dict(entity.normalized_bbox),
            pixel_x=entity.pixel_x,
            pixel_y=entity.pixel_y,
            pixel_width=entity.pixel_width,
            pixel_height=entity.pixel_height,
            heatmap_image_path=entity.heatmap_image_path,
            grounding_explanation=entity.grounding_explanation,
        )

    @staticmethod
    def to_entity(model: EvidenceModel) -> Evidence:
        """Convert SQLAlchemy EvidenceModel to Evidence domain entity."""
        bbox = dict_to_bbox(model.normalized_bbox)
        assert bbox is not None, "Evidence normalized_bbox must not be null"
        return Evidence(
            id=model.id,
            page_id=model.page_id,
            crop_image_path=model.crop_image_path,
            normalized_bbox=bbox,
            pixel_x=model.pixel_x,
            pixel_y=model.pixel_y,
            pixel_width=model.pixel_width,
            pixel_height=model.pixel_height,
            heatmap_image_path=model.heatmap_image_path,
            grounding_explanation=model.grounding_explanation,
        )

    to_domain = to_entity
