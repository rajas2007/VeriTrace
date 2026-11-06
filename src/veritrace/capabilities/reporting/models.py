"""Data models for PS-2 compliant Investigation Dossiers (Sections 7.1 to 7.6)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class DocumentOverviewItem:
    """PS-2 Section 7.1: Document Overview record."""

    document_id: str
    filename: str
    mime_type: str
    file_size_bytes: int
    sha256_hash: str
    page_count: int
    document_type: str
    status: str
    ingested_at: str


@dataclass(slots=True)
class ExtractedFieldItem:
    """PS-2 Section 7.2: Granular extracted field record with OCR confidence."""

    field_name: str
    field_value: str
    confidence: float
    page_number: int = 1
    language: str | None = None
    script: str | None = None


@dataclass(slots=True)
class ContextualInconsistencyItem:
    """PS-2 Section 7.3: Contextual, arithmetic, and chronological discrepancy record."""

    rule_name: str
    category: str
    description: str
    expected_value: Any = None
    observed_value: Any = None
    discrepancy: float = 0.0
    affected_fields: list[str] = field(default_factory=list)


@dataclass(slots=True)
class VisualForensicItem:
    """PS-2 Section 7.4: Visual forensic anomaly record (ELA, baselines, copy-move, signatures)."""

    finding_id: str
    category: str
    epistemic_tier: str
    severity: str
    title: str
    explanation: str
    confidence: float
    measurements: dict[str, Any] = field(default_factory=dict)
    evidence_crop_path: str | None = None


@dataclass(slots=True)
class EvidenceTraceabilityItem:
    """PS-2 Section 7.5: Coordinate anchor linking finding to original document page crop."""

    evidence_id: str
    page_number: int
    normalized_bbox: dict[str, float]
    crop_image_path: str
    heatmap_image_path: str | None = None
    grounding_explanation: str | None = None


@dataclass(slots=True)
class InvestigationSummarySection:
    """PS-2 Section 7.6: Investigation summary narrative, risk score, and auditor sign-off."""

    executive_narrative: str
    risk_score: float
    risk_classification: str
    findings_by_tier: dict[str, int] = field(default_factory=dict)
    findings_by_category: dict[str, int] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    examiner_name: str = "Lead Forensic Document Examiner"
    reviewed_at: str | None = None


@dataclass(slots=True)
class InvestigationDossierPayload:
    """Complete 6-Section Investigation Dossier conforming strictly to Hackathon PS-2."""

    investigation_id: str
    case_reference: str
    generated_at: str
    section_1_document_overview: list[DocumentOverviewItem] = field(default_factory=list)
    section_2_extracted_information: list[ExtractedFieldItem] = field(default_factory=list)
    section_3_contextual_analysis: list[ContextualInconsistencyItem] = field(default_factory=list)
    section_4_visual_forensic_findings: list[VisualForensicItem] = field(default_factory=list)
    section_5_evidence_traceability: list[EvidenceTraceabilityItem] = field(default_factory=list)
    section_6_investigation_summary: InvestigationSummarySection = field(
        default_factory=lambda: InvestigationSummarySection(
            executive_narrative="", risk_score=0.0, risk_classification="UNDETERMINED"
        )
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert dossier payload into serializable dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serialize dossier payload into JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)

