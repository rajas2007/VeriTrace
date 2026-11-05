"""CrossDocumentRelation domain entity mapping semantic relationships across documents."""

from __future__ import annotations

from dataclasses import dataclass

from veritrace.domain.enums.forensic import RelationType
from veritrace.domain.exceptions.base import (
    ConfidenceRangeError,
    RelationshipConstraintError,
    ValidationError,
)
from veritrace.domain.value_objects.identifiers import (
    DOC_PREFIX,
    FND_PREFIX,
    INV_PREFIX,
    REL_PREFIX,
    generate_id,
    validate_id,
)


@dataclass(slots=True)
class CrossDocumentRelation:
    """Represents a directional semantic relationship across two distinct documents."""

    id: str
    investigation_id: str
    source_document_id: str
    target_document_id: str
    relation_type: RelationType
    description: str
    finding_id: str | None = None
    similarity_score: float | None = None

    def __post_init__(self) -> None:
        self.id = validate_id(self.id, REL_PREFIX, "CrossDocumentRelation.id")
        self.investigation_id = validate_id(
            self.investigation_id,
            INV_PREFIX,
            "CrossDocumentRelation.investigation_id",
        )
        self.source_document_id = validate_id(
            self.source_document_id,
            DOC_PREFIX,
            "CrossDocumentRelation.source_document_id",
        )
        self.target_document_id = validate_id(
            self.target_document_id,
            DOC_PREFIX,
            "CrossDocumentRelation.target_document_id",
        )

        if self.source_document_id == self.target_document_id:
            raise RelationshipConstraintError(
                f"Cannot link doc to itself: source={self.source_document_id}, "
                f"target={self.target_document_id}"
            )

        if not self.description or not self.description.strip():
            raise ValidationError("CrossDocumentRelation.description must not be empty")

        if self.finding_id is not None:
            self.finding_id = validate_id(
                self.finding_id, FND_PREFIX, "CrossDocumentRelation.finding_id"
            )

        if self.similarity_score is not None and not (0.0 <= self.similarity_score <= 1.0):
            raise ConfidenceRangeError(
                f"similarity_score must be in [0.0, 1.0], got {self.similarity_score}"
            )

    @classmethod
    def create(
        cls,
        investigation_id: str,
        source_document_id: str,
        target_document_id: str,
        relation_type: RelationType,
        description: str,
        relation_id: str | None = None,
        finding_id: str | None = None,
        similarity_score: float | None = None,
    ) -> CrossDocumentRelation:
        """Factory method creating a CrossDocumentRelation entity."""
        rid = relation_id or generate_id(REL_PREFIX)
        return cls(
            id=rid,
            investigation_id=investigation_id,
            source_document_id=source_document_id,
            target_document_id=target_document_id,
            relation_type=relation_type,
            description=description.strip(),
            finding_id=finding_id,
            similarity_score=similarity_score,
        )
