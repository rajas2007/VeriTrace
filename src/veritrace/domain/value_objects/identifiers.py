"""Entity identifier generation, prefix constants, and UTC timestamp utilities."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

from veritrace.domain.exceptions.base import (
    InvalidIdentifierError,
    InvalidTimestampError,
)

# Standard entity prefixes
ORG_PREFIX = "org_"
SUBJ_PREFIX = "subj_"
SIGREF_PREFIX = "sigref_"
INV_PREFIX = "inv_"
JOB_PREFIX = "job_"
DOC_PREFIX = "doc_"
PAGE_PREFIX = "page_"
FLD_PREFIX = "fld_"
TOK_PREFIX = "tok_"
ENT_PREFIX = "ent_"
FND_PREFIX = "fnd_"
EVD_PREFIX = "evd_"
ANC_PREFIX = "anc_"
REL_PREFIX = "rel_"
REV_PREFIX = "rev_"
DOS_PREFIX = "dos_"
AUD_PREFIX = "aud_"

_HEX_32_PATTERN = re.compile(r"^[0-9a-f]{32}$")
_UUID_HYPHEN_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def generate_id(prefix: str) -> str:
    """Generate a strongly-typed entity identifier using prefix and random UUIDv4 hex."""
    return f"{prefix}{uuid.uuid4().hex}"


def validate_id(id_value: str, expected_prefix: str, field_name: str = "id") -> str:
    """Validate identifier non-empty, expected prefix, and valid hex or UUID."""
    if not isinstance(id_value, str) or not id_value.strip():
        raise InvalidIdentifierError(f"{field_name} must be a non-empty string, got {id_value!r}")

    if not id_value.startswith(expected_prefix):
        raise InvalidIdentifierError(
            f"{field_name} must start with prefix '{expected_prefix}', got '{id_value}'"
        )

    suffix = id_value[len(expected_prefix) :]
    clean_suffix = suffix.lower()

    if not (_HEX_32_PATTERN.match(clean_suffix) or _UUID_HYPHEN_PATTERN.match(clean_suffix)):
        raise InvalidIdentifierError(
            f"{field_name} has invalid UUID suffix '{suffix}' in '{id_value}'"
        )

    return f"{expected_prefix}{clean_suffix.replace('-', '')}"


def utc_now() -> datetime:
    """Return the current timestamp with explicit UTC timezone awareness."""
    return datetime.now(UTC)


def ensure_utc(dt: datetime, field_name: str = "timestamp") -> datetime:
    """Validate that a datetime is timezone-aware and convert/ensure UTC."""
    if not isinstance(dt, datetime):
        raise InvalidTimestampError(
            f"{field_name} must be a datetime instance, got {type(dt).__name__}"
        )

    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise InvalidTimestampError(
            f"{field_name} must be timezone-aware (UTC), received naive datetime: {dt}"
        )

    return dt.astimezone(UTC)
