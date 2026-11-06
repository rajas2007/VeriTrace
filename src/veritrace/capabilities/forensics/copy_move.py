"""Copy-move and duplicated stamp/signature detector using ORB feature matching."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from veritrace.capabilities.forensics.models import CopyMoveMatch
from veritrace.domain.exceptions.base import ValidationError
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox


class CopyMoveDetector:
    """Detects duplicated or cloned image patches (such as forged signatures or stamps)

    across different pages or distinct documents using multi-scale ORB feature matching.
    """

    def __init__(
        self,
        n_features: int = 1000,
        lowe_ratio: float = 0.75,
        min_inlier_matches: int = 12,
    ) -> None:
        self._n_features = n_features
        self._lowe_ratio = lowe_ratio
        self._min_inlier_matches = min_inlier_matches
        self._orb = cv2.ORB_create(nfeatures=self._n_features)  # type: ignore[attr-defined]

    def extract_features(self, img_bgr: np.ndarray) -> tuple[list[cv2.KeyPoint], np.ndarray | None]:
        """Extract ORB keypoints and binary descriptors from an image canvas."""
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY) if len(img_bgr.shape) == 3 else img_bgr
        keypoints, descriptors = self._orb.detectAndCompute(gray, None)
        return keypoints, descriptors

    def match_regions(
        self,
        source_crop: np.ndarray,
        target_crop: np.ndarray,
        source_page: int,
        source_bbox: NormalizedBoundingBox,
        target_page: int,
        target_bbox: NormalizedBoundingBox,
        match_type: str = "SIGNATURE",
    ) -> CopyMoveMatch | None:
        """Compare two localized image patches to determine if they are identical clones."""
        kp1, desc1 = self.extract_features(source_crop)
        kp2, desc2 = self.extract_features(target_crop)

        if desc1 is None or desc2 is None or len(desc1) < 5 or len(desc2) < 5:
            return None

        # BFMatcher with Hamming distance for binary ORB descriptors
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        raw_matches = bf.knnMatch(desc1, desc2, k=2)

        # Apply Lowe's ratio test to filter ambiguous correspondences
        good_matches: list[cv2.DMatch] = []
        for pair in raw_matches:
            if len(pair) == 2:
                m, n = pair
                if m.distance < self._lowe_ratio * n.distance:
                    good_matches.append(m)

        if len(good_matches) < self._min_inlier_matches:
            return None

        # Verify geometric consistency using RANSAC Homography
        src_pts = np.array([kp1[m.queryIdx].pt for m in good_matches], dtype=np.float32).reshape(
            -1, 1, 2
        )
        dst_pts = np.array([kp2[m.trainIdx].pt for m in good_matches], dtype=np.float32).reshape(
            -1, 1, 2
        )

        try:
            _, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
            inliers = int(np.sum(mask)) if mask is not None else 0
        except Exception:
            inliers = 0

        if inliers >= self._min_inlier_matches:
            similarity = min(1.0, float(inliers / max(len(kp1), len(kp2))))
            similarity = max(0.6, similarity)
            return CopyMoveMatch(
                source_page=source_page,
                source_bbox=source_bbox,
                target_page=target_page,
                target_bbox=target_bbox,
                inlier_match_count=inliers,
                similarity_score=similarity,
                match_type=match_type,
            )

        return None

    def compare_pages(
        self,
        page1_img: np.ndarray | Path | bytes,
        page2_img: np.ndarray | Path | bytes,
        page1_num: int = 1,
        page2_num: int = 2,
    ) -> list[CopyMoveMatch]:
        """Scan two full document pages to find identical copy-pasted patches."""
        img1 = self._load_image(page1_img)
        img2 = self._load_image(page2_img)
        h1, w1 = img1.shape[:2]
        h2, w2 = img2.shape[:2]

        kp1, desc1 = self.extract_features(img1)
        kp2, desc2 = self.extract_features(img2)

        if desc1 is None or desc2 is None or len(desc1) < 10 or len(desc2) < 10:
            return []

        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        raw_matches = bf.knnMatch(desc1, desc2, k=2)

        good_matches: list[cv2.DMatch] = []
        for pair in raw_matches:
            if len(pair) == 2:
                m, n = pair
                if m.distance < self._lowe_ratio * n.distance:
                    good_matches.append(m)

        if len(good_matches) < self._min_inlier_matches:
            return []

        src_pts = np.array([kp1[m.queryIdx].pt for m in good_matches], dtype=np.float32).reshape(
            -1, 1, 2
        )
        dst_pts = np.array([kp2[m.trainIdx].pt for m in good_matches], dtype=np.float32).reshape(
            -1, 1, 2
        )

        try:
            _, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
            inliers = int(np.sum(mask)) if mask is not None else 0
        except Exception:
            inliers = 0

        if inliers >= self._min_inlier_matches:
            # Approximate bounding box of matching keypoints
            inlier_mask = mask.ravel() == 1 if mask is not None else []
            if np.any(inlier_mask):
                inlier_src = src_pts[inlier_mask]
                inlier_dst = dst_pts[inlier_mask]

                x1_min, y1_min = np.min(inlier_src[:, 0, :], axis=0)
                x1_max, y1_max = np.max(inlier_src[:, 0, :], axis=0)
                x2_min, y2_min = np.min(inlier_dst[:, 0, :], axis=0)
                x2_max, y2_max = np.max(inlier_dst[:, 0, :], axis=0)

                bbox1 = NormalizedBoundingBox(
                    ymin=max(0.0, min(1.0, float(y1_min / h1))),
                    xmin=max(0.0, min(1.0, float(x1_min / w1))),
                    ymax=max(0.0, min(1.0, float(y1_max / h1))),
                    xmax=max(0.0, min(1.0, float(x1_max / w1))),
                )
                bbox2 = NormalizedBoundingBox(
                    ymin=max(0.0, min(1.0, float(y2_min / h2))),
                    xmin=max(0.0, min(1.0, float(x2_min / w2))),
                    ymax=max(0.0, min(1.0, float(y2_max / h2))),
                    xmax=max(0.0, min(1.0, float(x2_max / w2))),
                )

                similarity = min(1.0, float(inliers / len(good_matches)))
                return [
                    CopyMoveMatch(
                        source_page=page1_num,
                        source_bbox=bbox1,
                        target_page=page2_num,
                        target_bbox=bbox2,
                        inlier_match_count=inliers,
                        similarity_score=similarity,
                        match_type="CLONED_PATCH",
                    )
                ]

        return []

    def _load_image(self, image_or_path: np.ndarray | Path | bytes) -> np.ndarray:
        """Decode input into OpenCV BGR ndarray."""
        if isinstance(image_or_path, np.ndarray):
            return image_or_path

        if isinstance(image_or_path, Path):
            if not image_or_path.exists():
                raise ValidationError(f"Image not found: {image_or_path}")
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
