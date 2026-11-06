"""Deterministic field normalizers for cross-document entity and metric reconciliation.

CRITICAL INVARIANTS:
1. Normalization is strictly deterministic and idempotent: f(f(x)) == f(x).
2. Raw extracted values are strictly preserved without alteration.
3. Quantities and currencies use exact Decimal representation.
4. Ambiguous values (unspecified units, conflicting formats) are explicitly flagged.
5. Incompatible physical dimensions (e.g. mass vs length) are never converted.
6. Unknown material grade aliases are never invented.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from veritrace.capabilities.correlation.models import (
    NormalizedAmount,
    NormalizedDate,
    NormalizedIdentifier,
    NormalizedMaterialGrade,
    NormalizedOrganizationName,
    NormalizedQuantity,
)
from veritrace.domain.rules.cross_document import (
    canonicalize_quantity,
    clean_corporate_name,
    clean_string_identifier,
)

# Known canonical material grades and their accepted aliases
_CANONICAL_MATERIAL_GRADES: dict[str, str] = {
    # Stainless Steel 316L
    "SS 316L": "SS 316L",
    "SS-316L": "SS 316L",
    "SS316L": "SS 316L",
    "AISI 316L": "SS 316L",
    "AISI-316L": "SS 316L",
    "SUS 316L": "SS 316L",
    "316L": "SS 316L",
    "STAINLESS STEEL 316L": "SS 316L",
    # Stainless Steel 316
    "SS 316": "SS 316",
    "SS-316": "SS 316",
    "SS316": "SS 316",
    "AISI 316": "SS 316",
    "316": "SS 316",
    "STAINLESS STEEL 316": "SS 316",
    # Stainless Steel 304
    "SS 304": "SS 304",
    "SS-304": "SS 304",
    "SS304": "SS 304",
    "AISI 304": "SS 304",
    "SUS 304": "SS 304",
    "304": "SS 304",
    "STAINLESS STEEL 304": "SS 304",
    # Stainless Steel 304L
    "SS 304L": "SS 304L",
    "SS-304L": "SS 304L",
    "SS304L": "SS 304L",
    "AISI 304L": "SS 304L",
    "304L": "SS 304L",
    # Structural & Pressure Vessel Steels
    "IS 2062": "IS 2062",
    "IS-2062": "IS 2062",
    "IS2062": "IS 2062",
    "SA 516 GR 70": "SA 516 GR 70",
    "SA516-70": "SA 516 GR 70",
    "SA 516 GRADE 70": "SA 516 GR 70",
    "SA 106 GR B": "SA 106 GR B",
    "ASTM A106 GRADE B": "SA 106 GR B",
}

# Currency symbols to ISO codes
_CURRENCY_SYMBOLS: dict[str, str] = {
    "₹": "INR",
    "RS": "INR",
    "RS.": "INR",
    "INR": "INR",
    "$": "USD",
    "USD": "USD",
    "€": "EUR",
    "EUR": "EUR",
    "£": "GBP",
    "GBP": "GBP",
}


def normalize_quantity(
    raw_text: str,
    confidence: float = 1.0,
    default_unit: str | None = None,
) -> NormalizedQuantity:
    """Normalize extracted quantity string into a canonical unit (KG, M, PCS).

    Preserves verbatim raw text. Flags ambiguity if unit is missing or unrecognized.
    """
    clean_text = raw_text.strip()
    if not clean_text:
        return NormalizedQuantity(
            value=Decimal("0.0"),
            unit="UNSPECIFIED",
            raw_value=raw_text,
            confidence=0.0,
            is_ambiguous=True,
            ambiguity_reason="Empty quantity string",
        )

    # Extract numeric part and unit suffix
    match = re.match(
        r"^\s*([+-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+))\s*([A-Za-z]+(?:\s+[A-Za-z]+)?)?\s*$",
        clean_text,
    )
    if not match:
        # Fallback: extract first number found
        num_search = re.search(r"([+-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+))", clean_text)
        if not num_search:
            return NormalizedQuantity(
                value=Decimal("0.0"),
                unit="UNSPECIFIED",
                raw_value=raw_text,
                confidence=0.0,
                is_ambiguous=True,
                ambiguity_reason=f"Unable to parse numeric quantity from '{raw_text}'",
            )
        num_str = num_search.group(1).replace(",", "")
        unit_str = clean_text[num_search.end() :].strip()
    else:
        num_str = match.group(1).replace(",", "")
        unit_str = (match.group(2) or "").strip()

    try:
        val = Decimal(num_str)
    except InvalidOperation:
        return NormalizedQuantity(
            value=Decimal("0.0"),
            unit="UNSPECIFIED",
            raw_value=raw_text,
            confidence=0.0,
            is_ambiguous=True,
            ambiguity_reason=f"Invalid decimal number: '{num_str}'",
        )

    if not unit_str:
        if default_unit:
            unit_str = default_unit
        else:
            return NormalizedQuantity(
                value=val,
                unit="UNSPECIFIED",
                raw_value=raw_text,
                confidence=confidence,
                is_ambiguous=True,
                ambiguity_reason="Missing physical unit of measurement",
            )

    canon = canonicalize_quantity(val, unit_str)
    if canon is None:
        return NormalizedQuantity(
            value=val,
            unit=unit_str.upper(),
            raw_value=raw_text,
            confidence=confidence,
            is_ambiguous=True,
            ambiguity_reason=f"Unrecognized physical unit: '{unit_str}'",
        )

    canon_val, canon_unit = canon
    return NormalizedQuantity(
        value=canon_val,
        unit=canon_unit,
        raw_value=raw_text,
        confidence=confidence,
        is_ambiguous=False,
    )


def normalize_amount(
    raw_text: str,
    confidence: float = 1.0,
    default_currency: str = "INR",
) -> NormalizedAmount:
    """Normalize monetary amounts, currency symbols, and comma patterns."""
    clean_text = raw_text.strip()
    if not clean_text:
        return NormalizedAmount(
            value=Decimal("0.0"),
            currency=default_currency,
            raw_value=raw_text,
            confidence=0.0,
            is_ambiguous=True,
            ambiguity_reason="Empty currency string",
        )

    # Detect currency symbols or codes
    currency = default_currency
    for sym, code in _CURRENCY_SYMBOLS.items():
        if sym in clean_text.upper():
            currency = code
            clean_text = re.sub(re.escape(sym), "", clean_text, flags=re.IGNORECASE).strip()
            break

    # Strip commas and non-numeric artifacts except period and minus
    cleaned_num = re.sub(r"[^\d.-]", "", clean_text).strip()
    try:
        val = Decimal(cleaned_num)
    except InvalidOperation:
        return NormalizedAmount(
            value=Decimal("0.0"),
            currency=currency,
            raw_value=raw_text,
            confidence=0.0,
            is_ambiguous=True,
            ambiguity_reason=f"Unable to parse financial amount from '{raw_text}'",
        )

    return NormalizedAmount(
        value=val,
        currency=currency,
        raw_value=raw_text,
        confidence=confidence,
        is_ambiguous=False,
    )


def normalize_date(
    raw_text: str,
    confidence: float = 1.0,
) -> NormalizedDate:
    """Normalize extracted date string to a date object."""
    clean_text = raw_text.strip()
    if not clean_text:
        return NormalizedDate(
            value=date(1970, 1, 1),
            raw_value=raw_text,
            confidence=0.0,
            is_ambiguous=True,
            ambiguity_reason="Empty date string",
        )

    # Supported date formats
    date_formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%d-%b-%Y",
        "%d %b %Y",
        "%d-%B-%Y",
        "%d %B %Y",
        "%b %d, %Y",
        "%B %d, %Y",
    ]

    for fmt in date_formats:
        try:
            parsed = datetime.strptime(clean_text, fmt).date()
            return NormalizedDate(
                value=parsed,
                raw_value=raw_text,
                confidence=confidence,
                is_ambiguous=False,
            )
        except ValueError:
            continue

    return NormalizedDate(
        value=date(1970, 1, 1),
        raw_value=raw_text,
        confidence=0.0,
        is_ambiguous=True,
        ambiguity_reason=f"Unrecognized date format: '{raw_text}'",
    )


def normalize_material_grade(
    raw_text: str,
    confidence: float = 1.0,
) -> NormalizedMaterialGrade:
    """Normalize material specification to canonical industrial alloy grade.

    Never invents aliases for unknown materials.
    """
    clean_text = raw_text.strip().upper()
    if not clean_text:
        return NormalizedMaterialGrade(
            canonical_grade="",
            raw_value=raw_text,
            confidence=0.0,
            is_ambiguous=True,
            ambiguity_reason="Empty material grade string",
        )

    # 1. Direct dictionary alias lookup
    if clean_text in _CANONICAL_MATERIAL_GRADES:
        return NormalizedMaterialGrade(
            canonical_grade=_CANONICAL_MATERIAL_GRADES[clean_text],
            raw_value=raw_text,
            confidence=confidence,
            is_ambiguous=False,
        )

    # 2. Normalized alphanumeric key lookup
    clean_key = clean_string_identifier(clean_text)
    for alias, canonical in _CANONICAL_MATERIAL_GRADES.items():
        if clean_string_identifier(alias) == clean_key:
            return NormalizedMaterialGrade(
                canonical_grade=canonical,
                raw_value=raw_text,
                confidence=confidence,
                is_ambiguous=False,
            )

    # 3. Unknown material: preserve cleaned representation without hallucinating aliases
    cleaned_unknown = re.sub(r"\s+", " ", clean_text)
    return NormalizedMaterialGrade(
        canonical_grade=cleaned_unknown,
        raw_value=raw_text,
        confidence=confidence,
        is_ambiguous=False,
    )


def normalize_organization_name(
    raw_text: str,
    confidence: float = 1.0,
) -> NormalizedOrganizationName:
    """Normalize corporate entity name by removing legal entity suffixes."""
    clean_text = raw_text.strip()
    if not clean_text:
        return NormalizedOrganizationName(
            canonical_name="",
            raw_value=raw_text,
            confidence=0.0,
            is_ambiguous=True,
            ambiguity_reason="Empty organization name",
        )

    canonical = clean_corporate_name(clean_text)
    return NormalizedOrganizationName(
        canonical_name=canonical,
        raw_value=raw_text,
        confidence=confidence,
        is_ambiguous=not bool(canonical),
        ambiguity_reason=None if canonical else "Corporate name reduction produced empty string",
    )


def normalize_identifier(
    raw_text: str,
    id_type: str = "DOCUMENT_REFERENCE",
    confidence: float = 1.0,
) -> NormalizedIdentifier:
    """Normalize document reference codes, heat/batch numbers, or tax identifiers."""
    clean_text = raw_text.strip()
    if not clean_text:
        return NormalizedIdentifier(
            canonical_id="",
            identifier_type=id_type,
            raw_value=raw_text,
            confidence=0.0,
            is_ambiguous=True,
            ambiguity_reason="Empty identifier string",
        )

    canonical = clean_string_identifier(clean_text)
    return NormalizedIdentifier(
        canonical_id=canonical,
        identifier_type=id_type,
        raw_value=raw_text,
        confidence=confidence,
        is_ambiguous=not bool(canonical),
        ambiguity_reason=None if canonical else "Identifier stripped of all alphanumeric chars",
    )
