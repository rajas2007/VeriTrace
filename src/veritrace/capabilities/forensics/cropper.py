"""Forensic evidence cropper generating pixel-anchored visual patches with context padding."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from veritrace.domain.entities.evidence import Evidence
from veritrace.domain.exceptions.base import ValidationError
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox


class EvidenceCropper:
    """Extracts high-resolution visual evidence crops with standard context padding."""

    def __init__(self, padding_px: int = 20) -> None:
        self._padding_px = max(0, padding_px)

    def crop_bounding_box(
        self,
        image_or_path: np.ndarray | Path | bytes,
        bbox: NormalizedBoundingBox,
        output_path: Path,
        padding_px: int | None = None,
    ) -> tuple[Path, int, int, int, int]:
        """Crop a region defined by a NormalizedBoundingBox with context padding.

        Args:
            image_or_path: OpenCV BGR array, Path, or raw bytes.
            bbox: NormalizedBoundingBox in [0.0, 1.0].
            output_path: Destination path for saving the PNG crop.
            padding_px: Context padding in pixels (default: self._padding_px = 20px).

        Returns:
            Tuple of (output_path, pixel_x, pixel_y, pixel_width, pixel_height)
            representing the exact bounding box on the original page before padding.
        """
        img_bgr = self._load_image(image_or_path)
        img_h, img_w = img_bgr.shape[:2]
        pad = self._padding_px if padding_px is None else max(0, padding_px)

        # Convert normalized coordinates to absolute page pixels
        px_x1, px_y1, px_x2, px_y2 = bbox.to_pixels(img_w, img_h)
        orig_w = px_x2 - px_x1
        orig_h = px_y2 - px_y1

        # Apply padding clamped to image canvas boundaries
        crop_x1 = max(0, px_x1 - pad)
        crop_y1 = max(0, px_y1 - pad)
        crop_x2 = min(img_w, px_x2 + pad)
        crop_y2 = min(img_h, px_y2 + pad)

        if crop_x1 >= crop_x2 or crop_y1 >= crop_y2:
            raise ValidationError(
                f"Degenerate crop coordinates [{crop_x1}, {crop_y1}, {crop_x2}, {crop_y2}] "
                f"for image size {img_w}x{img_h}"
            )

        crop_bgr = img_bgr[crop_y1:crop_y2, crop_x1:crop_x2]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        success = cv2.imwrite(str(output_path), crop_bgr)
        if not success:
            # Fallback to PIL in case cv2.imwrite fails on non-ASCII paths
            pil_img = Image.fromarray(cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB))
            pil_img.save(str(output_path), format="PNG")

        return output_path, px_x1, px_y1, orig_w, orig_h

    def create_evidence_entity(
        self,
        page_id: str,
        image_or_path: np.ndarray | Path | bytes,
        bbox: NormalizedBoundingBox,
        output_crop_path: Path,
        heatmap_image_path: str | None = None,
        grounding_explanation: str | None = None,
        padding_px: int | None = None,
    ) -> Evidence:
        """Crop visual patch, save to disk, and return a domain Evidence entity."""
        saved_path, px, py, pw, ph = self.crop_bounding_box(
            image_or_path=image_or_path,
            bbox=bbox,
            output_path=output_crop_path,
            padding_px=padding_px,
        )

        return Evidence.create(
            page_id=page_id,
            crop_image_path=str(saved_path),
            normalized_bbox=bbox,
            pixel_x=px,
            pixel_y=py,
            pixel_width=pw,
            pixel_height=ph,
            heatmap_image_path=heatmap_image_path,
            grounding_explanation=grounding_explanation,
        )

    def _load_image(self, image_or_path: np.ndarray | Path | bytes) -> np.ndarray:
        """Decode input into OpenCV BGR ndarray."""
        if isinstance(image_or_path, np.ndarray):
            return image_or_path

        if isinstance(image_or_path, Path):
            if not image_or_path.exists():
                raise ValidationError(f"Image path not found: {image_or_path}")
            img = cv2.imread(str(image_or_path))
            if img is None:
                raise ValidationError(f"Failed to decode image from path: {image_or_path}")
            return img

        if isinstance(image_or_path, bytes):
            nparr = np.frombuffer(image_or_path, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValidationError("Failed to decode image from bytes")
            return img

        raise TypeError(f"Unsupported image type: {type(image_or_path)}")
