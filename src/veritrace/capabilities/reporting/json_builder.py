"""Builder compiling domain entities and forensic findings into PS-2 JSON dossier payloads."""

from __future__ import annotations

from veritrace.capabilities.forensics.models import ForensicProposal
from veritrace.capabilities.reporting.models import (
    ContextualInconsistencyItem,
    DocumentOverviewItem,
    EvidenceTraceabilityItem,
    ExtractedFieldItem,
    InvestigationDossierPayload,
    InvestigationSummarySection,
    VisualForensicItem,
)
from veritrace.domain.entities.document import Document
from veritrace.domain.entities.evidence import Evidence
from veritrace.domain.entities.extracted_field import ExtractedField
from veritrace.domain.entities.finding import Finding
from veritrace.domain.entities.investigation import Investigation
from veritrace.domain.enums.forensic import EpistemicTier, FindingCategory
from veritrace.domain.rules.base import RuleEvaluationResult
from veritrace.domain.value_objects.identifiers import utc_now


class JsonDossierBuilder:
    """Assembles all investigative artifacts into a structured 6-section JSON dossier."""

    def build_payload(
        self,
        investigation: Investigation,
        documents: list[Document],
        fields: list[ExtractedField],
        rule_evaluations: list[RuleEvaluationResult],
        findings_or_proposals: list[Finding] | list[ForensicProposal],
        evidence_records: list[Evidence],
        executive_narrative: str,
    ) -> InvestigationDossierPayload:
        """Construct typed InvestigationDossierPayload adhering to PS-2 Section 7."""
        # Section 1: Document Overview
        sec1: list[DocumentOverviewItem] = []
        for doc in documents:
            sec1.append(
                DocumentOverviewItem(
                    document_id=doc.id,
                    filename=doc.original_filename,
                    mime_type=doc.mime_type,
                    file_size_bytes=doc.file_size_bytes,
                    sha256_hash=doc.file_hash_sha256,
                    page_count=doc.page_count,
                    document_type=doc.document_type.value,
                    status=doc.status.value,
                    ingested_at=doc.created_at.isoformat(),
                )
            )

        # Section 2: Extracted Information
        sec2: list[ExtractedFieldItem] = []
        for f in fields:
            sec2.append(
                ExtractedFieldItem(
                    field_name=f.field_name,
                    field_value=f.field_value,
                    confidence=round(f.confidence, 4),
                    language=f.language,
                    script=f.script,
                )
            )

        # Section 3: Contextual Analysis (failed rules)
        sec3: list[ContextualInconsistencyItem] = []
        for r in rule_evaluations:
            if not r.passed:
                sec3.append(
                    ContextualInconsistencyItem(
                        rule_name=r.rule_name,
                        category=r.category.value,
                        description=r.explanation,
                        expected_value=r.expected_value,
                        observed_value=r.observed_value,
                        discrepancy=r.discrepancy,
                        affected_fields=r.affected_field_names,
                    )
                )

        # Section 4: Visual Forensic Findings
        sec4: list[VisualForensicItem] = []
        for item in findings_or_proposals:
            if isinstance(item, ForensicProposal):
                sec4.append(
                    VisualForensicItem(
                        finding_id="prop_candidate",
                        category=item.category.value,
                        epistemic_tier=item.epistemic_tier.value,
                        severity=item.severity.value,
                        title=item.title,
                        explanation=item.narrative_explanation,
                        confidence=round(item.confidence, 4),
                        measurements=item.measurements,
                        evidence_crop_path=(
                            str(item.evidence_crop_path) if item.evidence_crop_path else None
                        ),
                    )
                )
            elif isinstance(item, Finding):
                sec4.append(
                    VisualForensicItem(
                        finding_id=item.id,
                        category=item.category.value,
                        epistemic_tier=item.epistemic_tier.value,
                        severity=item.severity.value,
                        title=item.title,
                        explanation=item.narrative_explanation,
                        confidence=round(item.confidence, 4),
                    )
                )

        # Section 5: Evidence Traceability
        sec5: list[EvidenceTraceabilityItem] = []
        for ev in evidence_records:
            sec5.append(
                EvidenceTraceabilityItem(
                    evidence_id=ev.id,
                    page_number=1,
                    normalized_bbox={
                        "ymin": round(ev.norm_ymin, 4),
                        "xmin": round(ev.norm_xmin, 4),
                        "ymax": round(ev.norm_ymax, 4),
                        "xmax": round(ev.norm_xmax, 4),
                    },
                    crop_image_path=ev.crop_image_path,
                    heatmap_image_path=ev.heatmap_image_path,
                    grounding_explanation=ev.grounding_explanation,
                )
            )

        # Section 6: Summary & Risk Breakdown
        tier_counts: dict[str, int] = {}
        cat_counts: dict[str, int] = {}
        for item in findings_or_proposals:
            t = (
                item.epistemic_tier.value
                if isinstance(item.epistemic_tier, EpistemicTier)
                else str(item.epistemic_tier)
            )
            c = (
                item.category.value
                if isinstance(item.category, FindingCategory)
                else str(item.category)
            )
            tier_counts[t] = tier_counts.get(t, 0) + 1
            cat_counts[c] = cat_counts.get(c, 0) + 1

        sec6 = InvestigationSummarySection(
            executive_narrative=executive_narrative,
            risk_score=round(investigation.risk_score, 4),
            risk_classification=investigation.risk_classification.value,
            findings_by_tier=tier_counts,
            findings_by_category=cat_counts,
            limitations=[
                "Static 2D image analysis cannot reconstruct dynamic writing speed or pressure.",
                "Scanned resolution below 200 DPI increases character segmentation uncertainty.",
                "Machine observations are empirical findings requiring human examiner review.",
            ],
            reviewed_at=utc_now().isoformat(),
        )

        return InvestigationDossierPayload(
            investigation_id=investigation.id,
            case_reference=investigation.reference_code,
            generated_at=utc_now().isoformat(),
            section_1_document_overview=sec1,
            section_2_extracted_information=sec2,
            section_3_contextual_analysis=sec3,
            section_4_visual_forensic_findings=sec4,
            section_5_evidence_traceability=sec5,
            section_6_investigation_summary=sec6,
        )
