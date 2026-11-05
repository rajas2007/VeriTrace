"""Domain exception classes and error hierarchies."""

from veritrace.domain.exceptions.base import (
    AiModificationForbiddenError,
    ConfidenceRangeError,
    CoordinateBoundsError,
    CorruptedDocumentError,
    DocumentExtractionError,
    DocumentIngestionError,
    DomainError,
    ExtractionQualityError,
    InvalidIdentifierError,
    InvalidStateTransitionError,
    InvalidTimestampError,
    RelationshipConstraintError,
    UnauthorizedActionError,
    UnsupportedFormatError,
    ValidationError,
    VeriTraceError,
)

__all__ = [
    "AiModificationForbiddenError",
    "ConfidenceRangeError",
    "CoordinateBoundsError",
    "CorruptedDocumentError",
    "DocumentExtractionError",
    "DocumentIngestionError",
    "DomainError",
    "ExtractionQualityError",
    "InvalidIdentifierError",
    "InvalidStateTransitionError",
    "InvalidTimestampError",
    "RelationshipConstraintError",
    "UnauthorizedActionError",
    "UnsupportedFormatError",
    "ValidationError",
    "VeriTraceError",
]
