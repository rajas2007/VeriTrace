"""Cross-document intelligence and correlation capability.

Provides:
- Strongly typed normalization models (NormalizedQuantity, NormalizedAmount, etc.)
- Deterministic normalizers (quantity, amount, date, material grade, etc.)
- 4-tier entity aligner with anti-override protection
- CrossDocumentCorrelationEngine orchestrating cross-document consistency checks
"""

from __future__ import annotations

from veritrace.capabilities.correlation.engine import CrossDocumentCorrelationEngine
from veritrace.capabilities.correlation.entity_aligner import EntityAligner
from veritrace.capabilities.correlation.models import (
    AlignedEntityPair,
    AlignmentTier,
    ComparisonResult,
    CrossDocumentCorrelationResult,
    DocumentCorrelationInput,
    LineItemAggregation,
    NormalizedAmount,
    NormalizedDate,
    NormalizedIdentifier,
    NormalizedMaterialGrade,
    NormalizedOrganizationName,
    NormalizedQuantity,
)
from veritrace.capabilities.correlation.normalization import (
    normalize_amount,
    normalize_date,
    normalize_identifier,
    normalize_material_grade,
    normalize_organization_name,
    normalize_quantity,
)

__all__ = [
    "AlignedEntityPair",
    "AlignmentTier",
    "ComparisonResult",
    "CrossDocumentCorrelationEngine",
    "CrossDocumentCorrelationResult",
    "DocumentCorrelationInput",
    "EntityAligner",
    "LineItemAggregation",
    "NormalizedAmount",
    "NormalizedDate",
    "NormalizedIdentifier",
    "NormalizedMaterialGrade",
    "NormalizedOrganizationName",
    "NormalizedQuantity",
    "normalize_amount",
    "normalize_date",
    "normalize_identifier",
    "normalize_material_grade",
    "normalize_organization_name",
    "normalize_quantity",
]
