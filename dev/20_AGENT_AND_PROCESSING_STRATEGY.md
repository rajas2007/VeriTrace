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
