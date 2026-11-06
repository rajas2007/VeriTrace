"""Application service for Investigation case management."""

from __future__ import annotations

from collections.abc import Callable

from veritrace.application.dto.document import DocumentIngestionResultDTO
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
from veritrace.domain.entities.audit_event import AuditEvent
from veritrace.domain.entities.document_page import DocumentPage
from veritrace.domain.entities.investigation import Investigation
from veritrace.domain.entities.review_decision import ReviewDecision
from veritrace.domain.enums.audit import ActorType, AuditEventType
from veritrace.domain.enums.forensic import ReviewDecisionType
from veritrace.domain.enums.investigation import InvestigationStatus
from veritrace.domain.exceptions.base import EntityNotFoundError
from veritrace.domain.interfaces.unit_of_work import UnitOfWork


class InvestigationService:
    """Coordinates lifecycle, retrieval, and updates for Investigation cases."""

    def __init__(self, uow_factory: Callable[[], UnitOfWork] | UnitOfWork) -> None:
        if callable(uow_factory):
            self._uow_factory = uow_factory
        else:
            self._uow_factory = lambda: uow_factory

    def _get_uow(self) -> UnitOfWork:
        return self._uow_factory()

    def create_investigation(
        self,
        dto: InvestigationCreateDTO,
        actor_id: str = "analyst_01",
    ) -> InvestigationResponseDTO:
        """Create a new investigation aggregate within an organization and record audit trail."""
        inv = Investigation.create(
            title=dto.title,
            reference_code=dto.reference_code,
            organization_id=dto.organization_id,
        )

        with self._get_uow() as uow:
            uow.investigations.add(inv)

            actor_type = (
                ActorType.HUMAN_ANALYST
                if "analyst" in actor_id.lower()
                else ActorType.SYSTEM_PIPELINE
            )
            audit_event = AuditEvent.create(
                investigation_id=inv.id,
                event_type=AuditEventType.CASE_CREATED,
                actor_type=actor_type,
                actor_id=actor_id,
                event_payload={
                    "title": inv.title,
                    "reference_code": inv.reference_code,
                    "organization_id": dto.organization_id,
                },
            )
            uow.audit_events.add(audit_event, dto.organization_id)

        assert inv.organization_id is not None
        return InvestigationResponseDTO(
            id=inv.id,
            organization_id=inv.organization_id,
            title=inv.title,
            reference_code=inv.reference_code,
            status=inv.status,
            risk_score=inv.risk_score,
            risk_classification=inv.risk_classification,
            created_at=inv.created_at,
            updated_at=inv.updated_at,
        )

    def get_investigation(
        self,
        investigation_id: str,
        organization_id: str,
    ) -> InvestigationResponseDTO | None:
        """Retrieve an investigation by ID, strictly enforcing organization ownership."""
        with self._get_uow() as uow:
            inv = uow.investigations.get_by_id(investigation_id, organization_id)
            if inv is None:
                return None
            assert inv.organization_id is not None
            return InvestigationResponseDTO(
                id=inv.id,
                organization_id=inv.organization_id,
                title=inv.title,
                reference_code=inv.reference_code,
                status=inv.status,
                risk_score=inv.risk_score,
                risk_classification=inv.risk_classification,
                created_at=inv.created_at,
                updated_at=inv.updated_at,
            )

    def list_investigations(
        self,
        organization_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[InvestigationResponseDTO]:
        """List investigations belonging to an organization in descending order of creation."""
        with self._get_uow() as uow:
            items = uow.investigations.list_by_organization(organization_id, skip=skip, limit=limit)
            results: list[InvestigationResponseDTO] = []
            for inv in items:
                assert inv.organization_id is not None
                results.append(
                    InvestigationResponseDTO(
                        id=inv.id,
                        organization_id=inv.organization_id,
                        title=inv.title,
                        reference_code=inv.reference_code,
                        status=inv.status,
                        risk_score=inv.risk_score,
                        risk_classification=inv.risk_classification,
                        created_at=inv.created_at,
                        updated_at=inv.updated_at,
                    )
                )
            return results

    def update_investigation(
        self,
        investigation_id: str,
        organization_id: str,
        dto: InvestigationUpdateDTO,
        actor_id: str = "analyst_01",
    ) -> InvestigationResponseDTO:
        """Update permitted investigation metadata enforcing tenant ownership."""
        with self._get_uow() as uow:
            inv = uow.investigations.get_by_id(investigation_id, organization_id)
            if inv is None:
                raise EntityNotFoundError(
                    f"Investigation '{investigation_id}' not found in '{organization_id}'"
                )

            if dto.title is not None:
                inv.title = dto.title
            if dto.reference_code is not None:
                inv.reference_code = dto.reference_code
            if dto.risk_score is not None:
                inv.update_risk_score(dto.risk_score, dto.risk_classification)

            uow.investigations.update(inv, organization_id)

            assert inv.organization_id is not None
            return InvestigationResponseDTO(
                id=inv.id,
                organization_id=inv.organization_id,
                title=inv.title,
                reference_code=inv.reference_code,
                status=inv.status,
                risk_score=inv.risk_score,
                risk_classification=inv.risk_classification,
                created_at=inv.created_at,
                updated_at=inv.updated_at,
            )

    def transition_status(
        self,
        investigation_id: str,
        organization_id: str,
        new_status: InvestigationStatus,
        actor_id: str = "analyst_01",
    ) -> InvestigationResponseDTO:
        """Transition an investigation according to lifecycle rules."""
        with self._get_uow() as uow:
            inv = uow.investigations.get_by_id(investigation_id, organization_id)
            if inv is None:
                raise EntityNotFoundError(
                    f"Investigation '{investigation_id}' not found in '{organization_id}'"
                )

            inv.transition_to(new_status)
            uow.investigations.update(inv, organization_id)

            assert inv.organization_id is not None
            return InvestigationResponseDTO(
                id=inv.id,
                organization_id=inv.organization_id,
                title=inv.title,
                reference_code=inv.reference_code,
                status=inv.status,
                risk_score=inv.risk_score,
                risk_classification=inv.risk_classification,
                created_at=inv.created_at,
                updated_at=inv.updated_at,
            )

    def list_findings(
        self,
        investigation_id: str,
        organization_id: str,
    ) -> list[FindingResponseDTO]:
        """List all findings for an investigation with their review decisions."""
        with self._get_uow() as uow:
            findings = uow.findings.list_by_investigation(investigation_id, organization_id)
            results: list[FindingResponseDTO] = []
            for f in findings:
                decisions = uow.findings.list_review_decisions(f.id, organization_id)
                dec_dtos = [
                    ReviewDecisionDTO(
                        id=d.id,
                        finding_id=d.finding_id,
                        reviewer_id=d.reviewer_id,
                        decision=d.decision,
                        rationale=d.rationale,
                        timestamp=d.timestamp,
                    )
                    for d in decisions
                ]
                results.append(
                    FindingResponseDTO(
                        id=f.id,
                        investigation_id=f.investigation_id,
                        category=f.category,
                        epistemic_tier=f.epistemic_tier,
                        severity=f.severity,
                        title=f.title,
                        narrative_explanation=f.narrative_explanation,
                        confidence=f.confidence,
                        investigator_guidance=f.investigator_guidance,
                        review_status=f.review_status,
                        evidence_ids=sorted(list(f.evidence_ids)),
                        signature_reference_id=f.signature_reference_id,
                        created_at=f.created_at,
                        review_decisions=dec_dtos,
                    )
                )
            return results

    def get_finding(
        self,
        finding_id: str,
        organization_id: str,
    ) -> FindingResponseDTO | None:
        """Retrieve a finding by ID with its review decisions."""
        with self._get_uow() as uow:
            f = uow.findings.get_by_id(finding_id, organization_id)
            if f is None:
                return None
            decisions = uow.findings.list_review_decisions(f.id, organization_id)
            dec_dtos = [
                ReviewDecisionDTO(
                    id=d.id,
                    finding_id=d.finding_id,
                    reviewer_id=d.reviewer_id,
                    decision=d.decision,
                    rationale=d.rationale,
                    timestamp=d.timestamp,
                )
                for d in decisions
            ]
            return FindingResponseDTO(
                id=f.id,
                investigation_id=f.investigation_id,
                category=f.category,
                epistemic_tier=f.epistemic_tier,
                severity=f.severity,
                title=f.title,
                narrative_explanation=f.narrative_explanation,
                confidence=f.confidence,
                investigator_guidance=f.investigator_guidance,
                review_status=f.review_status,
                evidence_ids=sorted(list(f.evidence_ids)),
                signature_reference_id=f.signature_reference_id,
                created_at=f.created_at,
                review_decisions=dec_dtos,
            )

    def review_finding(
        self,
        investigation_id: str,
        request: ReviewFindingRequestDTO,
        organization_id: str,
    ) -> FindingResponseDTO:
        """Record human examiner review decision on a finding and update audit log."""
        with self._get_uow() as uow:
            finding = uow.findings.get_by_id(request.finding_id, organization_id)
            if finding is None or finding.investigation_id != investigation_id:
                raise EntityNotFoundError(
                    f"Finding '{request.finding_id}' not found in case '{investigation_id}'"
                )

            if request.decision == ReviewDecisionType.CONFIRMED:
                finding.confirm(reviewer_id=request.reviewer_id, rationale=request.rationale)
                audit_event_type = AuditEventType.HUMAN_REVIEW_CONFIRMED
            elif request.decision == ReviewDecisionType.DISMISSED:
                finding.dismiss(reviewer_id=request.reviewer_id, rationale=request.rationale)
                audit_event_type = AuditEventType.HUMAN_REVIEW_DISMISSED
            elif request.decision == ReviewDecisionType.ANNOTATED:
                finding.annotate(reviewer_id=request.reviewer_id, notes=request.rationale)
                audit_event_type = AuditEventType.HUMAN_REVIEW_ANNOTATED
            else:
                raise ValueError(f"Unsupported review decision: {request.decision}")

            rev_decision = ReviewDecision.create(
                finding_id=finding.id,
                reviewer_id=request.reviewer_id,
                decision=request.decision,
                rationale=request.rationale,
            )
            uow.findings.add_review_decision(rev_decision, organization_id)
            uow.findings.update(finding, organization_id)

            audit_event = AuditEvent.create(
                investigation_id=investigation_id,
                event_type=audit_event_type,
                actor_type=ActorType.HUMAN_ANALYST,
                actor_id=request.reviewer_id,
                event_payload={
                    "finding_id": finding.id,
                    "decision": request.decision.value,
                    "rationale": request.rationale,
                    "review_decision_id": rev_decision.id,
                },
            )
            uow.audit_events.add(audit_event, organization_id)

            decisions = uow.findings.list_review_decisions(finding.id, organization_id)
            dec_dtos = [
                ReviewDecisionDTO(
                    id=d.id,
                    finding_id=d.finding_id,
                    reviewer_id=d.reviewer_id,
                    decision=d.decision,
                    rationale=d.rationale,
                    timestamp=d.timestamp,
                )
                for d in decisions
            ]
            return FindingResponseDTO(
                id=finding.id,
                investigation_id=finding.investigation_id,
                category=finding.category,
                epistemic_tier=finding.epistemic_tier,
                severity=finding.severity,
                title=finding.title,
                narrative_explanation=finding.narrative_explanation,
                confidence=finding.confidence,
                investigator_guidance=finding.investigator_guidance,
                review_status=finding.review_status,
                evidence_ids=sorted(list(finding.evidence_ids)),
                signature_reference_id=finding.signature_reference_id,
                created_at=finding.created_at,
                review_decisions=dec_dtos,
            )

    def list_relations(
        self,
        investigation_id: str,
        organization_id: str,
    ) -> list[RelationResponseDTO]:
        """List all cross-document relations for an investigation."""
        with self._get_uow() as uow:
            relations = uow.investigations.list_relations(investigation_id, organization_id)
            return [
                RelationResponseDTO(
                    id=r.id,
                    investigation_id=r.investigation_id,
                    source_document_id=r.source_document_id,
                    target_document_id=r.target_document_id,
                    relation_type=r.relation_type,
                    description=r.description,
                    finding_id=r.finding_id,
                    similarity_score=r.similarity_score,
                )
                for r in relations
            ]

    def list_evidence(
        self,
        investigation_id: str,
        organization_id: str,
    ) -> list[EvidenceResponseDTO]:
        """List all visual evidence items in an investigation."""
        with self._get_uow() as uow:
            evidence_items = uow.evidence.list_by_investigation(investigation_id, organization_id)
            return [
                EvidenceResponseDTO(
                    id=e.id,
                    page_id=e.page_id,
                    crop_image_path=e.crop_image_path,
                    norm_ymin=e.norm_ymin,
                    norm_xmin=e.norm_xmin,
                    norm_ymax=e.norm_ymax,
                    norm_xmax=e.norm_xmax,
                    pixel_x=e.pixel_x,
                    pixel_y=e.pixel_y,
                    pixel_width=e.pixel_width,
                    pixel_height=e.pixel_height,
                    heatmap_image_path=e.heatmap_image_path,
                    grounding_explanation=e.grounding_explanation,
                )
                for e in evidence_items
            ]

    def list_documents(
        self,
        investigation_id: str,
        organization_id: str,
    ) -> list[DocumentIngestionResultDTO]:
        """List all documents in an investigation."""
        with self._get_uow() as uow:
            docs = uow.documents.list_by_investigation(investigation_id, organization_id)
            results: list[DocumentIngestionResultDTO] = []
            for d in docs:
                pages = uow.documents.list_pages(d.id, organization_id)
                results.append(
                    DocumentIngestionResultDTO(
                        document_id=d.id,
                        investigation_id=d.investigation_id,
                        organization_id=organization_id,
                        original_filename=d.original_filename,
                        file_hash_sha256=d.file_hash_sha256,
                        mime_type=d.mime_type,
                        document_type=d.document_type,
                        page_count=d.page_count,
                        file_size_bytes=d.file_size_bytes,
                        storage_path=d.storage_path,
                        status=d.status,
                        created_at=d.created_at,
                        page_ids=[p.id for p in pages],
                    )
                )
            return results

    def list_document_pages(
        self,
        document_id: str,
        organization_id: str,
    ) -> list[DocumentPage]:
        """List pages of a document."""
        with self._get_uow() as uow:
            return uow.documents.list_pages(document_id, organization_id)
