"""Unit tests for DossierExportService."""

from __future__ import annotations

import json
from pathlib import Path

from veritrace.application.dto.dossier import DossierExportRequestDTO
from veritrace.application.services.dossier_export_service import DossierExportService
from veritrace.domain.enums.audit import AuditEventType
from veritrace.gui.demo_data import seed_industrial_demo


def test_dossier_export_service_end_to_end(tmp_path: Path, test_uow_factory):
    """Verify DossierExportService compiles PDF, JSON, and records audit event."""
    org_id = "org_11111111111111111111111111111111"
    inv_id = seed_industrial_demo(test_uow_factory, organization_id=org_id)

    service = DossierExportService(test_uow_factory)

    pdf_out = tmp_path / "custom_dossier.pdf"
    json_out = tmp_path / "custom_dossier.json"

    req = DossierExportRequestDTO(
        investigation_id=inv_id,
        organization_id=org_id,
        output_pdf_path=str(pdf_out),
        output_json_path=str(json_out),
        executive_narrative="Comprehensive industrial procurement verification audit.",
    )

    result = service.export_dossier(req)

    assert result.investigation_id == inv_id
    assert result.dossier_id.startswith("dos_")
    assert Path(result.pdf_path).exists()
    assert Path(result.json_path).exists()
    assert len(result.sha256_hash) == 64
    assert result.documents_count >= 4

    # Verify JSON content
    with open(result.json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["investigation_id"] == inv_id
    assert "section_1_document_overview" in data
    assert "section_6_investigation_summary" in data

    # Verify audit event
    with test_uow_factory() as uow:
        events = uow.audit_events.list_by_investigation(inv_id, org_id)
        types = [e.event_type for e in events]
        assert AuditEventType.DOSSIER_COMPILED in types
