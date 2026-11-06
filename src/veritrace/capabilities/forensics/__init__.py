"""Visual forensics, Error Level Analysis (ELA), font baseline regression, and evidence cropping."""

from veritrace.capabilities.forensics.analyzer import (
    VisualForensicsAnalyzer,
    VisualForensicsProtocol,
)
from veritrace.capabilities.forensics.baseline import FontBaselineAnalyzer
from veritrace.capabilities.forensics.copy_move import CopyMoveDetector
from veritrace.capabilities.forensics.cropper import EvidenceCropper
from veritrace.capabilities.forensics.ela import ErrorLevelAnalyzer
from veritrace.capabilities.forensics.models import (
    BaselineAnomaly,
    CopyMoveMatch,
    ELAResult,
    ForensicProposal,
)

__all__ = [
    "BaselineAnomaly",
    "CopyMoveMatch",
    "ELAResult",
    "ErrorLevelAnalyzer",
    "EvidenceCropper",
    "FontBaselineAnalyzer",
    "ForensicProposal",
    "VisualForensicsAnalyzer",
    "VisualForensicsProtocol",
    "CopyMoveDetector",
]
