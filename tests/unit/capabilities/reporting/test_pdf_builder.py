"""Unit tests for PdfDossierBuilder ReportLab rendering."""

from pathlib import Path

import cv2
import numpy as np

from tests.unit.capabilities.reporting.test_json_builder import create_test_entities
from veritrace.capabilities.reporting.json_builder import JsonDossierBuilder
from veritrace.capabilities.reporting.pdf_builder import PdfDossierBuilder


def test_pdf_builder_generates_valid_pdf(tmp_path: Path):
    """Verify PdfDossierBuilder generates a valid, non-empty PDF binary."""
    inv, docs, fields, rules, proposals, evs = create_test_entities()

    # Create dummy image crop for evidence embedding
    dummy_crop = np.full((100, 200, 3), 240, dtype=np.uint8)
    crop_path = tmp_path / "crop_test.png"
    cv2.imwrite(str(crop_path), dummy_crop)
    evs[0].crop_image_path = str(crop_path)

    builder_json = JsonDossierBuilder()
    payload = builder_json.build_payload(
        investigation=inv,
        documents=docs,
        fields=fields,
        rule_evaluations=rules,
        findings_or_proposals=proposals,
        evidence_records=evs,
        executive_narrative="Sample executive forensic summary.",
    )

    pdf_builder = PdfDossierBuilder()
    out_pdf = tmp_path / "output_dossier.pdf"
    result_path = pdf_builder.build_pdf(payload=payload, output_pdf_path=out_pdf)

    assert result_path.exists()
    assert result_path.stat().st_size > 1000  # Multi-page styled PDF

    # Check PDF magic bytes
    with open(result_path, "rb") as f:
        header = f.read(5)
    assert header == b"%PDF-"
