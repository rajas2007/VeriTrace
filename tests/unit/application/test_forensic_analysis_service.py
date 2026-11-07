"""Unit tests for ForensicAnalysisService."""

from __future__ import annotations

from pathlib import Path

from veritrace.application.services.forensic_analysis_service import ForensicAnalysisService
from veritrace.gui.demo_data import seed_industrial_demo


def test_forensic_analysis_service_contextual_audit(test_uow_factory):
    """Verify contextual arithmetic and chronology audit across case documents."""
    org_id = "org_11111111111111111111111111111111"
    inv_id = seed_industrial_demo(test_uow_factory, organization_id=org_id)

    service = ForensicAnalysisService(test_uow_factory)
    audit_items = service.run_contextual_audit(inv_id, org_id)

    assert len(audit_items) >= 4
    codes = {item.rule_code for item in audit_items}
    assert "RULE_GRADE_CONSISTENCY" in codes
    assert "RULE_QTY_CONSISTENCY" in codes
    assert "RULE_INVOICE_TAX_CALC" in codes
    assert "RULE_WEIGHT_RECONCILIATION" in codes
    assert "RULE_CHRONOLOGY_AUDIT" in codes


def test_forensic_analysis_service_signature_verification(tmp_path: Path):
    """Verify signature detection and Hu moment verification."""
    import cv2
    import numpy as np

    # Create dummy signature images
    img1 = np.ones((100, 250, 3), dtype=np.uint8) * 255
    cv2.putText(img1, "John Doe", (20, 60), cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, 1.2, (0, 0, 0), 2)
    path1 = tmp_path / "sig1.png"
    cv2.imwrite(str(path1), img1)

    img2 = np.ones((100, 250, 3), dtype=np.uint8) * 255
    cv2.putText(img2, "John Doe", (25, 58), cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, 1.2, (0, 0, 0), 2)
    path2 = tmp_path / "sig2.png"
    cv2.imwrite(str(path2), img2)

    service = ForensicAnalysisService()
    comp = service.compare_signatures(
        questioned_crop_path=str(path1),
        reference_crop_path=str(path2),
        questioned_name="Questioned",
        reference_name="Reference",
    )

    assert comp.is_match is True
    assert comp.hu_distance >= 0.0
    assert comp.stroke_density_ratio > 0.0
