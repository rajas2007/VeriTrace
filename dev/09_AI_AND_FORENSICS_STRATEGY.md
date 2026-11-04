# 09_AI_AND_FORENSICS_STRATEGY.md
# AI, Forensics & Grounded Investigation Strategy

---

## 1. Technical Framework & Tool Evaluation

VeriTrace integrates specialized, industry-proven libraries and models. Each technology is assigned a strictly defined role based on its algorithmic strengths:

| Technology / Library | Domain | Assigned Architectural Role | Technical Justification |
| :--- | :--- | :--- | :--- |
| **PyMuPDF (`fitz`)** | PDF Processing & Vector Extraction | Direct vector text extraction, font descriptor analysis, metadata auditing, and lossless 300 DPI page rasterization. | High-performance C-backed engine (`MuPDF`); extracts character-level bounding boxes and embedded image layers without external binaries. |
| **Tesseract OCR (`pytesseract`)** | Optical Character Recognition | Fallback text recognition for scanned bitmap PDFs, photographed documents, and image patches lacking vector layers. | Industry standard open-source OCR; outputs token-level bounding boxes and individual word confidence scores `[0 - 100]`. |
| **OpenCV (`cv2`)** | Computer Vision & Image Forensics | Grayscale preprocessing, adaptive thresholding, edge/contour detection, font baseline regression, and clone/patch matching. | Comprehensive algorithmic vision library; provides exact matrix operations required for forensic measurements. |
| **Pillow (`PIL`)** | Image Manipulation & ELA | Lossless format conversion, controlled-quality JPEG re-compression for Error Level Analysis, and visual evidence cropping. | Native Python imaging library; provides pixel-perfect `ImageChops.difference` arithmetic for ELA generation. |
| **RapidFuzz** | Fuzzy String Matching | Cross-document entity reconciliation (matching variations in person names, street addresses, company titles). | High-speed C++ implementation of Levenshtein and token sort distance; orders of magnitude faster than fuzzywuzzy. |
| **Pydantic V2** | Schema Enforcement & Validation | Data contract serialization, JSON schema validation, mathematical model enforcement, and LLM output parsing. | Strict type validation with compiled Rust core (`pydantic-core`); eliminates schema errors in LLM JSON mode responses. |
| **Groq ChatGroq (`llama-3.3-70b-versatile`)** | Large Language Model Reasoning | Grounded contextual reasoning, cross-document discrepancy synthesis, and narrative generation for investigation dossiers. | Sub-second inference speeds (300+ tokens/sec); supports native JSON schema response formatting for guaranteed schema alignment. |
| **ReportLab** | Document Generation | Programmatic compilation of the standardized, multi-page PDF Investigation Dossier. | Standard Python engine for generating professional, printable PDF documents with embedded image crops, tables, and headers. |
| **PySide6 / QGraphicsView** | Desktop Document Viewer | High-fidelity interactive document rendering with zoom, pan, and coordinate-aligned bounding box overlays. | Qt graphics architecture; ensures sub-millimeter visual alignment of forensic bounding boxes over document pages. |

---

## 2. Six Foundational Forensic Principles

To comply with forensic digital evidence standards (ISO/IEC 27037 / 27042) and PS-2 assessment guidelines, VeriTrace operates under six immutable engineering rules:

### Principle 1: OCR Extraction is Not Proof of Authenticity
* Extracting text via OCR merely records what characters appear on the page surface.
* A forged or digitally spliced salary slip will parse cleanly into text strings.
* **Engineering Standard:** The system must never label a document as "authentic" simply because its text fields parsed successfully. OCR is solely an extraction layer.

### Principle 2: Error Level Analysis (ELA) is an Investigative Signal, Not Proof
* Error Level Analysis highlights areas with different rates of compression error when resaved at a known JPEG quality (typically 90%).
* Text on high-contrast backgrounds naturally yields higher error levels than flat backgrounds; repeated resaving or scanning also affects noise.
* **Engineering Standard:** An elevated ELA score must be labeled as an *Observed Compression Variance Signal*, not as "Confirmed Forgery." It highlights a region for human inspection.

### Principle 3: Zero Ungrounded LLM Claims
* LLMs are susceptible to hallucinating plausible-sounding fraud narratives.
* **Engineering Standard:** An LLM prompt must never ask "is this document forged?" in free text. The LLM is provided only with structured, pre-calculated measurements (e.g., "Math mismatch: A+B != C", "Font baseline offset: 3.5px at [x,y,w,h]"). The LLM's role is strictly to explain the investigative implications of recorded facts.

### Principle 4: Strict Epistemic Classification (Three-Tier Findings)
Every detected finding must be classified into one of three distinct categories:
1. **Confirmed Observation:** An objective, mathematically verified measurement (e.g., "Date of birth on Doc A is 1988; Date of birth on Doc B is 1992").
2. **Detected Inconsistency:** An internal or cross-document contradiction violating known domain logic (e.g., "Monthly net pay ₹85,000 does not reconcile with annual gross ₹18,00,000").
3. **Suspected Manipulation:** A visual or structural irregularity indicating potential intentional tampering (e.g., "Font baseline discontinuity of +3.5px combined with 42% ELA compression spike").

### Principle 5: Confidence Values Must Not Be Invented
* Arbitrary pseudo-random confidence percentages (e.g., "94.2% Fraud Probability") destroy forensic credibility.
* **Engineering Standard:** Confidence scores must derive from documented formulas:
  * OCR Confidence: Direct mean of Tesseract word confidences.
  * Fuzzy Match Score: Exact Levenshtein token sort ratio from RapidFuzz `[0.0 - 1.0]`.
  * ELA Anomaly Score: Local variance normalized against global background variance:
    $$\text{Score}_{\text{ELA}} = \min\left(1.0, \frac{\sigma_{\text{local}} - \mu_{\text{background}}}{\kappa \cdot \sigma_{\text{background}}}\right)$$

### Principle 6: Total Page & Coordinate Traceability
* Every finding must permanently retain its source metadata:
  $$\text{Evidence Anchor} = \{\text{investigation\_id}, \text{document\_id}, \text{page\_number}, \text{normalized\_bbox}\}$$
* Clicking any finding in the UI must immediately pan the viewer to the exact physical pixel location on the page.

### Principle 7: Data Minimization & Optional Cloud AI Execution
* **100% Offline Core Capability:** PDF rendering, Tesseract OCR, OpenCV forensics, arithmetic checksums, cross-document correlation, and ReportLab PDF dossier generation execute purely locally with zero network connectivity.
* **Optional Cloud Inference:** Groq LLM inference is strictly optional and user-controlled.
* **Strict Data Minimization:** Raw document binaries, full-page scans, or unredacted personal files are NEVER transmitted off the user's desktop. When Groq is enabled, only pre-calculated numerical findings and anonymized text discrepancies are sent for narrative synthesis.
* **Deterministic Fallback:** If offline or if `GROQ_API_KEY` is not provided, the pipeline seamlessly generates standard factual forensic observations using local rule templates, without crashing or degrading functionality.

---

## 3. Coordinate Convention & Anomaly Representation

### 3.1 Normalized Bounding Box Convention
To ensure complete independence from display screen resolutions, zoom levels, and render DPIs, all spatial coordinates are stored in **Normalized Bounding Box Format**:

$$\text{BBox} = [y_{\min}, x_{\min}, y_{\max}, x_{\max}]$$

Where:
* $y_{\min}, x_{\min}, y_{\max}, x_{\max} \in [0.0, 1.0]$
* $(x_{\min}, y_{\min})$ represents the top-left corner as a fraction of total page width and height.
* $(x_{\max}, y_{\max})$ represents the bottom-right corner.

**Translation to Rendered Pixels (300 DPI):**
$$X_{\text{pixel}} = x_{\min} \times \text{PageWidth}_{\text{pixels}}$$
$$Y_{\text{pixel}} = y_{\min} \times \text{PageHeight}_{\text{pixels}}$$
$$\text{Width}_{\text{pixel}} = (x_{\max} - x_{\min}) \times \text{PageWidth}_{\text{pixels}}$$
$$\text{Height}_{\text{pixel}} = (y_{\max} - y_{\min}) \times \text{PageHeight}_{\text{pixels}}$$

---

### 3.2 Anomaly Classification Ontology

```json
{
  "anomaly_id": "anom_77492",
  "investigation_id": "inv_9b1deb4d",
  "document_id": "doc_02_salary",
  "page_number": 1,
  "category": "FONT_BASELINE_MISALIGNMENT",
  "epistemic_classification": "SUSPECTED_MANIPULATION",
  "severity": "HIGH",
  "normalized_bbox": [0.650, 0.612, 0.675, 0.640],
  "metrics": {
    "baseline_deviation_pixels": 3.5,
    "line_standard_deviation": 0.8,
    "z_score": 4.375,
    "ela_local_variance_ratio": 1.42
  },
  "observed_characteristics": {
    "expected_font_family": "Calibri",
    "detected_glyph_style": "Arial",
    "text_content": "1"
  },
  "forensic_explanation": "Character '1' in '₹1,85,000' is elevated +3.5px above the fitted row baseline (z-score 4.38). In conjunction with localized JPEG compression variance, this indicates digital insertion of a prefix digit to inflate stated salary.",
  "investigator_guidance": "Compare against original direct employer bank credit statements to confirm genuine net compensation."
}
```

---

## 4. Visual Forensic Algorithms

### 4.1 Error Level Analysis (ELA) Pipeline
```
[Original Rendered Page (PNG)]
         │
         ▼
[Save to In-Memory Buffer as JPEG (Quality=90)]
         │
         ▼
[Compute Absolute Difference: |Original - JPEG_90|]
         │
         ▼
[Apply Dynamic Contrast Scaling (Multiplier = 15x)]
         │
         ▼
[Compute Local Window Variance (32x32 pixel grid)]
         │
         ▼
[Threshold Clusters Exceeding Global Mean + 3*StdDev]
         │
         ▼
[Generate Bounding Boxes & Heatmap Overlay PNG]
```

### 4.2 Font & Baseline Alignment Verification Pipeline
```
[PyMuPDF Word Spans / Tesseract Character BBoxes]
         │
         ▼
[Cluster Tokens by Y-Center into Horizontal Text Lines]
         │
         ▼
[Fit Linear Regression Line: Y_baseline = m*X + c]
         │
         ▼
[Calculate Residuals: r_i = |Y_i - Y_baseline(X_i)|]
         │
         ▼
[Flag Characters with Residual r_i > 2.5 * Sigma]
         │
         ▼
[Highlight Spliced Characters on Canvas]
```
