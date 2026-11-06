"""Application Data Transfer Objects."""

from veritrace.application.dto.correlation import (
    CorrelationDiscrepancyDTO,
    CorrelationRequestDTO,
    CorrelationSummaryDTO,
)
from veritrace.application.dto.document import (
    DocumentIngestDTO,
    DocumentIngestionResultDTO,
)
from veritrace.application.dto.dossier import (
    DossierExportRequestDTO,
    DossierExportResultDTO,
)
from veritrace.application.dto.extraction import (
    DocumentExtractionResultDTO,
    PageExtractionResultDTO,
)
from veritrace.application.dto.forensics import (
    ContextualAuditItemDTO,
    SignatureComparisonDTO,
    SignatureDetectionDTO,
)
from veritrace.application.dto.investigation import (
    EvidenceResponseDTO,
    FindingResponseDTO,
    InvestigationCreateDTO,
    InvestigationResponseDTO,
    InvestigationUpdateDTO,
    RelationResponseDTO,
    ReviewDecisionDTO,
    ReviewFindingRequestDTO,
)

__all__ = [
    "ContextualAuditItemDTO",
    "CorrelationDiscrepancyDTO",
    "CorrelationRequestDTO",
    "CorrelationSummaryDTO",
    "DocumentExtractionResultDTO",
    "DocumentIngestDTO",
    "DocumentIngestionResultDTO",
    "DossierExportRequestDTO",
    "DossierExportResultDTO",
    "EvidenceResponseDTO",
    "FindingResponseDTO",
    "InvestigationCreateDTO",
    "InvestigationResponseDTO",
    "InvestigationUpdateDTO",
    "PageExtractionResultDTO",
    "RelationResponseDTO",
    "ReviewDecisionDTO",
    "ReviewFindingRequestDTO",
    "SignatureComparisonDTO",
    "SignatureDetectionDTO",
]
