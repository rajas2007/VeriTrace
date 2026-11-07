# VeriTrace — Advanced Neural OCR & Layout Parsing Environment

## Architecture & Dependency Isolation

VeriTrace maintains a strict dependency isolation policy to protect core computer vision routines (Hu moments, stroke width analysis, Error Level Analysis, copy-move detection) from package version conflicts.

### The Conflict Problem
1. **Primary Workstation Stack (`.venv`):**
   - Python: 3.11.9
   - NumPy: `2.4.6`
   - OpenCV: `opencv-python-headless 5.0.0.93`
   - Footprint: ~120 MB
2. **PaddleOCR Requirements:**
   - PaddlePaddle 2.6.x requires `numpy < 2.0.0` (NumPy 1.x ABI).
   - PaddleOCR pins `opencv-contrib-python == 4.10.0.84`.
   - Installing PaddleOCR directly into the primary `.venv` forcibly downgrades NumPy and breaks C-extensions.
3. **IBM Docling Requirements:**
   - Requires PyTorch 2.x, HuggingFace transformers, and vision models.
   - Storage footprint: ~3.5 GB for CPU wheels; ~6.5 GB for CUDA wheels.

### The Isolated Solution
A dedicated sidecar environment (`.venv-advanced-engines`) runs independently of the main application.

```
+-------------------------------------------------------------+
| VeriTrace Primary Environment (.venv)                       |
|   - PySide6 GUI Workbench                                    |
|   - Core Domain, Correlation Rules & Forensic Detectors      |
|   - Tesseract OCR & PyMuPDF Vector Text Extractor (Default)  |
|   - Classical Morphological Signature Verifier               |
|   - SQLCipher 4.x & Windows DPAPI Security                   |
+-------------------------------------------------------------+
                              |
                     IPC / Subprocess
                              v
+-------------------------------------------------------------+
| Optional Advanced Engines Sidecar (.venv-advanced-engines)   |
|   - Baidu PaddleOCR (PP-OCRv4 detection & recognition)       |
|   - IBM Docling (Deep Layout Parsing & Table Extraction)     |
|   - PyTorch CPU Runtime                                      |
+-------------------------------------------------------------+
```

---

## Setup & Installation

### Prerequisites
- Windows 10/11 x64
- Python 3.11 installed on system PATH
- Approximately 4 GB free disk space

### Automated Installation
Run the PowerShell setup script from the repository root:
```powershell
.\scripts\environments\setup_advanced_engines_venv.ps1
```
Or use the batch script:
```cmd
scripts\environments\setup_advanced_engines_venv.bat
```

### Manual Installation
```cmd
python -m venv .venv-advanced-engines
.venv-advanced-engines\Scripts\python.exe -m pip install --upgrade pip
.venv-advanced-engines\Scripts\pip.exe install -r scripts\environments\requirements-advanced-engines.txt
```

---

## Model Weights & Licensing

| Component | Framework | Model Architecture | License | Storage Footprint |
| :--- | :--- | :--- | :--- | :--- |
| **PaddleOCR Detection** | PaddlePaddle | `ch_PP-OCRv4_det` | Apache 2.0 | ~4.6 MB |
| **PaddleOCR Classifier** | PaddlePaddle | `ch_ppocr_mobile_v2.0_cls` | Apache 2.0 | ~1.4 MB |
| **PaddleOCR Recognition** | PaddlePaddle | `ch_PP-OCRv4_rec` / `en_PP-OCRv4_rec` | Apache 2.0 | ~10.8 MB |
| **PaddleOCR Devanagari** | PaddlePaddle | `devanagari_PP-OCRv3_rec` (Hindi/Marathi) | Apache 2.0 | ~11.5 MB |
| **Docling Layout** | PyTorch | `TableFormer` / `LayoutLM` | MIT License | ~280 MB - 1.2 GB |

*Automatic Download:* On first inference, both engines download their official pretrained weights to `~/.paddleocr/` and `~/.cache/docling/`.

---

## Fallback Guarantees

If `.venv-advanced-engines` is not configured or installed:
1. `OcrEngineRegistry` automatically selects Tesseract OCR (`TesseractOcrEngine`) or PyMuPDF digital text extraction.
2. `TextExtractionService` automatically uses digital vector text extraction and geometric table line-clustering.
3. No crashes, unhandled exceptions, or missing module errors are propagated to the user.
