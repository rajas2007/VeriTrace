"""Integration tests for VeriTrace PySide6 GUI Workstation."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from veritrace.application.dto.correlation import (
    CorrelationRequestDTO,
    CorrelationSummaryDTO,
)
from veritrace.application.dto.investigation import (
    ReviewDecisionType,
    ReviewFindingRequestDTO,
)
from veritrace.application.services.cross_document_correlation_service import (
    CrossDocumentCorrelationService,
)
from veritrace.application.services.investigation_service import (
    InvestigationService,
)
from veritrace.domain.enums.audit import AuditEventType
from veritrace.domain.enums.forensic import (
    ReviewStatus,
)
from veritrace.domain.exceptions.base import ValidationError
from veritrace.gui.controllers.correlation_worker import CorrelationWorker
from veritrace.gui.demo_data import seed_industrial_demo
from veritrace.gui.views.main_window import MainWindow
from veritrace.infrastructure.persistence.database import (
    create_db_engine,
    create_session_factory,
    init_db,
)
from veritrace.infrastructure.persistence.models.organization import (
    OrganizationModel,
)
from veritrace.infrastructure.persistence.unit_of_work import (
    SqlAlchemyUnitOfWork,
)


@pytest.fixture
def test_uow_factory(tmp_path):
    """Create temporary SQLite database and return unit of work factory."""
    db_path = tmp_path / "gui_test.db"
    engine = create_db_engine(f"sqlite:///{db_path.as_posix()}")
    init_db(engine)
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        session.add(
            OrganizationModel(
                id="org_11111111111111111111111111111111",
                name="Default Manufacturing Organization",
                industry_sector="MANUFACTURING",
                created_at=datetime.now(UTC),
            )
        )
        session.commit()
    return lambda: SqlAlchemyUnitOfWork(session_factory)


@pytest.fixture
def app_instance():
    """Ensure a QApplication instance exists in offscreen mode."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_main_window_initialization(app_instance, test_uow_factory):
    """Verify MainWindow mounts all 4 workstation panes cleanly."""
    inv_service = InvestigationService(test_uow_factory)
    corr_service = CrossDocumentCorrelationService(test_uow_factory)

    window = MainWindow(
        investigation_service=inv_service,
        correlation_service=corr_service,
        uow_factory=test_uow_factory,
        organization_id="org_11111111111111111111111111111111",
    )
    assert window.windowTitle().startswith("VeriTrace Workstation")
    assert window._sidebar is not None
    assert window._finding_table is not None
    assert window._doc_viewer is not None
    assert window._inspector_dock is not None
    assert window._status_bar is not None
    window.close()


def test_industrial_demo_seeding_and_visual_workflow(app_instance, test_uow_factory):
    """Verify loading the 4-document demo, physical files, visual canvas, and correlation."""
    inv_service = InvestigationService(test_uow_factory)
    corr_service = CrossDocumentCorrelationService(test_uow_factory)

    window = MainWindow(
        investigation_service=inv_service,
        correlation_service=corr_service,
        uow_factory=test_uow_factory,
        organization_id="org_11111111111111111111111111111111",
    )

    # 1. Load industrial demo
    window._on_load_demo()
    assert window._active_investigation_id is not None

    # Check 4 documents ingested with physical viewable files on disk
    docs = inv_service.list_documents(
        window._active_investigation_id, "org_11111111111111111111111111111111"
    )
    assert len(docs) == 4
    doc_names = {d.original_filename for d in docs}
    assert "PO-2026-IND-001.pdf" in doc_names
    assert "DC-98741.pdf" in doc_names
    assert "MTC-H8821.pdf" in doc_names
    assert "INV-88992.pdf" in doc_names

    # Verify each document has physical PDF and rendered PNG page images on disk
    for d in docs:
        assert Path(d.storage_path).exists(), f"Original file missing: {d.storage_path}"
        pages = inv_service.list_document_pages(
            d.document_id, "org_11111111111111111111111111111111"
        )
        assert len(pages) >= 1
        p = pages[0]
        assert Path(p.image_storage_path).exists(), f"Page image missing: {p.image_storage_path}"

    # 2. Test document tree click navigation
    po_doc = next(d for d in docs if d.original_filename == "PO-2026-IND-001.pdf")
    window._on_document_selected(po_doc.document_id)
    assert window._tabs.currentIndex() == 1  # Switched to visual canvas tab
    assert "PO-2026-IND-001.pdf" in window._doc_viewer._left_title.text()
    assert window._doc_viewer._left_canvas._pixmap_item is not None

    # 3. Run correlation (open order: is_order_closed=False)
    corr_req = CorrelationRequestDTO(
        investigation_id=window._active_investigation_id,
        organization_id="org_11111111111111111111111111111111",
        is_order_closed=False,
    )
    summary = corr_service.correlate_investigation(corr_req)

    # Verify discrepancies: Grade conflict, Over-billing
    assert summary.discrepancies_count >= 2
    rule_codes = {d.rule_code for d in summary.discrepancies}
    assert "RULE_GRADE_CONSISTENCY" in rule_codes  # Grade mismatch (PO SS 316L vs DC SS 304)
    assert "RULE_QTY_CONSISTENCY" in rule_codes  # Over-billing (INV 1000 KG vs DC 800 KG)

    # Partial delivery on open order should NOT be flagged as short delivery
    shortfall = next(
        (d for d in summary.discrepancies if "shortfall" in d.title.lower()),
        None,
    )
    assert shortfall is None

    # Reload case into window
    window._reload_case_data()
    assert len(window._current_findings) >= 2

    # 4. Test finding table selection and side-by-side evidence visualization
    finding = window._current_findings[0]
    window._on_finding_selected(finding.id)
    assert window._inspector_dock._active_finding is not None
    assert window._inspector_dock._active_finding.id == finding.id

    # Verify both canvases loaded real pixmaps and rendered bounding boxes
    assert window._doc_viewer._left_canvas._pixmap_item is not None
    assert window._doc_viewer._left_canvas._highlight_rect is not None
    assert window._doc_viewer._right_canvas._pixmap_item is not None
    assert window._doc_viewer._right_canvas._highlight_rect is not None

    # Verify document titles in comparison header
    docs_in_view = (
        window._doc_viewer._left_title.text() + " " + window._doc_viewer._right_title.text()
    )
    assert "PO-2026-IND-001.pdf" in docs_in_view
    assert "MTC-H8821.pdf" in docs_in_view or "DC-98741.pdf" in docs_in_view

    window.close()


def test_human_review_adjudication_and_reload_persistence(app_instance, test_uow_factory):
    """Verify human confirmation, dismissal, annotation, audit trail, and restart persistence."""
    inv_service = InvestigationService(test_uow_factory)
    corr_service = CrossDocumentCorrelationService(test_uow_factory)

    window = MainWindow(
        investigation_service=inv_service,
        correlation_service=corr_service,
        uow_factory=test_uow_factory,
        organization_id="org_11111111111111111111111111111111",
    )
    window._on_load_demo()

    # Run correlation to produce findings
    corr_req = CorrelationRequestDTO(
        investigation_id=window._active_investigation_id,
        organization_id="org_11111111111111111111111111111111",
        is_order_closed=False,
    )
    corr_service.correlate_investigation(corr_req)
    window._reload_case_data()

    assert len(window._current_findings) >= 3
    f1 = window._current_findings[0]
    f2 = window._current_findings[1]
    f3 = window._current_findings[2]

    # 1. Confirm finding 1
    window._on_review_submitted(
        finding_id=f1.id,
        decision=ReviewDecisionType.CONFIRMED,
        rationale=(
            "Verified against Mill Test Certificate: Delivered SS 304 does not match PO "
            "specification SS 316L."
        ),
        reviewer_id="lead_examiner_01",
    )
    updated1 = inv_service.get_finding(f1.id, "org_11111111111111111111111111111111")
    assert updated1 is not None
    assert updated1.review_status == ReviewStatus.CONFIRMED
    assert len(updated1.review_decisions) == 1
    assert updated1.review_decisions[0].decision == ReviewDecisionType.CONFIRMED
    assert updated1.review_decisions[0].reviewer_id == "lead_examiner_01"

    # 2. Dismiss finding 2 - verify whitespace-only rationale is rejected
    with pytest.raises(ValidationError):
        inv_service.review_finding(
            investigation_id=window._active_investigation_id,
            request=ReviewFindingRequestDTO(
                finding_id=f2.id,
                decision=ReviewDecisionType.DISMISSED,
                rationale="   ",
                reviewer_id="analyst_01",
            ),
            organization_id="org_11111111111111111111111111111111",
        )

    # Now dismiss with valid justification
    window._on_review_submitted(
        finding_id=f2.id,
        decision=ReviewDecisionType.DISMISSED,
        rationale="Alternative alloy grade authorized under technical deviation concession C-102.",
        reviewer_id="lead_examiner_02",
    )
    updated2 = inv_service.get_finding(f2.id, "org_11111111111111111111111111111111")
    assert updated2 is not None
    assert updated2.review_status == ReviewStatus.DISMISSED

    # 3. Annotate finding 3 (multiple annotations appended without overwriting)
    window._on_review_submitted(
        finding_id=f3.id,
        decision=ReviewDecisionType.ANNOTATED,
        rationale="Supplier representative contacted; claims warehouse batch mix-up.",
        reviewer_id="lead_examiner_01",
    )
    window._on_review_submitted(
        finding_id=f3.id,
        decision=ReviewDecisionType.ANNOTATED,
        rationale="Commercial department confirmed credit note issued for 200 KG overrun.",
        reviewer_id="lead_examiner_03",
    )
    updated3 = inv_service.get_finding(f3.id, "org_11111111111111111111111111111111")
    assert updated3 is not None
    assert updated3.review_status == ReviewStatus.ANNOTATED
    assert len(updated3.review_decisions) == 2
    assert "warehouse batch mix-up" in (updated3.investigator_guidance or "")
    assert "credit note issued" in (updated3.investigator_guidance or "")

    # 4. Verify immutable audit events
    with test_uow_factory() as uow:
        events = uow.audit_events.list_by_investigation(
            window._active_investigation_id, "org_11111111111111111111111111111111"
        )
        types = [e.event_type for e in events]
        assert AuditEventType.HUMAN_REVIEW_CONFIRMED in types
        assert AuditEventType.HUMAN_REVIEW_DISMISSED in types
        assert AuditEventType.HUMAN_REVIEW_ANNOTATED in types

    # 5. Simulate application restart: load new MainWindow on same database
    active_inv_id = window._active_investigation_id
    window.close()

    window_reloaded = MainWindow(
        investigation_service=inv_service,
        correlation_service=corr_service,
        uow_factory=test_uow_factory,
        organization_id="org_11111111111111111111111111111111",
    )
    window_reloaded._on_investigation_selected(active_inv_id)

    # Verify all findings retain their review statuses and review decision histories
    reloaded_f1 = next(f for f in window_reloaded._current_findings if f.id == f1.id)
    reloaded_f2 = next(f for f in window_reloaded._current_findings if f.id == f2.id)
    reloaded_f3 = next(f for f in window_reloaded._current_findings if f.id == f3.id)

    assert reloaded_f1.review_status == ReviewStatus.CONFIRMED
    assert len(reloaded_f1.review_decisions) == 1
    assert reloaded_f2.review_status == ReviewStatus.DISMISSED
    assert len(reloaded_f2.review_decisions) == 1
    assert reloaded_f3.review_status == ReviewStatus.ANNOTATED
    assert len(reloaded_f3.review_decisions) == 2

    window_reloaded.close()


def test_correlation_worker_thread(app_instance, test_uow_factory):
    """Verify background CorrelationWorker signals without UI blocking."""
    corr_service = CrossDocumentCorrelationService(test_uow_factory)
    demo_id = seed_industrial_demo(test_uow_factory, "org_11111111111111111111111111111111")

    request = CorrelationRequestDTO(
        investigation_id=demo_id,
        organization_id="org_11111111111111111111111111111111",
        is_order_closed=False,
    )

    worker = CorrelationWorker(corr_service, request)

    results: list[CorrelationSummaryDTO] = []
    progress_updates: list[tuple[int, str]] = []

    worker.progress_signal.connect(lambda pct, msg: progress_updates.append((pct, msg)))
    worker.finished_signal.connect(lambda res: results.append(res))

    worker.run()  # Direct synchronous run call to verify logic and signals

    assert len(results) == 1
    assert results[0].discrepancies_count >= 2
    assert len(progress_updates) >= 4
