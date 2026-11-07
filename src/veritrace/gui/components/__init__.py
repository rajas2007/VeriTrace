"""PySide6 Presentation Components."""

from veritrace.gui.components.contextual_audit_table import (
    ContextualAuditWidget,
)
from veritrace.gui.components.dashboard_widget import (
    DashboardBannerWidget,
    MetricCard,
)
from veritrace.gui.components.document_viewer import (
    DocumentCanvasView,
    SideBySideDocumentViewer,
)
from veritrace.gui.components.evidence_inspector import EvidenceInspectorDock
from veritrace.gui.components.finding_table import FindingTableWidget
from veritrace.gui.components.investigation_sidebar import InvestigationSidebar
from veritrace.gui.components.signature_workbench import (
    SignatureWorkbenchWidget,
)
from veritrace.gui.components.status_bar import VeriTraceStatusBar

__all__ = [
    "ContextualAuditWidget",
    "DashboardBannerWidget",
    "DocumentCanvasView",
    "EvidenceInspectorDock",
    "FindingTableWidget",
    "InvestigationSidebar",
    "MetricCard",
    "SideBySideDocumentViewer",
    "SignatureWorkbenchWidget",
    "VeriTraceStatusBar",
]
