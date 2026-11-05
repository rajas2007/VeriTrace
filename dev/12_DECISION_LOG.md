# 12_DECISION_LOG.md
# VeriTrace Architectural Decision Records (ADR) Register

---

## 1. Architectural Decision Framework

This register documents all fundamental architectural decisions established for the **VeriTrace** project. Each record follows the standardized MADR (Markdown Architectural Decision Records) structure, capturing the decision context, alternatives considered, chosen approach, and engineering consequences.

* **Status Categories:** 
  1. `APPROVED & STABLE`: Authoritatively finalized; foundational invariant; no implementation validation needed.
  2. `APPROVED WITH IMPLEMENTATION VALIDATION`: Approach accepted; concrete parameters, benchmark validation, or edge-case mechanics validated during specific milestone execution.
  3. `PROVISIONAL`: Working assumption subject to early milestone viability tests.
  4. `DEFERRED`: Formally postponed to secondary or future phases.
  5. `SUPERSEDED`: Replaced by a subsequent architectural decision.

* **Current Governance Status:** 
  * Total Records: 33 (ADR-001 through ADR-033)
  * Approved & Stable: 21
  * Approved with Implementation Validation: 3 (ADR-023, ADR-028, ADR-029)
  * Provisional: 0
  * Deferred: 1 (ADR-018)
  * Superseded: 8 (ADR-003, ADR-014, ADR-015, ADR-016, ADR-020, ADR-022, ADR-024, plus ADR-018 secondary role)

---

## 2. Decision Register Summary

| ADR ID | Decision Title | Governance Classification | Date | Primary Impact Area |
| :---: | :--- | :---: | :---: | :--- |
| **ADR-001** | Standalone Product Identity on Reusable Foundation | **APPROVED & STABLE** | 2026-11-04 | Project Charter & Scope |
| **ADR-002** | Source Code Invariance and Isolation of UdyogPermit AI | **APPROVED & STABLE** | 2026-11-04 | Repository Management |
| **ADR-003** | Core Stack Reuse: FastAPI, React 18, ChatGroq & LangGraph | **SUPERSEDED by ADR-025 & ADR-026** | 2026-11-04 | System Stack & Orchestration |
| **ADR-004** | Deprecation of Industrial Compliance & Geospatial Features | **APPROVED & STABLE** | 2026-11-04 | Domain Decoupling |
| **ADR-005** | Deterministic-First Strategy for Forensic Measurements | **APPROVED & STABLE** | 2026-11-04 | Forensic Engine Design |
| **ADR-006** | Strict Evidence Anchoring for All AI-Generated Reasoning | **APPROVED & STABLE** | 2026-11-04 | AI Safety & Grounding |
| **ADR-007** | Three-Tier Epistemic Classification of Visual Findings | **APPROVED & STABLE** | 2026-11-04 | Legal & Forensic Integrity |
| **ADR-008** | Priority of Mandatory PS-2 Prototype over Advanced Features | **APPROVED & STABLE** | 2026-11-04 | Roadmap & Delivery |
| **ADR-009** | Local SQLite & File Storage for Persistence | **APPROVED & STABLE** | 2026-11-04 | Persistence Architecture |
| **ADR-010** | Normalized Bounding Box Coordinate Standard | **APPROVED & STABLE** | 2026-11-04 | Computer Vision & UI |
| **ADR-011** | Modular Monolith Architecture Pattern (Rejecting Microservices) | **APPROVED & STABLE** | 2026-11-04 | System Architecture |
| **ADR-012** | Agent Minimization Principle (Deterministic by Default) | **APPROVED & STABLE** | 2026-11-04 | AI & Orchestration Strategy |
| **ADR-013** | Entity Rationalization (12 Core Entities + 1 Assoc Table) | **APPROVED & STABLE** | 2026-11-04 | Domain Modeling & Schema |
| **ADR-014** | Asynchronous Job Processing with Status Polling for Pipeline | **SUPERSEDED by ADR-028** | 2026-11-04 | API & Execution Protocol |
| **ADR-015** | Normalizing Frontend Package Name & Directory Root | **SUPERSEDED by ADR-020** | 2026-11-04 | Repository Structure |
| **ADR-016** | Persistent SQLite-Backed Job Queue (No Redis/Celery) | **SUPERSEDED by ADR-018 & ADR-028** | 2026-11-04 | Asynchronous Processing Architecture |
| **ADR-017** | Multi-Signal Forensic Convergence Standard | **APPROVED & STABLE** | 2026-11-04 | Forensic Reliability & Integrity |
| **ADR-018** | Dedicated Standalone Python Worker Process for Durable Execution | **DEFERRED (Secondary Batch CLI)** | 2026-11-04 | Background Job Processing Architecture |
| **ADR-019** | Standalone Desktop Product Direction (Target: Windows 10/11 x64) | **APPROVED & STABLE** | 2026-11-04 | Product Strategy & Form Factor |
| **ADR-020** | Tauri 2 Desktop Shell with React 18 & TypeScript | **SUPERSEDED by ADR-025** | 2026-11-04 | Desktop Framework & Frontend Root |
| **ADR-021** | Local-First Processing and Configurable Local Storage (%LOCALAPPDATA%) | **APPROVED & STABLE** | 2026-11-04 | Storage & Privacy Architecture |
| **ADR-022** | Python Backend Bundling and Local Process Supervision | **SUPERSEDED by ADR-026 & ADR-028** | 2026-11-04 | Desktop Process Lifecycle |
| **ADR-023** | Initial Default OCR Candidate (Tesseract) & TextExtractorProtocol | **APPROVED (WITH IMPL VALIDATION)** | 2026-11-04 (Updated 2026-11-05) | OCR Engine Strategy |
| **ADR-024** | Windows Installer and Distribution Strategy (Tauri + NSIS) | **SUPERSEDED by ADR-029** | 2026-11-04 | Packaging & Release Engineering |
| **ADR-025** | Native PySide6 (Qt) Desktop Application Framework | **APPROVED & STABLE** | 2026-11-04 | Desktop Framework & Language |
| **ADR-026** | Direct In-Process Python Application Services (FastAPI Removal) | **APPROVED & STABLE** | 2026-11-04 | Application Architecture & Communication |
| **ADR-027** | Qt Widgets, QSS Styling, and Qt Model/View Architecture | **APPROVED & STABLE** | 2026-11-04 | UI Architecture & Theming |
| **ADR-028** | Multi-Threaded Execution (QThreadPool) & Resilient Job Checkpoints | **APPROVED (WITH IMPL VALIDATION)** | 2026-11-04 (Updated 2026-11-05) | Background Execution Architecture |
| **ADR-029** | Windows Packaging via PyInstaller and Inno Setup | **APPROVED (WITH IMPL VALIDATION)** | 2026-11-04 | Packaging & Release Engineering |
| **ADR-030** | Unified Python src-Layout and Layered Monolith Architecture | **APPROVED & STABLE** | 2026-11-04 | Repository Structure & Architecture |
| **ADR-031** | Explicit Dependency Tier Partitioning & Automated Architectural Boundary Enforcement | **APPROVED & STABLE** | 2026-11-04 | Dependency Management & Governance |
| **ADR-032** | Configurable GenAI Provider, Deterministic Offline Fallback & Privacy Gating | **APPROVED & STABLE** | 2026-11-05 | AI Narrative & Privacy Architecture |
| **ADR-033** | Three-Tier Documentation Architecture & Chat-Only Task Reporting | **APPROVED & STABLE** | 2026-11-05 | Repository Governance & Policy |

---

## 3. Detailed Architectural Decision Records

### ADR-001: Standalone Product Identity on Reusable Engineering Foundation
* **Status:** ACCEPTED
* **Context:** Innovating for DataOps Hackathon PS-2. Reusable engineering foundations from `UdyogPermit AI` are adopted.
* **Decision:** VeriTrace is established as a completely distinct, standalone forensics product.
* **Consequences:** Focus strictly on forensic requirements.

---

### ADR-002: Source Code Invariance and Isolation of UdyogPermit AI
* **Status:** ACCEPTED
* **Context:** The original UdyogPermit AI codebase must remain pristine.
* **Decision:** Never edit, move, or delete files in the source repository.
* **Consequences:** Absolute source isolation guaranteed.

---

### ADR-003: Core Stack Reuse: FastAPI, React 18, ChatGroq and LangGraph
* **Status:** SUPERSEDED by ADR-025 and ADR-026
* **Context:** Initial migration evaluated existing web stack.
* **Superseded Reason:** Replaced by PySide6 native desktop monolith and direct Python application services.

---

### ADR-004: Deprecation & Quarantine of Industrial and Geospatial Modules
* **Status:** ACCEPTED
* **Context:** Industrial zoning and satellite GIS are irrelevant to PS-2.
* **Decision:** Quarantined in `legacy/`.

---

### ADR-005: Deterministic-First Strategy for Forensic Measurements
* **Status:** ACCEPTED
* **Context:** LLMs hallucinate when asked to detect visual fraud directly.
* **Decision:** Compute ELA, baseline deviations, checksums, and fuzzy alignments deterministically using OpenCV, Pillow, and RapidFuzz.

---

### ADR-006: Strict Evidence Anchoring for All AI-Generated Reasoning
* **Status:** ACCEPTED
* **Context:** Legal and forensic standards require evidence traceability.
* **Decision:** Every finding must link to an immutable evidence anchor `[document_id, page_number, normalized_bbox]`.

---

### ADR-007: Three-Tier Epistemic Classification of Visual Findings
* **Status:** ACCEPTED
* **Decision:** Classify findings into: `CONFIRMED_OBSERVATION`, `DETECTED_INCONSISTENCY`, and `SUSPECTED_MANIPULATION`.

---

### ADR-008: Priority of Mandatory PS-2 Prototype over Advanced Features
* **Status:** ACCEPTED
* **Decision:** Prioritize the 8 core capabilities and 6 dossier sections required by PS-2 before stretch features.

---

### ADR-009: Local SQLite & File Storage for Persistence
* **Status:** ACCEPTED
* **Decision:** Store relational data in SQLite WAL mode and binary files in `%LOCALAPPDATA%/VeriTrace/`.

---

### ADR-010: Normalized Bounding Box Coordinate Standard
* **Status:** ACCEPTED
* **Decision:** All bounding box coordinates normalized to `[ymin, xmin, ymax, xmax] \in [0.0, 1.0]`.

---

### ADR-011: Modular Monolith Architecture Pattern (Rejecting Microservices)
* **Status:** ACCEPTED
* **Decision:** Single codebase organized into cohesive capability modules.

---

### ADR-012: Agent Minimization Principle (Deterministic by Default)
* **Status:** ACCEPTED
* **Decision:** Use LLMs only downstream for grounded reasoning and narrative synthesis.

---

### ADR-013: Entity Rationalization (12 Core Entities + 1 Assoc Table)
* **Status:** ACCEPTED
* **Decision:** Standardize domain model on 12 Core Entities + 1 Association Table.

---

### ADR-014: Asynchronous Job Processing with Status Tracking for Pipeline
* **Status:** SUPERSEDED by ADR-028
* **Superseded Reason:** Replaced by in-process QThreadPool background execution with reactive Qt Signals and durable SQLite stage checkpoints.

---

### ADR-015: Normalizing Frontend Package Name & Directory Root
* **Status:** SUPERSEDED by ADR-020 (and subsequently ADR-025 and ADR-030).

---

### ADR-016: Persistent SQLite-Backed Job Queue (No Redis/Celery)
* **Status:** SUPERSEDED by ADR-018 and ADR-028.
* **Superseded Reason:** Replaced by QThreadPool in-process execution with SQLite checkpoints.

---

### ADR-017: Multi-Signal Forensic Convergence Standard
* **Status:** APPROVED & STABLE
* **Decision:** High-severity manipulation flags require multiple corroborating forensic signals.

---

### ADR-018: Dedicated Standalone Python Worker Process for Durable Execution
* **Status:** DEFERRED (Secondary CLI Utility)
* **Context:** Originally designed as the primary execution engine. Under ADR-028, Qt `QThreadPool` is approved as the primary in-process engine for the desktop workstation.
* **Decision:** Retain the standalone worker (`src/veritrace/workers/job_runner.py`) using `BEGIN IMMEDIATE` atomic claiming as an optional secondary headless CLI runner for batch tasks. Primary desktop execution runs via `QThreadPool`.

---

### ADR-019: Standalone Desktop Product Direction (Target: Windows 10/11 x64)
* **Status:** ACCEPTED
* **Decision:** VeriTrace is a native Windows desktop application with 100% offline core processing.

---

### ADR-020: Tauri 2 Desktop Shell with React 18 & TypeScript
* **Status:** SUPERSEDED by ADR-025
* **Superseded Reason:** Replaced by PySide6 native Python desktop architecture to eliminate multi-language toolchain complexity and HTTP loopback overhead.

---

### ADR-021: Local-First Processing and Configurable Local Storage (%LOCALAPPDATA%)
* **Status:** ACCEPTED
* **Decision:** All user runtime documents, crops, and databases reside in `%LOCALAPPDATA%/VeriTrace/`.

---

### ADR-022: Python Backend Bundling and Local Process Supervision
* **Status:** SUPERSEDED by ADR-026 and ADR-028
* **Superseded Reason:** FastAPI and process supervision are eliminated; in-process Python services and QThreadPool background execution replace them.

---

### ADR-023: Initial Default OCR Candidate (Tesseract) & TextExtractorProtocol Abstraction
* **Status:** APPROVED (WITH IMPLEMENTATION VALIDATION)
* **Context:** High-fidelity optical character recognition is critical for document ingestion and text forensics. Multiple OCR engines exist (Tesseract, RapidOCR/ONNX, EasyOCR, PaddleOCR). Prior drafts contained unverified accuracy figures (>92% vs >96%) and latency claims that had not been empirically measured on the target Windows environment. Furthermore, hardcoding a specific engine into application services would create severe vendor lock-in.
* **Decision:**
  1. **Initial Default Candidate:** Adopt **Tesseract OCR 5.x** (accessed via `pytesseract`) bundled with English trained data (`eng.traineddata`) as the initial default baseline candidate for offline text extraction.
  2. **Architectural Protocol Isolation:** All text and layout extraction must be abstracted behind a formal `TextExtractorProtocol` located in `src/veritrace/capabilities/extraction/protocols.py`. Downstream layout parsing, table extraction, quality scoring, cross-document correlation, and forensic verification depend exclusively on this protocol interface, never on engine-specific concrete classes.
  3. **Empirical Benchmarking Gate:** Formal selection or replacement of the OCR engine is subject to an empirical multi-dimensional benchmark suite (specified in `dev/24_TESTING_AND_DEMO_STRATEGY.md` Section 2.6). The benchmark suite evaluates CER (Character Error Rate), WER (Word Error Rate), Exact Field Match rate, Bounding Box IoU (evaluating an initial heuristic target of $\ge 0.70$ as a candidate threshold to be calibrated empirically), latency per page (ms), peak memory RSS (MB), and CPU utilization across an initial representative dataset of at least 30 diverse documents spanning 7 categories (CAT-01 to CAT-07: clean scans, degraded scans, skewed/rotated pages, microtext, dense tables, low contrast, stamped/watermarked).
  4. **Initial Smoke-Testing:** A preliminary 10-document test serves strictly as a development smoke-test to verify pipeline wiring; no statistical accuracy claims may be made until the full 30+ document benchmark is executed.
  5. **Pluggable Alternatives:** RapidOCR (ONNX runtime) is designated as the primary alternative candidate and can be plugged in via `TextExtractorProtocol` without modifying any domain or pipeline code.
* **Consequences:** Positive: Zero engine lock-in; claims are grounded in empirical evidence rather than speculation; predictable development progression; clean architectural separation. Negative: Requires maintaining the benchmark test harness and golden ground-truth annotations.

---

### ADR-024: Windows Installer and Distribution Strategy (Tauri + NSIS)
* **Status:** SUPERSEDED by ADR-029
* **Superseded Reason:** Replaced by PyInstaller + Inno Setup for native Python desktop packaging.

---

### ADR-025: Native PySide6 (Qt) Desktop Application Framework
* **Status:** ACCEPTED (Task 02.4 Decision)
* **Context:** The Tauri 2 + React 18 architecture introduced an unnecessary multi-language boundary (Rust, Node.js, TypeScript, Vite) requiring complex HTTP loopback serialization and external process supervision.
* **Decision:** Migrate the desktop presentation layer to **PySide6 (Qt 6.7+ for Python)**. All UI components are written in native Python using Qt Widgets, QSS stylesheets, Qt Signals & Slots, and Qt Model/View.
* **Alternatives Considered:** 
  1. *Tauri 2 + React:* Rejected due to toolchain complexity, port management hazards, and IPC serialization overhead.
  2. *Electron:* Rejected due to severe RAM consumption, bundled Chromium overhead, and multi-process IPC lag.
* **Consequences:** Positive: Single-language (Python 3.11) architecture; eliminates Node.js, npm, Rust, and Cargo; direct memory access to PyMuPDF and OpenCV; instant method calls; simplified build and packaging pipeline. Negative: UI layout and styling must be implemented via Qt Widgets and QSS rather than web HTML/React components.

---

### ADR-026: Direct In-Process Python Application Services (FastAPI Removal)
* **Status:** ACCEPTED (Task 02.4 Decision)
* **Context:** In a native PySide6 desktop monolith, running an internal FastAPI HTTP REST server on loopback (`127.0.0.1:{dynamic_port}`) is redundant. It introduces JSON serialization overhead, ephemeral port binding conflicts, Windows Firewall prompts, and security token overhead.
* **Decision:** Completely eliminate FastAPI, Uvicorn, and loopback HTTP communication from the active application architecture. PySide6 UI controllers call Python Application Services (`src/veritrace/application/services/`) directly in-process using strongly typed Pydantic v2 schemas and domain dataclasses.
* **Alternatives Considered:** 
  1. *Retaining FastAPI Loopback Gateway:* Rejected because both presentation and service layers run in Python within the same process; network loopback adds latency, complexity, and failure modes with zero benefit.
* **Consequences:** Positive: Sub-millisecond direct method calls; zero network stack overhead; zero port collision hazards; zero security token overhead; eliminated supervisor complexity. Negative: None for desktop software.

---

### ADR-027: Qt Widgets, QSS Styling, and Qt Model/View Architecture
* **Status:** ACCEPTED (Task 02.4 Decision)
* **Context:** An investigation workstation requires high performance, custom dark theming, docked tool panels, and sub-millimeter document coordinate rendering.
* **Decision:** Implement UI components using **Qt Widgets** styled with **Qt Style Sheets (QSS)** (`dark_theme.qss`). Use `QGraphicsView` / `QGraphicsScene` for sub-millimeter document rendering, zoom/pan, and interactive bounding box coordinate overlays. Use `QAbstractTableModel` and `QAbstractItemModel` for efficient display of findings and evidence trees.
* **Consequences:** Positive: Hardware-accelerated graphics rendering; native Windows High-DPI support; customizable docking system (`QDockWidget`); rock-solid widget stability.

---

### ADR-028: Multi-Threaded Background Processing (QThreadPool) & Resilient Job Checkpoints
* **Status:** APPROVED (WITH IMPLEMENTATION VALIDATION)
* **Context:** Forensic document analysis involves CPU-intensive multi-stage pipelines (300 DPI page rendering, OCR, ELA computation, RapidFuzz cross-correlation, and AI narrative synthesis). These operations must never block the main Qt GUI thread. Furthermore, desktop workstation sessions may experience sudden crashes, power interruptions, or user cancellations. Long-running document analysis must be robust, idempotent, and resilient against data corruption.
* **Decision:** Implement an in-process multi-threaded background execution architecture governed by 12 definitive execution, recovery, and idempotency rules:
  1. **Primary Execution Engine:** Use Qt's native `QThreadPool` and `QRunnable` within the desktop workstation process for all background tasks. Thread pool capacity defaults to `max(1, QThread.idealThreadCount() - 1)` to keep the UI thread responsive.
  2. **Thread Boundary Decoupling:** Background worker threads communicate progress, stage transitions, and completion exclusively via Qt Signals (`pyqtSignal`) marshaled to the main thread's Qt event loop. Background threads are strictly prohibited from touching GUI widgets or Qt scene graphs.
  3. **Durable Job Persistence:** Job states, active stages, progress percentages, error logs, and timestamps are persisted to the SQLite `investigation_jobs` table.
  4. **Explicit Lifecycle States:** Job status transitions strictly follow: `QUEUED` $\to$ `RUNNING` $\to$ `COMPLETED` / `FAILED` / `CANCELLED` / `INTERRUPTED`.
  5. **Granular Stage Checkpointing:** Each pipeline stage (`INGESTION`, `EXTRACTION`, `QUALITY_ASSESSMENT`, `FORENSICS`, `CORRELATION`, `REASONING`, `REPORTING`) commits a checkpoint record (`last_completed_stage`, `completed_at`, `stage_metadata`) upon successful completion.
  6. **Idempotent Stage Execution:** Every processing stage is designed to be idempotent. Before executing, a stage checks whether its output artifacts (rendered page images, OCR JSON, ELA maps) already exist on disk and in SQLite with matching source file hashes. If verified valid, the stage skips redundant recomputation and immediately yields its cached results.
  7. **Startup Interrupted Job Sweeper:** On application launch, `JobRecoveryService` queries `investigation_jobs` for any records in `RUNNING` or `QUEUED` state (orphaned by previous process crash or sudden exit) and automatically transitions them to `INTERRUPTED` with an explanatory diagnostic message.
  8. **User-Controlled Resume:** When an `INTERRUPTED` job is detected, the UI prompts the user with options to **Resume from Last Checkpoint** or **Restart from Beginning**. If resumed, the pipeline inspects `last_completed_stage` and begins execution at the subsequent stage.
  9. **Controlled User Cancellation:** Cancellation flags (`QAtomicInt` / `threading.Event`) are polled cooperatively between stage boundaries and document pages. When cancelled, the pipeline cleanly flushes open file handles, commits partial progress, marks the job `CANCELLED`, and releases worker threads.
  10. **In-Place Finding Deduplication on Retry:** If a failed or interrupted stage is retried, existing findings and discrepancies associated with that stage and document in SQLite are updated in-place or purged using transaction-safe upsert semantics, preventing duplicate or ghost findings in the UI.
  11. **Resource Throttling & Memory Governance:** Large PDF rendering and full-page OpenCV arrays are released eagerly (`del`, gc collection, or image cache eviction) following each page's processing to keep workstation peak RAM below 1.5 GB.
  12. **Decoupled Worker Process Option (Deferred/Secondary):** A standalone worker CLI (`python -m veritrace.workers.job_runner`) using atomic SQLite locking (`BEGIN IMMEDIATE`) is preserved for optional headless batch processing, but `QThreadPool` remains the primary workstation engine.
* **Consequences:** Positive: Zero external broker dependencies (no Redis, no Celery); 60 FPS responsive UI; crash-resilient document processing; verified checkpointing and resumability; zero phantom findings on stage retries.

---

### ADR-029: Windows Packaging via PyInstaller and Inno Setup
* **Status:** APPROVED (WITH IMPLEMENTATION VALIDATION)
* **Context:** The application must be distributed as a single downloadable Windows installer (`VeriTrace-Setup.exe`) that installs cleanly on Windows 10/11 x64 without requiring Python, development tools, or manual dependency installation.
* **Decision:** Package the native Python desktop application into a standalone one-folder distribution using **PyInstaller**, and bundle the executable, PySide6 plugins, native C-runtimes, and Tesseract OCR into a single installer using **Inno Setup** (`packaging/installer/veritrace_setup.iss`).
* **Alternatives Considered:** 
  1. *Tauri Bundler / NSIS:* Superseded with the removal of Tauri.
  2. *MSIX / Windows Store:* Rejected due to signing certificate requirements and sandbox filesystem restrictions conflicting with `%LOCALAPPDATA%`.
* **Consequences:** Positive: Standard Windows installer wizard (`VeriTrace-Setup.exe`); desktop and Start Menu shortcuts; clean uninstaller that preserves user investigation databases; high LZMA2 compression.

---

### ADR-030: Unified Python src-Layout and Layered Monolith Architecture
* **Status:** ACCEPTED (Task 02.5 Decision)
* **Context:** Following the decision in ADR-025 to adopt PySide6 and eliminate FastAPI in ADR-026, the repository still retained the legacy two-tier directory structure (`desktop/` and `backend/`), with duplicate or ambiguous config files (`backend/pyproject.toml`, `backend/alembic.ini`, etc.) and awkward relative cross-imports. For a native Python desktop application, having separate `desktop/` and `backend/` roots created impedance mismatches, packaging confusion in PyInstaller, and blurred module boundaries. Furthermore, extraction quality assessment (OCR confidence scoring, vector confidence gating) lacked a first-class architectural home.
* **Decision:** Consolidate the entire codebase into a canonical Python `src`-layout rooted at `src/veritrace/`. Define six strict architectural layers:
  1. `src/veritrace/gui/`: Presentation layer (PySide6 widgets, views, viewmodels, controllers, styles, resources). Direct dependency on `application/` and `domain/`. Strictly forbidden from importing `infrastructure/` or calling raw SQL/DB or low-level external adapters.
  2. `src/veritrace/application/`: Application services, use-case coordinators, workflow facades, and DTO mappings. Coordinates work between domain and capabilities.
  3. `src/veritrace/domain/`: Pure business logic, forensic rules, entity models, value objects, domain events, and repository interfaces. Strictly isolated with ZERO external dependencies (no PySide6, no SQLAlchemy, no OpenCV, no PyMuPDF).
  4. `src/veritrace/capabilities/`: Pure processing engines and algorithms:
     - `ingestion/` (document intake, MIME validation, and SHA-256 calculation)
     - `classification/` (document type classification)
     - `extraction/` (text, table, key-value extraction via TextExtractorProtocol)
     - `quality/` (OCR quality scoring, vector confidence gating, image quality assessment)
     - `forensics/` (visual, metadata, text forensics, ELA, copy-move)
     - `correlation/` (cross-document matching, entity reconciliation)
     - `reasoning/` (contextual intelligence, discrepancy reasoning)
     - `reporting/` (dossier generation)
  5. `src/veritrace/infrastructure/`: Technical adapters implementing interfaces (persistence/SQLAlchemy, PDF rendering via PyMuPDF, OCR via Tesseract/RapidOCR, vision via OpenCV/Pillow, AI client via ChatGroq, security/storage).
  6. `src/veritrace/workers/`: Concurrency and background job runner (`job_runner.py`, background QRunnable workers, thread pools).
  Establish single root-level configuration files: `pyproject.toml`, `requirements.txt`, `alembic.ini`.
  Provide central entrypoints at `src/veritrace/main.py` and execution via `python -m veritrace` or `python scripts/development/run_desktop.py`.
* **Consequences:** Positive: Eliminates confusing `backend/` vs `desktop/` distinction; clean editable installation (`pip install -e .`); standard packaging with PyInstaller targeting `src/veritrace/main.py`; clear code ownership for multi-developer teams; strict unidirectional dependency flow verified by automated architecture checks; extraction quality is elevated to a first-class capability. Negative: Requires maintaining discipline regarding architectural import boundaries (enforced by `scripts/validation/check_architecture.py`).

---

### ADR-031: Explicit Dependency Tier Partitioning & Automated Architectural Boundary Enforcement
* **Status:** ACCEPTED (Task 02.6 Decision)
* **Context:** In Task 02.5, dependencies in `pyproject.toml` and `requirements.txt` mixed core offline desktop requirements with optional cloud AI frameworks (`langgraph`, `langchain-groq`), development tools, and test suites, creating duplicate declarations without a clear source of truth. Additionally, while the initial architectural validator checked basic rules, it did not strictly forbid domain modules from importing AI, OCR, or image libraries (e.g. `groq`, `pytesseract`, `PIL`), nor did it prevent GUI widgets from directly accessing capability engines.
* **Decision:**
  1. **Canonical Dependency Tiering:** Establish `pyproject.toml` as the sole authoritative source of truth for dependencies. Strictly partition dependencies into:
     - *Core Runtime Dependencies:* Strictly offline-capable libraries (PySide6, SQLAlchemy, Alembic, PyMuPDF, Pillow, NumPy, OpenCV, RapidFuzz, ReportLab, pytesseract, python-dotenv, psutil, pydantic).
     - *Optional Cloud AI (`[project.optional-dependencies] ai`):* `groq`, `langchain-groq`, `langgraph`.
     - *Development Tools (`dev`):* `ruff`, `mypy`.
     - *Testing Suite (`test`):* `pytest`, `pytest-qt`, `pytest-cov`, `pytest-mock`.
     - *Packaging (`packaging`):* `pyinstaller`.
     - *Complete Bundle (`all`):* `veritrace[ai,dev,test,packaging]`.
  2. **Authoritative Requirements Manifest:** `requirements.txt` references `pyproject.toml` as the source of truth and mirrors the tiered structure for standard `pip` workflows.
  3. **Package Data Declaration:** Configure `[tool.setuptools.package-data]` in `pyproject.toml` to guarantee inclusion of `.qss` stylesheets, `.svg` icons, and static assets in wheels and PyInstaller builds.
  4. **Strict AST Boundary Enforcement:** Enhanced `scripts/validation/check_architecture.py` to enforce that:
     - `domain/` contains zero imports of UI, database (`sqlalchemy`, `sqlite3`), OCR (`pytesseract`), PDF (`fitz`), vision (`cv2`, `PIL`), or AI (`groq`, `langchain`, `langgraph`).
     - `gui/` cannot directly import `infrastructure/` or `capabilities/` (all forensic actions must route through `application/services/`).
     - `capabilities/` cannot import `PySide6` or manipulate UI widgets.
     - Global codebase cannot import obsolete web/legacy modules (`fastapi`, `uvicorn`, `starlette`, `tauri`, `legacy`).
* **Consequences:** Positive: Single source of truth for dependencies; offline-first purity guaranteed; packaging safety for assets; automated CI gating prevents architectural rot. Negative: Requires developers to install via `pip install -e .[all]` during active development.

---

### ADR-032: Configurable GenAI Provider Strategy, Deterministic Offline Fallback, and Privacy Gating
* **Status:** APPROVED & STABLE
* **Context:** VeriTrace utilizes generative language models strictly to translate verified deterministic findings, cross-document discrepancies, and forensic anchors into human-readable investigative narratives. In prior drafts, a specific model identifier (`llama-3.3-70b-versatile` on Groq) was referenced in multiple documents without formal abstraction, and the fallback behavior for air-gapped or offline environments lacked clear operational rules.
* **Decision:**
  1. **Configurable Model & Provider Abstraction:** All LLM interactions must be routed through the `LLMProviderProtocol` abstraction located in `src/veritrace/infrastructure/ai/protocols.py`. No specific model identifier is hardcoded into application services or capability engines. The model identifier and API provider are dynamically configured via environment variables and settings (`VERITRACE_AI_PROVIDER`, default: `groq`; `VERITRACE_AI_MODEL`, default candidate: `llama-3.3-70b-versatile`). Groq candidate models (e.g. `llama-3.3-70b-versatile`, `openai/gpt-oss-120b`, or equivalent open-weight checkpoints) remain subject to evaluation.
  2. **Deterministic Offline Fallback:** VeriTrace must remain fully functional in completely offline, air-gapped, or keyless environments. When no API key is provided, when network connectivity is unavailable, or when offline mode is selected:
     - The AI narrative stage automatically routes to the **Deterministic Template Engine** (`TemplateNarrativeGenerator`).
     - The template engine generates structured, grammatically coherent investigative summaries directly from verified domain findings, rule violations, and evidence anchors.
     - The UI clearly banners the narrative with a badge: `[Deterministic Template - Offline Mode]`, ensuring full transparency.
  3. **Strict Epistemic Guardrail (No Hallucinated Fraud):** The generative AI component is strictly prohibited from declaring fraud, inventing anomalies, or drawing conclusions unsupported by deterministic evidence anchors. The AI prompt accepts only structured JSON containing verified findings and is instructed solely to summarize and explain the mathematical and textual evidence.
  4. **Strict PII & Privacy Gating:** VeriTrace never transmits raw document images, raw PDF binaries, or full unredacted document text to external cloud APIs. When cloud AI narratives are enabled:
     - Only structured finding summaries and anonymized text snippets containing detected anomalies are transmitted.
     - A pre-transmission privacy filter redacts high-risk Personal Identifiable Information (e.g., Aadhaar numbers, PAN numbers, tax IDs, credit card numbers, phone numbers) using regular expression maskers.
  5. **Optional Dependency Tiering:** Cloud AI libraries (`groq`, `langchain-groq`, `langgraph`) are partitioned into `[project.optional-dependencies] ai` in `pyproject.toml`. Core forensic analysis and desktop UI operate 100% independently of these libraries.
* **Consequences:** Positive: Complete offline independence; compliance with forensic privacy standards; protection against model deprecation or vendor lock-in; guaranteed zero hallucinated findings. Negative: Requires maintaining high-quality deterministic narrative templates alongside AI prompt templates.

---

### ADR-033: Three-Tier Documentation Architecture and Chat-Only Task Reporting Policy
* **Status:** APPROVED & STABLE
* **Context:** Creation of task-specific execution reports (`TASK_XX_COMPLETION_REPORT.md`) directly inside the repository creates file clutter in the repository root, duplicates information preserved in permanent `dev/` specifications and commit histories, and blurs the boundary between permanent technical documentation and temporary agent execution transcripts.
* **Decision:**
  1. **Three-Tier Documentation Model:** Formalize repository documentation into:
     - *Tier 1 (Permanent Technical Documentation):* Living architecture specifications, contracts, and guides (`dev/`, `docs/`, `README.md`).
     - *Tier 2 (Governance & Progress):* Authoritative ADR log (`dev/12_DECISION_LOG.md`) and milestone tracker (`dev/13_PROGRESS_TRACKER.md`).
     - *Tier 3 (Ephemeral Execution Reports):* Detailed task completion reports are presented directly in the AI agent's chat responses and PR descriptions.
  2. **Zero Report Sprawl:** Separate `TASK_XX_COMPLETION_REPORT.md` files are strictly forbidden inside the active repository. Only user-facing deliverables (e.g. investigation dossiers) or explicitly mandated milestone reports may be saved to disk.
  3. **Repository Cleanliness:** Redundant execution reports from prior planning tasks are purged from the repository root after verifying that all unique decisions have been transferred to `dev/`.
* **Consequences:** Positive: Clean, professional repository root; zero drift between duplicate markdown reports; clear distinction between living architecture and historical execution records. Negative: Requires reviewers to consult chat history or PR descriptions for full step-by-step tool invocation traces.

---

### ADR-034: Capability, Domain, and Application Boundary Ownership for Validation, Findings, and Evidence
* **Status:** APPROVED & STABLE
* **Context:** During Task 02.10 structural simplification, redundant scaffolding directories (`validation/`, `findings/`, `evidence/`) were consolidated to prevent sprawl and ambiguity. Task 02.11 performed a formal boundary verification to confirm where deterministic validation, finding lifecycle management, and evidence traceability reside without responsibility conflicts or improper coupling.
* **Decision:**
  1. **Validation Ownership & Cross-Document Separation:**
     - *Structural Validation:* Handled at intake by `capabilities/ingestion/validator.py` (magic bytes, MIME type, file bounds) and `capabilities/extraction/` (table and layout integrity).
     - *Extraction Quality Validation:* Handled by `capabilities/quality/evaluator.py` (OCR confidence scoring, character/word error heuristics, blur/skew degradation gating).
     - *Deterministic Domain Rules & Invariants:* Defined in `src/veritrace/domain/rules/` (`base.py`, `arithmetic.py`, `format.py`, `chronology.py`, `cross_document.py`). Rules are pure, deterministic comparison functions depending only on the Python Standard Library.
     - *Correlation (Entity Resolution):* `src/veritrace/capabilities/correlation/entity_aligner.py` resolves and aligns entities across documents via RapidFuzz and token matching, producing candidate alignment pairs.
     - *Application Workflow Orchestration:* `src/veritrace/application/workflows/` coordinates the pipeline: it invokes correlation to match entity pairs, evaluates aligned pairs against domain comparison rules (`cross_document.py`), and feeds results into `contradiction_matrix.py` to aggregate the contradiction graph without duplicating validation logic.
  2. **Findings Ownership & Independent Evaluation Dimensions:**
     - *Domain Entity:* A Finding is a core Domain Entity (`src/veritrace/domain/entities/finding.py`), NOT a capability engine.
     - *Three Strictly Independent Dimensions:*
       * **Severity:** Impact or importance of the finding (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`).
       * **Confidence:** Numerical reliability of the detection and supporting evidence ($[0.0, 1.0]$).
       * **Epistemic Tier:** Evidentiary strength supporting the conclusion (`CONFIRMED_OBSERVATION` / `DEFINITIVE`, `CORROBORATED`, `SUSPICIOUS` / `DETECTED_INCONSISTENCY`).
     - *Forensic Neutrality:* Findings represent empirical observations, discrepancies, or mathematical contradictions. An anomaly does NOT prove fraud or deliberate manipulation. Monetary magnitude and isolated forensic signals do not automatically promote epistemic tier.
     - *Deterministic Generation:* Detector outputs (`VisualAnomaly` from `capabilities/forensics/`, `ValidationResult` from `domain/rules/` and `capabilities/correlation/`) are transformed into standardized `Finding` records by `src/veritrace/application/workflows/finding_builder.py`.
     - *Review State:* Managed by `application/workflows/review_gate.py` (HITL confirmation/dismissal) and persisted via `infrastructure/persistence/repositories/finding_repository.py`.
  3. **Evidence, EvidenceAnchor & FindingEvidenceMap:**
     - *EvidenceAnchor (Value Object):* Immutable in-memory spatial and provenance coordinate reference (`document_id`, `page_number`, `normalized_bbox: [ymin, xmin, ymax, xmax]`, `context_snippet`).
     - *Evidence (Persistent Aggregate Root):* First-class domain entity (`src/veritrace/domain/entities/evidence.py`) and database table (`evidence`) persisting the physical 300 DPI crop path, SHA-256 crop hash, detector metadata, and embedded anchor coordinates. Independently addressable by UI and API.
     - *FindingEvidenceMap (Association Relation):* Relational join mapping (`finding_evidence`) linking `Finding` records to `Evidence` records in a many-to-many relationship, guaranteeing full audit traceability in Section 7.4 of the dossier.
  4. **AI Reasoning Permissions & Guardrails:**
     - *Permitted:* AI is permitted to synthesize explanatory narratives for both verified and unverified findings, referencing supplied evidence and explicitly preserving uncertainty.
     - *Strict Negative Guardrails:* The AI capability must NEVER independently create findings, change finding severity, upgrade epistemic tier, confirm or dismiss findings, or modify evidence records.
  5. **Retention of 8 Canonical Capabilities:**
     - The current 8 capabilities (`classification`, `correlation`, `extraction`, `forensics`, `ingestion`, `quality`, `reasoning`, `reporting`) provide clean, non-overlapping processing boundaries.
* **Consequences:** Positive: Eliminates god-objects; preserves pure domain invariants in `domain/rules/`; prevents AI hallucination in finding creation; guarantees independent evidence addressability; eliminates structural clutter. Negative: Requires developers to understand the distinction between domain entity lifecycles and capability processing engines.

---

### ADR-035: Milestone 1 Shared Contract Freeze between Desktop Application and Document Processing Engine
* **Status:** APPROVED & FROZEN
* **Context:** Milestone 1 development is divided between two developers: Rajas (Desktop application, investigation management, persistence, orchestration, background processing, integration) and Shravan (Document ingestion, PDF/image processing, digital text extraction, OCR, extraction provenance, extraction quality). To proceed with parallel implementation without interface breakage, conflicting data representations, or architectural boundary leaks, all shared data structures, service interfaces, error models, and integration expectations must be formally frozen.
* **Decision:**
  1. **Codification of Shared Data Contracts:** Adopt the pure Python dataclasses and enums codified in `dev/27_MILESTONE_1_SHARED_CONTRACTS.md`: `NormalizedBoundingBox`, `PageDimensions`, `ExtractedToken`, `ExtractedField`, `ExtractionProvenance`, `ProcessingWarning`, `ProcessingError`, `PageExtractionResult`, `IngestionRequest`, `IngestionResult`, `InvestigationIdentity`, and `InvestigationDTO`.
  2. **Coordinate & Provenance Standard:** Standardize on normalized bounding boxes $[ymin, xmin, ymax, xmax] \in [0.0, 1.0]$ with top-left origin $(0.0, 0.0)$, $x$ rightwards, $y$ downwards. Codify the epistemic invariant that OCR confidence measures character recognizer probability and must never be treated as legal or factual correctness.
  3. **Decoupled Service Protocols:** Define five core service protocols using Python's `typing.Protocol` with `@runtime_checkable`:
     - Shravan's engines: `DocumentIngestionServiceProtocol`, `DocumentExtractionServiceProtocol`, `ExtractionQualityEvaluatorProtocol`.
     - Rajas's orchestration: `InvestigationServiceProtocol`, `ProcessingWorkflowProtocol`.
     - Telemetry: `ProgressCallback` and `CancellationToken`.
     - The desktop GUI must interact with processing capabilities strictly via application workflows and protocols, never importing PDF or OCR libraries directly.
  4. **Granular Ownership & Dual-Approval Rules:**
     - Rajas exclusively owns `gui/`, investigation services, job services, workflows, SQLite persistence, and worker threads.
     - Shravan exclusively owns `capabilities/ingestion/`, `capabilities/extraction/`, `capabilities/quality/`, `infrastructure/pdf/`, and `infrastructure/ocr/`.
     - Shared directories (`domain/`, `application/dto/`, root build files) require formal RFC and dual-developer approval for any modification.
  5. **Resilient 9-Stage Integration & Shared Fixtures:**
     - Formalize the 9-stage intake-to-render workflow.
     - Enforce per-document error containment so that a single corrupted or unsupported file does not abort the processing of valid documents in a batch.
     - Define 7 canonical test fixtures in `tests/fixtures/` covering digital PDF, scanned raster, ID card PNG, salary slip JPEG, corrupted PDF, unsupported DOCX, and multi-page statements.
* **Consequences:** Positive: Enables fully independent parallel feature development with zero interface ambiguity; prevents GUI-capability coupling; establishes rock-solid error containment; guarantees reproducible testing against canonical fixtures. Negative: Requires both developers to coordinate through the formal RFC change procedure if contract modifications are needed during implementation.

---

### ADR-036: Evolution to Industrial Document Intelligence, Forensics & Authenticity Verification Platform
* **Status:** APPROVED & STABLE
* **Context:** VeriTrace is evolving from a general-purpose document forensics prototype into an industrial-grade document intelligence, forensics, and authenticity verification platform. Industrial documentation (manufacturing purchase orders, delivery challans, mill test certificates, commercial invoices, bills of lading, compliance affidavits) presents distinct forensic challenges including spliced quantities, altered metallurgical specifications, forged authorization signatures, and multi-document supply-chain contradictions.
* **Decision:**
  1. **New Product Positioning:** Formally position VeriTrace as an **Industrial Document Intelligence, Forensics & Authenticity Verification Platform** across seven target industries:
     - 1. Manufacturing *(Initial Demonstration Domain)*
     - 2. Logistics and Supply Chain *(Initial Demonstration Domain)*
     - 3. Banking and Financial Services (BFSI)
     - 4. Insurance
     - 5. Government and Public Administration
     - 6. Construction and Infrastructure
     - 7. Human Resources and Enterprise Administration
  2. **Cross-Industry Extensibility:** While manufacturing and supply-chain documents serve as the initial demonstration domain, the core architecture, data contracts, and verification engines remain strictly modular, extensible, and non-domain-locked.
  3. **Architectural Continuity:** Retain the native PySide6 Windows desktop monolith, in-process Python application services, local SQLite WAL persistence, exactly eight canonical capabilities, and six architectural layers. No web frameworks, microservices, or external supervisor processes are introduced.
* **Consequences:** Positive: Expands product market value and enterprise relevance; aligns with complex industrial document inspection workflows; provides rich demonstration scenarios (PO vs. Challan vs. Test Certificate). Negative: Broadens test dataset scope and requires handling complex industrial table layouts.

---

### ADR-037: Multilingual Indian Document Intelligence & OCR Engine Abstraction
* **Status:** APPROVED & STABLE
* **Context:** Indian enterprise and industrial workflows routinely process documents containing regional scripts (Devanagari, Bengali, Gurmukhi, Dravidian scripts) alongside English. A single-engine, English-only approach is insufficient for real-world Indian document intelligence.
* **Decision:**
  1. **Twelve-Language Roadmap (Ten-Language Target):** Establish an architectural roadmap covering 12 Indian languages across three operational readiness stages:
     - *Stage 3 (Validated for Release):* English, Hindi, Marathi (Priority 1: Core Latin & Devanagari extraction, normalization, and field matching).
     - *Stage 2 (Experimental / Benchmarking):* Bengali, Gujarati, Punjabi, Tamil, Telugu (Priority 2: Regional script OCR evaluation).
     - *Stage 1 (Planned Roadmap):* Kannada, Malayalam, Odia, Urdu (Priority 3: Complex conjuncts and RTL layout support).
  2. **Engine Abstraction via `TextExtractorProtocol`:** Implement an extensible OCR engine abstraction capable of routing between PyMuPDF (native vector text), bundled Tesseract 5.x (baseline OCR fallback), and PaddleOCR (primary multilingual benchmarking candidate for Indian scripts).
  3. **Language & Script Detection Pre-Filter:** Utilize Unicode block analysis and lightweight script classifiers to detect page-level and region-level scripts, routing mixed-language pages to appropriate recognition models, with manual examiner override in the UI when confidence is low ($<0.70$).
  4. **Multilingual Normalization Standard:** Implement Unicode NFC normalization, script-aware numeral normalization (converting Devanagari/regional digits to Hindu-Arabic for arithmetic rules), and punctuation normalization.
  5. **Verbatim Source Text Preservation Invariant:** The system must NEVER replace source-language text with machine translation. Original extracted text is preserved verbatim with full spatial and provenance metadata.
  6. **Deterministic Concept Mapping:** Utilize standardized multilingual concept dictionaries for critical financial and legal terms ("Total Amount" $\leftrightarrow$ "एकूण रक्कम" $\leftrightarrow$ "कुल रकम"). Sentence Transformers may be evaluated for unstructured clauses, but embeddings alone must never be used for financial, legal, or identity-critical fields.
* **Consequences:** Positive: Native support for Indian enterprise documentation; robust handling of bilingual invoices and challans; clean multi-engine routing. Negative: Increases OCR evaluation complexity and requires managing language-specific model weights.

---

### ADR-038: Signature Forensics & Reference Verification Sub-Capability
* **Status:** APPROVED & STABLE
* **Context:** Forged authorization signatures, cloned digital signature images, and unauthorized approvals represent major fraud vectors in industrial procurement and quality assurance.
* **Decision:**
  1. **Sub-Capability Integration:** Integrate Signature Forensics as a major specialized sub-capability inside `src/veritrace/capabilities/forensics/`. Do NOT create a ninth top-level capability.
  2. **Functional Scope:**
     - *Localization:* Isolate signature candidate regions on 300 DPI pages, distinguishing handwritten strokes from printed form lines and rubber stamps.
     - *Offline Visual Forensics:* Inspect stroke continuity, curvature, proportions, alignment, and tracing indicators (hesitation marks, uniform line thickness).
     - *Reference Comparison:* Compare questioned signatures against enrolled reference samples of authorized subjects using metric embedding distance via a quantized Siamese CNN model.
     - *Tampering & Clone Detection:* Detect pixel-identical cut-and-paste signature patches across documents via ORB matching, and detect boundary clipping masks and ELA compression spikes.
  3. **Local ONNX Runtime Inference:** Model training is conducted offline in PyTorch; inference in the desktop application executes exclusively via **ONNX Runtime (`onnxruntime`) on the local CPU**, ensuring zero cloud latency, zero GPU hardware dependency, and complete privacy.
  4. **Strict Forensic Guardrails (Six-Level Scale):** Visual similarity does NOT prove legal authorship or fraud. The system strictly classifies signature findings into:
     - 1. `SIGNATURE_DETECTED`
     - 2. `VISUAL_ANOMALY_OBSERVED`
     - 3. `SIMILARITY_WITH_REFERENCE`
     - 4. `POSSIBLE_MANIPULATION_INDICATOR`
     - 5. `INSUFFICIENT_EVIDENCE`
     - 6. `HUMAN_EXAMINER_DECISION`
     *The system must never automatically declare a person guilty of forgery.*
* **Consequences:** Positive: Provides industry-leading forensic depth for document authentication; operates 100% offline; prevents false accusations through rigorous epistemic guardrails. Negative: Requires maintaining an authorized reference signature registry and calibrating similarity thresholds on diverse ground-truth datasets.

---

### ADR-039: Technology Stack Evaluation, Dependency Governance & Offline Local Inference
* **Status:** APPROVED & STABLE
* **Context:** The evolution to industrial document intelligence introduces candidates for multilingual OCR (PaddleOCR), layout analysis (Docling), local model inference (ONNX Runtime), model training (PyTorch), and semantic matching (Sentence Transformers). Uncontrolled dependency expansion would cause package bloat, Windows compilation failures, and fragile installer builds.
* **Decision:**
  1. **Five-Tier Dependency Governance:** Classify all technologies into:
     - *Adopted:* Python 3.11, PySide6, SQLite, SQLAlchemy 2.0, Alembic, Pydantic, PyMuPDF, OpenCV, Pillow, NumPy, RapidFuzz, Tesseract 5.x, Groq API (optional), ReportLab, Pytest, pytest-qt, Ruff, Mypy, PyInstaller, Inno Setup.
     - *Evaluate / Benchmark:* PaddleOCR, Docling, Language/script detection libraries, ONNX Runtime, scikit-image, Sentence Transformers.
     - *Optional:* Groq ChatGroq (cloud AI narrative synthesis, strictly user-controlled with offline template fallback).
     - *Deferred:* Docker, PostgreSQL, multi-tenant cloud IAM.
     - *Rejected:* FastAPI, Uvicorn, React, Vite, Tauri 2, microservices.
  2. **Strict PyTorch Isolation:** PyTorch is strictly permitted for offline model development and research on developer workstations. It is **NEVER** added to runtime dependencies or packaged into the desktop distribution.
  3. **Lightweight Local Inference via ONNX Runtime:** All neural models (signature verification, layout classification) must be exported to quantized `.onnx` models and executed locally via `onnxruntime` on CPU.
  4. **Authoritative Manifest Guardrail:** Do NOT install heavy packages (`paddlepaddle`, `torch`, `docling`) or add them to `pyproject.toml` during architecture tasks. Only adopted, empirically justified dependencies enter the active project manifest.
* **Consequences:** Positive: Prevents dependency bloat; ensures 100% reproducible CI and local development; keeps desktop installer lightweight and reliable. Negative: Requires benchmarking candidates under protocol abstractions before official adoption.

---

### ADR-040: Industrial Security, Multi-Tenant Workspaces & Data Governance Architecture
* **Status:** APPROVED & STABLE
* **Context:** Industrial document intelligence requires organizational workspace isolation, role-based access control, secure local storage, reference sample chain-of-custody, and strict governance over cloud AI data sharing.
* **Decision:**
  1. **Relational Entity Expansion:** Extend the core domain model to include:
     - `Organization` (`organizations` table): Multi-tenant workspace aggregate.
     - `AuthorizedSubject` (`authorized_subjects` table): Enterprise personnel authorized to endorse documents.
     - `SignatureReferenceProfile` (`signature_references` table): Enrolled reference signature samples with crop paths, SHA-256 hashes, and feature embeddings.
  2. **Workstation Storage Security:** Clarify that local `%LOCALAPPDATA%` storage does not automatically provide disk encryption. Establish a security architecture roadmap supporting Windows DPAPI for API key protection and recommending BitLocker / SQLCipher for at-rest encryption in regulated enterprise environments.
  3. **Cloud AI Privacy & Data Minimization Guardrails:**
     - Cloud AI (Groq API) is strictly optional, disabled by default, and user-controlled via settings.
     - Confidential industrial documents (drawings, contracts, financial sheets) are **NEVER** transmitted to external cloud APIs.
     - When enabled, only anonymized numerical metrics and pre-calculated discrepancy summaries are sent for narrative synthesis.
     - 100% offline deterministic template fallback is maintained for air-gapped industrial facilities.
  4. **Human Examiner Oversight:** All consequential findings (especially signature discrepancies and financial contradictions) require human-in-the-loop review (`CONFIRM`, `DISMISS`, `ANNOTATE`) before inclusion in the final legal dossier.
* **Consequences:** Positive: Satisfies enterprise compliance, ISO/IEC 27037 chain-of-custody, and data sovereignty requirements; protects proprietary industrial IP. Negative: Requires managing workspace contexts and reference sample enrollment workflows.

---

### ADR-041: Domain Model Count Reconciliation, Multilingual Data Representation & Forensic Signal Calibration
* **Status:** APPROVED & STABLE
* **Context:** An architectural audit of the data model and capability specifications revealed four critical inconsistencies:
  1. An off-by-one arithmetic error in documentation that claimed "14 Core Entities + 1 Association Table", whereas the actual schema contains 15 distinct entities (`Investigation`, `InvestigationJob`, `Document`, `DocumentPage`, `ExtractedField`, `Entity`, `Finding`, `Evidence`, `CrossDocumentRelation`, `ReviewDecision`, `Dossier`, `AuditEvent`, `Organization`, `AuthorizedSubject`, `SignatureReferenceProfile`) plus 1 association table (`FindingEvidenceMap`), totaling 16 database tables in SQLite WAL.
  2. The `primary_language: str` column on `Document` was inadequate for bilingual or multi-script industrial documents (e.g. English-Hindi procurement challans).
  3. Visual forensic anomaly thresholds (ELA 90% quality $>3.0\sigma$, font baseline regression offset $>2.5\sigma$, ORB feature match count) were documented as hardcoded production rules rather than candidate signals requiring labelled dataset calibration.
  4. Language operational readiness was prematurely described as "Validated for Release" without supporting empirical benchmark evidence.
* **Decision:**
  1. **Reconcile Relational Model Count:** Formally codify the schema across all documentation and models as exactly **15 Core Relational Entities + 1 Association Table (16 SQLite Tables Total)**.
  2. **Multilingual Value Object Representation:** Support multi-script, mixed-language documents without relational table proliferation:
     - Embed `LanguageDetectionProfile` structured value objects as JSON columns on `Document` (`languages_json`) and `DocumentPage` (`languages_json`), capturing language distribution lists, script families, detection confidences, and detection engine provenance.
     - Retain indexed summary columns (`primary_language`, `primary_script`) for fast query filtering.
     - Persist token/region-level attributes (`language`, `script`, `lang_confidence`, `ocr_engine`, `ocr_model_version`) on `ExtractedField`.
     - Strictly enforce verbatim source preservation in `ExtractedField.raw_text` and normalized coordinates $[ymin, xmin, ymax, xmax] \in [0.0, 1.0]$.
  3. **Forensic Signal Calibration & Multi-Signal Corroboration:**
     - Classify ELA, font baseline offset, ORB matching, and compression anomalies as **candidate forensic signals requiring empirical calibration against labelled domain datasets**.
     - Gate visual forensic signals using `ExtractionQualityReport` (downgrading confidence on degraded/blurred documents).
     - Prohibit elevating single, isolated visual anomalies to high-severity findings; require multi-signal corroboration across independent measurements (e.g. ELA anomaly corroborated by font baseline misalignment or cross-document contradiction).
  4. **Correct Language Operational Readiness:** Reclassify Priority 1 languages (English, Hindi, Marathi) from "Validated for Release" to "Stage 2: Initial Implementation and Benchmarking", and establish explicit empirical acceptance criteria (CER, WER, conjunct/matra accuracy, Indic numeral normalization).
* **Consequences:** Positive: Eliminates schema ambiguity; provides flexible multi-script support without table explosion; aligns forensic claims with SWGDOC/ASTM scientific standards. Negative: Requires calibration against labelled ground-truth datasets during testing milestones.

---

### ADR-042: Signature Forensic Boundaries, Evidence Governance & Three-Tier AI Privacy Modes
* **Status:** APPROVED & STABLE
* **Context:** Preliminary documentation contained scientifically unsupported claims regarding static 2D scanned signature analysis (e.g. pen pressure reconstruction, writing velocity, pen-lift sequences). Additionally, enterprise industrial IP protection required clear operational definitions for AI data sharing.
* **Decision:**
  1. **Strict Scientific Delineation of Static 2D Signature Analysis:**
     - *Directly Measurable:* 2D geometry, bounding box, apparent pixel stroke width variance, binarized stroke density/topology, duplicate clone keypoints (ORB), digital manipulation boundary masks, and ELA compression discontinuity.
     - *Estimated:* Metric embedding feature distance via local ONNX Runtime CPU inference, apparent stroke line smoothness heuristics.
     - *Strictly Excluded / Unsupported:* True 3D pen pressure (indentation force), dynamic writing velocity/acceleration, chronological pen-lift sequencing, and physiological motor tremor. Stroke width, curvature, and continuity must be treated as quality-dependent visual features.
  2. **Signature Reference Governance & Cryptographic Precision:** Enrolling and matching reference signature samples requires:
     - Authorized legal enrollment from verified instruments (board resolutions, witnessed specimen cards).
     - Explicit written signatory consent/mandate (`consent_mandate_ref`).
     - Role-based access control (RBAC restricted to `FORENSIC_INVESTIGATOR` or `LEAD_AUDITOR`).
     - **Cryptographic Storage Architecture (Planned Security Specification):** Windows DPAPI (`CryptProtectData`) protects the Data Encryption Key (DEK), NOT arbitrary image files or SQLite database pages directly. Sensitive reference signature crops and embedding BLOBs are designated to be encrypted using symmetric AES-256-GCM under the DEK unsealed in-memory via DPAPI within the active authenticated Windows session. Key lifecycle and recovery must be explicitly governed. If a Windows user account is deleted or password-reset without domain recovery keys, encrypted biometric reference assets fail secure.
     - **Database Page Encryption Status:** The SQLite WAL database itself is NOT encrypted by DPAPI. Full database encryption via SQLCipher versus OS-level disk protection (BitLocker) remains an open implementation decision for Milestone 11.
     - **Cryptographic Erasure & Retention Lifecycle Design:** Retention expiry or mandate revocation triggers cryptographic erasure (cryptographic key destruction) -- destroying the relevant encryption key and all recoverable in-memory or persisted key copies, followed by deletion of encrypted artifacts and temporary copies. Physical block erasure must NOT be guaranteed by ordinary application-level overwrite operations, as SSD wear-leveling algorithms, flash translation layers (FTL), and OS file buffering prevent predictable block overwriting. Backups, snapshots, SQLite WAL files, exports, and recovery mechanisms must be comprehensively included in the retention lifecycle design to ensure residual ciphertext cannot be decrypted. (Note: This cryptographic storage and erasure design is an architectural specification for subsequent milestones and is not claimed as already implemented in application code).
     - Mandatory Human Examiner Review: Machine similarity does NOT prove legal authorship; visual difference does NOT prove forgery. Zero automated legal determinations of authenticity or forgery are permitted.
  3. **Three-Tier AI Privacy Modes:**
     - *Mode A: Offline Deterministic (Default):* Guarantees zero external network or AI calls for document intake, extraction, analysis, forensics, and dossier explanation. All explanations are synthesized locally using deterministic rules, mathematical checksums, and Jinja2 text templates.
     - *Mode B: Privacy-Preserving AI (Opt-In Statistical Synthesis):* Investigator-enabled. Sends strictly pre-calculated anonymized numerical metrics, classification tags, and summary statistics. Zero raw document text, zero page pixel crops, zero personal names, and zero proprietary formulas are transmitted.
     - *Mode C: Explicitly Authorized AI (Selected Redacted Excerpts):* Requires dual-key authorization (organizational policy + per-case investigator consent). Transmits short, explicitly selected textual excerpts strictly after automated and manual PII/IP redaction. Full unredacted page scans and raw PDF binaries are NEVER transmitted.
     - *Audit Logging:* Every Mode C invocation generates an immutable record in `audit_events` with timestamp, user ID, API endpoint, and SHA-256 hash of the exact redacted payload transmitted.
* **Consequences:** Positive: Establishes legally defensible, scientifically grounded signature forensic capabilities; prevents false accusations; provides complete data sovereignty and trade-secret protection for industrial enterprises. Negative: Limits automated signature decisions to investigative triage; requires managing reference consent lifecycles.
