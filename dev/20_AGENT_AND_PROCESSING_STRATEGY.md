# 20_AGENT_AND_PROCESSING_STRATEGY.md
# Agent Minimization, Deterministic Processing & Dependency Strategy

---

## 1. Agent Minimization Philosophy

A prevalent anti-pattern in modern AI hackathon architectures is "Agent Bloat"—wrapping every utility function, string formatter, or database query in an LLM agent with multi-turn conversational loops. This approach causes uncontrollable latency, high operational costs, non-deterministic failures, and severe hallucination risks.

**VeriTrace enforces strict Agent Minimization:**
* **Processing is Deterministic by Default:** File hashing, PDF rendering, OCR, computer vision (ELA, baseline regression), arithmetic validation, fuzzy string matching, database storage, and PDF report compilation are executed purely algorithmically using specialized C/Python libraries.
* **AI is Restricted to High-Order Synthesis:** The system uses exactly **one unified AI reasoning component** (invoked via Groq ChatGroq) across two tightly bounded tasks:
  1. *Classification Fallback:* Classifying document headers when keyword rules are inconclusive.
  2. *Forensic Synthesis & Explanation:* Synthesizing pre-calculated deterministic measurements into clear, grounded narrative explanations for the investigator and dossier.

---

## 2. Processing Strategy & Capability Classification Matrix

| Investigation Capability | Implementation Type | Primary Tool / Library | AI Required? | Technical Reason |
| :--- | :--- | :--- | :---: | :--- |
| **1. File Validation & Intake** | Deterministic Code | Python `hashlib`, magic bytes | **NO** | Cryptographic SHA-256 and byte inspection must be 100% exact. |
| **2. Storage Lifecycle** | Deterministic Code | Python `pathlib`, `shutil` | **NO** | Filesystem operations require reliable OS calls, not AI prompts. |
| **3. Document Classification** | Hybrid Rule / AI | Regex keywords; Groq (fallback) | *FALLBACK ONLY* | 90% of documents have standard headers; LLM zero-shot is used only when ambiguous. |
| **4. PDF Page Rasterization** | Deterministic Engine | `PyMuPDF` (`fitz`) | **NO** | 300 DPI image rendering requires exact vector graphics rasterization. |
| **5. OCR & Bounding Boxes** | Deterministic Engine | `PyMuPDF` vector; `Tesseract OCR` | **NO** | Character geometry and token bounding boxes are mathematical extractions. |
| **6. Layout Understanding** | Deterministic Algorithm | Spatial proximity clustering | **NO** | Key-value adjacency and table boundaries are geometric coordinates. |
| **7. Visual Forensics (ELA & CV)**| Deterministic Vision | `OpenCV`, `Pillow`, `NumPy` | **NO** | Error Level Analysis is pixel subtraction: $\|Orig - Resaved\|$; baseline deviation is linear regression. |
| **8. Contextual Rules & Math** | Deterministic Rules | Python math, `re`, `datetime` | **NO** | Arithmetic checksums and date logic must be mathematically exact. |
| **9. Cross-Document Correlation**| Deterministic Algorithm | `RapidFuzz` (Token Sort Ratio) | **NO** | String distance calculations are deterministic C++ algorithms. |
| **10. Finding Generation & Narrative**| **AI-Assisted Synthesis** | `ChatGroq` (`llama-3.3-70b`) | **YES** | Translates structured metrics into coherent forensic explanations. |
| **11. Evidence Crop Extraction** | Deterministic Engine | `Pillow`, `OpenCV` | **NO** | Image cropping at pixel coordinates is standard raster manipulation. |
| **12. Workflow Orchestration** | Deterministic StateGraph| `LangGraph` | **NO** | DAG transition and Human-in-the-Loop interrupt gates are programmatic state machines. |
| **13. Dossier PDF Compilation** | Deterministic Document | `ReportLab` | **NO** | PDF layout, table formatting, and image embedding require exact coordinate positioning. |
| **14. Audit History Logging** | Deterministic Database | `SQLAlchemy 2.0`, `SQLite` | **NO** | ACID transaction logging is a relational database function. |

---

## 3. Exhaustive Technology & Dependency Evaluation

The following table evaluates every proposed technology, verifying its necessity, deployment complexity, and whether a simpler alternative exists.

### 3.1 Backend & Computational Dependencies

| Technology | Purpose in VeriTrace | Where Used | Present in Repo? | Installation & Deployment Complexity | Simpler Alternative Considered? |
| :--- | :--- | :--- | :---: | :--- | :--- |
| **Python Application Services** | Direct in-process service facade (replacing FastAPI) | `src/veritrace/application/services/` | **YES** | Trivial (Pure Python modular architecture). | Direct in-process calls eliminate network serialization, port conflicts, and security tokens. |
| **LangGraph** | Stateful workflow orchestrator with checkpointing | `src/veritrace/capabilities/reasoning/` | **YES** | Trivial (Pure Python pip package). | Custom Python loop was considered, but LangGraph provides out-of-the-box state snapshots and HITL `interrupt_before`. |
| **Configurable AI Inference** | Grounded narrative synthesis over established findings | `src/veritrace/infrastructure/ai/` | **PLANNED** | Trivial (Requires API key if cloud provider enabled; offline fallback requires 0 dependencies). | Evaluated candidate models include Groq-hosted models (e.g., `llama-3.3-70b-versatile`, `openai/gpt-oss-120b`). Selection is fully configurable via `VERITRACE_AI_MODEL`. |
| **PyMuPDF (`fitz`)** | Direct PDF vector text extraction & 300 DPI page rendering | `src/veritrace/infrastructure/pdf/`, `src/veritrace/capabilities/extraction/` | **NO** | Low (`pip install pymupdf`, includes pre-compiled C wheels). | `pypdf` + `pdf2image` was considered. Rejected because `pdf2image` requires external `poppler` binaries on Windows, whereas PyMuPDF embeds MuPDF with zero external system binaries. |
| **Tesseract OCR (`pytesseract`)** | Initial default OCR candidate for scanned raster fallback | `src/veritrace/infrastructure/ocr/`, `src/veritrace/capabilities/extraction/` | **NO** | Medium (Requires Tesseract C-binary bundled with installer). | Abstracted behind `TextExtractorProtocol`. Initial default subject to comparative empirical benchmark before performance claims. |
| **Extraction Quality Engine** | OCR confidence evaluation & degradation scoring | `src/veritrace/capabilities/quality/` | **YES** | Trivial (Pure Python / NumPy metrics). | Skipping quality check was rejected as it risks unverified data entering downstream rules. |
| **OpenCV (`cv2`)** | Image preprocessing, contour analysis, font baseline regression | `src/veritrace/infrastructure/vision/`, `src/veritrace/capabilities/forensics/` | **NO** | Low (`pip install opencv-python-headless`, no GUI dependencies). | Raw NumPy was considered; rejected because OpenCV provides optimized C++ morphology and contour routines. |
| **Pillow (`PIL`)** | Lossless image format conversion and ELA differential math | `src/veritrace/infrastructure/vision/`, `src/veritrace/capabilities/forensics/` | **NO** | Trivial (Standard Python imaging library). | None. Pillow is the universal standard for Python image manipulation. |
| **RapidFuzz** | High-speed Levenshtein & token sort ratio for cross-doc entity matching | `src/veritrace/capabilities/correlation/` | **NO** | Trivial (`pip install rapidfuzz`, includes pre-compiled C++ wheels). | `fuzzywuzzy` was considered. RapidFuzz is 10x-50x faster and has no GPL licensing issues. |
| **SQLAlchemy 2.0** | Relational ORM for investigations, findings, and audit events | `src/veritrace/infrastructure/persistence/` | **NO** | Trivial (Pure Python package). | Raw `sqlite3` was considered. SQLAlchemy is preferred for typed models, migration safety, and clean session management. |
| **SQLite 3** | Embedded ACID relational database | `%LOCALAPPDATA%/VeriTrace/database/veritrace.sqlite` | **YES** (Python built-in) | Zero. Embedded in standard Python runtime; requires no servers or Docker containers. | PostgreSQL was considered. Rejected for prototype because it introduces container dependencies and port conflicts during judge demos. |
| **ReportLab** | Programmatic PDF compilation for Investigation Dossier | `src/veritrace/infrastructure/reporting/` | **NO** | Trivial (`pip install reportlab`). | `WeasyPrint` was considered. Rejected because WeasyPrint requires complex GTK/Pango C-libraries on Windows that frequently fail during installation. |

---

### 3.2 OCR Engine Evaluation & Benchmark Governance

| Evaluation Dimension | Tesseract OCR (`pytesseract`) | PaddleOCR (`paddlepaddle`) | Architectural Evaluation & Decision |
| :--- | :--- | :--- | :--- |
| **Architectural Isolation** | Implements `TextExtractorProtocol` | Implements `TextExtractorProtocol` | **Zero downstream impact:** Layout parsers, quality scorers, and rules depend only on `ExtractedToken` dataclasses, never engine internals. |
| **Disk & Dependency Footprint** | Lightweight native C++ binary ($\sim 45\text{MB}$ bundled). | Heavy framework ($>1.5\text{GB}$ with Paddle/PyTorch wheels & models). | **Tesseract** avoids multi-gigabyte downloads and fragile Windows C-runtime compilation during packaging. |
| **CPU Execution Overhead** | Native compiled C++ execution without deep learning runtime. | Python deep-learning inference; requires OpenMP / AVX optimizations. | **Tesseract** is the lower-risk initial baseline for diverse laptop environments. |
| **Field & Table Suitability** | Word/line bounding boxes with LSTM text recognition. | DBNet detection with CRNN recognition. | Both require custom geometric layout reconstruction in `capabilities/extraction/layout_parser.py`. |
| **Comparative Accuracy Status** | **Subject to empirical benchmark** across standard test suite. | **Subject to empirical benchmark** across standard test suite. | **No speculative accuracy claims (e.g. ">92% vs >96%") are recognized** until measured on representative dataset. |
| **Initial Architectural Status** | **APPROVED INITIAL DEFAULT** (Milestones 0–2) | **PLANNED EVALUATION CANDIDATE** | Adopt Tesseract as initial baseline; evaluate PaddleOCR under `TextExtractorProtocol` if benchmark justifies it. |

* **Mandatory Empirical Benchmark Specification:**
  Before making definitive comparative performance claims or switching engines, an empirical benchmark must be executed measuring:
  1. *OCR Accuracy:* Character Error Rate (CER) and Word Error Rate (WER).
  2. *Field Extraction Accuracy:* Exact field match rate, field-level precision and recall.
  3. *Localization Accuracy:* Bounding-box Intersection over Union (IoU) with ground truth.
  4. *System Performance:* Wall-clock processing time per page, peak memory (RSS in MB), and CPU core utilization.
  5. *Dataset Breadth:* Must evaluate across 7 document categories (digital PDFs, high-res scans, low-res scans, skewed captures, complex tables, financial fields, mixed typography). An initial 10-document set serves only as a sanity check and does not support broad statistical claims.

---

### 3.3 Desktop Presentation Layer & Packaging Dependencies

| Technology | Purpose in VeriTrace | Where Used | Present in Repo? | Architectural Justification |
| :--- | :--- | :--- | :---: | :--- |
| **PySide6 (Qt 6.7+)** | Native desktop UI framework (Qt Widgets, QSS, Signals) | `src/veritrace/gui/` | **YES** | Native Python desktop monolith; High-DPI support; rock-solid widget stability; direct memory access. |
| **QGraphicsView / Scene** | High-performance document & bounding box viewing | `src/veritrace/gui/components/document_viewer.py` | **PLANNED** | Hardware-accelerated 2D canvas with pan/zoom and coordinate bounding box overlays. |
| **PyInstaller** | Python application bundler (one-folder mode) | `packaging/pyinstaller/` | **PLANNED** | Bundles Python 3.11 runtime, PySide6 plugins, and C-extensions into standalone folder. |
| **Inno Setup** | Single-click Windows setup installer | `packaging/installer/` | **PLANNED** | Produces single-click `VeriTrace-Setup.exe` installer with desktop shortcut and clean uninstallation. |

---

### 3.4 Exhaustive New Technology & Dependency Governance Matrix

In accordance with Phase 5 of the Industrial Architecture Evolution, all newly evaluated technologies are classified into five strict governance tiers:
1. **Adopted:** Integrated into the active baseline architecture and dependencies.
2. **Evaluate / Benchmark:** Under active empirical benchmarking; abstracted behind protocols; **NOT** added to `pyproject.toml` until validated.
3. **Optional:** Available as user-controlled plugins or configurations with zero impact on offline execution.
4. **Deferred:** Validated for post-hackathon enterprise production; excluded from prototype runtime.
5. **Rejected:** Architecturally incompatible, redundant, or violating core principles.

| Technology | Architectural Domain | Governance Tier | Python 3.11 & Windows Compat | CPU / GPU Req | Disk & Package Size | License & Redistribution | Offline Support | Initial Release Req? | Technical Decision Rationale |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **PaddleOCR (`paddlepaddle`)** | Multilingual OCR Engine | **Evaluate / Benchmark** | Compatible with Python 3.11 x64 on Windows; wheels available. | CPU-optimized inference (OpenMP/AVX); GPU optional. | **Heavy:** $\sim 1.8\text{GB}$ total (framework + models). | Apache 2.0 (Permissive, commercial redistribution OK). | **100% Offline** (bundled local model weights). | **NO** (Evaluated behind `TextExtractorProtocol`) | SOTA text detection (DBNet++) and recognition (SVTR) for Devanagari (Hindi, Marathi) and Indic scripts. Kept behind protocol; not added to `pyproject.toml` during architecture phase. |
| **Docling (IBM Docling)** | Document Structure & Layout | **Evaluate / Benchmark** | Compatible with Python 3.11 x64 on Windows. | CPU-friendly; multi-core recommended. | **Medium-Heavy:** $\sim 650\text{MB}$ with layout models. | MIT License (Permissive, commercial OK). | **100% Offline** (bundled layout weights). | **NO** (Optional layout adapter) | Evaluated as an optional adapter for complex nested engineering tables and reading order. PyMuPDF remains default vector foundation. |
| **Language / Script Detection (`pycld2` / `fasttext-wheel`)** | Ingestion & Script ID | **Evaluate / Benchmark** | Windows pre-compiled wheels available for Python 3.11. | Minimal CPU overhead ($<5\text{ms}$ per page). | **Lightweight:** $<25\text{MB}$ total. | Apache 2.0 / BSD. | **100% Offline**. | **YES (Experimental)** | Essential for routing multilingual Indian pages to script-specific OCR models. Fallback to Unicode block analysis. |
| **PyTorch (`torch`)** | Model Development & Training | **Evaluate (Offline Dev Only)** | Fully compatible on Windows x64. | GPU recommended for training; CPU adequate for test. | **Very Heavy:** $>2.5\text{GB}$ with CUDA runtime. | BSD-style (Permissive). | **100% Offline**. | **NO (Zero Runtime Presence)** | **STRICT ISOLATION:** PyTorch is strictly used for offline research and Siamese CNN training on developer workstations. It is **NEVER** bundled into the desktop client distribution. |
| **ONNX Runtime (`onnxruntime`)** | Local Model Inference | **Evaluate / Benchmark** | Outstanding Windows 10/11 x64 compatibility via pre-compiled DLLs. | Optimized CPU inference via Eigen/MKL; zero GPU requirement. | **Lightweight:** $\sim 35\text{MB}$ pip package; quantized model $<20\text{MB}$. | MIT License (Permissive). | **100% Offline**. | **YES (Signature Prototype)** | Enables local, blazing-fast execution of quantized Siamese CNN signature comparison models on standard enterprise laptops without PyTorch overhead. |
| **scikit-image (`skimage`)** | Morphological Forensics | **Evaluate / Benchmark** | Fully compatible on Python 3.11 Windows x64. | Pure CPU array math. | **Lightweight:** $\sim 45\text{MB}$. | BSD-3-Clause (Permissive). | **100% Offline**. | **NO (Optional CV tool)** | Evaluated for specialized structural similarity (SSIM) and advanced morphological filters; OpenCV remains primary vision baseline. |
| **Sentence Transformers** | Multilingual Semantic Matching | **Evaluate / Benchmark** | Compatible via ONNX Runtime or lightweight PyTorch. | CPU inference acceptable for single phrases. | **Medium:** $\sim 150\text{MB}$ (quantized MiniLM model). | Apache 2.0 (Permissive). | **100% Offline**. | **NO (Roadmap)** | Evaluated for cross-language phrase matching ("Total Amount" vs "एकूण रक्कम"). Deterministic dictionary prioritized for critical totals. |
| **Groq ChatGroq API** | Contextual Narrative Synthesis | **Optional / User-Gated** | Pure HTTP/JSON protocol; zero system binary requirements. | Zero workstation compute; remote cloud execution. | **Trivial:** Python client $<5\text{MB}$. | Proprietary Cloud API (Gated by user API key). | **Requires Internet** (100% offline template fallback). | **NO (Optional Enhancement)** | User-controlled narrative synthesizer. Never receives raw scans; operates only on anonymized numerical/textual findings. |
| **FastAPI / Uvicorn** | Web Gateway | **REJECTED** | Obsolete legacy web stack. | Unnecessary network loopback overhead. | Bloat. | Permissive. | N/A | **NO (Eliminated)** | Eliminated under ADR-026 and ADR-030. Direct in-process Python calls provide zero-overhead communication with PySide6. |
| **Tauri 2 / Rust** | Desktop Shell | **REJECTED** | Deprecated in Task 02.4. | Complex dual-runtime IPC (Rust-Python). | Bloat. | Permissive. | N/A | **NO (Eliminated)** | Replaced by native PySide6 under ADR-025, unifying entire stack in pure Python 3.11. |
| **Docker / PostgreSQL** | Database Containers | **DEFERRED (Enterprise)** | Requires Docker Desktop on Windows. | Heavy memory and virtualization overhead. | Multi-gigabyte containers. | Permissive. | Local container. | **NO (Excluded from Prototype)** | SQLite WAL mode provides complete local ACID persistence with zero external service dependencies. |

---

### 3.5 AI Privacy Modes & Data Governance Policies

To ensure industrial trade secrets, competitive procurement prices, and proprietary manufacturing formulations are protected:

1. **Mode A: Offline Deterministic Explanations (Default & Air-Gapped):**
   * 100% local execution using deterministic rule evaluation, math checks, and Jinja2 text templates.
   * Guarantees zero external network or AI calls for document intake, extraction, analysis, forensics, and dossier generation.
   * Mandatory for defense, government tenders, and zero-trust networks.

2. **Mode B: Privacy-Preserving AI (Opt-In Statistical Synthesis):**
   * Investigator-controlled toggle in workstation settings.
   * Sends **strictly pre-calculated anonymized numerical metrics**, classification labels, and error codes.
   * **Zero document text, zero page pixel crops, zero personal names, zero tax IDs, and zero proprietary formulas** are transmitted.
   * Cloud LLM synthesizes natural language summaries from abstract statistics.

3. **Mode C: Explicitly Authorized AI Processing (Selected Redacted Excerpts):**
   * Requires dual-key authorization: organizational policy enablement and per-case affirmative investigator consent.
   * Transmits short, explicitly selected textual excerpts (e.g., a specific disputed warranty clause) strictly after automated and manual PII/IP redaction.
   * **Full unredacted page scans and raw PDF binaries are NEVER transmitted.**
   * Mandatory audit logging in `audit_events` with UTC timestamp, user ID, API endpoint, and SHA-256 hash of the exact redacted payload transmitted.
