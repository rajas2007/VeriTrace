"""Tests for MainWindow forensic tabs and workbench interactions."""

from __future__ import annotations

from veritrace.application.services.cross_document_correlation_service import (
    CrossDocumentCorrelationService,
)
from veritrace.application.services.investigation_service import (
    InvestigationService,
)
from veritrace.gui.views.main_window import MainWindow


def test_main_window_tabs_and_workbenches(app_instance, test_uow_factory):
    """Verify tabs, signature workbench, contextual audit, and layer switching."""
    inv_service = InvestigationService(test_uow_factory)
    corr_service = CrossDocumentCorrelationService(test_uow_factory)

    window = MainWindow(
        investigation_service=inv_service,
        correlation_service=corr_service,
        uow_factory=test_uow_factory,
        organization_id="org_11111111111111111111111111111111",
    )

    # 1. Check auto-seeding on fresh launch
    assert window._active_investigation_id is not None
    assert len(window._docs_by_id) == 4

    # 2. Check 4 tabs mounted
    assert window._tabs.count() == 4
    assert window._tabs.tabText(0) == "Contradiction Matrix"
    assert window._tabs.tabText(1) == "Side-by-Side Evidence Canvas"
    assert window._tabs.tabText(2) == "✍️ Signature Workbench"
    assert window._tabs.tabText(3) == "🧮 Math & Chronology Audit"

    # 3. Test Signature Workbench trigger
    window._on_run_signatures()
    assert window._tabs.currentIndex() == 2
    assert window._signature_workbench._table.rowCount() >= 1

    # 4. Test Contextual Audit trigger
    window._on_run_contextual_audit()
    assert window._tabs.currentIndex() == 3
    assert window._contextual_audit._table.rowCount() >= 4

    # 5. Test Canvas layer toggle
    window._tabs.setCurrentIndex(1)
    window._doc_viewer._combo_layer.setCurrentIndex(1)  # Switch to ELA
    assert window._doc_viewer._left_canvas._active_layer_mode == "ela"

    # 6. Test Inspector Dock crops
    finding = window._current_findings[0]
    window._on_finding_selected(finding.id)
    assert window._inspector_dock._active_finding is not None

    window.close()
