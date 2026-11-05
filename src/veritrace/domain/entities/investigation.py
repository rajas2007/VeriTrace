"""Investigation root aggregate entity representing a forensic investigation case."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from veritrace.domain.enums.investigation import (
    InvestigationStatus,
    RiskClassification,
)
from veritrace.domain.exceptions.base import (
    ConfidenceRangeError,
    InvalidStateTransitionError,
    ValidationError,
)
from veritrace.domain.value_objects.identifiers import (
    INV_PREFIX,
    ORG_PREFIX,
    ensure_utc,
    generate_id,
    utc_now,
    validate_id,
)

# Valid state transitions for Investigation lifecycle
_VALID_INVESTIGATION_TRANSITIONS: dict[InvestigationStatus, set[InvestigationStatus]] = {
    InvestigationStatus.DRAFT: {
        InvestigationStatus.PROCESSING,
        InvestigationStatus.FAILED,
    },
    InvestigationStatus.PROCESSING: {
        InvestigationStatus.WAITING_REVIEW,
        InvestigationStatus.COMPLETED,
        InvestigationStatus.FAILED,
    },
    InvestigationStatus.WAITING_REVIEW: {
        InvestigationStatus.PROCESSING,
        InvestigationStatus.COMPLETED,
        InvestigationStatus.FAILED,
    },
    InvestigationStatus.COMPLETED: set(),  # Terminal state
    InvestigationStatus.FAILED: {
        InvestigationStatus.DRAFT,
        InvestigationStatus.PROCESSING,
    },
}


@dataclass(slots=True)
class Investigation:
    """Root aggregate representing an industrial multi-document forensic investigation case."""

    id: str
    title: str
    reference_code: str
    status: InvestigationStatus
    created_at: datetime
    updated_at: datetime
    risk_score: float = 0.0
    risk_classification: RiskClassification = RiskClassification.UNDETERMINED
    organization_id: str | None = None

    def __post_init__(self) -> None:
        self.id = validate_id(self.id, INV_PREFIX, "Investigation.id")
        if not self.title or not self.title.strip():
            raise ValidationError("Investigation.title must not be empty")
        if not self.reference_code or not self.reference_code.strip():
            raise ValidationError("Investigation.reference_code must not be empty")
        if not (0.0 <= self.risk_score <= 1.0):
            raise ConfidenceRangeError(f"risk_score must be in [0.0, 1.0], got {self.risk_score}")
        if self.organization_id is not None:
            self.organization_id = validate_id(
                self.organization_id, ORG_PREFIX, "Investigation.organization_id"
            )

        self.created_at = ensure_utc(self.created_at, "Investigation.created_at")
        self.updated_at = ensure_utc(self.updated_at, "Investigation.updated_at")

        if self.updated_at < self.created_at:
            raise ValidationError(
                f"updated_at ({self.updated_at}) earlier than created_at ({self.created_at})"
            )

    def transition_to(self, new_status: InvestigationStatus) -> None:
        """Transition the investigation to a new lifecycle state enforcing invariant rules."""
        if self.status == new_status:
            return

        valid_targets = _VALID_INVESTIGATION_TRANSITIONS.get(self.status, set())
        if new_status not in valid_targets:
            raise InvalidStateTransitionError(
                f"Cannot transition Investigation from {self.status.value} to {new_status.value}."
            )

        self.status = new_status
        self.updated_at = utc_now()

    def update_risk_score(
        self,
        risk_score: float,
        classification: RiskClassification | None = None,
    ) -> None:
        """Update aggregate case risk score and classification with timestamp tracking."""
        if not (0.0 <= risk_score <= 1.0):
            raise ConfidenceRangeError(f"risk_score must be in [0.0, 1.0], got {risk_score}")
        self.risk_score = risk_score
        if classification is not None:
            self.risk_classification = classification
        self.updated_at = utc_now()

    @classmethod
    def create(
        cls,
        title: str,
        reference_code: str,
        investigation_id: str | None = None,
        organization_id: str | None = None,
        status: InvestigationStatus = InvestigationStatus.DRAFT,
        risk_score: float = 0.0,
        risk_classification: RiskClassification = RiskClassification.UNDETERMINED,
        created_at: datetime | None = None,
    ) -> Investigation:
        """Factory method creating an Investigation entity."""
        iid = investigation_id or generate_id(INV_PREFIX)
        now = created_at or utc_now()
        return cls(
            id=iid,
            title=title.strip(),
            reference_code=reference_code.strip(),
            status=status,
            risk_score=risk_score,
            risk_classification=risk_classification,
            organization_id=organization_id,
            created_at=now,
            updated_at=now,
        )
