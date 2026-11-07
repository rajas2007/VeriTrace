"""ONNX Runtime CPU inference engine for Siamese neural signature verification.

Executes local, quantized neural embeddings on cropped signature patches,
calculating cosine metric distance with zero cloud calls and zero GPU dependency.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger("veritrace.capabilities.forensics.signatures.onnx_engine")

try:
    import onnxruntime as ort  # type: ignore[import-untyped]

    _ONNXRUNTIME_AVAILABLE = True
except (ImportError, Exception):
    ort = None
    _ONNXRUNTIME_AVAILABLE = False

ONNX_AVAILABLE: bool = _ONNXRUNTIME_AVAILABLE


class SiameseOnnxSignatureEngine:
    """Inference engine for Siamese CNN signature comparison models via ONNX Runtime."""

    def __init__(
        self,
        model_path: Path | str | None = None,
        target_size: tuple[int, int] = (128, 128),
    ) -> None:
        self._target_size = target_size
        self._explicit_model_path = Path(model_path) if model_path else None
        self._session: Any = None
        self._input_name: str | None = None
        self._output_name: str | None = None
        self._resolved_model_path: Path | None = None

        self._resolve_and_init_session()

    def _resolve_model_path(self) -> Path | None:
        """Resolve candidate model paths on workstation."""
        if self._explicit_model_path and self._explicit_model_path.is_file():
            return self._explicit_model_path

        # Candidate locations
        appdata_base = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            Path("models/signature_siamese.onnx"),
            Path("packaging/resources/signature_siamese.onnx"),
            Path(appdata_base) / "VeriTrace" / "models" / "signature_siamese.onnx"
            if appdata_base
            else None,
        ]

        for cand in candidates:
            if cand and cand.is_file():
                return cand.resolve()
        return None

    def _resolve_and_init_session(self) -> None:
        """Initialize ONNX Runtime inference session if model and runtime are available."""
        if not _ONNXRUNTIME_AVAILABLE or ort is None:
            return

        model_file = self._resolve_model_path()
        if not model_file:
            return

        try:
            # Configure CPU execution provider with optimized thread count
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 2
            opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

            self._session = ort.InferenceSession(
                str(model_file),
                sess_options=opts,
                providers=["CPUExecutionProvider"],
            )
            self._resolved_model_path = model_file
            self._input_name = self._session.get_inputs()[0].name
            self._output_name = self._session.get_outputs()[0].name
            logger.info("Loaded Siamese ONNX signature model from: %s", model_file)
        except Exception as exc:
            logger.warning("Failed to initialize ONNX session for '%s': %s", model_file, exc)
            self._session = None

    def is_available(self) -> bool:
        """Return True if ONNX Runtime is installed and a valid model is loaded."""
        return self._session is not None and self._input_name is not None

    def get_model_path(self) -> str:
        """Return resolved model file path or status description."""
        if self._resolved_model_path:
            return str(self._resolved_model_path)
        if not _ONNXRUNTIME_AVAILABLE:
            return "onnxruntime_not_installed"
        return "model_file_not_found"

    def preprocess_crop(
        self,
        image_or_path: np.ndarray | Path | bytes,
    ) -> np.ndarray:
        """Preprocess signature image crop into model input tensor [1, 1, 128, 128]."""
        # 1. Decode to grayscale
        gray: np.ndarray
        if isinstance(image_or_path, np.ndarray):
            if len(image_or_path.shape) == 3 and image_or_path.shape[2] == 3:
                gray = cv2.cvtColor(image_or_path, cv2.COLOR_BGR2GRAY)
            else:
                gray = image_or_path.copy()
        elif isinstance(image_or_path, Path):
            if not image_or_path.exists():
                raise FileNotFoundError(f"Signature crop not found: {image_or_path}")
            decoded_p = cv2.imread(str(image_or_path), cv2.IMREAD_GRAYSCALE)
            if decoded_p is None:
                raise ValueError(f"Failed to read image from path: {image_or_path}")
            gray = decoded_p
        elif isinstance(image_or_path, bytes):
            nparr = np.frombuffer(image_or_path, np.uint8)
            decoded_b = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
            if decoded_b is None:
                raise ValueError("Failed to decode image from bytes")
            gray = decoded_b
        else:
            raise TypeError(f"Unsupported image type: {type(image_or_path)}")

        # 2. Resize to model target resolution (128x128)
        resized = cv2.resize(gray, self._target_size, interpolation=cv2.INTER_AREA)

        # 3. Normalize pixel intensities to [0.0, 1.0] and format as NCHW float32
        norm = resized.astype(np.float32) / 255.0
        tensor = np.expand_dims(norm, axis=(0, 1))  # Shape: (1, 1, 128, 128)
        return tensor

    def compute_embedding(
        self,
        image_or_path: np.ndarray | Path | bytes,
    ) -> np.ndarray:
        """Execute local model inference and return normalized L2 feature embedding."""
        if not self.is_available():
            raise RuntimeError(
                f"Siamese ONNX signature engine is unavailable (Status: {self.get_model_path()})."
            )

        tensor = self.preprocess_crop(image_or_path)
        assert self._session is not None and self._input_name is not None
        outputs = self._session.run(None, {self._input_name: tensor})
        embedding = outputs[0][0]  # Shape: (embedding_dim,)

        # L2 normalize embedding vector
        norm_val = float(np.linalg.norm(embedding))
        if norm_val > 1e-6:
            embedding = embedding / norm_val
        return np.asarray(embedding, dtype=np.float32)

    def compute_metric_distance(
        self,
        questioned_crop: np.ndarray | Path | bytes,
        reference_crop_or_embedding: np.ndarray | Path | bytes,
    ) -> float:
        """Compute cosine metric distance in [0.0, 1.0] between questioned signature and reference.

        Distance d = 1.0 - cosine_similarity.
        """
        q_emb = self.compute_embedding(questioned_crop)

        if (
            isinstance(reference_crop_or_embedding, np.ndarray)
            and reference_crop_or_embedding.ndim == 1
        ):
            ref_emb = reference_crop_or_embedding
        else:
            ref_emb = self.compute_embedding(reference_crop_or_embedding)

        # Compute cosine similarity
        cos_sim = float(np.dot(q_emb, ref_emb))
        cos_sim = max(-1.0, min(1.0, cos_sim))

        # Normalized metric distance [0.0, 1.0]
        # (sim=1.0 -> dist=0.0; sim=0.0 -> dist=0.5; sim=-1.0 -> dist=1.0)
        metric_dist = (1.0 - cos_sim) / 2.0
        return float(max(0.0, min(1.0, metric_dist)))
