"""Bidirectional mapper between Dossier domain entity and DossierModel."""

from __future__ import annotations

from veritrace.domain.entities.dossier import Dossier
from veritrace.infrastructure.persistence.mappers.converters import to_utc
from veritrace.infrastructure.persistence.models.dossier import DossierModel


class DossierMapper:
    """Maps between Dossier domain entity and SQLAlchemy DossierModel."""

    @staticmethod
    def to_model(entity: Dossier) -> DossierModel:
        """Convert Dossier domain entity to SQLAlchemy model."""
        return DossierModel(
            id=entity.id,
            investigation_id=entity.investigation_id,
            dossier_data=entity.dossier_data,
            pdf_storage_path=entity.pdf_storage_path,
            pdf_hash_sha256=entity.pdf_hash_sha256,
            generated_at=to_utc(entity.generated_at),
        )

    @staticmethod
    def to_entity(model: DossierModel) -> Dossier:
        """Convert SQLAlchemy DossierModel to Dossier domain entity."""
        generated_at = to_utc(model.generated_at)
        assert generated_at is not None
        return Dossier(
            id=model.id,
            investigation_id=model.investigation_id,
            dossier_data=model.dossier_data,
            pdf_storage_path=model.pdf_storage_path,
            pdf_hash_sha256=model.pdf_hash_sha256,
            generated_at=generated_at,
        )
