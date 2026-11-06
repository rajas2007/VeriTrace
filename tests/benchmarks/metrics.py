"""Empirical OCR & Extraction Benchmark Evaluation Metrics.

Implements standard mathematical formulas specified in dev/24_TESTING_AND_DEMO_STRATEGY.md:
- Character Error Rate (CER): (S_c + D_c + I_c) / N_c
- Word Error Rate (WER): (S_w + D_w + I_w) / N_w
- Exact Field Match Rate: sum(pred == gt) / N_fields
- Field Precision, Recall, and F1
- Bounding Box Intersection over Union (IoU) on [ymin, xmin, ymax, xmax]
"""

from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz.distance import Levenshtein


def compute_cer(reference: str, hypothesis: str) -> float:
    """Compute Character Error Rate (CER).

    CER = (Substitutions + Deletions + Insertions) / Total Reference Characters
    Range: [0.0, inf). 0.0 indicates exact character match.
    """
    ref_len = len(reference)
    if ref_len == 0:
        return 0.0 if len(hypothesis) == 0 else 1.0

    edit_dist = Levenshtein.distance(reference, hypothesis)
    return float(edit_dist / ref_len)


def compute_wer(reference: str, hypothesis: str) -> float:
    """Compute Word Error Rate (WER).

    WER = (Substitutions + Deletions + Insertions) / Total Reference Words
    Range: [0.0, inf). 0.0 indicates exact word sequence match.
    """
    ref_words = reference.split()
    hyp_words = hypothesis.split()
    ref_count = len(ref_words)

    if ref_count == 0:
        return 0.0 if len(hyp_words) == 0 else 1.0

    # Word-level Levenshtein distance
    edit_dist = Levenshtein.distance(ref_words, hyp_words)
    return float(edit_dist / ref_count)


def compute_exact_field_match_rate(
    predictions: dict[str, str], ground_truth: dict[str, str]
) -> float:
    """Compute proportion of fields with exact string equality."""
    if not ground_truth:
        return 1.0 if not predictions else 0.0

    matches = sum(
        1
        for k, gt_val in ground_truth.items()
        if k in predictions and predictions[k].strip() == gt_val.strip()
    )
    return float(matches / len(ground_truth))


def compute_field_precision_recall(
    predictions: dict[str, str], ground_truth: dict[str, str]
) -> tuple[float, float, float]:
    """Compute Precision, Recall, and F1 score for extracted key-value fields.

    Returns:
        Tuple of (precision, recall, f1)
    """
    if not predictions and not ground_truth:
        return 1.0, 1.0, 1.0
    if not predictions:
        return 0.0, 0.0, 0.0
    if not ground_truth:
        return 0.0, 0.0, 0.0

    tp = sum(
        1
        for k, gt_val in ground_truth.items()
        if k in predictions and predictions[k].strip() == gt_val.strip()
    )
    fp = sum(
        1
        for k, pred_val in predictions.items()
        if k not in ground_truth or ground_truth[k].strip() != pred_val.strip()
    )
    fn = sum(
        1
        for k, gt_val in ground_truth.items()
        if k not in predictions or predictions[k].strip() != gt_val.strip()
    )

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return float(precision), float(recall), float(f1)


def compute_box_iou(box1: list[float], box2: list[float]) -> float:
    """Compute Intersection over Union (IoU) for normalized boxes [ymin, xmin, ymax, xmax].

    Args:
        box1: [ymin, xmin, ymax, xmax] in [0.0, 1.0]
        box2: [ymin, xmin, ymax, xmax] in [0.0, 1.0]

    Returns:
        IoU score in [0.0, 1.0]
    """
    y1_min, x1_min, y1_max, x1_max = box1
    y2_min, x2_min, y2_max, x2_max = box2

    inter_ymin = max(y1_min, y2_min)
    inter_xmin = max(x1_min, x2_min)
    inter_ymax = min(y1_max, y2_max)
    inter_xmax = min(x1_max, x2_max)

    inter_w = max(0.0, inter_xmax - inter_xmin)
    inter_h = max(0.0, inter_ymax - inter_ymin)
    inter_area = inter_w * inter_h

    area1 = max(0.0, x1_max - x1_min) * max(0.0, y1_max - y1_min)
    area2 = max(0.0, x2_max - x2_min) * max(0.0, y2_max - y2_min)

    union_area = area1 + area2 - inter_area
    if union_area <= 0.0:
        return 1.0 if inter_area == 0.0 and area1 == 0.0 and area2 == 0.0 else 0.0

    return float(inter_area / union_area)


@dataclass(slots=True)
class BenchmarkSampleEvaluation:
    """Quantitative performance evaluation for a single benchmark document."""

    sample_id: str
    category_id: str
    cer: float
    wer: float
    exact_field_match_rate: float
    precision: float
    recall: float
    f1: float
    mean_box_iou: float
    target_iou_met: bool  # Mean IoU >= 0.70
    latency_ms: float
    peak_rss_mb: float
