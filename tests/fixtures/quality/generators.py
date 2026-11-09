"""Synthetic Test Fixture Generator for Quality Capability.

Generates controlled, deterministic synthetic images and PDFs for testing:
- High quality document image (sharp text, good contrast, upright)
- Blurry image (Gaussian blur applied)
- Low resolution image (downscaled to low pixel dimensions)
- Rotated image (90 degrees)
- Skewed image (affine tilted by 4.5 degrees)
- Blank image (uniform white canvas)
- Low contrast image (compressed dynamic range)
- Excessive noise image (Gaussian noise added)
- Uneven brightness / shadow image (spatial luminance gradient applied)
- Cut-off content image (text touching outer margins)
- Valid multi-page PDF
- Blank page PDF
- Mixed orientation PDF
- Corrupted PDF
"""

from pathlib import Path
from typing import cast

import cv2
import numpy as np
import pymupdf as fitz


def create_clean_document_image(width: int = 1200, height: int = 1600) -> np.ndarray:
    """Generate a clean, high-contrast, sharp synthetic document image."""
    img = np.full((height, width, 3), 250, dtype=np.uint8)

    # Title
    cv2.putText(
        img,
        "VERITRACE AUDIT CERTIFICATE",
        (100, 150),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (20, 20, 20),
        2,
    )
    cv2.line(img, (100, 180), (min(width - 100, 1050), 180), (40, 40, 40), 2)

    # Body lines
    for i in range(25):
        y = 240 + i * 45
        text_line = f"Record Entry #{1000 + i}: Verified status VALID - RefCode 0x{i * 37:04X}"
        cv2.putText(img, text_line, (100, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (30, 30, 30), 2)

    return img


def create_blurry_image(base_img: np.ndarray, ksize: int = 25) -> np.ndarray:
    """Apply severe optical defocus blur."""
    return cv2.GaussianBlur(base_img, (ksize, ksize), 0)


def create_low_res_image(base_img: np.ndarray, target_dim: int = 250) -> np.ndarray:
    """Downscale to low pixel dimensions."""
    h, w = base_img.shape[:2]
    aspect = w / h
    new_w = int(target_dim * aspect)
    new_h = target_dim
    return cv2.resize(base_img, (new_w, new_h), interpolation=cv2.INTER_AREA)


def create_skewed_image(base_img: np.ndarray, angle_deg: float = 4.5) -> np.ndarray:
    """Apply affine skew rotation."""
    h, w = base_img.shape[:2]
    center = (w // 2, h // 2)
    rot_mat = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
    return cv2.warpAffine(base_img, rot_mat, (w, h), borderValue=(250, 250, 250))


def create_rotated_image(base_img: np.ndarray) -> np.ndarray:
    """Rotate 90 degrees clockwise."""
    return cv2.rotate(base_img, cv2.ROTATE_90_CLOCKWISE)


def create_blank_image(width: int = 1200, height: int = 1600) -> np.ndarray:
    """Create a completely blank white canvas."""
    return np.full((height, width, 3), 255, dtype=np.uint8)


def create_low_contrast_image(base_img: np.ndarray) -> np.ndarray:
    """Compress dynamic range so text is barely distinguishable from background."""
    gray = cv2.cvtColor(base_img, cv2.COLOR_BGR2GRAY) if base_img.ndim == 3 else base_img
    # Map [0, 255] to [185, 215] (30 gray levels, low contrast range)
    scaled = (gray.astype(np.float32) / 255.0) * 30.0 + 185.0
    res = np.clip(scaled, 0, 255).astype(np.uint8)
    return cast(np.ndarray, cv2.cvtColor(res, cv2.COLOR_GRAY2BGR))


def create_noisy_image(base_img: np.ndarray, sigma: float = 40.0) -> np.ndarray:
    """Add Gaussian noise."""
    noise = np.random.normal(0, sigma, base_img.shape).astype(np.float32)
    noisy = np.clip(base_img.astype(np.float32) + noise, 0, 255).astype(np.uint8)
    return cast(np.ndarray, noisy)


def create_uneven_illumination_image(base_img: np.ndarray) -> np.ndarray:
    """Apply harsh spatial gradient / shadow."""
    h, w = base_img.shape[:2]
    # Create gradient mask: 1.0 on left, 0.1 on right
    x = np.linspace(1.0, 0.1, w)
    y = np.linspace(1.0, 0.2, h)
    xx, yy = np.meshgrid(x, y)
    mask = (xx * yy)[:, :, np.newaxis]
    return (base_img.astype(np.float32) * mask).astype(np.uint8)


def create_cutoff_image(width: int = 1200, height: int = 1600) -> np.ndarray:
    """Draw text intersecting and touching the outermost border pixels."""
    img = np.full((height, width, 3), 250, dtype=np.uint8)
    # Draw thick content intersecting edges
    cv2.putText(
        img,
        "CLIPPED CONTENT AT TOP EDGE",
        (20, 15),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (10, 10, 10),
        4,
    )
    cv2.putText(
        img,
        "CLIPPED CONTENT AT BOTTOM",
        (20, height - 5),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (10, 10, 10),
        4,
    )
    cv2.rectangle(img, (0, 200), (25, 400), (10, 10, 10), -1)
    cv2.rectangle(img, (width - 25, 200), (width, 400), (10, 10, 10), -1)
    return img


def create_synthetic_pdf(
    file_path: Path,
    num_pages: int = 2,
    blank_page_index: int = -1,
    landscape_page_index: int = -1,
) -> Path:
    """Generate a clean synthetic PDF using PyMuPDF."""
    doc = fitz.open()
    for i in range(num_pages):
        rect = fitz.Rect(0, 0, 842, 595) if i == landscape_page_index else fitz.Rect(0, 0, 595, 842)

        page = doc.new_page(width=rect.width, height=rect.height)

        if i != blank_page_index:
            page.insert_text(
                fitz.Point(72, 100),
                f"VERITRACE SYNTHETIC AUDIT REPORT - PAGE {i + 1}\n\n"
                f"Employee ID: EMP-{98234 + i}\n"
                f"Department: Quantitative Risk Verification\n"
                f"Monthly Basic Pay: INR 85,000.00\n"
                f"Special Allowance: INR 15,000.00\n"
                f"Gross Remuneration: INR 1,00,000.00\n"
                f"Net Credit Bank Account: HDFC-00987216\n"
                f"This document represents an automated audit trail for forensic evaluation.\n",
                fontsize=11,
            )

    doc.save(str(file_path))
    doc.close()
    return file_path
