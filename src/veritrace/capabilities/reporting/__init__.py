"""Forensic Investigation Dossier Builder (JSON & ReportLab PDF)."""

from veritrace.capabilities.reporting.dossier_compiler import DossierCompiler
from veritrace.capabilities.reporting.json_builder import JsonDossierBuilder
from veritrace.capabilities.reporting.models import (
    ContextualInconsistencyItem,
    DocumentOverviewItem,
    EvidenceTraceabilityItem,
    ExtractedFieldItem,
    InvestigationDossierPayload,
    InvestigationSummarySection,
    VisualForensicItem,
)
from veritrace.capabilities.reporting.pdf_builder import PdfDossierBuilder

__all__ = [
    "ContextualInconsistencyItem",
    "DocumentOverviewItem",
    "DossierCompiler",
    "EvidenceTraceabilityItem",
    "ExtractedFieldItem",
    "InvestigationDossierPayload",
    "InvestigationSummarySection",
    "JsonDossierBuilder",
    "PdfDossierBuilder",
    "VisualForensicItem",
]
