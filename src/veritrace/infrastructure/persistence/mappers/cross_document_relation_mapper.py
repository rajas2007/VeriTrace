"""Bidirectional mapper between CrossDocumentRelation entity and CrossDocumentRelationModel."""

from __future__ import annotations

from veritrace.domain.entities.cross_document_relation import CrossDocumentRelation
from veritrace.domain.enums.forensic import RelationType
from veritrace.infrastructure.persistence.models.cross_document_relation import (
    CrossDocumentRelationModel,
)


class CrossDocumentRelationMapper:
    """Maps between CrossDocumentRelation domain entity and SQLAlchemy model."""

    @staticmethod
    def to_model(entity: CrossDocumentRelation) -> CrossDocumentRelationModel:
        """Convert CrossDocumentRelation domain entity to SQLAlchemy model."""
        return CrossDocumentRelationModel(
            id=entity.id,
            investigation_id=entity.investigation_id,
            source_document_id=entity.source_document_id,
            target_document_id=entity.target_document_id,
            relation_type=entity.relation_type.value,
            description=entity.description,
            finding_id=entity.finding_id,
            similarity_score=entity.similarity_score,
        )

    @staticmethod
    def to_entity(model: CrossDocumentRelationModel) -> CrossDocumentRelation:
        """Convert SQLAlchemy model to CrossDocumentRelation domain entity."""
        return CrossDocumentRelation(
            id=model.id,
            investigation_id=model.investigation_id,
            source_document_id=model.source_document_id,
            target_document_id=model.target_document_id,
            relation_type=RelationType(model.relation_type),
            description=model.description,
            finding_id=model.finding_id,
            similarity_score=model.similarity_score,
        )
