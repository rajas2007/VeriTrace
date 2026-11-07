"""Signature detection, stroke morphology analysis, crop quality, and reference verification."""

from veritrace.capabilities.forensics.signatures.crop_quality import (
    SignatureCropQualityAssessor,
    SignatureCropQualityResult,
)
from veritrace.capabilities.forensics.signatures.detector import SignatureDetector
from veritrace.capabilities.forensics.signatures.stroke_analyzer import SignatureStrokeAnalyzer
from veritrace.capabilities.forensics.signatures.verifier import (
    SignatureForensicsProtocol,
    SignatureVerifier,
)

__all__ = [
    "SignatureCropQualityAssessor",
    "SignatureCropQualityResult",
    "SignatureDetector",
    "SignatureForensicsProtocol",
    "SignatureStrokeAnalyzer",
    "SignatureVerifier",
]
