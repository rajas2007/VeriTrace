"""Unit tests for DossierCompiler end-to-end dossier artifact compilation."""

import hashlib
import json
from pathlib import Path

from tests.unit.capabilities.reporting.test_json_builder import create_test_entities
from veritrace.capabilities.reporting.dossier_compiler import DossierCompiler
from veritrace.domain.entities.dossier import Dossier


def test_dossier_compiler_end_to_end(tmp_path: Path):
    """Verify DossierCompiler outputs Dossier entity, PDF, JSON, and verified cryptographic hash."""
    inv, docs, fields, rules, proposals, evs = create_test_entities()
    compiler = DossierCompiler()

    out_dir = tmp_path / "compiled_dossiers"
    dossier, payload, pdf_path, json_path = compiler.compile_dossier(
        investigation=inv,
        documents=docs,
        fields=fields,
        rule_evaluations=rules,
        findings_or_proposals=proposals,
        evidence_records=evs,
        executive_narrative="End-to-end compiled investigation summary.",
        output_dir=out_dir,
    )

    # 1. Domain entity checks
    assert isinstance(dossier, Dossier)
    assert dossier.investigation_id == inv.id
    assert dossier.id.startswith("dos_")

    # 2. File output checks
    assert pdf_path.exists()
    assert json_path.exists()
    assert pdf_path.stat().st_size > 500
    assert json_path.stat().st_size > 100

    # 3. Cryptographic hash integrity check
    hasher = hashlib.sha256()
    with open(pdf_path, "rb") as f:
        hasher.update(f.read())
    expected_sha256 = hasher.hexdigest()

    assert dossier.pdf_hash_sha256 == expected_sha256

    # 4. JSON structure check
    with open(json_path, encoding="utf-8") as f:
        json_data = json.load(f)
    assert json_data["investigation_id"] == inv.id
    assert "section_1_document_overview" in json_data
    assert "section_6_investigation_summary" in json_data
