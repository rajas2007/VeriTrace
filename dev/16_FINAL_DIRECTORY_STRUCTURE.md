# 16_FINAL_DIRECTORY_STRUCTURE.md
# Authoritative Repository Directory & Package Structure Specification

---

## 1. Directory Organization Philosophy: Unified Python `src`-Layout

VeriTrace is organized as a **native Python desktop modular monolith** using the standard Python **`src`-layout** (PEP 517/518). 

### 1.1 Why Eliminate the `desktop/` and `backend/` Split?
In earlier iterations (Tasks 02.1 to 02.3), the repository separated `desktop/` (Tauri shell) and `backend/` (FastAPI loopback service). With the transition to **PySide6 (Qt for Python)**, maintaining `desktop/` and `backend/` as top-level directories is an anti-pattern:
1. **Disconnected Module Roots:** It splits a single Python desktop application into two separate packages, requiring brittle `sys.path` workarounds and non-standard imports.
2. **Subdirectory Configuration Bloat:** It buried `pyproject.toml`, `requirements.txt`, and `alembic.ini` inside `backend/`, preventing root-level tooling (`pip install -e .`, `pytest`, `ruff`, `mypy`) from functioning cleanly.
3. **Packaging Friction:** It complicated PyInstaller bundling by forcing analysis across disjointed directories.

### 1.2 The Unified `src/veritrace` Solution
All application source code resides under a single importable namespace: `src/veritrace/`.
* Root level contains standard project configuration (`pyproject.toml`, `requirements.txt`, `alembic.ini`).
* Clean layer boundaries: `gui/` (Presentation), `application/` (Use Cases & Services), `domain/` (Pure Business Rules), `capabilities/` (Forensics & Document Processing Engines), `infrastructure/` (Concrete Tech Adapters), `workers/` (Async Task Execution).
* Tests are consolidated at the repository root under `tests/`.
* Packaging configurations live at the repository root under `packaging/`.
* Runtime user data remains strictly external in `%LOCALAPPDATA%/VeriTrace/`.

---

## 2. Complete Authoritative Repository Tree

```text
VeriTrace/
├── pyproject.toml                     # Modern root Python project configuration (PEP 517/518)
├── requirements.txt                   # Locked dependencies (-e .[all])
├── alembic.ini                        # Database schema migrations
├── README.md                          # Authoritative desktop product README
├── LICENSE                            # MIT License
├── .gitignore                         # Protects %LOCALAPPDATA%, binaries, caches
├── .env.example                       # Local environment configuration template
├── .github/                           # GitHub governance, templates & CI
│   ├── workflows/
│   │   └── ci.yml                     # Continuous integration workflow
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   ├── feature_request.md
│   │   └── architecture_task.md
│   ├── pull_request_template.md       # PR checklist & governance
│   ├── CONTRIBUTING.md                # Multi-developer workflow & branch policies
│   └── CODEOWNERS                     # Workstream ownership declarations
│
├── src/                               # Standard Python src-layout root
│   └── veritrace/                     # Single root Python package
│       ├── __init__.py                # Package version and root metadata
│       ├── __main__.py                # Module entrypoint: python -m veritrace
│       ├── main.py                    # Application launch script
│       ├── bootstrap.py               # Application startup, logging, High-DPI, config
│       │
│       ├── gui/                       # Presentation Layer (PySide6 / Qt 6.7+)
│       │   ├── __init__.py
│       │   ├── app.py                 # QApplication lifecycle & theme management
│       │   ├── main_window.py         # Main investigation workstation window (QMainWindow)
│       │   ├── views/                 # Top-level workspace views (CaseView, DocumentView, DossierView)
│       │   │   └── __init__.py
│       │   ├── components/            # Reusable UI widgets
│       │   │   ├── __init__.py
│       │   │   ├── document_viewer.py # QGraphicsView high-res canvas with coordinate overlays
│       │   │   ├── evidence_inspector.py # QDockWidget for visual crops and ELA heatmaps
│       │   │   ├── sidebar.py         # QTreeView for case & document navigation
│       │   │   ├── finding_table.py   # QTableView for findings triage
│       │   │   └── status_bar.py      # QStatusBar with QProgressBar & stage telemetry
│       │   ├── controllers/           # Presentation mediators mediating service calls
│       │   │   └── __init__.py
│       │   ├── viewmodels/            # UI state holders decoupling domain models from widgets
│       │   │   └── __init__.py
│       │   ├── dialogs/               # Modal dialogs
│       │   │   ├── __init__.py
│       │   │   ├── new_case_dialog.py # Case creation & document drag-and-drop
│       │   │   ├── export_dialog.py   # Dossier PDF export options
│       │   │   └── settings_dialog.py # OCR path, optional Groq API key
│       │   ├── models/                # Qt Model/View implementations
│       │   │   ├── __init__.py
│       │   │   ├── document_model.py  # QAbstractListModel for documents
│       │   │   ├── finding_model.py   # QAbstractTableModel for findings
│       │   │   └── evidence_model.py  # QAbstractItemModel for cross-document graph
│       │   ├── styles/                # Theming and styling
│       │   │   ├── __init__.py
│       │   │   ├── theme_manager.py   # QSS loader and font scaler
│       │   │   └── dark_theme.qss     # Professional forensic dark theme stylesheet
│       │   └── resources/             # Icons, QRC bundles
│       │       └── __init__.py
│       │
│       ├── application/               # Application Layer / Use Cases / Orchestration
│       │   ├── __init__.py
│       │   ├── services/              # High-level Application Services
│       │   │   ├── __init__.py
│       │   │   ├── investigation_service.py # Case lifecycle & metadata
│       │   │   ├── document_service.py      # Intake, SHA-256 hashing, page retrieval
│       │   │   ├── forensics_service.py     # Findings retrieval, evidence anchors
│       │   │   └── dossier_service.py       # ReportLab PDF & JSON compilation
│       │   ├── use_cases/             # CQRS Query/Command use case handlers
│       │   │   └── __init__.py
│       │   ├── dto/                   # Data Transfer Objects (Pydantic v2 schemas)
│       │   │   ├── __init__.py
│       │   │   ├── case_dtos.py       # CreateInvestigationDTO, CaseSummaryDTO
│       │   │   ├── document_dtos.py   # IngestDocumentDTO, DocumentDetailDTO
│       │   │   ├── finding_dtos.py    # FindingDTO, EvidenceAnchorDTO
│       │   │   └── dossier_dtos.py    # DossierExportDTO
│       │   └── workflows/             # Pipeline Coordination & HITL Review
│       │       ├── __init__.py
│       │       ├── pipeline.py        # 12-stage forensic investigation coordinator
│       │       └── review_gate.py     # Human-in-the-Loop checkpoint controller
│       │
│       ├── domain/                    # Pure Domain Layer (No UI/DB/External deps)
│       │   ├── __init__.py
│       │   ├── entities/              # 12 Core Entities
│       │   │   ├── __init__.py
│       │   │   ├── investigation.py   # Root aggregate case container
│       │   │   ├── document.py        # Submitted document entity
│       │   │   ├── document_page.py   # 300 DPI raster page entity
│       │   │   ├── extracted_field.py # OCR token & key-value entity
│       │   │   ├── entity.py          # Canonical real-world fact entity
│       │   │   ├── finding.py         # Standardized forensic conclusion
│       │   │   ├── evidence.py        # Visual crop & coordinate anchor
│       │   │   ├── cross_relation.py  # Cross-document semantic relation
│       │   │   ├── review_decision.py # Human sign-off / dismissal entity
│       │   │   ├── dossier.py         # Compiled report record
│       │   │   ├── audit_event.py     # Immutable event ledger entity
│       │   │   └── job.py             # Investigation processing job entity
│       │   ├── value_objects/         # Domain Value Objects
│       │   │   ├── __init__.py
│       │   │   ├── coordinates.py     # BoundingBox [ymin, xmin, ymax, xmax]
│       │   │   ├── finding_tier.py    # Epistemic tier enum (Observation, Inconsistency, Manipulation)
│       │   │   ├── severity.py        # Severity enum (Critical, Warning, Informational)
│       │   │   └── hash.py            # SHA-256 value object
│       │   ├── rules/                 # Business invariants & verification formulas
│       │   │   └── __init__.py
│       │   ├── interfaces/            # Protocol definitions for adapters and repositories
│       │   │   └── __init__.py
│       │   ├── events/                # Domain event models
│       │   │   └── __init__.py
│       │   └── exceptions/            # Domain-level exceptions
│       │       └── __init__.py
│       │
│       ├── capabilities/              # Document Processing & Forensics Engines (8 Canonical Capabilities)
│       │   ├── __init__.py
│       │   ├── ingestion/             # File intake validation, MIME checking & SHA-256 hash computation
│       │   │   └── __init__.py
│       │   ├── classification/        # Document type classifier (ID, Salary Slip, Invoice, etc.)
│       │   │   └── __init__.py
│       │   ├── extraction/            # Hybrid text extraction (TextExtractorProtocol, vector + OCR fallback)
│       │   │   └── __init__.py
│       │   ├── quality/               # Explicit extraction quality assessment & confidence gating
│       │   │   └── __init__.py
│       │   ├── forensics/             # Visual forensics: ELA, font baseline, clone stamps, evidence crops
│       │   │   └── __init__.py
│       │   ├── correlation/           # Cross-document entity reconciliation (RapidFuzz) & contradiction matrix
│       │   │   └── __init__.py
│       │   ├── reasoning/             # Grounded AI reasoning & narrative synthesis (with offline template fallback)
│       │   │   └── __init__.py
│       │   └── reporting/             # PS-2 Section 7.1-7.6 forensic dossier compilation (ReportLab PDF & JSON)
│       │       └── __init__.py
│       │
│       ├── infrastructure/            # Concrete External Adapters & Third-Party Wrappers
│       │   ├── __init__.py
│       │   ├── persistence/           # SQLite database & SQLAlchemy 2.0 ORM
│       │   │   ├── __init__.py
│       │   │   ├── session.py         # Engine & sessionmaker (PRAGMA journal_mode=WAL)
│       │   │   ├── base.py            # DeclarativeBase
│       │   │   ├── models/            # SQLAlchemy table definitions (12 entities + 1 assoc)
│       │   │   │   └── __init__.py
│       │   │   └── migrations/        # Alembic versioned migration scripts
│       │   │       └── __init__.py
│       │   ├── storage/               # Local filesystem manager (%LOCALAPPDATA%/VeriTrace/)
│       │   │   └── __init__.py
│       │   ├── pdf/                   # PyMuPDF adapter (300 DPI render, vector text parser)
│       │   │   └── __init__.py
│       │   ├── ocr/                   # Tesseract OCR engine adapter
│       │   │   └── __init__.py
│       │   ├── vision/                # OpenCV & Pillow image processing adapter
│       │   │   └── __init__.py
│       │   ├── reporting/             # ReportLab PDF compiler adapter
│       │   │   └── __init__.py
│       │   ├── ai/                    # Groq client adapter (ChatGroq with JSON schema)
│       │   │   └── __init__.py
│       │   └── security/              # Windows DPAPI encryption adapter
│       │       └── __init__.py
│       │
│       └── workers/                   # Concurrency & Background Task Execution
│           ├── __init__.py
│           ├── qt_pool.py             # QThreadPool & QRunnable wrappers for in-process tasks
│           ├── signals.py             # Qt Signal definitions for telemetry
│           └── job_runner.py          # Persistent SQLite WAL job coordination & crash recovery
│
├── packaging/                         # Standalone Packaging Configurations
│   ├── pyinstaller/
│   │   └── veritrace.spec             # One-folder PyInstaller build specification
│   ├── installer/
│   │   └── veritrace_setup.iss        # Inno Setup compiler script (VeriTrace-Setup.exe)
│   └── resources/                     # Application icons and installer bitmaps
│
├── scripts/                           # Developer & Release Tooling
│   ├── development/
│   │   └── run_desktop.py             # Developer runner script
│   ├── build/                         # PyInstaller build automation
│   ├── packaging/                     # Inno Setup build automation
│   └── validation/
│       └── check_architecture.py      # Automated AST architecture boundary validator
│
├── tests/                             # Unified Test Hierarchy
│   ├── __init__.py
│   ├── unit/                          # Fast unit tests (math, rules, hashing, domain)
│   ├── integration/                   # Pipeline integration tests (PDF render, ELA, DB)
│   ├── desktop/                       # PySide6 UI tests (pytest-qt)
│   ├── architecture/                  # AST import rule & layer separation tests
│   ├── benchmarks/                    # Multi-document OCR & capability benchmark tests
│   ├── packaging/                     # Installer build & executable smoke tests
│   └── fixtures/                      # Test cases & synthetic ground-truth files
│
├── dev/                               # 27 Authoritative Planning & Architecture Documents
├── docs/                              # User guides and technical documentation
└── legacy/                            # Quarantined Reference Assets
    ├── backend/                       # Deprecated UdyogPermit AI backend, agents, geospatial
    ├── frontend/                      # Deprecated UdyogPermit AI React components
    ├── desktop_tauri/                 # Retired Tauri 2 + React 18 scaffolding
    └── Dockerfile                     # Deprecated container configuration
```

---

## 3. Storage Hierarchy Outside the Repository

```text
%LOCALAPPDATA%/VeriTrace/
│
├── database/
│   └── veritrace.sqlite               # Persistent SQLite database (WAL mode)
│
├── investigations/
│   └── <investigation_id>/
│       ├── originals/                 # Immutable uploaded files (SHA-256 hashed)
│       ├── processed/                 # 300 DPI rendered PNG pages
│       ├── evidence/                  # High-res bounding box crops & ELA heatmaps
│       └── reports/                   # Generated ReportLab PDF dossiers & JSON exports
│
├── logs/                              # Structured forensic execution logs
├── config/                            # User preferences & DPAPI encrypted tokens
└── cache/                             # Temporary computation scratch files
```
