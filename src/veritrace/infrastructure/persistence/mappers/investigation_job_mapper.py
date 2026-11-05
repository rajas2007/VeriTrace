"""Bidirectional mapper between InvestigationJob domain entity and InvestigationJobModel."""

from __future__ import annotations

from veritrace.domain.entities.investigation_job import InvestigationJob
from veritrace.domain.enums.investigation import JobStatus
from veritrace.infrastructure.persistence.mappers.converters import to_utc
from veritrace.infrastructure.persistence.models.investigation_job import (
    InvestigationJobModel,
)


class InvestigationJobMapper:
    """Maps between InvestigationJob domain entity and SQLAlchemy InvestigationJobModel."""

    @staticmethod
    def to_model(entity: InvestigationJob) -> InvestigationJobModel:
        """Convert InvestigationJob domain entity to SQLAlchemy model."""
        return InvestigationJobModel(
            id=entity.id,
            investigation_id=entity.investigation_id,
            status=entity.status.value,
            current_stage=entity.current_stage,
            progress_pct=entity.progress_pct,
            stage_message=entity.stage_message,
            error_message=entity.error_message,
            can_resume=entity.can_resume,
            retry_count=entity.retry_count,
            max_retries=entity.max_retries,
            started_at=to_utc(entity.started_at),
            completed_at=to_utc(entity.completed_at),
            created_at=to_utc(entity.created_at),
        )

    @staticmethod
    def to_entity(model: InvestigationJobModel) -> InvestigationJob:
        """Convert SQLAlchemy InvestigationJobModel to InvestigationJob domain entity."""
        created_at = to_utc(model.created_at)
        assert created_at is not None
        return InvestigationJob(
            id=model.id,
            investigation_id=model.investigation_id,
            status=JobStatus(model.status),
            current_stage=model.current_stage,
            progress_pct=model.progress_pct,
            created_at=created_at,
            stage_message=model.stage_message,
            error_message=model.error_message,
            can_resume=model.can_resume,
            retry_count=model.retry_count,
            max_retries=model.max_retries,
            started_at=to_utc(model.started_at),
            completed_at=to_utc(model.completed_at),
        )
