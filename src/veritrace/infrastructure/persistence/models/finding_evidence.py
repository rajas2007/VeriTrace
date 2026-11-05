"""Association table mapping Findings to supporting Evidence anchors."""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Index, String, Table

from veritrace.infrastructure.persistence.base import Base

finding_evidence_map = Table(
    "finding_evidence_map",
    Base.metadata,
    Column(
        "finding_id",
        String(36),
        ForeignKey("findings.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "evidence_id",
        String(36),
        ForeignKey("evidence.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Index("idx_finding_evidence_map_finding_id", "finding_id"),
    Index("idx_finding_evidence_map_evidence_id", "evidence_id"),
)
