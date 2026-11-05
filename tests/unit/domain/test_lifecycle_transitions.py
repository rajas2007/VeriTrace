"""Unit tests for Investigation and InvestigationJob lifecycle state transitions."""

import pytest

from veritrace.domain.entities.investigation import Investigation
from veritrace.domain.entities.investigation_job import InvestigationJob
from veritrace.domain.enums.investigation import (
    InvestigationStatus,
    JobStatus,
    RiskClassification,
)
from veritrace.domain.exceptions import (
    ConfidenceRangeError,
    InvalidStateTransitionError,
    ValidationError,
)
from veritrace.domain.value_objects.identifiers import (
    INV_PREFIX,
    generate_id,
)


def test_investigation_lifecycle_success_path() -> None:
    """Verify standard happy path of investigation lifecycle."""
    inv = Investigation.create(
        title="Vendor Invoice Forensic Audit",
        reference_code="INV-2026-001",
    )
    assert inv.status == InvestigationStatus.DRAFT

    # DRAFT -> PROCESSING
    inv.transition_to(InvestigationStatus.PROCESSING)
    assert inv.status == InvestigationStatus.PROCESSING

    # PROCESSING -> WAITING_REVIEW
    inv.transition_to(InvestigationStatus.WAITING_REVIEW)
    assert inv.status == InvestigationStatus.WAITING_REVIEW

    # WAITING_REVIEW -> COMPLETED
    inv.transition_to(InvestigationStatus.COMPLETED)
    assert inv.status == InvestigationStatus.COMPLETED


def test_investigation_same_state_is_noop() -> None:
    """Verify transitioning to the same state does not raise."""
    inv = Investigation.create(title="Audit", reference_code="REF-1")
    inv.transition_to(InvestigationStatus.DRAFT)
    assert inv.status == InvestigationStatus.DRAFT


def test_investigation_invalid_transition_raises() -> None:
    """Verify illegal jumps across states raise InvalidStateTransitionError."""
    inv = Investigation.create(title="Audit", reference_code="REF-1")
    # Cannot jump DRAFT -> COMPLETED directly
    with pytest.raises(InvalidStateTransitionError):
        inv.transition_to(InvestigationStatus.COMPLETED)


def test_investigation_terminal_completed_state() -> None:
    """Verify COMPLETED is terminal and cannot transition further."""
    inv = Investigation.create(
        title="Audit",
        reference_code="REF-1",
        status=InvestigationStatus.COMPLETED,
    )
    with pytest.raises(InvalidStateTransitionError):
        inv.transition_to(InvestigationStatus.PROCESSING)
    with pytest.raises(InvalidStateTransitionError):
        inv.transition_to(InvestigationStatus.DRAFT)


def test_investigation_risk_score_update() -> None:
    """Verify risk score bounds and classification updates."""
    inv = Investigation.create(title="Audit", reference_code="REF-1")
    assert inv.risk_score == 0.0
    assert inv.risk_classification == RiskClassification.UNDETERMINED

    inv.update_risk_score(0.85, RiskClassification.SUSPECTED_MANIPULATION)
    assert inv.risk_score == 0.85
    assert inv.risk_classification == RiskClassification.SUSPECTED_MANIPULATION

    with pytest.raises(ConfidenceRangeError):
        inv.update_risk_score(1.5)
    with pytest.raises(ConfidenceRangeError):
        inv.update_risk_score(-0.1)


def test_investigation_job_lifecycle_success_path() -> None:
    """Verify happy path of InvestigationJob."""
    job = InvestigationJob.create(
        investigation_id=generate_id(INV_PREFIX),
        current_stage="INIT",
    )
    assert job.status == JobStatus.QUEUED
    assert job.progress_pct == 0
    assert job.started_at is None

    # QUEUED -> RUNNING sets started_at
    job.transition_to(JobStatus.RUNNING)
    assert job.status == JobStatus.RUNNING
    assert job.started_at is not None

    # Update progress
    job.update_progress(45, stage="OCR", message="Extracting page 3")
    assert job.progress_pct == 45
    assert job.current_stage == "OCR"
    assert job.stage_message == "Extracting page 3"

    # Complete sets 100% and completed_at
    job.complete()
    assert job.status == JobStatus.COMPLETED
    assert job.progress_pct == 100
    assert job.completed_at is not None


def test_investigation_job_failure_and_retry() -> None:
    """Verify job failure and retry count tracking."""
    job = InvestigationJob.create(
        investigation_id=generate_id(INV_PREFIX),
        max_retries=2,
        can_resume=False,
    )
    job.transition_to(JobStatus.RUNNING)

    # Fail job
    job.fail("Connection timed out to OCR engine")
    assert job.status == JobStatus.FAILED
    assert job.error_message == "Connection timed out to OCR engine"
    assert job.retry_count == 0

    # Retry 1: FAILED -> QUEUED
    job.transition_to(JobStatus.QUEUED)
    assert job.status == JobStatus.QUEUED
    assert job.retry_count == 1

    # Run and fail again
    job.transition_to(JobStatus.RUNNING)
    job.fail("Disk write failure")

    # Retry 2: FAILED -> QUEUED
    job.transition_to(JobStatus.QUEUED)
    assert job.retry_count == 2

    # Run and fail 3rd time
    job.transition_to(JobStatus.RUNNING)
    job.fail("Exhausted retries error")

    # Retry 3: exceeds max_retries (2) -> must raise InvalidStateTransitionError
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        job.transition_to(JobStatus.QUEUED)
    assert "exceeded max retries (2)" in str(exc_info.value)


def test_investigation_job_resumable_bypasses_retry_limit() -> None:
    """Verify a resumable job can be re-queued even after max retries."""
    job = InvestigationJob.create(
        investigation_id=generate_id(INV_PREFIX),
        max_retries=1,
        can_resume=True,
    )
    job.transition_to(JobStatus.RUNNING)
    job.fail("Error 1")
    job.transition_to(JobStatus.QUEUED)  # retry_count = 1

    job.transition_to(JobStatus.RUNNING)
    job.fail("Error 2")

    # Because can_resume=True, retry succeeds despite retry_count >= 1
    job.transition_to(JobStatus.QUEUED)
    assert job.retry_count == 2
    assert job.status == JobStatus.QUEUED


def test_investigation_job_terminal_states() -> None:
    """Verify terminal states COMPLETED and CANCELLED reject transitions."""
    job_completed = InvestigationJob.create(
        investigation_id=generate_id(INV_PREFIX),
        status=JobStatus.COMPLETED,
    )
    with pytest.raises(InvalidStateTransitionError):
        job_completed.transition_to(JobStatus.RUNNING)

    job_cancelled = InvestigationJob.create(
        investigation_id=generate_id(INV_PREFIX),
        status=JobStatus.CANCELLED,
    )
    with pytest.raises(InvalidStateTransitionError):
        job_cancelled.transition_to(JobStatus.RUNNING)


def test_investigation_job_progress_bounds() -> None:
    """Verify progress percentage validation [0, 100]."""
    job = InvestigationJob.create(investigation_id=generate_id(INV_PREFIX))
    with pytest.raises(ValidationError):
        job.update_progress(-1)
    with pytest.raises(ValidationError):
        job.update_progress(101)
