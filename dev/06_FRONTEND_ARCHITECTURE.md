# 06_FRONTEND_ARCHITECTURE.md
# VeriTrace Desktop Presentation Layer Architecture & PySide6 UI Specification

---

## 1. UI Design Philosophy & Native Desktop Workstation UX

**VeriTrace Desktop** is an installed forensic investigation workstation, NOT a web dashboard. Built natively using **PySide6 (Qt 6.7+ for Python)** with **Qt Widgets**, custom **Qt Style Sheets (QSS)**, and a reactive **Signals & Slots** event system, the interface is optimized for forensic clarity, high-throughput evidence exploration, and responsive workstation operation:
1. **Native Desktop Monolith:** Direct Python execution without browser engines, webviews, or loopback HTTP servers. High performance, zero IPC serialization latency, and direct access to native Windows UI capabilities.
2. **Investigation Workstation Layout:** Optimized 4-pane workstation layout:
   * **Left Sidebar:** Case navigation, document gallery, recent investigations, and pipeline status.
   * **Central Workspace:** High-DPI document viewer with sub-millimeter coordinate overlays and split-screen comparison.
   * **Right Inspector:** Evidence Inspector dock widget displaying visual crops, ELA heatmaps, and OCR confidence.
   * **Bottom Panel:** Job execution progress, pipeline telemetry, and audit logs.
3. **High-Performance Document Viewer:** Powered by PyMuPDF and Qt's `QGraphicsView` / `QGraphicsScene` architecture for smooth pan, infinite zoom, and interactive bounding box coordinate overlays.
4. **Qt Model/View Architecture:** Decoupled data models (`QAbstractTableModel`, `QAbstractItemModel`) feeding structured findings and evidence trees to UI views with zero UI stutter.
5. **Multi-Threaded Responsiveness:** All long-running operations (PDF rendering, OCR, ELA, RapidFuzz) run on background threads via `QThreadPool` / `QRunnable`, keeping the Qt UI event loop at a constant 60 FPS.

---

## 2. Authoritative Presentation Directory Structure

Under ADR-030, the native PySide6 presentation layer is located inside `src/veritrace/gui/`:

```
src/veritrace/gui/
├── __init__.py
├── app.py                             # QApplication subclass, lifecycle & High-DPI setup
│
├── views/                             # Primary Views & Top-Level Windows
│   ├── __init__.py
│   ├── main_window.py                 # Main investigation workstation window
│   ├── investigation_view.py          # Investigation dashboard & multi-document workspace
│   ├── document_view.py               # Document review & page navigation container
│   ├── evidence_view.py               # Discrepancy matrix & evidence tree browser
│   ├── dossier_view.py                # Dossier preview & export configuration
│   └── settings_view.py               # Engine configuration & API key management
│
├── components/                        # Reusable Custom Qt Widgets
│   ├── __init__.py
│   ├── document_viewer.py             # QGraphicsView + QGraphicsScene page viewer with zoom/pan
│   ├── evidence_inspector.py          # QDockWidget for ELA crops & metadata inspection
│   ├── investigation_sidebar.py       # Case & document navigation tree
│   ├── finding_table.py               # QTableView for 3-tier findings & anomalies
│   └── status_bar.py                  # QStatusBar with QProgressBar & stage telemetry
│
├── controllers/                       # Presentation Mediators
│   ├── __init__.py
│   ├── investigation_controller.py    # Mediates case actions & application service calls
│   ├── document_controller.py         # Mediates page navigation, zoom, and coordinate scaling
│   └── forensics_controller.py        # Mediates finding reviews, filtering, and confirmations
│
├── viewmodels/                        # UI State Holders
│   ├── __init__.py
│   ├── case_vm.py                     # Active case state, document list, and metadata
│   ├── document_vm.py                 # Active document, page cache, zoom factor, and overlays
│   └── findings_vm.py                 # Filtered findings, tier selections, and triage flags
│
├── styles/                            # Theming & Qt Style Sheets
│   ├── __init__.py
│   ├── theme_manager.py               # QSS loader, icon color resolver & font scaler
│   └── dark_theme.qss                 # Professional forensic dark theme stylesheet
│
└── resources/                         # Assets & Static Icons
    ├── __init__.py
    ├── icons/                         # SVG & PNG forensic icons
    └── fonts/                         # Bundled monospace & UI fonts
```
│   ├── __init__.py
│   ├── investigation_vm.py            # Case metadata & status signals
│   ├── document_vm.py                 # Active document, page & zoom state
│   └── evidence_vm.py                 # Selected finding & crop state
│
└── resources/                         # Application Icon & Packaging Assets
    ├── __init__.py
    └── veritrace.ico                  # Native Windows executable icon
```

---

## 3. Core UI Component Specifications

### 3.1 Main Window (`ui/windows/main_window.py`)
* **Base Class:** `QMainWindow`.
* **Features:**
  * Frameless or native styled window with custom toolbar and status bar.
  * Integration of Qt Docking system (`QDockWidget`) allowing investigators to customize, detach, or collapse panels.
  * Persistence of window geometry and splitter states in Windows Registry / QSettings.

### 3.2 High-DPI Document & Bounding Box Viewer (`ui/components/document_viewer.py`)
* **Base Class:** `QGraphicsView` backed by `QGraphicsScene`.
* **Features:**
  * Renders 300 DPI page images directly from disk using `QPixmap`.
  * Interactive coordinate overlays with color-coded bounding box items (`QGraphicsRectItem`):
    * **Red Boxes:** Visual manipulation / ELA compression anomalies.
    * **Orange Boxes:** Cross-document contradictory values.
    * **Blue Boxes:** Normal extracted fields with OCR confidence tags.
  * Smooth mouse-wheel zooming, click-and-drag panning, and sub-pixel box selection.
  * **Visual Diff Mode:** Instant hotkey or button toggle between *Original Render*, *ELA Heatmap*, and *Threshold Mask*.

### 3.3 Evidence Inspector (`ui/components/evidence_inspector.py`)
* **Base Class:** `QDockWidget`.
* **Features:**
  * Displays high-resolution visual crops of the active finding.
  * Side-by-side comparison of original crop vs. ELA differential heatmap.
  * Extracted text, character bounding box coordinates, and token confidence score.
  * Rule violation summary and optional LLM forensic reasoning.
  * Human-in-the-Loop review buttons: `Confirm Finding`, `Dismiss (False Positive)`, `Add Investigator Note`.

### 3.4 Investigation Sidebar (`ui/components/investigation_sidebar.py`)
* **Base Class:** `QWidget` hosting a `QTreeView`.
* **Features:**
  * Tree hierarchy: Case $\rightarrow$ Documents $\rightarrow$ Pages.
  * Drag-and-drop file ingestion area for adding new PDFs, PNGs, and JPEGs.
  * Document classification badges (ID, Salary Slip, Bank Statement, Invoice).

### 3.5 Status Bar & Progress Telemetry (`ui/components/status_bar.py`)
* **Base Class:** `QStatusBar`.
* **Features:**
  * Embedded `QProgressBar` tracking active pipeline percentage (0% to 100%).
  * Stage label (`INTAKE`, `OCR`, `FORENSICS`, `CORRELATION`, `DOSSIER`).
  * Telemetry indicators (CPU memory usage, worker thread state).

---

## 4. UI Threading & Background Task Strategy

The UI thread must never freeze during forensic computation:
* **Interactive Requests:** Creating cases, querying documents, or changing view filters are sub-millisecond in-process service calls.
* **Heavy Processing Pipeline:** Triggering document analysis launches a `QRunnable` task submitted to the global `QThreadPool`.
* **Signals & Slots Communication:**
  * The background runnable emits custom Qt signals (`progress_updated`, `stage_changed`, `pipeline_completed`, `pipeline_failed`) through a helper `QObject` signal bridge.
  * The main window and status bar receive these signals on the main Qt event loop and update widgets safely and instantly.
