"""Investigation and Job lifecycle status enums."""

from enum import StrEnum


class InvestigationStatus(StrEnum):
    """Lifecycle stages of an Investigation case container."""

    DRAFT = "DRAFT"
    PROCESSING = "PROCESSING"
    WAITING_REVIEW = "WAITING_REVIEW"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobStatus(StrEnum):
    """Execution lifecycle of an asynchronous processing job."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING_REVIEW = "WAITING_REVIEW"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ProcessingStatus(StrEnum):
    """Uniform status lifecycle across ingestion, extraction, and background jobs."""

    PENDING = "pending"
    VALIDATING = "validating"
    INGESTING = "ingesting"
    EXTRACTING = "extracting"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RiskClassification(StrEnum):
    """Overall forensic risk classification assigned to an investigation."""

    UNDETERMINED = "UNDETERMINED"
    LOW_RISK = "LOW_RISK"
    FLAGGED_INCONSISTENCY = "FLAGGED_INCONSISTENCY"
    SUSPECTED_MANIPULATION = "SUSPECTED_MANIPULATION"
