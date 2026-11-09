"""Application service for Investigation case management."""

from __future__ import annotations

import hashlib
import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from sqlalchemy.exc import IntegrityError

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
from veritrace.application.dto.signature_reference import (
    AuthorizedSubjectDTO,
    SignatureReferenceDTO,
    SignatureReferenceEnrollDTO,
)
from veritrace.capabilities.classification.classifier import DocumentClassifier
from veritrace.capabilities.forensics.copy_move import CopyMoveDetector
from veritrace.capabilities.forensics.cropper import EvidenceCropper
from veritrace.capabilities.forensics.signatures.crop_quality import SignatureCropQualityAssessor
from veritrace.capabilities.forensics.signatures.detector import SignatureDetector
from veritrace.capabilities.forensics.signatures.stroke_analyzer import (
    SignatureStrokeAnalyzer,
)
from veritrace.capabilities.forensics.signatures.verifier import SignatureVerifier
from veritrace.capabilities.quality.analyzer import DocumentQualityAnalyzer
from veritrace.capabilities.quality.models import DocumentQualityResult
from veritrace.capabilities.reasoning.contextual_engine import ContextualReasoningEngine
from veritrace.capabilities.reasoning.synthesizer import (
    LLMProviderProtocol,
    NarrativeSynthesizer,
)
from veritrace.capabilities.reporting.dossier_compiler import DossierCompiler
from veritrace.capabilities.reporting.models import InvestigationDossierPayload
from veritrace.domain.entities.audit_event import AuditEvent
from veritrace.domain.entities.authorized_subject import AuthorizedSubject
from veritrace.domain.entities.document_page import DocumentPage
from veritrace.domain.entities.dossier import Dossier
from veritrace.domain.entities.evidence import Evidence
from veritrace.domain.entities.finding import Finding
from veritrace.domain.entities.investigation import Investigation
from veritrace.domain.entities.review_decision import ReviewDecision
from veritrace.domain.entities.signature_reference import SignatureReferenceProfile
from veritrace.domain.enums.audit import ActorType, AuditEventType
from veritrace.domain.enums.document import DocumentStatus, DocumentType
from veritrace.domain.enums.forensic import (
    EpistemicTier,
    FindingCategory,
    FindingSeverity,
    ReviewDecisionType,
    ReviewStatus,
)
from veritrace.domain.enums.investigation import InvestigationStatus
from veritrace.domain.exceptions.base import (
    EntityNotFoundError,
    ValidationError,
)
from veritrace.domain.interfaces.unit_of_work import UnitOfWork
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox
from veritrace.domain.value_objects.identifiers import FND_PREFIX, generate_id
from veritrace.infrastructure.persistence.models.signature_reference import (
    SignatureReferenceProfileModel,
)

logger = logging.getLogger("veritrace.application.services.investigation_service")


class InvestigationService:
    """Coordinates lifecycle, retrieval, and updates for Investigation cases."""

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork] | UnitOfWork,
        llm_provider: LLMProviderProtocol | None = None,
    ) -> None:
        if callable(uow_factory):
            self._uow_factory = uow_factory
        else:
            self._uow_factory = lambda: uow_factory
        self._llm_provider = llm_provider

    def get_llm_provider(self) -> LLMProviderProtocol | None:
        """Return configured large language model provider or None."""
        return self._llm_provider

    def set_llm_provider(self, provider: LLMProviderProtocol | None) -> None:
        """Update or configure active large language model provider."""
        self._llm_provider = provider

    def configure_ai_provider(
        self,
        privacy_mode: Any = "MODE_A_OFFLINE",
        api_key: str | None = None,
        model_name: str = "llama-3.3-70b-versatile",
        persist_key: bool = True,
    ) -> None:
        """Configure AI reasoning provider, privacy boundaries, and DPAPI key persistence."""
        from veritrace.domain.enums.investigation import PrivacyMode
        from veritrace.infrastructure.ai.groq_client import GroqLLMProvider
        from veritrace.infrastructure.security.dpapi_store import DpapiDataEncryptionKey

        if isinstance(privacy_mode, str):
            try:
                mode_enum = PrivacyMode(privacy_mode)
            except ValueError:
                mode_enum = PrivacyMode.MODE_A_OFFLINE
        else:
            mode_enum = privacy_mode

        key_mgr = DpapiDataEncryptionKey()

        if mode_enum == PrivacyMode.MODE_A_OFFLINE:
            # Mode A guarantees zero data egress; delete any persisted API key
            key_mgr.delete_secret_string("groq_api_key")
            resolved_key = None
        else:
            resolved_key = (
                api_key
                or key_mgr.load_secret_string("groq_api_key")
                or os.environ.get("GROQ_API_KEY")
            )
            if persist_key and resolved_key:
                key_mgr.save_secret_string("groq_api_key", resolved_key)

        provider = GroqLLMProvider(
            api_key=resolved_key,
            model_name=model_name,
            privacy_mode=mode_enum,
        )
        self.set_llm_provider(provider)

    def test_ai_connection(
        self,
        api_key: str | None = None,
        model_name: str = "llama-3.3-70b-versatile",
    ) -> tuple[bool, str]:
        """Test Groq API connection and credential validity via minimal probe."""
        from veritrace.domain.enums.investigation import PrivacyMode
        from veritrace.infrastructure.ai.groq_client import GroqLLMProvider
        from veritrace.infrastructure.security.dpapi_store import DpapiDataEncryptionKey

        resolved_key = (
            api_key
            or DpapiDataEncryptionKey().load_secret_string("groq_api_key")
            or os.environ.get("GROQ_API_KEY")
        )
        if not resolved_key:
            return False, "No API key provided. Please enter a valid Groq API key."

        probe_provider = GroqLLMProvider(
            api_key=resolved_key,
            model_name=model_name,
            privacy_mode=PrivacyMode.MODE_B_STATISTICAL,
        )
        return probe_provider.test_connection()

    def get_persisted_ai_key(self) -> str | None:
        """Retrieve DPAPI-sealed Groq API key if available, falling back to environment."""
        from veritrace.infrastructure.security.dpapi_store import DpapiDataEncryptionKey

        try:
            persisted = DpapiDataEncryptionKey().load_secret_string("groq_api_key")
            if persisted:
                return persisted
        except Exception:
            pass
        return os.environ.get("GROQ_API_KEY")

    def clear_persisted_ai_key(self) -> bool:
        """Eradicate DPAPI-sealed Groq API key."""
        from veritrace.infrastructure.security.dpapi_store import DpapiDataEncryptionKey

        return DpapiDataEncryptionKey().delete_secret_string("groq_api_key")

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
                        evidence_ids=sorted(f.evidence_ids),
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
                evidence_ids=sorted(f.evidence_ids),
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
                evidence_ids=sorted(finding.evidence_ids),
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

    def assess_document_quality(
        self,
        investigation_id: str,
        organization_id: str,
    ) -> list[DocumentQualityResult]:
        """Run multi-factor quality inspection across all documents in an investigation."""
        with self._get_uow() as uow:
            docs = uow.documents.list_by_investigation(investigation_id, organization_id)
            analyzer = DocumentQualityAnalyzer()
            results: list[DocumentQualityResult] = []
            for d in docs:
                if d.storage_path and Path(d.storage_path).exists():
                    res = analyzer.analyze_document(file_path=d.storage_path, document_id=d.id)
                    results.append(res)
            return results

    def classify_document(
        self,
        document_id: str,
        organization_id: str,
    ) -> tuple[DocumentType, float]:
        """Classify a single document after extraction has completed.

        Requires the document to be in DocumentStatus.PROCESSED status.
        Preserves UNCLASSIFIED when extraction is incomplete or content is insufficient.
        Preserves human-validated or pre-set classifications.
        """
        with self._get_uow() as uow:
            doc = uow.documents.get_by_id(document_id, organization_id)
            if doc is None:
                raise EntityNotFoundError(
                    f"Document '{document_id}' not found in organization '{organization_id}'"
                )

            # 1. Do not overwrite an already validated human or pre-set classification
            if doc.document_type != DocumentType.UNCLASSIFIED:
                logger.info(
                    "Document '%s' already classified as '%s'; preserving existing classification.",
                    document_id,
                    doc.document_type,
                )
                return doc.document_type, doc.classification_confidence or 1.0

            # 2. Precondition: Document must be in successfully PROCESSED status
            if doc.status != DocumentStatus.PROCESSED:
                logger.warning(
                    "Classification deferred: Document '%s' is in status '%s' (expected '%s'). "
                    "Extraction must complete successfully before classification.",
                    document_id,
                    doc.status,
                    DocumentStatus.PROCESSED,
                )
                return DocumentType.UNCLASSIFIED, 0.0

            # 3. Retrieve extracted fields and text
            fields = uow.documents.list_extracted_fields_by_document(document_id, organization_id)
            raw_text_parts = [f.raw_text for f in fields if f.raw_text]
            combined_text = "\n".join(raw_text_parts) if raw_text_parts else None

            # 4. If no text or fields exist, preserve UNCLASSIFIED
            if not combined_text and not fields:
                logger.info(
                    "Document '%s' has no extracted text or fields; remaining UNCLASSIFIED.",
                    document_id,
                )
                return DocumentType.UNCLASSIFIED, 0.0

            classifier = DocumentClassifier()
            dtype, conf = classifier.classify(
                text=combined_text,
                filename=doc.original_filename,
                extracted_fields=fields,
            )

            if dtype != DocumentType.UNCLASSIFIED:
                doc.document_type = dtype
                doc.classification_confidence = conf
                uow.documents.update(doc, organization_id)
                uow.commit()

            return doc.document_type, conf

    def classify_documents(
        self,
        investigation_id: str,
        organization_id: str,
    ) -> dict[str, DocumentType]:
        """Automatically classify unclassified, processed documents in an investigation."""
        with self._get_uow() as uow:
            docs = uow.documents.list_by_investigation(investigation_id, organization_id)
            classifier = DocumentClassifier()
            classification_map: dict[str, DocumentType] = {}
            for d in docs:
                # 1. Preserve existing classifications
                if d.document_type != DocumentType.UNCLASSIFIED:
                    classification_map[d.id] = d.document_type
                    continue

                # 2. Precondition: Must be in PROCESSED status
                if d.status != DocumentStatus.PROCESSED:
                    classification_map[d.id] = d.document_type
                    continue

                fields = uow.documents.list_extracted_fields_by_document(d.id, organization_id)
                raw_text_parts = [f.raw_text for f in fields if f.raw_text]
                combined_text = "\n".join(raw_text_parts) if raw_text_parts else None

                if not combined_text and not fields:
                    classification_map[d.id] = d.document_type
                    continue

                dtype, conf = classifier.classify(
                    text=combined_text,
                    filename=d.original_filename,
                    extracted_fields=fields,
                )
                if dtype != DocumentType.UNCLASSIFIED:
                    d.document_type = dtype
                    d.classification_confidence = conf
                    uow.documents.update(d, organization_id)
                classification_map[d.id] = d.document_type
            uow.commit()
            return classification_map

    def compile_investigation_dossier(
        self,
        investigation_id: str,
        organization_id: str,
        output_dir: Path | str | None = None,
    ) -> tuple[Dossier, InvestigationDossierPayload, Path, Path]:
        """Compile complete PS-2 Investigation Dossier (JSON and ReportLab PDF) and record audit."""
        with self._get_uow() as uow:
            inv = uow.investigations.get_by_id(investigation_id, organization_id)
            if inv is None:
                msg = (
                    f"Investigation '{investigation_id}' not found in "
                    f"organization '{organization_id}'"
                )
                raise EntityNotFoundError(msg)

            documents = uow.documents.list_by_investigation(investigation_id, organization_id)
            all_fields = []
            for d in documents:
                fields = uow.documents.list_extracted_fields_by_document(d.id, organization_id)
                all_fields.extend(fields)

            findings = uow.findings.list_by_investigation(investigation_id, organization_id)
            evidence_records = uow.evidence.list_by_investigation(investigation_id, organization_id)

            reasoning_engine = ContextualReasoningEngine()
            evals, _ = reasoning_engine.evaluate_document(all_fields)

            synthesizer = NarrativeSynthesizer(llm_provider=self._llm_provider)
            executive_narrative = synthesizer.synthesize_executive_summary(findings)

            if output_dir:
                target_dir = Path(output_dir)
            else:
                target_dir = Path("artifacts/dossiers") / str(investigation_id)
            target_dir.mkdir(parents=True, exist_ok=True)

            compiler = DossierCompiler()
            dossier_entity, payload, pdf_path, json_path = compiler.compile_dossier(
                investigation=inv,
                documents=documents,
                fields=all_fields,
                rule_evaluations=evals,
                findings_or_proposals=findings,
                evidence_records=evidence_records,
                executive_narrative=executive_narrative,
                output_dir=target_dir,
            )

            uow.investigations.add_dossier(dossier_entity, organization_id)

            audit = AuditEvent.create(
                investigation_id=investigation_id,
                event_type=AuditEventType.DOSSIER_COMPILED,
                actor_type=ActorType.SYSTEM_PIPELINE,
                actor_id="dossier_compiler",
                event_payload={
                    "dossier_id": dossier_entity.id,
                    "pdf_path": str(pdf_path),
                    "json_path": str(json_path),
                    "pdf_sha256": dossier_entity.pdf_hash_sha256,
                    "findings_included": len(findings),
                    "documents_included": len(documents),
                },
            )
            uow.audit_events.add(audit, organization_id)
            uow.commit()

            return dossier_entity, payload, pdf_path, json_path

    def list_dossiers(
        self,
        investigation_id: str,
        organization_id: str,
    ) -> list[Dossier]:
        """List all compiled dossier records for an investigation."""
        with self._get_uow() as uow:
            return uow.investigations.list_dossiers(investigation_id, organization_id)

    @staticmethod
    def _compute_forensic_fingerprint(
        category: FindingCategory,
        analysis_type: str,
        scope_key: str,
        coord_key: str = "",
        content_hash: str = "",
    ) -> str:
        """Calculate deterministic fingerprint for a forensic finding.

        Incorporates immutable source-content hash where available to guarantee
        that re-uploaded or modified content produces distinct fingerprints without
        corrupting historical review decisions.
        """
        raw = f"{category.value}|{analysis_type}|{scope_key}|{coord_key}|{content_hash}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def run_forensic_analysis(
        self,
        investigation_id: str,
        organization_id: str,
        reference_profiles: list[SignatureReferenceProfile] | None = None,
        crops_dir: Path | str | None = None,
    ) -> list[FindingResponseDTO]:
        """Execute visual forensic analysis (signatures, stroke morphology, copy-move detection)

        across all document pages in an investigation.

        Adheres strictly to the Six-Level Epistemic Assessment Scale:
        - Safe, deterministic idempotency: Repeated analysis reuses existing findings and crops.
        - Preserves human review decisions (ReviewStatus, ReviewDecision records, audit history).
        - Keeps forensic observations separate from confirmed fraud conclusions.
        - Records candidates under ReviewStatus.PENDING_REVIEW for human adjudication.
        - Clearly indicates when image quality prevents reliable optical stroke analysis.
        - Persists visual evidence crops and ANOMALY_FLAGGED audit events without duplication.
        """
        newly_created_files: list[Path] = []
        try:
            with self._get_uow() as uow:
                inv = uow.investigations.get_by_id(investigation_id, organization_id)
                if inv is None:
                    raise EntityNotFoundError(
                        f"Investigation '{investigation_id}' "
                        f"not found in organization '{organization_id}'"
                    )

                docs = uow.documents.list_by_investigation(investigation_id, organization_id)
                cropper = EvidenceCropper(padding_px=15)
                sig_detector = SignatureDetector()
                stroke_analyzer = SignatureStrokeAnalyzer()
                sig_verifier = SignatureVerifier(
                    detector=sig_detector, stroke_analyzer=stroke_analyzer
                )
                copy_move_detector = CopyMoveDetector(min_inlier_matches=10)

                base_crops_dir = (
                    Path(crops_dir)
                    if crops_dir
                    else Path("artifacts/crops") / str(investigation_id)
                )
                base_crops_dir.mkdir(parents=True, exist_ok=True)

                # Auto-load enrolled reference profiles for tenant if not explicitly provided
                if reference_profiles is None:
                    reference_profiles = uow.signature_references.list_by_organization(
                        organization_id
                    )

                existing_findings = uow.findings.list_by_investigation(
                    investigation_id, organization_id
                )
                existing_evidence = uow.evidence.list_by_investigation(
                    investigation_id, organization_id
                )

                # Index existing evidence by crop path and page+coord key
                existing_evidence_by_crop_path: dict[str, Evidence] = {}
                existing_evidence_by_coord: dict[tuple[str, int, int, int, int], Evidence] = {}
                for ev in existing_evidence:
                    try:
                        resolved_crop = str(Path(ev.crop_image_path).resolve())
                        existing_evidence_by_crop_path[resolved_crop] = ev
                    except Exception:
                        pass
                    coord_key = (
                        str(ev.page_id),
                        int(round(ev.norm_ymin * 100)),
                        int(round(ev.norm_xmin * 100)),
                        int(round(ev.norm_ymax * 100)),
                        int(round(ev.norm_xmax * 100)),
                    )
                    existing_evidence_by_coord[coord_key] = ev

                # Index existing findings by fingerprint and category+title
                existing_findings_by_fp: dict[str, Finding] = {}
                existing_findings_by_title: dict[tuple[FindingCategory, str], Finding] = {}
                for f in existing_findings:
                    if f.investigator_guidance and "[fp:" in f.investigator_guidance:
                        try:
                            start = f.investigator_guidance.index("[fp:") + 4
                            end = f.investigator_guidance.index("]", start)
                            fp_str = f.investigator_guidance[start:end]
                            existing_findings_by_fp[fp_str] = f
                        except Exception:
                            pass
                    existing_findings_by_title[(f.category, f.title)] = f

                newly_created_findings: list[Finding] = []
                newly_created_evidence: list[Evidence] = []
                active_findings: list[Finding] = []
                seen_finding_ids: set[str] = set()

                def get_or_create_evidence(
                    page_id: str,
                    img_bgr: np.ndarray,
                    bbox: NormalizedBoundingBox,
                    target_crop_path: Path,
                    grounding: str,
                ) -> Evidence:
                    resolved_target = str(target_crop_path.resolve())
                    c_key = (
                        str(page_id),
                        int(round(bbox.ymin * 100)),
                        int(round(bbox.xmin * 100)),
                        int(round(bbox.ymax * 100)),
                        int(round(bbox.xmax * 100)),
                    )
                    matched_ev = existing_evidence_by_crop_path.get(
                        resolved_target
                    ) or existing_evidence_by_coord.get(c_key)
                    if matched_ev and Path(matched_ev.crop_image_path).is_file():
                        return matched_ev

                    for ev in newly_created_evidence:
                        if ev.page_id == page_id:
                            ev_c_key = (
                                str(ev.page_id),
                                int(round(ev.norm_ymin * 100)),
                                int(round(ev.norm_xmin * 100)),
                                int(round(ev.norm_ymax * 100)),
                                int(round(ev.norm_xmax * 100)),
                            )
                            if ev_c_key == c_key and Path(ev.crop_image_path).is_file():
                                return ev

                    new_ev = cropper.create_evidence_entity(
                        page_id=page_id,
                        image_or_path=img_bgr,
                        bbox=bbox,
                        output_crop_path=target_crop_path,
                        grounding_explanation=grounding,
                    )
                    newly_created_files.append(target_crop_path)
                    newly_created_evidence.append(new_ev)
                    existing_evidence_by_crop_path[resolved_target] = new_ev
                    existing_evidence_by_coord[c_key] = new_ev
                    return new_ev

                def register_or_reuse_finding(
                    category: FindingCategory,
                    analysis_type: str,
                    scope_key: str,
                    coord_key: str,
                    epistemic_tier: EpistemicTier,
                    severity: FindingSeverity,
                    title: str,
                    narrative: str,
                    confidence: float,
                    evidence_items: list[Evidence],
                    investigator_guidance: str | None = None,
                    signature_ref_id: str | None = None,
                    content_hash: str = "",
                ) -> Finding:
                    fp = self._compute_forensic_fingerprint(
                        category, analysis_type, scope_key, coord_key, content_hash
                    )
                    matched = existing_findings_by_fp.get(fp)
                    if not matched:
                        title_match = existing_findings_by_title.get((category, title))
                        # Fall back to title match only if no conflicting fingerprint exists
                        if title_match and (
                            not title_match.investigator_guidance
                            or "[fp:" not in title_match.investigator_guidance
                        ):
                            matched = title_match

                    if matched:
                        if matched.id in seen_finding_ids:
                            return matched
                        seen_finding_ids.add(matched.id)

                        # Strict Human Review Preservation:
                        # Never alter review_status, decisions, or human-edited fields
                        if matched.review_status != ReviewStatus.PENDING_REVIEW:
                            logger.info(
                                "Preserving human-reviewed finding '%s' (status: %s)",
                                matched.id,
                                matched.review_status,
                            )
                        else:
                            matched.confidence = confidence

                        # Maintain evidence associations
                        ev_updated = False
                        for ev in evidence_items:
                            if ev.id not in matched.evidence_ids:
                                matched.link_evidence(ev.id)
                                ev_updated = True
                        if ev_updated:
                            uow.findings.update(matched, organization_id)

                        active_findings.append(matched)
                        return matched

                    # Genuinely new finding
                    guidance_with_fp = f"[fp:{fp}] {investigator_guidance or ''}".strip()
                    new_fnd = Finding.create(
                        finding_id=generate_id(FND_PREFIX),
                        investigation_id=investigation_id,
                        category=category,
                        epistemic_tier=epistemic_tier,
                        severity=severity,
                        title=title,
                        narrative_explanation=narrative,
                        confidence=confidence,
                        investigator_guidance=guidance_with_fp,
                        review_status=ReviewStatus.PENDING_REVIEW,
                        signature_reference_id=signature_ref_id,
                    )
                    for ev in evidence_items:
                        new_fnd.link_evidence(ev.id)

                    newly_created_findings.append(new_fnd)
                    active_findings.append(new_fnd)
                    seen_finding_ids.add(new_fnd.id)
                    existing_findings_by_fp[fp] = new_fnd
                    existing_findings_by_title[(category, title)] = new_fnd
                    return new_fnd

                page_data: list[tuple[Any, Any, np.ndarray]] = []

                for doc in docs:
                    pages = uow.documents.list_pages(doc.id, organization_id)
                    for page in pages:
                        if not page.image_storage_path:
                            continue
                        p_path = Path(page.image_storage_path)
                        if not p_path.is_file():
                            continue
                        img_bgr = cv2.imread(str(p_path))
                        if img_bgr is None:
                            continue

                        img_h, img_w = img_bgr.shape[:2]

                        # Quality Verification Gate: Check for minimum operational resolution
                        if img_h < 150 or img_w < 150:
                            register_or_reuse_finding(
                                category=FindingCategory.SIGNATURE_VERIFICATION,
                                analysis_type="LOW_RES_PAGE",
                                scope_key=str(page.id),
                                coord_key=f"{img_w}x{img_h}",
                                content_hash=doc.file_hash_sha256[:16]
                                if doc.file_hash_sha256
                                else "",
                                epistemic_tier=EpistemicTier.CONFIRMED_OBSERVATION,
                                severity=FindingSeverity.LOW,
                                title=(
                                    f"Forensic Quality Limitation: Low Resolution "
                                    f"({doc.original_filename}, Page {page.page_number})"
                                ),
                                narrative=(
                                    f"Page image resolution ({img_w}x{img_h}px) is below "
                                    "threshold for reliable optical stroke and feature extraction. "
                                    "Epistemic rating: INSUFFICIENT_EVIDENCE."
                                ),
                                confidence=1.0,
                                evidence_items=[],
                            )
                            continue

                        page_data.append((doc, page, img_bgr))

                        # 1. Signature Candidate Detection & Stroke Analysis
                        candidates = sig_detector.detect_candidate_regions(img_bgr)
                        for c_idx, bbox in enumerate(candidates):
                            crop_path = (
                                base_crops_dir / f"{doc.id}_p{page.page_number}_sig_{c_idx}.png"
                            )
                            try:
                                ev = get_or_create_evidence(
                                    page_id=page.id,
                                    img_bgr=img_bgr,
                                    bbox=bbox,
                                    target_crop_path=crop_path,
                                    grounding=(
                                        f"Signature candidate on {doc.original_filename} "
                                        f"(page {page.page_number})"
                                    ),
                                )
                            except Exception as crop_err:
                                logger.warning(
                                    "Evidence cropping failed for signature: %s", crop_err
                                )
                                continue

                        # Crop-level Quality Gate (Part B)
                        crop_quality = SignatureCropQualityAssessor().evaluate(
                            Path(ev.crop_image_path)
                        )
                        if not crop_quality.is_adequate:
                            coord_str = (
                                f"{int(round(bbox.ymin * 100))}_{int(round(bbox.xmin * 100))}"
                            )
                            register_or_reuse_finding(
                                category=FindingCategory.SIGNATURE_VERIFICATION,
                                analysis_type="INADEQUATE_CROP_QUALITY",
                                scope_key=str(page.id),
                                coord_key=coord_str,
                                content_hash=doc.file_hash_sha256[:16]
                                if doc.file_hash_sha256
                                else "",
                                epistemic_tier=EpistemicTier.CONFIRMED_OBSERVATION,
                                severity=FindingSeverity.LOW,
                                title=(
                                    f"Signature Quality Limitation: Inadequate Crop "
                                    f"({doc.original_filename}, Page {page.page_number})"
                                ),
                                narrative=(
                                    "Signature candidate crop exhibits quality limitations "
                                    f"({', '.join(crop_quality.reasons)}). "
                                    "Cannot perform reliable optical stroke comparison. "
                                    "Human adjudication required."
                                ),
                                confidence=1.0,
                                evidence_items=[ev],
                                investigator_guidance=(
                                    "Inspect physical original document to verify "
                                    "handwritten signature clarity."
                                ),
                            )
                            continue

                        # Analyze stroke morphology
                        try:
                            meas, est = stroke_analyzer.analyze_crop(Path(ev.crop_image_path), bbox)
                        except Exception:
                            continue

                        # Compare against reference profiles if provided
                        evaluated_ref = False
                        if reference_profiles:
                            for ref in reference_profiles:
                                if ref.organization_id != organization_id:
                                    continue
                                analysis_res = sig_verifier.verify_against_reference(
                                    questioned_crop=Path(ev.crop_image_path),
                                    reference_profile_or_crop=ref,
                                    document_id=doc.id,
                                    page_number=page.page_number,
                                    normalized_bbox=bbox,
                                )
                                evaluated_ref = True
                                dist = analysis_res.estimate.metric_embedding_distance
                                if dist is not None and dist > 0.35:
                                    persisted_ref_id: str | None = None
                                    session = getattr(uow, "_session", None)
                                    if session is not None and session.get(
                                        SignatureReferenceProfileModel, ref.id
                                    ):
                                        persisted_ref_id = ref.id

                                    ymin_int = int(round(bbox.ymin * 100))
                                    xmin_int = int(round(bbox.xmin * 100))
                                    coord_str = f"{ymin_int}_{xmin_int}"
                                    register_or_reuse_finding(
                                        category=FindingCategory.SIGNATURE_VERIFICATION,
                                        analysis_type="STROKE_DIVERGENCE",
                                        scope_key=f"{page.id}:{ref.id}",
                                        coord_key=coord_str,
                                        content_hash=doc.file_hash_sha256[:16]
                                        if doc.file_hash_sha256
                                        else "",
                                        epistemic_tier=EpistemicTier.DETECTED_INCONSISTENCY,
                                        severity=(
                                            FindingSeverity.HIGH
                                            if dist > 0.55
                                            else FindingSeverity.MEDIUM
                                        ),
                                        title=(
                                            f"Signature Stroke Divergence against Reference "
                                            f"({getattr(ref, 'signatory_name', None) or ref.id})"
                                        ),
                                        narrative=(
                                            f"Optical stroke distance ({dist:.3f}) exceeds "
                                            f"threshold against enrolled profile '{ref.id}'. "
                                            f"Width: {meas.apparent_stroke_width_mean_px:.1f}px. "
                                            "Status remains unconfirmed pending adjudication."
                                        ),
                                        confidence=min(
                                            1.0, max(0.4, 1.0 - analysis_res.uncertainty_score)
                                        ),
                                        evidence_items=[ev],
                                        signature_ref_id=persisted_ref_id,
                                    )
                                    break

                        # If no reference matched or provided, inspect perimeter discontinuity
                        if not evaluated_ref and meas.boundary_mask_discontinuity > 0.30:
                            coord_str = (
                                f"{int(round(bbox.ymin * 100))}_{int(round(bbox.xmin * 100))}"
                            )
                            register_or_reuse_finding(
                                category=FindingCategory.SIGNATURE_VERIFICATION,
                                analysis_type="BOUNDARY_DISCONTINUITY",
                                scope_key=str(page.id),
                                coord_key=coord_str,
                                content_hash=doc.file_hash_sha256[:16]
                                if doc.file_hash_sha256
                                else "",
                                epistemic_tier=EpistemicTier.DETECTED_INCONSISTENCY,
                                severity=FindingSeverity.MEDIUM,
                                title=f"Signature Boundary Discontinuity (Page {page.page_number})",
                                narrative=(
                                    f"Mask discontinuity ({meas.boundary_mask_discontinuity:.2f}) "
                                    f"detected on {doc.original_filename}. "
                                    "Suggests potential clipping artifact. Status: PENDING_REVIEW."
                                ),
                                confidence=0.75,
                                evidence_items=[ev],
                            )

                # 2. Cross-Page Copy-Move Detection
                for i in range(len(page_data)):
                    for j in range(i + 1, len(page_data)):
                        doc_a, page_a, img_a = page_data[i]
                        doc_b, page_b, img_b = page_data[j]

                        matches = copy_move_detector.compare_pages(
                            img_a, img_b, page_a.page_number, page_b.page_number
                        )
                        for m_idx, match in enumerate(matches):
                            if match.inlier_match_count >= 10:
                                src_crop_path = (
                                    base_crops_dir / f"cm_src_{page_a.id}_{page_b.id}_{m_idx}.png"
                                )
                                tgt_crop_path = (
                                    base_crops_dir / f"cm_tgt_{page_a.id}_{page_b.id}_{m_idx}.png"
                                )

                                try:
                                    ev_a = get_or_create_evidence(
                                        page_id=page_a.id,
                                        img_bgr=img_a,
                                        bbox=match.source_bbox,
                                        target_crop_path=src_crop_path,
                                        grounding=(
                                            f"Match on {doc_a.original_filename} "
                                            f"(p. {page_a.page_number})"
                                        ),
                                    )
                                    ev_b = get_or_create_evidence(
                                        page_id=page_b.id,
                                        img_bgr=img_b,
                                        bbox=match.target_bbox,
                                        target_crop_path=tgt_crop_path,
                                        grounding=(
                                            f"Match on {doc_b.original_filename} "
                                            f"(p. {page_b.page_number})"
                                        ),
                                    )

                                    sorted_pages = sorted([page_a.id, page_b.id])
                                    s_ymin = int(round(match.source_bbox.ymin * 100))
                                    s_xmin = int(round(match.source_bbox.xmin * 100))
                                    t_ymin = int(round(match.target_bbox.ymin * 100))
                                    t_xmin = int(round(match.target_bbox.xmin * 100))
                                    coord_str = f"{s_ymin}_{s_xmin}:{t_ymin}_{t_xmin}"
                                    ch_pair = (
                                        f"{doc_a.file_hash_sha256[:8]}:{doc_b.file_hash_sha256[:8]}"
                                        if doc_a.file_hash_sha256 and doc_b.file_hash_sha256
                                        else ""
                                    )

                                    if match.is_suppressed:
                                        register_or_reuse_finding(
                                            category=FindingCategory.COPY_MOVE_CLONE,
                                            analysis_type="SUPPRESSED_LAYOUT_CORRESPONDENCE",
                                            scope_key=f"{sorted_pages[0]}:{sorted_pages[1]}",
                                            coord_key=coord_str,
                                            content_hash=ch_pair,
                                            epistemic_tier=EpistemicTier.CONFIRMED_OBSERVATION,
                                            severity=FindingSeverity.LOW,
                                            title=(
                                                "Suppressed Layout Correspondence: "
                                                f"{doc_a.original_filename} vs "
                                                f"{doc_b.original_filename}"
                                            ),
                                            narrative=(
                                                "Candidate match suppressed: "
                                                f"{match.suppression_reason} "
                                                f"(inliers: {match.inlier_match_count}, "
                                                f"similarity: {match.similarity_score:.2f}). "
                                                "Spatial coordinates and evidence crops "
                                                "preserved for human review."
                                            ),
                                            confidence=match.similarity_score,
                                            evidence_items=[ev_a, ev_b],
                                            investigator_guidance=(
                                                "Verify whether the matched visual region "
                                                "corresponds to legitimate stationary "
                                                "rather than illicit duplicate reproduction."
                                            ),
                                        )
                                    else:
                                        register_or_reuse_finding(
                                            category=FindingCategory.COPY_MOVE_CLONE,
                                            analysis_type="COPY_MOVE_CORRESPONDENCE",
                                            scope_key=f"{sorted_pages[0]}:{sorted_pages[1]}",
                                            coord_key=coord_str,
                                            content_hash=ch_pair,
                                            epistemic_tier=EpistemicTier.DETECTED_INCONSISTENCY,
                                            severity=FindingSeverity.HIGH,
                                            title=(
                                                "Visual Pattern Correspondence: "
                                                f"{doc_a.original_filename} vs "
                                                f"{doc_b.original_filename}"
                                            ),
                                            narrative=(
                                                f"ORB identified {match.inlier_match_count} visual "
                                                f"correspondences between p.{page_a.page_number} "
                                                f"of '{doc_a.original_filename}' and "
                                                f"p.{page_b.page_number} of "
                                                f"'{doc_b.original_filename}' "
                                                f"(similarity: {match.similarity_score:.2f}). "
                                                "Notice: Standard vendor logos, headers, or forms "
                                                "naturally produce high keypoint correspondence "
                                                "across valid documents. This finding denotes an "
                                                "optical observation for human verification and "
                                                "does NOT constitute proof of document tampering."
                                            ),
                                            confidence=match.similarity_score,
                                            evidence_items=[ev_a, ev_b],
                                            investigator_guidance=(
                                                "Verify whether the matched visual region "
                                                "corresponds to a legitimate shared template "
                                                "(e.g. corporate logo or table grid) rather "
                                                "than an unauthorized duplicate patch."
                                            ),
                                        )
                                except Exception as cm_err:
                                    logger.warning(
                                        "Copy-move evidence generation failed: %s", cm_err
                                    )

                # 3. Persist Generated Evidence and Findings
                for ev in newly_created_evidence:
                    uow.evidence.add(ev, organization_id)

                for fnd in newly_created_findings:
                    uow.findings.add(fnd, organization_id)

                if newly_created_findings or newly_created_evidence:
                    audit = AuditEvent.create(
                        investigation_id=investigation_id,
                        event_type=AuditEventType.ANOMALY_FLAGGED,
                        actor_type=ActorType.SYSTEM_PIPELINE,
                        actor_id="forensic_engine",
                        event_payload={
                            "new_findings_count": len(newly_created_findings),
                            "new_evidence_count": len(newly_created_evidence),
                            "reused_findings_count": len(active_findings)
                            - len(newly_created_findings),
                        },
                    )
                    uow.audit_events.add(audit, organization_id)

                uow.commit()

                # Map all active findings in scope to DTOs with populated review decisions
                dto_results: list[FindingResponseDTO] = []
                for f in active_findings:
                    decisions = uow.findings.list_review_decisions(f.id, organization_id)
                    dto_results.append(
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
                            evidence_ids=sorted(f.evidence_ids),
                            signature_reference_id=f.signature_reference_id,
                            created_at=f.created_at,
                            review_decisions=[
                                ReviewDecisionDTO(
                                    id=d.id,
                                    finding_id=d.finding_id,
                                    reviewer_id=d.reviewer_id,
                                    decision=d.decision,
                                    rationale=d.rationale,
                                    timestamp=d.timestamp,
                                )
                                for d in decisions
                            ],
                        )
                    )
                return dto_results
        except Exception:
            # Clean up any newly created files on disk that were not committed
            for file_path in newly_created_files:
                try:
                    if file_path.is_file():
                        file_path.unlink(missing_ok=True)
                except Exception:
                    pass
            raise

    def create_authorized_subject(
        self,
        organization_id: str,
        full_name: str,
        designation: str,
        id_reference: str,
    ) -> AuthorizedSubjectDTO:
        """Register a designated signer profile authorized for enterprise documents."""
        with self._get_uow() as uow:
            subj = AuthorizedSubject.create(
                organization_id=organization_id,
                full_name=full_name,
                designation=designation,
                id_reference=id_reference,
            )
            uow.signature_references.add_subject(subj, organization_id)
            uow.commit()
            return AuthorizedSubjectDTO(
                id=subj.id,
                organization_id=subj.organization_id,
                full_name=subj.full_name,
                designation=subj.designation,
                id_reference=subj.id_reference,
                created_at=subj.created_at,
            )

    def list_authorized_subjects(
        self,
        organization_id: str,
    ) -> list[AuthorizedSubjectDTO]:
        """List all authorized subjects belonging to an organization."""
        with self._get_uow() as uow:
            subjects = uow.signature_references.list_subjects(organization_id)
            return [
                AuthorizedSubjectDTO(
                    id=s.id,
                    organization_id=s.organization_id,
                    full_name=s.full_name,
                    designation=s.designation,
                    id_reference=s.id_reference,
                    created_at=s.created_at,
                )
                for s in subjects
            ]

    def get_authorized_subject(
        self,
        subject_id: str,
        organization_id: str,
    ) -> AuthorizedSubjectDTO:
        """Retrieve an authorized subject by ID."""
        with self._get_uow() as uow:
            s = uow.signature_references.get_subject_by_id(subject_id, organization_id)
            if s is None:
                raise EntityNotFoundError(
                    f"AuthorizedSubject '{subject_id}' not found in "
                    f"organization '{organization_id}'"
                )
            return AuthorizedSubjectDTO(
                id=s.id,
                organization_id=s.organization_id,
                full_name=s.full_name,
                designation=s.designation,
                id_reference=s.id_reference,
                created_at=s.created_at,
            )

    def enroll_signature_reference(
        self,
        dto: SignatureReferenceEnrollDTO,
    ) -> SignatureReferenceDTO:
        """Enroll a specimen reference signature profile under chain-of-custody governance."""
        crop_path = Path(dto.crop_image_path)
        if not crop_path.is_file():
            raise ValidationError(f"Reference signature image file not found: {crop_path}")

        file_bytes = crop_path.read_bytes()
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        # Compute optical feature embedding vector
        verifier = SignatureVerifier()
        embedding = verifier.compute_embedding(crop_path)

        with self._get_uow() as uow:
            subj = uow.signature_references.get_subject_by_id(dto.subject_id, dto.organization_id)
            if subj is None:
                raise EntityNotFoundError(
                    f"AuthorizedSubject '{dto.subject_id}' not found in "
                    f"organization '{dto.organization_id}'"
                )

            # Prevent silent replacement: check if identical hash already enrolled for subject
            existing = uow.signature_references.list_by_subject(dto.subject_id, dto.organization_id)
            for ex in existing:
                if ex.sha256_hash == file_hash:
                    logger.info(
                        "Signature reference with hash %s already enrolled for subject %s",
                        file_hash,
                        dto.subject_id,
                    )
                    return SignatureReferenceDTO(
                        id=ex.id,
                        subject_id=ex.subject_id,
                        organization_id=ex.organization_id,
                        crop_image_path=ex.crop_image_path,
                        sha256_hash=ex.sha256_hash,
                        source_document_ref=ex.source_document_ref,
                        consent_mandate_ref=ex.consent_mandate_ref,
                        enrollment_date=ex.enrollment_date,
                        retention_expiry_date=ex.retention_expiry_date,
                        has_embedding=ex.embedding_vector is not None,
                        access_role_required=ex.access_role_required,
                    )

            profile = SignatureReferenceProfile.create(
                subject_id=dto.subject_id,
                organization_id=dto.organization_id,
                crop_image_path=str(crop_path.resolve()),
                sha256_hash=file_hash,
                source_document_ref=dto.source_document_ref,
                consent_mandate_ref=dto.consent_mandate_ref,
                retention_expiry_date=dto.retention_expiry_date,
                embedding_vector=embedding,
                access_role_required=dto.access_role_required,
            )
            try:
                uow.signature_references.add(profile, dto.organization_id)

                if dto.investigation_id:
                    inv = uow.investigations.get_by_id(dto.investigation_id, dto.organization_id)
                    if inv is not None:
                        audit = AuditEvent.create(
                            investigation_id=dto.investigation_id,
                            event_type=AuditEventType.SIGNATURE_ENROLLED,
                            actor_type=ActorType.HUMAN_ANALYST,
                            actor_id=dto.subject_id,
                            event_payload={
                                "profile_id": profile.id,
                                "subject_id": dto.subject_id,
                                "source_ref": dto.source_document_ref,
                                "consent_ref": dto.consent_mandate_ref,
                                "sha256_hash": file_hash,
                            },
                        )
                        uow.audit_events.add(audit, dto.organization_id)
                uow.commit()
            except Exception as exc:
                # Handle concurrent duplicate enrollment collision safely
                uow.rollback()
                is_unique_violation = isinstance(exc, IntegrityError) and (
                    "unique" in str(exc).lower() or "uq_signature_references" in str(exc).lower()
                )
                if is_unique_violation:
                    existing_after = uow.signature_references.list_by_subject(
                        dto.subject_id, dto.organization_id
                    )
                    for ex in existing_after:
                        if ex.sha256_hash == file_hash:
                            logger.info(
                                "Concurrent enrollment collision resolved: returning existing "
                                "profile %s for subject %s",
                                ex.id,
                                dto.subject_id,
                            )
                            return SignatureReferenceDTO(
                                id=ex.id,
                                subject_id=ex.subject_id,
                                organization_id=ex.organization_id,
                                crop_image_path=ex.crop_image_path,
                                sha256_hash=ex.sha256_hash,
                                source_document_ref=ex.source_document_ref,
                                consent_mandate_ref=ex.consent_mandate_ref,
                                enrollment_date=ex.enrollment_date,
                                retention_expiry_date=ex.retention_expiry_date,
                                has_embedding=ex.embedding_vector is not None,
                                access_role_required=ex.access_role_required,
                            )
                logger.error("Failed to enroll signature reference: %s", exc)
                raise

            return SignatureReferenceDTO(
                id=profile.id,
                subject_id=profile.subject_id,
                organization_id=profile.organization_id,
                crop_image_path=profile.crop_image_path,
                sha256_hash=profile.sha256_hash,
                source_document_ref=profile.source_document_ref,
                consent_mandate_ref=profile.consent_mandate_ref,
                enrollment_date=profile.enrollment_date,
                retention_expiry_date=profile.retention_expiry_date,
                has_embedding=profile.embedding_vector is not None,
                access_role_required=profile.access_role_required,
            )

    def list_signature_references(
        self,
        organization_id: str,
        subject_id: str | None = None,
    ) -> list[SignatureReferenceDTO]:
        """List enrolled signature references for an organization or subject."""
        with self._get_uow() as uow:
            if subject_id:
                profiles = uow.signature_references.list_by_subject(subject_id, organization_id)
            else:
                profiles = uow.signature_references.list_by_organization(organization_id)
            return [
                SignatureReferenceDTO(
                    id=p.id,
                    subject_id=p.subject_id,
                    organization_id=p.organization_id,
                    crop_image_path=p.crop_image_path,
                    sha256_hash=p.sha256_hash,
                    source_document_ref=p.source_document_ref,
                    consent_mandate_ref=p.consent_mandate_ref,
                    enrollment_date=p.enrollment_date,
                    retention_expiry_date=p.retention_expiry_date,
                    has_embedding=p.embedding_vector is not None,
                    access_role_required=p.access_role_required,
                )
                for p in profiles
            ]

    def get_signature_reference(
        self,
        profile_id: str,
        organization_id: str,
    ) -> SignatureReferenceProfile | None:
        """Retrieve an enrolled signature reference profile entity."""
        with self._get_uow() as uow:
            return uow.signature_references.get_by_id(profile_id, organization_id)
