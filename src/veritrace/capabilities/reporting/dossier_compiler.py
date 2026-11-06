"""Dossier compilation orchestrator producing standardized JSON payloads and signed PDF reports."""

from __future__ import annotations

import hashlib
from pathlib import Path

from veritrace.capabilities.forensics.models import ForensicProposal
from veritrace.capabilities.reporting.json_builder import JsonDossierBuilder
from veritrace.capabilities.reporting.models import InvestigationDossierPayload
from veritrace.capabilities.reporting.pdf_builder import PdfDossierBuilder
from veritrace.domain.entities.document import Document
from veritrace.domain.entities.dossier import Dossier
from veritrace.domain.entities.evidence import Evidence
from veritrace.domain.entities.extracted_field import ExtractedField
from veritrace.domain.entities.finding import Finding
from veritrace.domain.entities.investigation import Investigation
from veritrace.domain.rules.base import RuleEvaluationResult
from veritrace.domain.value_objects.identifiers import DOS_PREFIX, generate_id, utc_now


class DossierCompiler:
    """Public orchestration facade compiling complete PS-2 Investigation Dossiers

    in both machine-readable JSON format and auditor-grade printable PDF format.
    """

    def __init__(
        self,
        json_builder: JsonDossierBuilder | None = None,
        pdf_builder: PdfDossierBuilder | None = None,
    ) -> None:
        self._json_builder = json_builder or JsonDossierBuilder()
        self._pdf_builder = pdf_builder or PdfDossierBuilder()

    def compile_dossier(
        self,
        investigation: Investigation,
        documents: list[Document],
        fields: list[ExtractedField],
        rule_evaluations: list[RuleEvaluationResult],
        findings_or_proposals: list[Finding] | list[ForensicProposal],
        evidence_records: list[Evidence],
        executive_narrative: str,
        output_dir: Path | str,
        dossier_id: str | None = None,
    ) -> tuple[Dossier, InvestigationDossierPayload, Path, Path]:
        """Compile complete investigation dossier and persist both JSON and PDF outputs.

        Args:
            investigation: Root investigation domain entity.
            documents: List of ingested document entities.
            fields: Granular extracted field entities.
            rule_evaluations: Outcomes of contextual arithmetic and chronology rules.
            findings_or_proposals: Flagged forensic findings or proposals.
            evidence_records: Supporting pixel-anchored evidence crops.
            executive_narrative: Auditor-grade natural language summary.
            output_dir: Output directory where artifacts will be saved.
            dossier_id: Optional predetermined Dossier entity identifier.

        Returns:
            Tuple of (Dossier domain entity, InvestigationDossierPayload, PDF Path, JSON Path).
        """
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        did = dossier_id or generate_id(DOS_PREFIX)
        json_file_path = out_path / f"{investigation.id}_dossier.json"
        pdf_file_path = out_path / f"{investigation.id}_dossier.pdf"

        # 1. Assemble structured 6-section payload
        payload = self._json_builder.build_payload(
            investigation=investigation,
            documents=documents,
            fields=fields,
            rule_evaluations=rule_evaluations,
            findings_or_proposals=findings_or_proposals,
            evidence_records=evidence_records,
            executive_narrative=executive_narrative,
        )

        # 2. Write structured JSON dossier
        with open(json_file_path, "w", encoding="utf-8") as f:
            f.write(payload.to_json(indent=2))

        # 3. Render printable ReportLab PDF dossier
        self._pdf_builder.build_pdf(payload=payload, output_pdf_path=pdf_file_path)

        # 4. Compute cryptographic SHA-256 hash of compiled PDF
        hasher = hashlib.sha256()
        with open(pdf_file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        pdf_sha256 = hasher.hexdigest()

        # 5. Instantiate Dossier domain entity
        dossier_entity = Dossier.create(
            investigation_id=investigation.id,
            dossier_data=payload.to_dict(),
            pdf_storage_path=str(pdf_file_path),
            pdf_hash_sha256=pdf_sha256,
            dossier_id=did,
            generated_at=utc_now(),
        )

        return dossier_entity, payload, pdf_file_path, json_file_path
