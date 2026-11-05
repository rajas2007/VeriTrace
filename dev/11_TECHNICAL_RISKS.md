# 11_TECHNICAL_RISKS.md
# Technical Risk Assessment, Failure Modes & Mitigation Strategies

---

## 1. Risk Matrix Overview

Forensic document analysis involves significant complexities spanning low-level image processing, variable scan qualities, generative AI behaviors, and strict legal-grade evidence requirements. The following matrix identifies the primary technical risks and specifies concrete engineering mitigations.

| Risk ID | Risk Domain | Severity | Likelihood | Mitigation Strategy Summary |
| :---: | :--- | :---: | :---: | :--- |
| **TR-01** | OCR Extraction Inaccuracy on Scans | **HIGH** | **HIGH** | Dual-engine OCR (PyMuPDF vector first; CLAHE-preprocessed Tesseract fallback); confidence score gating. |
| **TR-02** | Coordinate Misalignment Across DPIs | **HIGH** | **MEDIUM** | Standardized normalized coordinate convention `[ymin, xmin, ymax, xmax]` in range `[0.0 - 1.0]`. |
| **TR-03** | Visual Forensics False Positives (ELA) | **HIGH** | **HIGH** | Three-tier epistemic classification (Observation vs. Suspicion); human review gate; adaptive noise baseline. |
| **TR-04** | LLM Hallucinations in Fraud Claims | **CRITICAL**| **MEDIUM** | Strict evidence anchoring; prompt injection barriers; LLM receives only structured facts; cannot declare ungrounded findings. |
| **TR-05** | Groq API Rate Limits & Token Quotas | **MEDIUM** | **MEDIUM** | Batched entity payloads; fallback to deterministic template reporting if API limits are encountered. |
| **TR-06** | Large Multi-Page PDF Memory Spikes | **HIGH** | **MEDIUM** | Page-by-page streaming; maximum resolution downsampling (max 2048px); lazy rasterization. |
| **TR-07** | File Upload Security & Malicious PDFs | **HIGH** | **LOW** | Strict MIME verification; magic byte validation; file size capping (20MB/file); sandboxed PyMuPDF parsing. |
| **TR-08** | Evidence Traceability Loss in Pipeline | **CRITICAL**| **LOW** | Immutable `evidence_id` created at point of detection; permanent foreign keys linking crops, pages, and dossiers. |
| **TR-09** | Cross-Document Entity False Matches | **MEDIUM** | **HIGH** | Multi-tier RapidFuzz scoring with distinct thresholds for "Likely Same Person" vs "Ambiguous" vs "Mismatch". |
| **TR-10** | PySide6 Native DLL & Plugin Bundling | **HIGH** | **MEDIUM** | Explicit PyInstaller configuration bundling Qt platform plugins (`platforms/qwindows.dll`) and styles. |
| **TR-11** | Ethical Harm from Automated Accusations| **CRITICAL**| **MEDIUM** | System enforces advisory classification only; prohibited from outputting "Fraudster" or "Guilty" labels. |
| **TR-12** | Python C-Extensions (OpenCV, PyMuPDF) | **HIGH** | **MEDIUM** | PyInstaller one-folder build with explicit hidden-imports for `fitz`, `cv2`, `PIL`, and bundled C-runtime DLLs. |
| **TR-13** | UI Thread Freezing during Heavy Forensics | **HIGH** | **LOW** | Offload all OCR, rasterization, and ELA processing to `QThreadPool` / `QRunnable`; communicate via Qt Signals. |
| **TR-14** | SQLite Concurrent Access in Desktop Runtime | **MEDIUM** | **LOW** | SQLite WAL mode (`PRAGMA journal_mode=WAL;`), short write transactions, and atomic job claims (`BEGIN IMMEDIATE`). |
| **TR-15** | Windows SmartScreen & Defender Warnings | **HIGH** | **MEDIUM** | Clean virtual environment build; Inno Setup compression; clear installation and security verification documentation. |
| **TR-16** | Installer Size & Bundled OCR Assets | **MEDIUM** | **LOW** | Strip unused PySide6 modules; bundle single language (`eng.traineddata`); Inno Setup ultra-compression (LZMA2). |
| **TR-17** | SQLite Multi-Process Locking in WAL Mode | **MEDIUM** | **LOW** | `PRAGMA journal_mode=WAL;`, short write transactions, `BEGIN IMMEDIATE;` atomic row claims. |
| **TR-18** | Complete Offline Operation & Cloud AI Loss | **HIGH** | **LOW** | 100% of core pipeline runs offline; deterministic template fallback when Groq is unreachable. |
| **TR-19** | Multilingual Indic OCR Degraded Accuracy | **HIGH** | **MEDIUM** | Multi-engine abstraction (PaddleOCR / Tesseract); Unicode NFC & numeral normalization; confidence gating. |
| **TR-20** | Signature Comparison False Accusations | **CRITICAL**| **MEDIUM** | 6-level assessment scale; visual similarity does not prove authorship; local ONNX Runtime CPU inference; HITL review. |
| **TR-21** | Industrial Storage Physical Access Exposure | **HIGH** | **LOW** | Clear disclosure that `%LOCALAPPDATA%` lacks auto-encryption; DPAPI API key protection; enterprise BitLocker/SQLCipher roadmap. |
| **TR-22** | Cloud AI Exposure of Confidential Industrial IP | **HIGH** | **LOW** | Cloud AI is strictly optional and user-gated; raw documents never sent to cloud; only anonymized pre-calculated metrics transmitted. |

---

## 2. In-Depth Risk Analyses & Engineering Mitigations

### TR-01: OCR Accuracy on Degraded, Low-Contrast Scans
* **Risk Description:** Scanned photocopies, skewed camera captures, or compressed receipts often produce garbled OCR text, dropping digits or confusing characters (e.g., mistaking `8` for `B`, `0` for `O`, or `1` for `l`).
* **Failure Impact:** Erroneous text extraction leads to spurious math discrepancies or false name mismatches.
* **Engineering Mitigations:**
  1. **Adaptive Image Enhancement:** Before passing raster images to Tesseract, apply OpenCV preprocessing:
     * Grayscale conversion $\to$ Contrast Limited Adaptive Histogram Equalization (CLAHE) $\to$ Otsu binarization.
     * Automated deskewing via minimum-area bounding box angle estimation.
  2. **Confidence Gating:** Any extracted token with OCR confidence $<60\%$ is tagged with `LOW_CONFIDENCE_FLAG`. Downstream rules treat low-confidence values as "Uncertain Readings" rather than confirmed discrepancies.

---

### TR-02: PDF Coordinate Misalignment Across Display Scales
* **Risk Description:** PDF documents use points ($1/72$ inch) measured from bottom-left; raster images use pixels measured from top-left; web browser canvases use scaled CSS pixels. Miscalculating coordinate transformations causes bounding boxes to appear offset from the actual text or tampering region.
* **Failure Impact:** Judges or analysts see bounding boxes highlighting empty white space instead of the altered numeral.
* **Engineering Mitigations:**
  1. **Normalized Unit Invariance:** All coordinates throughout the entire backend and database are strictly normalized to unit fractions `[ymin, xmin, ymax, xmax] \in [0.0, 1.0]` relative to the page width and height:
     $$y_{\min} = \frac{Y_{\text{top}}}{H_{\text{total}}}, \quad x_{\min} = \frac{X_{\text{left}}}{W_{\text{total}}}$$
  2. **Top-Left Origin Normalization:** PyMuPDF coordinates are inverted from PDF point space to top-left normalized coordinates at the exact moment of extraction.
  3. **Visual Regression Test:** Automated integration tests render a synthetic PDF with known colored markers and verify that extracted bounding boxes match the rendered pixels within $\pm 2$ pixels.

---

### TR-03: Visual Forensics False Positives in Error Level Analysis
* **Risk Description:** Error Level Analysis (ELA) detects differences in JPEG compression error. However, high-contrast edges (such as bold black text on a white background) naturally produce higher compression artifacts than smooth backgrounds, even on completely authentic documents.
* **Failure Impact:** The system flags every bold header or high-contrast signature as "tampered," leading to high false-positive rates and loss of user trust.
* **Engineering Mitigations:**
  1. **Differential Noise Baseline:** ELA scores are not evaluated in absolute terms. The engine computes the baseline noise of the surrounding paragraph or table cell. Only regions whose local variance exceeds the ambient text baseline by more than $3.0\sigma$ are flagged.
  2. **Multi-Signal Corroboration:** A visual anomaly is elevated to "High Severity" only if corroborated by a secondary signal (e.g., ELA compression spike AND font baseline offset AND cross-document math conflict).
  3. **Epistemic Humility:** The UI and dossier explicitly classify ELA findings as *Observed Compression Anomaly (Potential Artifact)*, inviting human confirmation.

---

### TR-04: LLM Hallucinations and Ungrounded Accusations
* **Risk Description:** Large Language Models prompted to investigate fraud can invent convincing but fictitious explanations, hallucinate non-existent numbers, or make ungrounded accusations of fraudulent intent.
* **Failure Impact:** Breach of assessment integrity; potential legal exposure in real-world compliance environments.
* **Engineering Mitigations:**
  1. **Strict Information Bounding:** Groq LLM prompts are injected only with structured factual JSON objects containing pre-computed measurements, bounding boxes, and rule outputs. The LLM is explicitly forbidden from introducing numbers or names not present in the input JSON.
  2. **Evidence Anchor Validation:** The backend runs a post-generation regex validator confirming that every claim in the LLM's output corresponds to an existing `evidence_id`. Any sentence referencing an unanchored finding is stripped.
  3. **Zero Autonomous Verdicts:** The system is hardcoded to never use accusatory language (e.g., "The applicant committed fraud"). It generates objective forensic observations (e.g., "A numerical mismatch of ₹1,00,000 was identified between Document A and Document B").

---

### TR-05: Groq API Rate Limits and Latency Spikes
* **Risk Description:** High-frequency API calls or large token payloads during live demonstrations could trigger Groq rate limits (`429 Too Many Requests`) or network timeouts.
* **Failure Impact:** The application hangs or crashes during the judges' live walkthrough.
* **Engineering Mitigations:**
  1. **Consolidated Payloads:** Instead of calling the LLM per document or per page, a single consolidated prompt is executed during Stage 9 (`ai_reasoning`), passing all anomalies for the entire investigation in one turn.
  2. **Graceful Deterministic Fallback:** If the Groq API returns a rate limit or timeout error, the system activates a deterministic fallback synthesizer that formats the dossier using standard Jinja2 templates directly from the rule outputs, ensuring 100% demo continuity.

---

### TR-06: Large Multi-Page PDF Memory and CPU Spikes
* **Risk Description:** Ingesting 50-page bank statements rasterized at 300 DPI (approx. $2480 \times 3508$ pixels per page $\approx 25\text{MB}$ uncompressed RAM per page) could exhaust server memory.
* **Failure Impact:** Out-Of-Memory (OOM) crashes on the server.
* **Engineering Mitigations:**
  1. **Page-by-Page Streaming:** The PDF service processes pages iteratively, writing rendered PNGs to disk and releasing PyMuPDF page pixmaps immediately with `pix = None`.
  2. **Investigation Page Cap:** In the prototype configuration, processing is capped at the first 5 relevant pages per document, which is sufficient for all hackathon demonstration packages.
  3. **Dynamic Downsampling for Computer Vision:** Full 300 DPI images are used for visual display; images are downsampled to a maximum dimension of 1600px when computing full-page ELA matrices, reducing memory consumption by over $70\%$.

---

### TR-07: File Upload Security & Malicious Payloads
* **Risk Description:** File upload endpoints could be exploited via directory traversal (`../../`), oversized zip bombs, or executable scripts disguised as PDF files.
* **Failure Impact:** Server compromise or denial of service.
* **Engineering Mitigations:**
  1. **UUID Path Isolation:** Uploaded files are renamed immediately to UUID-based filenames and stored in strictly partitioned investigation directories.
  2. **Magic Byte Verification:** The ingestion service inspects the leading bytes of every file (e.g., `%PDF` for PDFs, `\x89PNG` for PNGs) rather than relying on user-provided file extensions.
  3. **Strict Size Limits:** Enforces a maximum file size of 20MB per file and 50MB per investigation batch at the ingestion service level.

---

### TR-08: Cross-Document Entity False Matches
* **Risk Description:** Common Indian names (e.g., "Kumar", "Singh", "Sharma") or variations in initials ("R. K. Sharma" vs "Rajesh Kumar Sharma") can cause fuzzy matching engines to either miss genuine matches or falsely conflate distinct individuals.
* **Failure Impact:** Spurious conflict reports or missed identity contradictions.
* **Engineering Mitigations:**
  1. **Multi-Factor Entity Alignment:** Names are not evaluated in isolation. Entity reconciliation requires matching Name + Secondary Identifier (e.g., PAN number, Date of Birth, or Phone number).
  2. **Three-Band Similarity Classification:**
     * **Score $\ge 0.90$:** Reconciled as the same entity.
     * **Score $0.65 - 0.89$:** Flagged as *Potential Name Variation* (Requires Human Confirmation).
     * **Score $< 0.65$:** Confirmed distinct entities; triggers cross-document conflict if documents claim to belong to the same applicant.

---

### TR-12: Python Desktop Packaging & Native C-Extension Bundling
* **Risk Description:** Packaging heavy C-extensions (`fitz` for PyMuPDF, `cv2` for OpenCV, `PIL` for Pillow, PySide6 plugins) via PyInstaller frequently fails due to missing dynamic link libraries (`.dll`) or hidden imports on target Windows machines.
* **Failure Impact:** The packaged desktop application crashes immediately upon launch with `ModuleNotFoundError` or `DLL load failed`.
* **Engineering Mitigations:**
  1. **PyInstaller One-Folder Mode:** Use `--onedir` rather than `--onefile` during initial packaging to prevent runtime temp extraction latency and facilitate straightforward DLL dependency auditing.
  2. **Dedicated PyInstaller Spec Configuration:** Explicitly define `collect_data_files` and `collect_submodules` in `packaging/pyinstaller/veritrace.spec` for PySide6, OpenCV, PyMuPDF, and SQLAlchemy.
  3. **Milestone 0 Feasibility Gate:** Verify PySide6 desktop execution and virtual environment dependencies early in Milestone 0, avoiding last-minute packaging emergencies.

---

### TR-13: UI Event Loop Starvation & Background Worker Lifecycle
* **Risk Description:** Heavy CPU-bound forensic calculations running on the main Qt thread will freeze the UI event loop, causing Windows "Not Responding" dialogs. Additionally, orphaned worker processes could lock SQLite databases.
* **Failure Impact:** Application unresponsiveness or database busy errors.
* **Engineering Mitigations:**
  1. **QThreadPool Execution:** All CPU-bound processing (300 DPI rasterization, OCR, ELA) is offloaded to Qt's `QThreadPool` via `QRunnable` tasks, emitting Qt Signals for telemetry.
  2. **Graceful Qt Shutdown Hook:** The `QApplication` `aboutToQuit` signal terminates running background threads and closes SQLite connections cleanly.
  3. **Standalone Worker Isolation:** When running in out-of-process worker mode, `investigation_worker.py` monitors parent PID via `psutil` and exits immediately if the parent process terminates.

---

### TR-14: In-Process Thread Concurrency & Signal Safety
* **Risk Description:** Calling UI widget methods directly from background threads causes fatal Qt runtime crashes or undefined graphical glitches.
* **Failure Impact:** Immediate desktop process crash during background processing.
* **Engineering Mitigations:**
  1. **Qt Signal/Slot Decoupling:** Background runnables never touch Qt widgets directly. All communication routes through a helper `QObject` signal bridge using queued signal connections.
  2. **Elimination of Local Ports:** By replacing FastAPI with direct Python service calls, all port collision and localhost socket hijacking risks are permanently eliminated.

---

### TR-15: Windows Antivirus False Positives on Packaged Binaries
* **Risk Description:** Windows Defender or third-party antivirus software commonly flags unsigned PyInstaller executable binaries as suspicious heuristics.
* **Failure Impact:** The installer is blocked or quarantined during judge evaluation.
* **Engineering Mitigations:**
  1. **Clean Virtual Environment Build:** Build all PyInstaller packages in an isolated clean virtual environment containing only verified packages.
  2. **Inno Setup Installer Packaging:** Wrapping the payload inside a standard Inno Setup wizard reduces heuristic false-positive triggers compared to raw standalone executables.
  3. **Distribution Guidance:** Document SHA-256 release checksums and clear Windows Defender exclusion instructions in user documentation.

---

### TR-16: Desktop Installer Size & Bundled OCR Assets
* **Risk Description:** Bundling Python, PyTorch/Paddle weights, Tesseract, and multi-language OCR dictionaries could inflate the installer size to $>1.5\text{GB}$.
* **Failure Impact:** Slow downloads, high memory overhead, and poor installation experience.
* **Engineering Mitigations:**
  1. **Tesseract as Sole Bundled Engine:** Avoid heavy neural OCR frameworks like PaddleOCR; Tesseract adds $<50\text{MB}$.
  2. **Language Pruning:** Bundle only English (`eng.traineddata`, ~22MB) for the prototype.
  3. **Inno Setup Ultra Compression (LZMA2):** Use Inno Setup solid LZMA2 compression to keep final installer under 150MB.

---

### TR-17: SQLite Concurrent Access in WAL Mode
* **Risk Description:** Concurrent database access (Main UI thread reading findings, Background worker updating pipeline progress) could trigger `sqlite3.OperationalError: database is locked` if write transactions conflict.
* **Failure Impact:** Pipeline aborts; job updates fail.
* **Engineering Mitigations:**
  1. **WAL Mode Enforcement:** Database initialized with `PRAGMA journal_mode=WAL;` and `PRAGMA synchronous=NORMAL;`, allowing concurrent readers during writes.
  2. **Short Write Transactions:** Write transactions are scoped strictly to brief `BEGIN IMMEDIATE; ... COMMIT;` blocks, releasing locks in $<10\text{ms}$.
  3. **SQLAlchemy Timeout:** Configure `connect_args={"timeout": 30.0}` to allow automatic retries during brief lock contentions.

---

### TR-18: Complete Offline Operation & Cloud AI Loss
* **Risk Description:** If the host machine is disconnected from the internet or Groq API services experience an outage, systems dependent on cloud LLMs will fail completely.
* **Failure Impact:** Investigation pipeline crashes or freezes during evaluation.
* **Engineering Mitigations:**
  1. **100% Offline Core Capabilities:** Ingestion, PDF parsing, 300 DPI rendering, Tesseract OCR, visual forensics (ELA, font baseline regressions), arithmetic checks, cross-document correlation, and ReportLab PDF dossier generation execute purely locally with zero network calls.
  2. **Deterministic Template Fallback:** If `GROQ_API_KEY` is missing or Groq returns a network error, the pipeline immediately falls back to local rule-based Jinja2 templates, outputting complete, high-quality investigation dossiers without interruption.

---

### TR-19: Multilingual Indic OCR Degraded Accuracy (Complex Conjuncts & Matras)
* **Risk Description:** Devanagari (Hindi, Marathi) and regional Indian scripts feature complex conjuncts (युक्ताक्षर), top hanging shirorekha lines, and vowel matras above/below consonants. Standard OCR engines often fail on degraded scans, dropping diacritics or fracturing conjunct glyphs.
* **Failure Impact:** Inaccurate field extraction, garbled vendor names, and false numerical contradictions on bilingual invoices and challans.
* **Engineering Mitigations:**
  1. **Multi-Engine Abstraction (`TextExtractorProtocol`):** Route Devanagari text to PaddleOCR models optimized for Indic scripts, using Tesseract as robust fallback.
  2. **Unicode NFC Normalization:** Apply Unicode NFC normalization to canonicalize disparate matra encoding sequences before string matching.
  3. **Script-Aware Numeral Normalization:** Deterministically normalize Devanagari digits (`०-९`) to standard Hindu-Arabic digits (`0-9`) for math validation while preserving original strings in provenance.
  4. **Confidence Gating & Manual Override:** Flag extractions with confidence $<0.65$; provide UI manual script override when language detection is ambiguous.

---

### TR-20: Signature Comparison False Accusations & Intra-Writer Variability
* **Risk Description:** Machine learning signature verification models compute visual feature distances. Authentic signatures naturally vary across sessions, writing surfaces, instruments, or author fatigue. Treating visual dissimilarity as proof of forgery creates severe legal liability and assessment harm.
* **Failure Impact:** False accusation of fraud against authorized industrial personnel (e.g. Quality Inspectors or Plant Managers).
* **Engineering Mitigations:**
  1. **Six-Level Assessment Scale:** The system strictly outputs neutral forensic categories (`SIGNATURE_DETECTED`, `VISUAL_ANOMALY_OBSERVED`, `SIMILARITY_WITH_REFERENCE`, `POSSIBLE_MANIPULATION_INDICATOR`, `INSUFFICIENT_EVIDENCE`, `HUMAN_EXAMINER_DECISION`).
  2. **Zero Autonomous Accusations:** Machine output is strictly prohibited from declaring "Forged" or "Guilty."
  3. **Multiple Enrolled Reference Samples:** Organizations enroll multiple verified reference samples per subject to capture natural intra-writer variance.
  4. **Human Examiner Gate:** Every consequential signature finding requires review, annotation, and authoritative sign-off by a qualified human examiner.

---

### TR-21: Industrial Storage Physical Access & Encryption Exposure
* **Risk Description:** Desktop applications storing document originals, 300 DPI page renders, visual evidence crops, and SQLite databases in `%LOCALAPPDATA%/VeriTrace/` are vulnerable to physical workstation compromise or malware inspection if the host drive is unencrypted.
* **Failure Impact:** Exposure of proprietary industrial schematics, vendor pricing schedules, or employee credentials.
* **Engineering Mitigations:**
  1. **Transparent Security Documentation:** Explicitly document that `%LOCALAPPDATA%` does NOT provide automatic encryption; strongly recommend enterprise BitLocker drive encryption.
  2. **API Key Security via Windows DPAPI:** Store cloud API credentials using Windows Data Protection API (DPAPI) rather than plain text `.env` files in production builds.
  3. **Post-Hackathon SQLCipher Roadmap:** Architecture specifies a migration path to SQLCipher for transparent AES-256 database encryption at rest.

---

### TR-22: Cloud AI Data Leakage of Confidential Industrial IP
* **Risk Description:** Transmitting proprietary manufacturing drawings, chemical formulas on mill test certificates, or confidential vendor contracts to cloud LLM APIs violates enterprise non-disclosure agreements and data sovereignty laws.
* **Failure Impact:** Critical industrial IP theft; breach of enterprise compliance.
* **Engineering Mitigations:**
  1. **Cloud AI is Strictly Opt-In:** Groq LLM integration is disabled by default and requires explicit user enablement in desktop settings.
  2. **Zero Raw Document Transmission:** Raw document binaries, high-resolution scans, or unredacted files are NEVER sent to cloud APIs.
  3. **Strict Data Minimization:** When cloud AI is enabled, only anonymized numerical metrics (e.g., "Math delta: ₹5,000") and pre-calculated discrepancy summaries are sent for narrative synthesis.
  4. **100% Offline Capability:** The application remains 100% functional with offline deterministic template narratives when internet access is disabled or forbidden.
