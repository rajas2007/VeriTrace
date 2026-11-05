"""Unit tests for domain identifier and timestamp value objects and helpers."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from veritrace.domain.exceptions import InvalidIdentifierError, InvalidTimestampError
from veritrace.domain.value_objects.identifiers import (
    ANC_PREFIX,
    AUD_PREFIX,
    DOC_PREFIX,
    DOS_PREFIX,
    ENT_PREFIX,
    EVD_PREFIX,
    FLD_PREFIX,
    FND_PREFIX,
    INV_PREFIX,
    JOB_PREFIX,
    ORG_PREFIX,
    PAGE_PREFIX,
    REL_PREFIX,
    REV_PREFIX,
    SIGREF_PREFIX,
    SUBJ_PREFIX,
    TOK_PREFIX,
    ensure_utc,
    generate_id,
    utc_now,
    validate_id,
)

ALL_PREFIXES = [
    ORG_PREFIX,
    SUBJ_PREFIX,
    SIGREF_PREFIX,
    INV_PREFIX,
    JOB_PREFIX,
    DOC_PREFIX,
    PAGE_PREFIX,
    FLD_PREFIX,
    TOK_PREFIX,
    ENT_PREFIX,
    FND_PREFIX,
    EVD_PREFIX,
    ANC_PREFIX,
    REL_PREFIX,
    REV_PREFIX,
    DOS_PREFIX,
    AUD_PREFIX,
]


def test_evidence_id_prefix_is_evd() -> None:
    """Verify authoritative Evidence ID prefix is evd_ and anchor prefix is anc_."""
    assert EVD_PREFIX == "evd_"
    assert ANC_PREFIX == "anc_"


def test_legacy_ev_prefix_strictly_rejected() -> None:
    """Verify legacy ev_ prefix is rejected in canonical domain validation paths."""
    legacy_id = "ev_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
    with pytest.raises(InvalidIdentifierError) as exc_info:
        validate_id(legacy_id, EVD_PREFIX, "evidence_id")
    assert "must start with prefix 'evd_'" in str(exc_info.value)


def test_all_prefixes_end_with_underscore() -> None:
    """Verify that all standard domain entity prefixes end with an underscore."""
    for prefix in ALL_PREFIXES:
        assert prefix.endswith("_")
        assert prefix.islower() or "_" in prefix


def test_generate_id_format() -> None:
    """Verify generated identifier structure and uniqueness."""
    ids = set()
    for prefix in ALL_PREFIXES:
        new_id = generate_id(prefix)
        assert new_id.startswith(prefix)
        hex_part = new_id[len(prefix) :]
        assert len(hex_part) == 32
        assert all(c in "0123456789abcdef" for c in hex_part)
        ids.add(new_id)

    # All distinct IDs generated
    assert len(ids) == len(ALL_PREFIXES)


def test_validate_id_success() -> None:
    """Verify validation passes for properly formatted IDs."""
    test_id = generate_id(DOC_PREFIX)
    validated = validate_id(test_id, DOC_PREFIX, "test_doc_id")
    assert validated == test_id


def test_validate_id_wrong_prefix_raises() -> None:
    """Verify validation raises when prefix does not match expected prefix."""
    doc_id = generate_id(DOC_PREFIX)
    with pytest.raises(InvalidIdentifierError) as exc_info:
        validate_id(doc_id, INV_PREFIX, "investigation_id")
    assert "must start with prefix 'inv_'" in str(exc_info.value)


def test_validate_id_non_hex_raises() -> None:
    """Verify validation raises when the UUID component contains non-hex chars."""
    bad_id = f"{DOC_PREFIX}{'z' * 32}"
    with pytest.raises(InvalidIdentifierError) as exc_info:
        validate_id(bad_id, DOC_PREFIX, "document_id")
    assert "invalid UUID suffix" in str(exc_info.value)


def test_validate_id_wrong_length_raises() -> None:
    """Verify validation raises when the UUID hex is too short or too long."""
    short_id = f"{DOC_PREFIX}1234"
    with pytest.raises(InvalidIdentifierError):
        validate_id(short_id, DOC_PREFIX, "document_id")

    long_id = f"{DOC_PREFIX}{'a' * 33}"
    with pytest.raises(InvalidIdentifierError):
        validate_id(long_id, DOC_PREFIX, "document_id")


def test_validate_id_non_string_raises() -> None:
    """Verify validation raises when passed a non-string value."""
    with pytest.raises(InvalidIdentifierError):
        validate_id(12345, DOC_PREFIX, "document_id")  # type: ignore[arg-type]


def test_utc_now_is_timezone_aware() -> None:
    """Verify utc_now produces timezone-aware UTC datetime."""
    now = utc_now()
    assert isinstance(now, datetime)
    assert now.tzinfo is not None
    assert now.tzinfo == UTC


def test_ensure_utc_rejects_naive_datetime() -> None:
    """Verify ensure_utc strictly rejects naive datetimes."""
    naive = datetime(2026, 11, 5, 12, 0, 0)
    with pytest.raises(InvalidTimestampError) as exc_info:
        ensure_utc(naive)
    assert "must be timezone-aware (UTC)" in str(exc_info.value)


def test_ensure_utc_aware_datetime() -> None:
    """Verify ensure_utc converts non-UTC aware datetime to UTC."""
    est = timezone(timedelta(hours=-5))
    dt_est = datetime(2026, 11, 5, 12, 0, 0, tzinfo=est)
    dt_utc = ensure_utc(dt_est)
    assert dt_utc.tzinfo == UTC
    assert dt_utc.hour == 17  # 12:00 EST -> 17:00 UTC


def test_ensure_utc_invalid_type_raises() -> None:
    """Verify ensure_utc raises InvalidTimestampError on non-datetime."""
    with pytest.raises(InvalidTimestampError) as exc_info:
        ensure_utc("not-a-datetime")  # type: ignore[arg-type]
    assert "must be a datetime instance" in str(exc_info.value)
