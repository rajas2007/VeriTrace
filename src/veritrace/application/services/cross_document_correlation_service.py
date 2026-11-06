"""Application service orchestrating cross-document intelligence and correlation.

Coordinates:
1. Investigation and document retrieval scoped strictly to tenant boundary.
2. Extracted field gathering across PO, Delivery Challans, MTC, and Invoices.
3. Execution of the CrossDocumentCorrelationEngine.
4. Materialization of evidence-backed Finding domain entities.
5. Bidirectional linking and persistence of CrossDocumentRelation records.
6. Atomic transactional persistence and audit trail logging.
"""

from __future__ import annotations

from collections.abc import Callable

from veritrace.application.dto.correlation import (
    CorrelationDiscrepancyDTO,
    CorrelationRequestDTO,
    CorrelationSummaryDTO,
)
from veritrace.capabilities.correlation.engine import CrossDocumentCorrelationEngine
from veritrace.capabilities.correlation.models import DocumentCorrelationInput
from veritrace.domain.entities.audit_event import AuditEvent
from veritrace.domain.entities.cross_document_relation import CrossDocumentRelation
from veritrace.domain.entities.evidence import Evidence
from veritrace.domain.entities.extracted_field import ExtractedField
from veritrace.domain.entities.finding import Finding
from veritrace.domain.enums.audit import ActorType, AuditEventType
from veritrace.domain.enums.forensic import RelationType
from veritrace.domain.exceptions.base import EntityNotFoundError
from veritrace.domain.interfaces.unit_of_work import UnitOfWork
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox


class CrossDocumentCorrelationService:
    """Headless application service coordinating cross-document forensic correlation."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        correlation_engine: CrossDocumentCorrelationEngine | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._engine = correlation_engine or CrossDocumentCorrelationEngine()

    def correlate_investigation(
        self,
        request: CorrelationRequestDTO,
    ) -> CorrelationSummaryDTO:
        """Run full correlation across all documents in an investigation case."""
        with self._uow_factory() as uow:
            # 1. Verify investigation exists and belongs to organization
            investigation = uow.investigations.get_by_id(
                request.investigation_id, request.organization_id
            )
            if investigation is None:
                raise EntityNotFoundError(
                    f"Investigation '{request.investigation_id}' not found in "
                    f"organization '{request.organization_id}'"
                )

            # 2. Retrieve all documents belonging to this investigation
            documents = uow.documents.list_by_investigation(
                request.investigation_id, request.organization_id
            )

            # 3. Retrieve extracted fields for each document
            fields_by_id: dict[str, ExtractedField] = {}
            doc_inputs: list[DocumentCorrelationInput] = []

            for doc in documents:
                doc_type_str = (
                    doc.document_type.value
                    if hasattr(doc.document_type, "value")
                    else str(doc.document_type)
                )
                fields = uow.documents.list_extracted_fields_by_document(
                    doc.id, request.organization_id
                )
                for f in fields:
                    fields_by_id[f.id] = f

                doc_inputs.append(
                    DocumentCorrelationInput(
                        doc_id=doc.id,
                        doc_type=doc_type_str,
                        filename=doc.original_filename,
                        extracted_fields=fields,
                    )
                )

            # 4. Execute correlation engine
            engine = CrossDocumentCorrelationEngine(is_order_closed=request.is_order_closed)
            correlation_result = engine.correlate(request.investigation_id, doc_inputs)

            # 5. Materialize findings and evidence for each discrepancy
            discrepancy_dtos: list[CorrelationDiscrepancyDTO] = []
            findings_count = 0
            relations_count = 0

            for disc in correlation_result.discrepancies:
                finding = Finding.create(
                    investigation_id=request.investigation_id,
                    category=disc.category,
                    epistemic_tier=disc.epistemic_tier,
                    severity=disc.severity,
                    title=disc.title,
                    narrative_explanation=disc.explanation,
                    confidence=disc.confidence,
                    investigator_guidance=(
                        "Cross-document consistency check flagged an anomaly. "
                        "Examine visual crops and underlying transaction records."
                    ),
                )

                # Link visual evidence anchors for supporting extracted fields
                for fid in disc.evidence_field_ids:
                    field = fields_by_id.get(fid)
                    if field and field.page_id:
                        bbox = field.normalized_bbox or NormalizedBoundingBox(
                            ymin=0.0, xmin=0.0, ymax=1.0, xmax=1.0
                        )
                        evidence = Evidence.create(
                            page_id=field.page_id,
                            crop_image_path=f"evidence/crop_{field.id}.png",
                            normalized_bbox=bbox,
                            grounding_explanation=(
                                f"Extracted field '{field.field_name}': '{field.raw_text}'"
                            ),
                        )
                        uow.evidence.add(evidence, request.organization_id)
                        finding.link_evidence(evidence.id)

                # Persist the finding
                uow.findings.add(finding, request.organization_id)
                findings_count += 1

                # Persist directional CrossDocumentRelation if documents are distinct
                rel_id: str | None = None
                valid_source = disc.source_doc_id and disc.source_doc_id != "CASE_SUBMISSION"
                valid_target = disc.target_doc_id and disc.target_doc_id != "CASE_SUBMISSION"

                if valid_source and valid_target and disc.source_doc_id != disc.target_doc_id:
                    relation = CrossDocumentRelation.create(
                        investigation_id=request.investigation_id,
                        source_document_id=disc.source_doc_id,
                        target_document_id=disc.target_doc_id,
                        relation_type=RelationType.CONFLICTS_WITH,
                        description=disc.title,
                        finding_id=finding.id,
                        similarity_score=disc.confidence,
                    )
                    uow.investigations.add_relation(relation, request.organization_id)
                    rel_id = relation.id
                    relations_count += 1

                discrepancy_dtos.append(
                    CorrelationDiscrepancyDTO(
                        rule_code=disc.rule_code,
                        category=disc.category.value,
                        epistemic_tier=disc.epistemic_tier.value,
                        severity=disc.severity.value,
                        confidence=disc.confidence,
                        title=disc.title,
                        explanation=disc.explanation,
                        source_doc_id=disc.source_doc_id,
                        target_doc_id=disc.target_doc_id,
                        finding_id=finding.id,
                        relation_id=rel_id,
                        discrepancy_delta=disc.discrepancy_delta,
                        discrepancy_percent=disc.discrepancy_percent,
                    )
                )

            # 6. Persist corroborating relations
            for corrob in correlation_result.corroborations:
                valid_source = corrob.source_doc_id and corrob.source_doc_id != "CASE_SUBMISSION"
                valid_target = corrob.target_doc_id and corrob.target_doc_id != "CASE_SUBMISSION"

                if valid_source and valid_target and corrob.source_doc_id != corrob.target_doc_id:
                    relation = CrossDocumentRelation.create(
                        investigation_id=request.investigation_id,
                        source_document_id=corrob.source_doc_id,
                        target_document_id=corrob.target_doc_id,
                        relation_type=RelationType.CORROBORATES,
                        description=corrob.title,
                        finding_id=None,
                        similarity_score=corrob.confidence,
                    )
                    uow.investigations.add_relation(relation, request.organization_id)
                    relations_count += 1

            # 7. Append immutable audit event
            audit_event = AuditEvent.create(
                investigation_id=request.investigation_id,
                event_type=(
                    AuditEventType.ANOMALY_FLAGGED
                    if correlation_result.discrepancies
                    else AuditEventType.TEXT_EXTRACTED
                ),
                actor_type=ActorType.SYSTEM_PIPELINE,
                actor_id="correlation_engine",
                event_payload={
                    "documents_analyzed": len(documents),
                    "discrepancies_count": len(correlation_result.discrepancies),
                    "corroborations_count": len(correlation_result.corroborations),
                    "findings_created": findings_count,
                    "relations_created": relations_count,
                },
            )
            uow.audit_events.add(audit_event, request.organization_id)

            # Commit the atomic transaction
            uow.commit()

            return CorrelationSummaryDTO(
                investigation_id=request.investigation_id,
                organization_id=request.organization_id,
                documents_analyzed=len(documents),
                discrepancies_count=len(correlation_result.discrepancies),
                corroborations_count=len(correlation_result.corroborations),
                findings_generated=findings_count,
                relations_created=relations_count,
                discrepancies=discrepancy_dtos,
            )
