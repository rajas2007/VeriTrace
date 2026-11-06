"""SQLite implementation of FindingRepository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from veritrace.domain.entities.finding import Finding
from veritrace.domain.entities.review_decision import ReviewDecision
from veritrace.domain.exceptions.base import (
    EntityNotFoundError,
    RelationshipConstraintError,
    TenantIsolationError,
)
from veritrace.domain.value_objects.identifiers import (
    FindingId,
    InvestigationId,
    OrganizationId,
)
from veritrace.infrastructure.persistence.mappers.finding_mapper import FindingMapper
from veritrace.infrastructure.persistence.mappers.review_decision_mapper import (
    ReviewDecisionMapper,
)
from veritrace.infrastructure.persistence.models.document import DocumentModel
from veritrace.infrastructure.persistence.models.document_page import DocumentPageModel
from veritrace.infrastructure.persistence.models.evidence import EvidenceModel
from veritrace.infrastructure.persistence.models.finding import FindingModel
from veritrace.infrastructure.persistence.models.investigation import InvestigationModel
from veritrace.infrastructure.persistence.models.review_decision import ReviewDecisionModel


class SqliteFindingRepository:
    """SQLite-backed repository for Finding entities and finding_evidence_map associations."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, finding: Finding, organization_id: OrganizationId) -> None:
        """Persist a new Finding with evidence links, verifying tenant ownership."""
        inv = self._session.execute(
            select(InvestigationModel).where(
                InvestigationModel.id == str(finding.investigation_id),
                InvestigationModel.organization_id == str(organization_id),
            )
        ).scalar_one_or_none()
        if inv is None:
            any_inv = self._session.get(InvestigationModel, str(finding.investigation_id))
            if any_inv is not None:
                raise TenantIsolationError(
                    f"Cross-organization violation: Investigation '{finding.investigation_id}' "
                    f"belongs to organization '{any_inv.organization_id}', not '{organization_id}'"
                )
            raise EntityNotFoundError(
                f"Investigation '{finding.investigation_id}' not found "
                f"in organization '{organization_id}'"
            )

        model = FindingMapper.to_model(finding)

        # Attach evidence items ensuring they belong to the authorized organization
        if finding.evidence_ids:
            evd_ids = [str(eid) for eid in finding.evidence_ids]
            evd_models = (
                self._session.execute(
                    select(EvidenceModel)
                    .join(DocumentPageModel, EvidenceModel.page_id == DocumentPageModel.id)
                    .join(DocumentModel, DocumentPageModel.document_id == DocumentModel.id)
                    .join(
                        InvestigationModel,
                        DocumentModel.investigation_id == InvestigationModel.id,
                    )
                    .where(
                        EvidenceModel.id.in_(evd_ids),
                        InvestigationModel.organization_id == str(organization_id),
                    )
                )
                .scalars()
                .all()
            )
            if len(evd_models) != len(evd_ids):
                found_ids = {e.id for e in evd_models}
                missing_ids = set(evd_ids) - found_ids
                raise TenantIsolationError(
                    f"Evidence items {sorted(missing_ids)} do not exist or belong to another tenant"
                )
            model.evidence = list(evd_models)

        self._session.add(model)
        self._session.flush()

    def get_by_id(
        self,
        finding_id: FindingId,
        organization_id: OrganizationId,
    ) -> Finding | None:
        """Retrieve a finding with linked evidence IDs, scoped strictly to the organization."""
        stmt = (
            select(FindingModel)
            .join(InvestigationModel, FindingModel.investigation_id == InvestigationModel.id)
            .where(
                FindingModel.id == str(finding_id),
                InvestigationModel.organization_id == str(organization_id),
            )
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        if row is None:
            return None
        return FindingMapper.to_entity(row)

    def list_by_investigation(
        self,
        investigation_id: InvestigationId,
        organization_id: OrganizationId,
    ) -> list[Finding]:
        """List all findings for an investigation, enforcing tenant ownership."""
        inv = self._session.execute(
            select(InvestigationModel).where(
                InvestigationModel.id == str(investigation_id),
                InvestigationModel.organization_id == str(organization_id),
            )
        ).scalar_one_or_none()
        if inv is None:
            any_inv = self._session.get(InvestigationModel, str(investigation_id))
            if any_inv is not None:
                raise TenantIsolationError(
                    f"Cross-organization violation: Investigation '{investigation_id}' "
                    f"belongs to organization '{any_inv.organization_id}', not '{organization_id}'"
                )
            raise EntityNotFoundError(
                f"Investigation '{investigation_id}' not found in organization '{organization_id}'"
            )

        stmt = (
            select(FindingModel)
            .where(FindingModel.investigation_id == str(investigation_id))
            .order_by(FindingModel.created_at.asc())
        )
        rows = self._session.execute(stmt).scalars().all()
        return [FindingMapper.to_entity(r) for r in rows]

    def update(
        self,
        finding: Finding,
        organization_id: OrganizationId,
    ) -> None:
        """Update an existing finding and its evidence associations, enforcing tenant ownership."""
        stmt = (
            select(FindingModel)
            .join(InvestigationModel, FindingModel.investigation_id == InvestigationModel.id)
            .where(
                FindingModel.id == str(finding.id),
                InvestigationModel.organization_id == str(organization_id),
            )
        )
        model = self._session.execute(stmt).scalar_one_or_none()
        if model is None:
            any_fnd = self._session.get(FindingModel, str(finding.id))
            if any_fnd is not None:
                raise TenantIsolationError(
                    f"Cross-organization access violation: Finding '{finding.id}' does not belong "
                    f"to organization '{organization_id}'"
                )
            raise EntityNotFoundError(
                f"Finding '{finding.id}' not found in organization '{organization_id}'"
            )

        model.category = finding.category.value
        model.epistemic_tier = finding.epistemic_tier.value
        model.severity = finding.severity.value
        model.title = finding.title
        model.narrative_explanation = finding.narrative_explanation
        model.confidence = finding.confidence
        model.investigator_guidance = finding.investigator_guidance
        model.review_status = finding.review_status.value
        model.signature_reference_id = finding.signature_reference_id

        # Synchronize associated evidence items
        evd_ids = [str(eid) for eid in finding.evidence_ids]
        if evd_ids:
            evd_models = (
                self._session.execute(
                    select(EvidenceModel)
                    .join(DocumentPageModel, EvidenceModel.page_id == DocumentPageModel.id)
                    .join(DocumentModel, DocumentPageModel.document_id == DocumentModel.id)
                    .join(
                        InvestigationModel,
                        DocumentModel.investigation_id == InvestigationModel.id,
                    )
                    .where(
                        EvidenceModel.id.in_(evd_ids),
                        InvestigationModel.organization_id == str(organization_id),
                    )
                )
                .scalars()
                .all()
            )
            if len(evd_models) != len(evd_ids):
                raise TenantIsolationError(
                    "One or more evidence items to link do not belong to the organization"
                )
            model.evidence = list(evd_models)
        else:
            model.evidence = []

        self._session.flush()

    def delete(
        self,
        finding_id: FindingId,
        organization_id: OrganizationId,
    ) -> None:
        """Delete an unadjudicated finding, enforcing tenant ownership."""
        stmt = (
            select(FindingModel)
            .join(InvestigationModel, FindingModel.investigation_id == InvestigationModel.id)
            .where(
                FindingModel.id == str(finding_id),
                InvestigationModel.organization_id == str(organization_id),
            )
        )
        model = self._session.execute(stmt).scalar_one_or_none()
        if model is None:
            any_fnd = self._session.get(FindingModel, str(finding_id))
            if any_fnd is not None:
                raise TenantIsolationError(
                    f"Cross-organization access violation: Finding '{finding_id}' does not belong "
                    f"to organization '{organization_id}'"
                )
            raise EntityNotFoundError(
                f"Finding '{finding_id}' not found in organization '{organization_id}'"
            )

        # Invariant check: review decisions protect findings against uncontrolled deletion
        if model.review_decisions:
            raise RelationshipConstraintError(
                f"Cannot delete Finding '{finding_id}': protected by {len(model.review_decisions)} "
                "recorded ReviewDecision adjudications."
            )

        self._session.delete(model)
        self._session.flush()

    def add_review_decision(
        self,
        decision: ReviewDecision,
        organization_id: OrganizationId,
    ) -> None:
        """Persist a human ReviewDecision adjudication, enforcing tenant ownership."""
        stmt = (
            select(FindingModel)
            .join(InvestigationModel, FindingModel.investigation_id == InvestigationModel.id)
            .where(
                FindingModel.id == str(decision.finding_id),
                InvestigationModel.organization_id == str(organization_id),
            )
        )
        finding_model = self._session.execute(stmt).scalar_one_or_none()
        if finding_model is None:
            raise EntityNotFoundError(
                f"Finding '{decision.finding_id}' not found in organization '{organization_id}'"
            )

        model = ReviewDecisionMapper.to_model(decision)
        self._session.add(model)
        self._session.flush()

    def list_review_decisions(
        self,
        finding_id: FindingId,
        organization_id: OrganizationId,
    ) -> list[ReviewDecision]:
        """List all ReviewDecision adjudications for a finding, enforcing tenant ownership."""
        stmt = (
            select(ReviewDecisionModel)
            .join(FindingModel, ReviewDecisionModel.finding_id == FindingModel.id)
            .join(InvestigationModel, FindingModel.investigation_id == InvestigationModel.id)
            .where(
                ReviewDecisionModel.finding_id == str(finding_id),
                InvestigationModel.organization_id == str(organization_id),
            )
            .order_by(ReviewDecisionModel.timestamp.asc())
        )
        rows = self._session.execute(stmt).scalars().all()
        return [ReviewDecisionMapper.to_entity(r) for r in rows]
