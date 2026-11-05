"""Bidirectional mapper between AuthorizedSubject domain entity and AuthorizedSubjectModel."""

from __future__ import annotations

from veritrace.domain.entities.authorized_subject import AuthorizedSubject
from veritrace.infrastructure.persistence.mappers.converters import to_utc
from veritrace.infrastructure.persistence.models.authorized_subject import (
    AuthorizedSubjectModel,
)


class AuthorizedSubjectMapper:
    """Maps between AuthorizedSubject domain entity and SQLAlchemy AuthorizedSubjectModel."""

    @staticmethod
    def to_model(entity: AuthorizedSubject) -> AuthorizedSubjectModel:
        """Convert AuthorizedSubject domain entity to SQLAlchemy model."""
        return AuthorizedSubjectModel(
            id=entity.id,
            organization_id=entity.organization_id,
            full_name=entity.full_name,
            designation=entity.designation,
            id_reference=entity.id_reference,
            created_at=to_utc(entity.created_at),
        )

    @staticmethod
    def to_entity(model: AuthorizedSubjectModel) -> AuthorizedSubject:
        """Convert SQLAlchemy AuthorizedSubjectModel to AuthorizedSubject domain entity."""
        created_at = to_utc(model.created_at)
        assert created_at is not None
        return AuthorizedSubject(
            id=model.id,
            organization_id=model.organization_id,
            full_name=model.full_name,
            designation=model.designation,
            id_reference=model.id_reference,
            created_at=created_at,
        )
