"""Pure deterministic cross-document comparison and consistency rules.

CRITICAL INVARIANTS:
1. Rules are pure functions / deterministic evaluators with zero side-effects.
2. Architecture boundary: depends ONLY on Python standard library and domain enums.
   No imports from infrastructure, application, GUI, or external third-party packages.
3. Quantities and currency amounts use exact Decimal arithmetic (never IEEE 754 float).
4. Finding severity, confidence, and epistemic tier are evaluated as independent concepts.
5. Inconsistencies are classified as detected discrepancies, never as confirmed fraud.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from veritrace.domain.enums.forensic import (
    EpistemicTier,
    FindingCategory,
    FindingSeverity,
)

# Standard mass conversion factors to canonical KG
_MASS_TO_KG: dict[str, Decimal] = {
    "KG": Decimal("1.0"),
    "KILOGRAM": Decimal("1.0"),
    "KILOGRAMS": Decimal("1.0"),
    "MT": Decimal("1000.0"),
    "T": Decimal("1000.0"),
    "TON": Decimal("1000.0"),
    "TONS": Decimal("1000.0"),
    "TONNE": Decimal("1000.0"),
    "TONNES": Decimal("1000.0"),
    "METRIC TON": Decimal("1000.0"),
    "METRIC TONNE": Decimal("1000.0"),
    "G": Decimal("0.001"),
    "GRAM": Decimal("0.001"),
    "GRAMS": Decimal("0.001"),
    "LB": Decimal("0.45359237"),
    "LBS": Decimal("0.45359237"),
    "POUND": Decimal("0.45359237"),
    "POUNDS": Decimal("0.45359237"),
}

# Standard length conversion factors to canonical M
_LENGTH_TO_M: dict[str, Decimal] = {
    "M": Decimal("1.0"),
    "METER": Decimal("1.0"),
    "METERS": Decimal("1.0"),
    "METRE": Decimal("1.0"),
    "METRES": Decimal("1.0"),
    "MM": Decimal("0.001"),
    "CM": Decimal("0.01"),
    "KM": Decimal("1000.0"),
    "FT": Decimal("0.3048"),
    "FEET": Decimal("0.3048"),
    "IN": Decimal("0.0254"),
    "INCH": Decimal("0.0254"),
    "INCHES": Decimal("0.0254"),
}

# Discrete unit synonyms mapped to canonical PCS
_COUNT_UNITS: set[str] = {
    "PCS",
    "PC",
    "PIECE",
    "PIECES",
    "NOS",
    "NO",
    "NUM",
    "NUMBER",
    "EACH",
    "EA",
    "UNIT",
    "UNITS",
    "BAG",
    "BAGS",
    "BOX",
    "BOXES",
    "SET",
    "SETS",
}


def canonicalize_quantity(qty: Decimal, unit: str) -> tuple[Decimal, str] | None:
    """Convert quantity and unit to a canonical base unit (KG, M, PCS).

    Returns (canonical_qty, canonical_unit) or None if unit is unrecognized.
    """
    clean_unit = unit.strip().upper()
    if clean_unit in _MASS_TO_KG:
        return (qty * _MASS_TO_KG[clean_unit], "KG")
    if clean_unit in _LENGTH_TO_M:
        return (qty * _LENGTH_TO_M[clean_unit], "M")
    if clean_unit in _COUNT_UNITS:
        return (qty, "PCS")
    return None


def clean_string_identifier(val: str) -> str:
    """Normalize code, grade, or reference for exact canonical comparison."""
    return re.sub(r"[^A-Za-z0-9]", "", val).upper()


def clean_corporate_name(val: str) -> str:
    """Strip common corporate suffixes and symbols for deterministic entity comparison."""
    s = val.upper().strip()
    # Remove common punctuation
    s = re.sub(r"[^\w\s]", " ", s)
    # Strip legal entity suffixes
    suffixes = [
        r"\bPRIVATE\s+LIMITED\b",
        r"\bPVT\s+LTD\b",
        r"\bLIMITED\b",
        r"\bLTD\b",
        r"\bLLP\b",
        r"\bINC\b",
        r"\bINCORPORATED\b",
        r"\bCORP\b",
        r"\bCORPORATION\b",
        r"\bCO\b",
        r"\bCOMPANY\b",
    ]
    for suf in suffixes:
        s = re.sub(suf, "", s)
    return re.sub(r"\s+", " ", s).strip()


@dataclass(slots=True)
class RuleEvaluationResult:
    """Deterministic result of a cross-document rule evaluation."""

    is_consistent: bool
    rule_code: str
    category: FindingCategory
    epistemic_tier: EpistemicTier
    severity: FindingSeverity
    confidence: float
    title: str
    explanation: str
    compared_fields: tuple[str, ...] = ("", "")
    original_values: tuple[str, ...] = ("", "")
    normalized_values: tuple[str, ...] = ("", "")
    evidence_field_ids: tuple[str, ...] = field(default_factory=tuple)
    discrepancy_delta: Decimal | None = None
    discrepancy_percent: Decimal | None = None

    @property
    def is_contradiction(self) -> bool:
        """True if this evaluation detected an inconsistency or contradiction."""
        return not self.is_consistent


class QuantityConsistencyRule:
    """Validates quantity parity between documents with unit conversion and graduated severity.

    Severity Scaling for Over-billing:
    - Delta <= 1%: LOW (commercial weighbridge / fractional variance)
    - 1% < Delta <= 10%: MEDIUM
    - 10% < Delta <= 50%: HIGH
    - Delta > 50%: CRITICAL (extreme discrepancy / unverified shipment)
    """

    RULE_CODE = "RULE_QTY_CONSISTENCY"

    @classmethod
    def evaluate(
        cls,
        qty_a: Decimal,
        unit_a: str,
        raw_a: str,
        field_id_a: str,
        conf_a: float,
        qty_b: Decimal,
        unit_b: str,
        raw_b: str,
        field_id_b: str,
        conf_b: float,
        doc_type_a: str = "PURCHASE_ORDER",
        doc_type_b: str = "COMMERCIAL_INVOICE",
        alignment_conf: float = 1.0,
        is_order_closed: bool = False,
    ) -> RuleEvaluationResult:
        """Compare quantity A (baseline, e.g. PO/Challan) with quantity B (claim, e.g. Invoice)."""
        joint_conf = min(conf_a, conf_b) * alignment_conf
        field_ids = tuple(fid for fid in (field_id_a, field_id_b) if fid)

        canon_a = canonicalize_quantity(qty_a, unit_a)
        canon_b = canonicalize_quantity(qty_b, unit_b)

        if canon_a is None or canon_b is None:
            # Unrecognized unit
            return RuleEvaluationResult(
                is_consistent=False,
                rule_code=cls.RULE_CODE,
                category=FindingCategory.CROSS_DOC_MISMATCH,
                epistemic_tier=EpistemicTier.DETECTED_INCONSISTENCY,
                severity=FindingSeverity.HIGH,
                confidence=joint_conf,
                title=f"Unrecognized Quantity Unit in {doc_type_a} or {doc_type_b}",
                explanation=(
                    f"Unable to normalize quantity units: '{unit_a}' vs '{unit_b}'. "
                    f"Raw values: {doc_type_a}='{raw_a}', {doc_type_b}='{raw_b}'."
                ),
                compared_fields=(field_id_a, field_id_b),
                original_values=(raw_a, raw_b),
                normalized_values=(f"{qty_a} {unit_a}", f"{qty_b} {unit_b}"),
                evidence_field_ids=field_ids,
            )

        val_a, can_unit_a = canon_a
        val_b, can_unit_b = canon_b

        if can_unit_a != can_unit_b:
            # Incompatible unit dimensions (e.g. Mass vs Length)
            return RuleEvaluationResult(
                is_consistent=False,
                rule_code=cls.RULE_CODE,
                category=FindingCategory.CROSS_DOC_MISMATCH,
                epistemic_tier=EpistemicTier.DETECTED_INCONSISTENCY,
                severity=FindingSeverity.HIGH,
                confidence=joint_conf,
                title=f"Incompatible Quantity Units: {can_unit_a} vs {can_unit_b}",
                explanation=(
                    f"Incompatible unit dimensions: {doc_type_a} specifies '{raw_a}' "
                    f"({can_unit_a}) while {doc_type_b} specifies '{raw_b}' ({can_unit_b}). "
                    f"Cross-document conversion cannot be established without density data."
                ),
                compared_fields=(field_id_a, field_id_b),
                original_values=(raw_a, raw_b),
                normalized_values=(f"{val_a} {can_unit_a}", f"{val_b} {can_unit_b}"),
                evidence_field_ids=field_ids,
            )

        # Units are compatible and normalized to can_unit_a
        if val_a == val_b:
            return RuleEvaluationResult(
                is_consistent=True,
                rule_code=cls.RULE_CODE,
                category=FindingCategory.CROSS_DOC_MISMATCH,
                epistemic_tier=EpistemicTier.CONFIRMED_OBSERVATION,
                severity=FindingSeverity.LOW,
                confidence=joint_conf,
                title=f"Consistent Quantities: {val_a} {can_unit_a}",
                explanation=(
                    f"Quantities across {doc_type_a} and {doc_type_b} are fully reconciled "
                    f"at {val_a} {can_unit_a}."
                ),
                compared_fields=(field_id_a, field_id_b),
                original_values=(raw_a, raw_b),
                normalized_values=(f"{val_a} {can_unit_a}", f"{val_b} {can_unit_b}"),
                evidence_field_ids=field_ids,
                discrepancy_delta=Decimal("0.0"),
                discrepancy_percent=Decimal("0.0"),
            )

        # Discrepancy detected
        if val_b > val_a:
            # Over-billing: document B exceeds baseline document A
            delta = val_b - val_a
            delta_pct = (delta / val_a * Decimal("100.0")) if val_a > 0 else Decimal("100.0")

            if delta_pct <= Decimal("1.0"):
                severity = FindingSeverity.LOW
            elif delta_pct <= Decimal("10.0"):
                severity = FindingSeverity.MEDIUM
            elif delta_pct <= Decimal("50.0"):
                severity = FindingSeverity.HIGH
            else:
                severity = FindingSeverity.CRITICAL

            return RuleEvaluationResult(
                is_consistent=False,
                rule_code=cls.RULE_CODE,
                category=FindingCategory.CROSS_DOC_MISMATCH,
                epistemic_tier=EpistemicTier.DETECTED_INCONSISTENCY,
                severity=severity,
                confidence=joint_conf,
                title=(
                    f"Quantity Discrepancy: {doc_type_b} exceeds {doc_type_a} by "
                    f"{delta} {can_unit_a} ({delta_pct:.2f}%)"
                ),
                explanation=(
                    f"{doc_type_b} claims {val_b} {can_unit_a} ('{raw_b}'), which exceeds "
                    f"{doc_type_a} baseline of {val_a} {can_unit_a} ('{raw_a}') by "
                    f"{delta} {can_unit_a} ({delta_pct:.2f}%). "
                    f"Requires investigation for excess billing or dispatch overrun."
                ),
                compared_fields=(field_id_a, field_id_b),
                original_values=(raw_a, raw_b),
                normalized_values=(f"{val_a} {can_unit_a}", f"{val_b} {can_unit_b}"),
                evidence_field_ids=field_ids,
                discrepancy_delta=delta,
                discrepancy_percent=delta_pct,
            )
        else:
            # Under-delivery or partial shipment: document B < baseline document A
            delta = val_a - val_b
            delta_pct = (delta / val_a * Decimal("100.0")) if val_a > 0 else Decimal("0.0")

            if not is_order_closed:
                # Normal partial delivery on an open purchase order / continuous supply contract
                return RuleEvaluationResult(
                    is_consistent=True,
                    rule_code=cls.RULE_CODE,
                    category=FindingCategory.CROSS_DOC_MISMATCH,
                    epistemic_tier=EpistemicTier.CONFIRMED_OBSERVATION,
                    severity=FindingSeverity.LOW,
                    confidence=joint_conf,
                    title=(
                        f"Partial Delivery (Open Order): {val_b} of {val_a} {can_unit_a} delivered"
                    ),
                    explanation=(
                        f"{doc_type_b} reflects {val_b} {can_unit_a} ('{raw_b}') delivered "
                        f"against {doc_type_a} order of {val_a} {can_unit_a} ('{raw_a}'). "
                        f"Order remains open; delivery shortfall of {delta} {can_unit_a} "
                        f"({delta_pct:.2f}%) is expected across subsequent shipments."
                    ),
                    compared_fields=(field_id_a, field_id_b),
                    original_values=(raw_a, raw_b),
                    normalized_values=(f"{val_a} {can_unit_a}", f"{val_b} {can_unit_b}"),
                    evidence_field_ids=field_ids,
                    discrepancy_delta=delta,
                    discrepancy_percent=delta_pct,
                )

            # Order is closed/finalized: shortfall constitutes an unfulfilled delivery discrepancy
            severity = (
                FindingSeverity.LOW if delta_pct <= Decimal("50.0") else FindingSeverity.MEDIUM
            )
            return RuleEvaluationResult(
                is_consistent=False,
                rule_code=cls.RULE_CODE,
                category=FindingCategory.CROSS_DOC_MISMATCH,
                epistemic_tier=EpistemicTier.DETECTED_INCONSISTENCY,
                severity=severity,
                confidence=joint_conf,
                title=(
                    f"Delivery Shortfall on Closed Order: {doc_type_b} short by "
                    f"{delta} {can_unit_a} ({delta_pct:.2f}%)"
                ),
                explanation=(
                    f"{doc_type_b} delivered only {val_b} {can_unit_a} ('{raw_b}') against "
                    f"closed {doc_type_a} requirement of {val_a} {can_unit_a} ('{raw_a}'). "
                    f"Shortfall of {delta} {can_unit_a} ({delta_pct:.2f}%) on closed case."
                ),
                compared_fields=(field_id_a, field_id_b),
                original_values=(raw_a, raw_b),
                normalized_values=(f"{val_a} {can_unit_a}", f"{val_b} {can_unit_b}"),
                evidence_field_ids=field_ids,
                discrepancy_delta=delta,
                discrepancy_percent=delta_pct,
            )


class MaterialGradeConsistencyRule:
    """Validates metallurgical / material alloy specifications across documents.

    Alloy substitution (e.g. SS 316L ordered, SS 304 delivered/certified) represents
    a critical quality and compliance violation.
    """

    RULE_CODE = "RULE_GRADE_CONSISTENCY"

    @classmethod
    def evaluate(
        cls,
        grade_a: str,
        raw_a: str,
        field_id_a: str,
        conf_a: float,
        grade_b: str,
        raw_b: str,
        field_id_b: str,
        conf_b: float,
        doc_type_a: str = "PURCHASE_ORDER",
        doc_type_b: str = "MILL_TEST_CERT",
        alignment_conf: float = 1.0,
    ) -> RuleEvaluationResult:
        """Compare ordered material grade with delivered or certified grade."""
        joint_conf = min(conf_a, conf_b) * alignment_conf
        field_ids = tuple(fid for fid in (field_id_a, field_id_b) if fid)

        clean_a = clean_string_identifier(grade_a)
        clean_b = clean_string_identifier(grade_b)

        if clean_a == clean_b:
            return RuleEvaluationResult(
                is_consistent=True,
                rule_code=cls.RULE_CODE,
                category=FindingCategory.CROSS_DOC_MISMATCH,
                epistemic_tier=EpistemicTier.CONFIRMED_OBSERVATION,
                severity=FindingSeverity.LOW,
                confidence=joint_conf,
                title=f"Consistent Material Grade: {grade_a}",
                explanation=(
                    f"Material specification matches between {doc_type_a} ('{raw_a}') "
                    f"and {doc_type_b} ('{raw_b}')."
                ),
                compared_fields=(field_id_a, field_id_b),
                original_values=(raw_a, raw_b),
                normalized_values=(clean_a, clean_b),
                evidence_field_ids=field_ids,
            )

        return RuleEvaluationResult(
            is_consistent=False,
            rule_code=cls.RULE_CODE,
            category=FindingCategory.CROSS_DOC_MISMATCH,
            epistemic_tier=EpistemicTier.DETECTED_INCONSISTENCY,
            severity=FindingSeverity.CRITICAL,
            confidence=joint_conf,
            title=f"Material Grade Contradiction: {grade_a} vs {grade_b}",
            explanation=(
                f"Metallurgical specification contradiction: {doc_type_a} ordered material grade "
                f"'{raw_a}' ({clean_a}), but {doc_type_b} specifies '{raw_b}' ({clean_b}). "
                f"Grade substitution may compromise structural or chemical compliance."
            ),
            compared_fields=(field_id_a, field_id_b),
            original_values=(raw_a, raw_b),
            normalized_values=(clean_a, clean_b),
            evidence_field_ids=field_ids,
        )


class EntityNameConsistencyRule:
    """Validates buyer and vendor corporate identities across documents."""

    RULE_CODE = "RULE_PARTY_CONSISTENCY"

    @classmethod
    def evaluate(
        cls,
        name_a: str,
        raw_a: str,
        field_id_a: str,
        conf_a: float,
        name_b: str,
        raw_b: str,
        field_id_b: str,
        conf_b: float,
        party_role: str = "Buyer",
        doc_type_a: str = "PURCHASE_ORDER",
        doc_type_b: str = "COMMERCIAL_INVOICE",
        alignment_conf: float = 1.0,
        is_order_closed: bool = False,
    ) -> RuleEvaluationResult:
        """Compare organization names for a given role across two documents."""
        joint_conf = min(conf_a, conf_b) * alignment_conf
        field_ids = tuple(fid for fid in (field_id_a, field_id_b) if fid)

        norm_a = clean_corporate_name(name_a)
        norm_b = clean_corporate_name(name_b)

        if norm_a == norm_b:
            return RuleEvaluationResult(
                is_consistent=True,
                rule_code=cls.RULE_CODE,
                category=FindingCategory.CROSS_DOC_MISMATCH,
                epistemic_tier=EpistemicTier.CONFIRMED_OBSERVATION,
                severity=FindingSeverity.LOW,
                confidence=joint_conf,
                title=f"Consistent {party_role} Identity: {norm_a}",
                explanation=(
                    f"{party_role} name matches across {doc_type_a} ('{raw_a}') "
                    f"and {doc_type_b} ('{raw_b}')."
                ),
                compared_fields=(field_id_a, field_id_b),
                original_values=(raw_a, raw_b),
                normalized_values=(norm_a, norm_b),
                evidence_field_ids=field_ids,
            )

        return RuleEvaluationResult(
            is_consistent=False,
            rule_code=cls.RULE_CODE,
            category=FindingCategory.CROSS_DOC_MISMATCH,
            epistemic_tier=EpistemicTier.DETECTED_INCONSISTENCY,
            severity=FindingSeverity.HIGH,
            confidence=joint_conf,
            title=f"{party_role} Identity Contradiction: '{name_a}' vs '{name_b}'",
            explanation=(
                f"{party_role} identity contradiction: {doc_type_a} lists '{raw_a}' ({norm_a}), "
                f"whereas {doc_type_b} lists '{raw_b}' ({norm_b})."
            ),
            compared_fields=(field_id_a, field_id_b),
            original_values=(raw_a, raw_b),
            normalized_values=(norm_a, norm_b),
            evidence_field_ids=field_ids,
        )


class ReferenceCodeConsistencyRule:
    """Validates cited cross-references against authoritative document numbers."""

    RULE_CODE = "RULE_REF_CONSISTENCY"

    @classmethod
    def evaluate(
        cls,
        cited_code: str,
        cited_raw: str,
        cited_field_id: str,
        cited_conf: float,
        actual_code: str,
        actual_raw: str,
        actual_field_id: str,
        actual_conf: float,
        reference_type: str = "Purchase Order",
        citing_doc_type: str = "DELIVERY_CHALLAN",
        target_doc_type: str = "PURCHASE_ORDER",
        alignment_conf: float = 1.0,
    ) -> RuleEvaluationResult:
        """Compare a cited reference in Document A with the actual identifier of Document B."""
        joint_conf = min(cited_conf, actual_conf) * alignment_conf
        field_ids = tuple(fid for fid in (cited_field_id, actual_field_id) if fid)

        clean_cited = clean_string_identifier(cited_code)
        clean_actual = clean_string_identifier(actual_code)

        if clean_cited == clean_actual:
            return RuleEvaluationResult(
                is_consistent=True,
                rule_code=cls.RULE_CODE,
                category=FindingCategory.CROSS_DOC_MISMATCH,
                epistemic_tier=EpistemicTier.CONFIRMED_OBSERVATION,
                severity=FindingSeverity.LOW,
                confidence=joint_conf,
                title=f"Consistent {reference_type} Reference: {actual_code}",
                explanation=(
                    f"{citing_doc_type} correctly references {target_doc_type} '{actual_code}'."
                ),
                compared_fields=(cited_field_id, actual_field_id),
                original_values=(cited_raw, actual_raw),
                normalized_values=(clean_cited, clean_actual),
                evidence_field_ids=field_ids,
            )

        return RuleEvaluationResult(
            is_consistent=False,
            rule_code=cls.RULE_CODE,
            category=FindingCategory.CROSS_DOC_MISMATCH,
            epistemic_tier=EpistemicTier.DETECTED_INCONSISTENCY,
            severity=FindingSeverity.HIGH,
            confidence=joint_conf,
            title=(
                f"Conflicting {reference_type} Reference: {citing_doc_type} cites "
                f"'{cited_code}' but {target_doc_type} is '{actual_code}'"
            ),
            explanation=(
                f"Reference mismatch: {citing_doc_type} cites {reference_type} '{cited_raw}' "
                f"({clean_cited}), but the actual {target_doc_type} identifier in this case is "
                f"'{actual_raw}' ({clean_actual})."
            ),
            compared_fields=(cited_field_id, actual_field_id),
            original_values=(cited_raw, actual_raw),
            normalized_values=(clean_cited, clean_actual),
            evidence_field_ids=field_ids,
        )


class FinancialTotalConsistencyRule:
    """Validates line item arithmetic (Rate * Qty = Total) and grand total summation."""

    RULE_CODE = "RULE_FIN_TOTAL_CONSISTENCY"
    ROUNDING_TOLERANCE = Decimal("0.02")

    @classmethod
    def evaluate_line_total(
        cls,
        unit_rate: Decimal,
        quantity: Decimal,
        stated_total: Decimal,
        raw_rate: str,
        raw_qty: str,
        raw_total: str,
        field_ids: tuple[str, ...],
        conf: float = 1.0,
        currency: str = "INR",
        doc_type: str = "COMMERCIAL_INVOICE",
    ) -> RuleEvaluationResult:
        """Verify line item arithmetic: unit_rate * quantity == stated_total."""
        expected_total = unit_rate * quantity
        delta = stated_total - expected_total

        if abs(delta) <= cls.ROUNDING_TOLERANCE:
            return RuleEvaluationResult(
                is_consistent=True,
                rule_code=cls.RULE_CODE,
                category=FindingCategory.ARITHMETIC_MISMATCH,
                epistemic_tier=EpistemicTier.CONFIRMED_OBSERVATION,
                severity=FindingSeverity.LOW,
                confidence=conf,
                title=f"Valid Line Total: {stated_total} {currency}",
                explanation=(
                    f"Line total in {doc_type} correctly calculates: "
                    f"{unit_rate} * {quantity} = {stated_total} {currency}."
                ),
                compared_fields=field_ids[:2] if len(field_ids) >= 2 else ("", ""),
                original_values=(f"{raw_rate} x {raw_qty}", raw_total),
                normalized_values=(str(expected_total), str(stated_total)),
                evidence_field_ids=field_ids,
                discrepancy_delta=Decimal("0.0"),
                discrepancy_percent=Decimal("0.0"),
            )

        delta_abs = abs(delta)
        delta_pct = (
            (delta_abs / expected_total * Decimal("100.0"))
            if expected_total > 0
            else Decimal("100.0")
        )

        if delta_pct <= Decimal("1.0"):
            severity = FindingSeverity.LOW
        elif delta_pct <= Decimal("10.0"):
            severity = FindingSeverity.MEDIUM
        elif delta_pct <= Decimal("50.0"):
            severity = FindingSeverity.HIGH
        else:
            severity = FindingSeverity.CRITICAL

        return RuleEvaluationResult(
            is_consistent=False,
            rule_code=cls.RULE_CODE,
            category=FindingCategory.ARITHMETIC_MISMATCH,
            epistemic_tier=EpistemicTier.DETECTED_INCONSISTENCY,
            severity=severity,
            confidence=conf,
            title=(
                f"Arithmetic Mismatch in {doc_type}: Line Total discrepancy of "
                f"{delta} {currency} ({delta_pct:.2f}%)"
            ),
            explanation=(
                f"Arithmetic discrepancy in {doc_type}: unit rate {unit_rate} * quantity "
                f"{quantity} yields {expected_total} {currency}, but stated line total is "
                f"{stated_total} {currency} (discrepancy {delta:+} {currency}, {delta_pct:.2f}%)."
            ),
            compared_fields=field_ids[:2] if len(field_ids) >= 2 else ("", ""),
            original_values=(f"{raw_rate} x {raw_qty}", raw_total),
            normalized_values=(str(expected_total), str(stated_total)),
            evidence_field_ids=field_ids,
            discrepancy_delta=delta,
            discrepancy_percent=delta_pct,
        )

    @classmethod
    def evaluate_grand_total(
        cls,
        subtotal: Decimal,
        taxes: Decimal,
        stated_grand_total: Decimal,
        freight: Decimal = Decimal("0.0"),
        discounts: Decimal = Decimal("0.0"),
        other_adjustments: Decimal = Decimal("0.0"),
        field_ids: tuple[str, ...] = (),
        conf: float = 1.0,
        currency: str = "INR",
        doc_type: str = "COMMERCIAL_INVOICE",
    ) -> RuleEvaluationResult:
        """Verify grand total arithmetic with subtotal, taxes, freight, discounts, adjustments."""
        expected = subtotal + taxes + freight + other_adjustments - discounts
        delta = stated_grand_total - expected

        orig_str = f"subtotal={subtotal}, tax={taxes}"
        if freight > 0:
            orig_str += f", freight={freight}"
        if discounts > 0:
            orig_str += f", disc={discounts}"
        if other_adjustments != 0:
            orig_str += f", adj={other_adjustments}"

        if abs(delta) <= cls.ROUNDING_TOLERANCE:
            return RuleEvaluationResult(
                is_consistent=True,
                rule_code=cls.RULE_CODE,
                category=FindingCategory.ARITHMETIC_MISMATCH,
                epistemic_tier=EpistemicTier.CONFIRMED_OBSERVATION,
                severity=FindingSeverity.LOW,
                confidence=conf,
                title=f"Valid Grand Total: {stated_grand_total} {currency}",
                explanation=(
                    f"Grand total in {doc_type} correctly calculates: expected "
                    f"{expected} {currency} matches stated {stated_grand_total} {currency}."
                ),
                compared_fields=field_ids[:2] if len(field_ids) >= 2 else ("", ""),
                original_values=(orig_str, str(stated_grand_total)),
                normalized_values=(str(expected), str(stated_grand_total)),
                evidence_field_ids=field_ids,
                discrepancy_delta=Decimal("0.0"),
                discrepancy_percent=Decimal("0.0"),
            )

        delta_abs = abs(delta)
        delta_pct = (delta_abs / expected * Decimal("100.0")) if expected > 0 else Decimal("100.0")

        if delta_pct <= Decimal("1.0"):
            severity = FindingSeverity.LOW
        elif delta_pct <= Decimal("10.0"):
            severity = FindingSeverity.MEDIUM
        elif delta_pct <= Decimal("50.0"):
            severity = FindingSeverity.HIGH
        else:
            severity = FindingSeverity.CRITICAL

        return RuleEvaluationResult(
            is_consistent=False,
            rule_code=cls.RULE_CODE,
            category=FindingCategory.ARITHMETIC_MISMATCH,
            epistemic_tier=EpistemicTier.DETECTED_INCONSISTENCY,
            severity=severity,
            confidence=conf,
            title=(
                f"Arithmetic Mismatch in {doc_type}: Grand Total discrepancy of "
                f"{delta} {currency} ({delta_pct:.2f}%)"
            ),
            explanation=(
                f"Grand total calculation error in {doc_type}: components ({orig_str}) "
                f"yield expected {expected} {currency}, but document states {stated_grand_total} "
                f"{currency} (difference {delta:+} {currency}, {delta_pct:.2f}%)."
            ),
            compared_fields=field_ids[:2] if len(field_ids) >= 2 else ("", ""),
            original_values=(orig_str, str(stated_grand_total)),
            normalized_values=(str(expected), str(stated_grand_total)),
            evidence_field_ids=field_ids,
            discrepancy_delta=delta,
            discrepancy_percent=delta_pct,
        )


class ChronologicalSequenceRule:
    """Validates document sequence (e.g. PO date <= Challan delivery date <= Invoice date)."""

    RULE_CODE = "RULE_CHRONOLOGY_CONSISTENCY"

    @classmethod
    def evaluate(
        cls,
        date_earlier: date,
        raw_earlier: str,
        field_id_earlier: str,
        conf_earlier: float,
        event_earlier: str,
        doc_type_earlier: str,
        date_later: date,
        raw_later: str,
        field_id_later: str,
        conf_later: float,
        event_later: str,
        doc_type_later: str,
        alignment_conf: float = 1.0,
    ) -> RuleEvaluationResult:
        """Verify that event_earlier occurred on or before event_later."""
        joint_conf = min(conf_earlier, conf_later) * alignment_conf
        field_ids = tuple(fid for fid in (field_id_earlier, field_id_later) if fid)

        if date_earlier <= date_later:
            days = (date_later - date_earlier).days
            return RuleEvaluationResult(
                is_consistent=True,
                rule_code=cls.RULE_CODE,
                category=FindingCategory.TEMPORAL_CONTRADICTION,
                epistemic_tier=EpistemicTier.CONFIRMED_OBSERVATION,
                severity=FindingSeverity.LOW,
                confidence=joint_conf,
                title=f"Valid Chronological Sequence: {doc_type_earlier} precedes {doc_type_later}",
                explanation=(
                    f"Timeline sequence verified: {event_earlier} ({date_earlier.isoformat()}) "
                    f"precedes {event_later} ({date_later.isoformat()}) by {days} days."
                ),
                compared_fields=(field_id_earlier, field_id_later),
                original_values=(raw_earlier, raw_later),
                normalized_values=(date_earlier.isoformat(), date_later.isoformat()),
                evidence_field_ids=field_ids,
            )

        days_inverted = (date_earlier - date_later).days
        return RuleEvaluationResult(
            is_consistent=False,
            rule_code=cls.RULE_CODE,
            category=FindingCategory.TEMPORAL_CONTRADICTION,
            epistemic_tier=EpistemicTier.DETECTED_INCONSISTENCY,
            severity=FindingSeverity.HIGH,
            confidence=joint_conf,
            title=(
                f"Temporal Contradiction: {event_later} ({date_later.isoformat()}) "
                f"predates {event_earlier} ({date_earlier.isoformat()})"
            ),
            explanation=(
                f"Inverted chronological timeline: {doc_type_later} specifies {event_later} on "
                f"'{raw_later}' ({date_later.isoformat()}), which predates {event_earlier} on "
                f"'{raw_earlier}' ({date_earlier.isoformat()}) in {doc_type_earlier} by "
                f"{days_inverted} days. An invoice or delivery cannot precede its purchase order."
            ),
            compared_fields=(field_id_earlier, field_id_later),
            original_values=(raw_earlier, raw_later),
            normalized_values=(date_earlier.isoformat(), date_later.isoformat()),
            evidence_field_ids=field_ids,
        )


class BatchNumberConsistencyRule:
    """Validates heat / batch / lot number correspondence between challan and test certificates."""

    RULE_CODE = "RULE_BATCH_CONSISTENCY"

    @classmethod
    def evaluate(
        cls,
        batch_a: str,
        raw_a: str,
        field_id_a: str,
        conf_a: float,
        batch_b: str,
        raw_b: str,
        field_id_b: str,
        conf_b: float,
        doc_type_a: str = "DELIVERY_CHALLAN",
        doc_type_b: str = "MILL_TEST_CERT",
        alignment_conf: float = 1.0,
    ) -> RuleEvaluationResult:
        """Compare batch or heat numbers across delivery documents and test certificates."""
        joint_conf = min(conf_a, conf_b) * alignment_conf
        field_ids = tuple(fid for fid in (field_id_a, field_id_b) if fid)

        clean_a = clean_string_identifier(batch_a)
        clean_b = clean_string_identifier(batch_b)

        if clean_a == clean_b:
            return RuleEvaluationResult(
                is_consistent=True,
                rule_code=cls.RULE_CODE,
                category=FindingCategory.CROSS_DOC_MISMATCH,
                epistemic_tier=EpistemicTier.CONFIRMED_OBSERVATION,
                severity=FindingSeverity.LOW,
                confidence=joint_conf,
                title=f"Consistent Heat/Batch Number: {batch_a}",
                explanation=(
                    f"Batch/heat number matches across {doc_type_a} ('{raw_a}') "
                    f"and {doc_type_b} ('{raw_b}')."
                ),
                compared_fields=(field_id_a, field_id_b),
                original_values=(raw_a, raw_b),
                normalized_values=(clean_a, clean_b),
                evidence_field_ids=field_ids,
            )

        return RuleEvaluationResult(
            is_consistent=False,
            rule_code=cls.RULE_CODE,
            category=FindingCategory.CROSS_DOC_MISMATCH,
            epistemic_tier=EpistemicTier.DETECTED_INCONSISTENCY,
            severity=FindingSeverity.HIGH,
            confidence=joint_conf,
            title=f"Heat/Batch Number Mismatch: '{batch_a}' vs '{batch_b}'",
            explanation=(
                f"Batch/heat number mismatch: {doc_type_a} lists '{raw_a}' ({clean_a}), "
                f"but {doc_type_b} certifies '{raw_b}' ({clean_b}). "
                f"Delivered goods cannot be confirmed as certified by this test report."
            ),
            compared_fields=(field_id_a, field_id_b),
            original_values=(raw_a, raw_b),
            normalized_values=(clean_a, clean_b),
            evidence_field_ids=field_ids,
        )


class ExplicitDocumentReferenceCompletenessRule:
    """Detects when Document A cites Document B, but Document B is missing from the case."""

    RULE_CODE = "RULE_EXPLICIT_REF_COMPLETENESS"

    @classmethod
    def evaluate(
        cls,
        citing_doc_id: str,
        citing_doc_type: str,
        cited_doc_type: str,
        cited_reference_code: str,
        available_doc_references: Sequence[str],
        evidence_field_ids: tuple[str, ...],
        conf: float = 1.0,
    ) -> RuleEvaluationResult:
        """Check if cited_reference_code is present in available_doc_references."""
        clean_cited = clean_string_identifier(cited_reference_code)
        clean_available = {clean_string_identifier(r) for r in available_doc_references if r}

        if clean_cited in clean_available:
            return RuleEvaluationResult(
                is_consistent=True,
                rule_code=cls.RULE_CODE,
                category=FindingCategory.CROSS_DOC_MISMATCH,
                epistemic_tier=EpistemicTier.CONFIRMED_OBSERVATION,
                severity=FindingSeverity.LOW,
                confidence=conf,
                title=f"Referenced Document Present: {cited_doc_type} '{cited_reference_code}'",
                explanation=(
                    f"{citing_doc_type} references {cited_doc_type} '{cited_reference_code}', "
                    f"which is present in the case submission."
                ),
                compared_fields=(citing_doc_id, cited_reference_code),
                original_values=(cited_reference_code, cited_reference_code),
                normalized_values=(clean_cited, clean_cited),
                evidence_field_ids=evidence_field_ids,
            )

        return RuleEvaluationResult(
            is_consistent=False,
            rule_code=cls.RULE_CODE,
            category=FindingCategory.CROSS_DOC_MISMATCH,
            epistemic_tier=EpistemicTier.CONFIRMED_OBSERVATION,
            severity=FindingSeverity.MEDIUM,
            confidence=conf,
            title=(
                f"Missing Referenced Document: {citing_doc_type} cites {cited_doc_type} "
                f"'{cited_reference_code}'"
            ),
            explanation=(
                f"{citing_doc_type} explicitly cites {cited_doc_type} '{cited_reference_code}', "
                f"but no document matching this reference was submitted to this investigation. "
                f"Physical delivery or quality certification cannot be independently verified."
            ),
            compared_fields=(citing_doc_id, cited_reference_code),
            original_values=(cited_reference_code, "NOT_FOUND"),
            normalized_values=(clean_cited, "MISSING"),
            evidence_field_ids=evidence_field_ids,
        )
