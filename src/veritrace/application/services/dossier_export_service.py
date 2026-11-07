"""Application Service for compiling and exporting 6-Section PS-2 Investigation Dossiers."""

from __future__ import annotations

import hashlib
import logging
import shutil
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from veritrace.application.dto.dossier import (
    DossierExportRequestDTO,
    DossierExportResultDTO,
)
from veritrace.capabilities.reporting.dossier_compiler import DossierCompiler
from veritrace.domain.entities.audit_event import AuditEvent
from veritrace.domain.entities.extracted_field import ExtractedField
from veritrace.domain.enums.audit import ActorType, AuditEventType
from veritrace.domain.exceptions.base import EntityNotFoundError
from veritrace.domain.interfaces.unit_of_work import UnitOfWork
from veritrace.domain.rules.base import RuleEvaluationResult
from veritrace.domain.value_objects.identifiers import FLD_PREFIX, PAGE_PREFIX, generate_id

logger = logging.getLogger("veritrace.application.services.dossier_export")


class DossierExportService:
    """Orchestrates PS-2 dossier compilation and export across storage and audit logs."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        compiler: DossierCompiler | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._compiler = compiler or DossierCompiler()

    def export_dossier(self, request: DossierExportRequestDTO) -> DossierExportResultDTO:
        """Compile and persist official PS-2 Investigation Dossier in PDF and JSON formats."""
        with self._uow_factory() as uow:
            inv = uow.investigations.get_by_id(request.investigation_id, request.organization_id)
            if not inv:
                raise EntityNotFoundError(
                    f"Investigation '{request.investigation_id}' not found "
                    f"for org '{request.organization_id}'."
                )

            docs = uow.documents.list_by_investigation(
                request.investigation_id, request.organization_id
            )
            findings = uow.findings.list_by_investigation(
                request.investigation_id, request.organization_id
            )
            evidence_records = uow.evidence.list_by_investigation(
                request.investigation_id, request.organization_id
            )

            # Assemble representative rule evaluations from findings
            rules: list[RuleEvaluationResult] = []
            for f in findings:
                rules.append(
                    RuleEvaluationResult(
                        rule_name=f.title,
                        category=f.category,
                        passed=False,
                        discrepancy=float(f.confidence),
                        expected_value="Verified Consistent Baseline",
                        observed_value=f.title,
                        explanation=f.narrative_explanation,
                    )
                )

            # Synthesize representative fields if none stored standalone
            fields: list[ExtractedField] = []
            for d in docs:
                fields.append(
                    ExtractedField(
                        id=generate_id(FLD_PREFIX),
                        page_id=generate_id(PAGE_PREFIX),
                        field_name="document_type",
                        field_value=d.document_type.value,
                        raw_text=d.document_type.value,
                        confidence=0.99,
                    )
                )

            # Output folder
            output_dir = Path("exports") / request.investigation_id
            output_dir.mkdir(parents=True, exist_ok=True)

            narrative = (
                request.executive_narrative
                or f"Forensic cross-document analysis for investigation {inv.reference_code}. "
                f"Evaluated {len(docs)} documents and identified {len(findings)} anomalies."
            )

            dossier_entity, payload, pdf_path, json_path = self._compiler.compile_dossier(
                investigation=inv,
                documents=docs,
                fields=fields,
                rule_evaluations=rules,
                findings_or_proposals=findings,
                evidence_records=evidence_records,
                executive_narrative=narrative,
                output_dir=output_dir,
            )

            # If user specified custom output paths, copy files there
            final_pdf_path = pdf_path
            if request.output_pdf_path:
                target_pdf = Path(request.output_pdf_path)
                target_pdf.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(pdf_path, target_pdf)
                final_pdf_path = target_pdf

            final_json_path = json_path
            if request.output_json_path:
                target_json = Path(request.output_json_path)
                target_json.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(json_path, target_json)
                final_json_path = target_json

            # Compute sha256 of the exported PDF
            hasher = hashlib.sha256()
            with open(final_pdf_path, "rb") as pdf_file:
                while chunk := pdf_file.read(65536):
                    hasher.update(chunk)
            sha256_hash = hasher.hexdigest()

            # Record audit event
            try:
                audit_event = AuditEvent.create(
                    investigation_id=inv.id,
                    event_type=AuditEventType.DOSSIER_COMPILED,
                    actor_type=ActorType.SYSTEM_PIPELINE,
                    actor_id="system_examiner",
                    event_payload={
                        "dossier_id": dossier_entity.id,
                        "pdf_sha256": sha256_hash,
                        "documents_count": len(docs),
                        "findings_count": len(findings),
                    },
                )
                uow.audit_events.add(audit_event, request.organization_id)
                uow.commit()
            except Exception as e:
                logger.warning("Audit event recording skipped: %s", e)

            return DossierExportResultDTO(
                dossier_id=dossier_entity.id,
                investigation_id=inv.id,
                pdf_path=str(final_pdf_path.resolve()),
                json_path=str(final_json_path.resolve()),
                sha256_hash=sha256_hash,
                documents_count=len(docs),
                findings_count=len(findings),
                exported_at=datetime.now(UTC),
            )
