"""Add unique constraint on signature references (subject_id, sha256_hash).

Revision ID: 002_sig_ref_unique_hash
Revises: 001_initial_schema
Create Date: 2026-11-07 14:35:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_sig_ref_unique_hash"
down_revision: str | None = "001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Pre-migration data audit: fail safely if duplicate (subject_id, sha256_hash) exist.
    # INVARIANT: Automatic deletion or modification of biometric reference profiles
    # is strictly prohibited to preserve forensic integrity and legal chain-of-custody.
    dup_query = sa.text(
        """
        SELECT subject_id, sha256_hash, COUNT(*) AS dup_count
        FROM signature_references
        GROUP BY subject_id, sha256_hash
        HAVING COUNT(*) > 1
        """
    )
    duplicates = conn.execute(dup_query).fetchall()
    if duplicates:
        dup_details = [
            f"subject_id='{row[0]}', sha256_hash='{row[1][:16]}...' (count={row[2]})"
            for row in duplicates
        ]
        raise RuntimeError(
            "Cannot apply migration 002_sig_ref_unique_hash: "
            f"Found {len(duplicates)} duplicate signature reference specimen(s) in database:\n"
            + "\n".join(f"  - {d}" for d in dup_details)
            + "\nACTION REQUIRED: Resolve duplicate signature reference specimens under strict "
            "chain-of-custody review before applying this unique constraint migration. "
            "Automatic deletion or deduplication is prohibited to protect forensic audit trails."
        )

    # 2. Forward migration: create unique index if not already present.
    inspector = sa.inspect(conn)
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("signature_references")}
    if "uq_signature_references_subject_hash" not in existing_indexes:
        op.create_index(
            "uq_signature_references_subject_hash",
            "signature_references",
            ["subject_id", "sha256_hash"],
            unique=True,
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("signature_references")}
    if "uq_signature_references_subject_hash" in existing_indexes:
        op.drop_index(
            "uq_signature_references_subject_hash",
            table_name="signature_references",
        )
