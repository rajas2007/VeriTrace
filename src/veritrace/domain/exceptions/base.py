"""Domain Exceptions Hierarchy for VeriTrace.

Defines the base error types and domain invariant violations following
Clean Architecture principles.
"""

from __future__ import annotations


class VeriTraceError(Exception):
    """Base exception for all VeriTrace runtime and domain errors."""


class DomainError(VeriTraceError):
    """Base exception for domain invariant violations."""


class ValidationError(DomainError):
    """Raised when domain field validation fails."""


class InvalidIdentifierError(ValidationError):
    """Raised when an identifier does not match expected prefix or format."""


class InvalidTimestampError(ValidationError):
    """Raised when a timestamp is naive (lacks UTC) or chronologically invalid."""


class CoordinateBoundsError(ValidationError):
    """Raised when bounding box coordinates violate [0.0, 1.0] or ordering rules."""


class ConfidenceRangeError(ValidationError):
    """Raised when a probability or confidence value is outside [0.0, 1.0]."""


class InvalidStateTransitionError(DomainError):
    """Raised when an invalid state transition is attempted on an entity."""


class RelationshipConstraintError(DomainError):
    """Raised when an entity relationship or foreign-key boundary is violated."""


class UnauthorizedActionError(DomainError):
    """Raised when an operation violates role-based access or signatory governance."""


class AiModificationForbiddenError(DomainError):
    """Raised when an AI actor attempts to create, modify, or adjudicate domain findings.

    INVARIANT: AI must not be allowed to create, modify, confirm, dismiss,
    or change the severity of domain findings.
    """


class DocumentIngestionError(VeriTraceError):
    """Raised when document ingestion fails at file intake."""


class UnsupportedFormatError(DocumentIngestionError):
    """Raised when file magic bytes or MIME type is unsupported."""


class CorruptedDocumentError(DocumentIngestionError):
    """Raised when file header or contents are corrupted/unreadable."""


class DocumentExtractionError(VeriTraceError):
    """Raised when vector rasterization or OCR engine fails."""


class ExtractionQualityError(VeriTraceError):
    """Raised when extraction quality fails strict verification gates."""
