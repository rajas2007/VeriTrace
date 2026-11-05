"""InvestigationJob domain entity managing asynchronous processing lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from veritrace.domain.enums.investigation import JobStatus
from veritrace.domain.exceptions.base import (
    InvalidStateTransitionError,
    ValidationError,
)
from veritrace.domain.value_objects.identifiers import (
    INV_PREFIX,
    JOB_PREFIX,
    ensure_utc,
    generate_id,
    utc_now,
    validate_id,
)

_VALID_JOB_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.QUEUED: {JobStatus.RUNNING, JobStatus.CANCELLED},
    JobStatus.RUNNING: {
        JobStatus.WAITING_REVIEW,
        JobStatus.COMPLETED,
        JobStatus.FAILED,
        JobStatus.CANCELLED,
    },
    JobStatus.WAITING_REVIEW: {
        JobStatus.RUNNING,
        JobStatus.COMPLETED,
        JobStatus.FAILED,
        JobStatus.CANCELLED,
    },
    JobStatus.COMPLETED: set(),  # Terminal
    JobStatus.CANCELLED: set(),  # Terminal
    JobStatus.FAILED: {JobStatus.QUEUED},  # Permitted on retry if eligible
}


@dataclass(slots=True)
class InvestigationJob:
    """Manages persistent asynchronous job lifecycle, progress, and failure recovery."""

    id: str
    investigation_id: str
    status: JobStatus
    current_stage: str
    progress_pct: int
    created_at: datetime
    stage_message: str | None = None
    error_message: str | None = None
    can_resume: bool = False
    retry_count: int = 0
    max_retries: int = 3
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        self.id = validate_id(self.id, JOB_PREFIX, "InvestigationJob.id")
        self.investigation_id = validate_id(
            self.investigation_id, INV_PREFIX, "InvestigationJob.investigation_id"
        )
        if not (0 <= self.progress_pct <= 100):
            raise ValidationError(
                f"progress_pct must be in range [0, 100], got {self.progress_pct}"
            )
        if self.retry_count < 0:
            raise ValidationError("retry_count cannot be negative")
        if self.max_retries < 0:
            raise ValidationError("max_retries cannot be negative")

        self.created_at = ensure_utc(self.created_at, "InvestigationJob.created_at")
        if self.started_at is not None:
            self.started_at = ensure_utc(self.started_at, "InvestigationJob.started_at")
        if self.completed_at is not None:
            self.completed_at = ensure_utc(self.completed_at, "InvestigationJob.completed_at")

    def transition_to(self, new_status: JobStatus) -> None:
        """Transition job status enforcing lifecycle invariant rules."""
        if self.status == new_status:
            return

        valid_targets = _VALID_JOB_TRANSITIONS.get(self.status, set())

        # If transitioning from FAILED to QUEUED, verify retry eligibility
        if self.status == JobStatus.FAILED and new_status == JobStatus.QUEUED:
            if not self.can_resume and self.retry_count >= self.max_retries:
                raise InvalidStateTransitionError(
                    f"Job {self.id} exceeded max retries ({self.max_retries}) and is not resumable."
                )
            self.retry_count += 1

        if new_status not in valid_targets:
            raise InvalidStateTransitionError(
                f"Invalid transition for job from {self.status.value} to {new_status.value}."
            )

        self.status = new_status
        now = utc_now()
        if new_status == JobStatus.RUNNING and self.started_at is None:
            self.started_at = now
        elif new_status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
            self.completed_at = now

    def update_progress(
        self,
        progress_pct: int,
        stage: str | None = None,
        message: str | None = None,
    ) -> None:
        """Update job stage progress and human-readable message."""
        if not (0 <= progress_pct <= 100):
            raise ValidationError(f"progress_pct must be in range [0, 100], got {progress_pct}")
        self.progress_pct = progress_pct
        if stage:
            self.current_stage = stage
        if message is not None:
            self.stage_message = message

    def complete(self) -> None:
        """Mark job as successfully completed at 100% progress."""
        self.update_progress(100, stage="COMPLETE", message="Job completed successfully")
        self.transition_to(JobStatus.COMPLETED)

    def fail(self, error_message: str) -> None:
        """Mark job as failed with error message."""
        self.error_message = error_message
        self.transition_to(JobStatus.FAILED)

    @classmethod
    def create(
        cls,
        investigation_id: str,
        job_id: str | None = None,
        status: JobStatus = JobStatus.QUEUED,
        current_stage: str = "INIT",
        progress_pct: int = 0,
        max_retries: int = 3,
        can_resume: bool = False,
        created_at: datetime | None = None,
    ) -> InvestigationJob:
        """Factory method creating an InvestigationJob entity."""
        jid = job_id or generate_id(JOB_PREFIX)
        ts = created_at or utc_now()
        return cls(
            id=jid,
            investigation_id=investigation_id,
            status=status,
            current_stage=current_stage,
            progress_pct=progress_pct,
            can_resume=can_resume,
            max_retries=max_retries,
            created_at=ts,
        )
