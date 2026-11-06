"""Empirical OCR & Extraction Benchmark Automated Tests.

Tests:
1. Mathematical precision of CER, WER, Exact Field Match, and IoU formulas.
2. Complete coverage of the 7 operational categories across 30 documents.
3. Initial 10-document development smoke-test.
4. Full 30-document multi-category empirical benchmark suite.
"""

from pathlib import Path

import pytest

from tests.benchmarks.dataset import generate_benchmark_dataset
from tests.benchmarks.harness import OcrBenchmarkHarness
from tests.benchmarks.metrics import (
    compute_box_iou,
    compute_cer,
    compute_exact_field_match_rate,
    compute_field_precision_recall,
    compute_wer,
)
from veritrace.capabilities.extraction.pdf_text_extractor import PdfDigitalTextExtractor


def test_benchmark_metrics_math():
    """Verify standard accuracy formulas for CER, WER, Field Matching, and IoU."""
    # 1. CER
    assert compute_cer("ABCD", "ABCD") == 0.0
    # 1 substitution in 4 chars = 0.25
    assert compute_cer("ABCD", "ABED") == 0.25
    # Empty string handling
    assert compute_cer("", "") == 0.0

    # 2. WER
    assert compute_wer("the quick brown fox", "the quick brown fox") == 0.0
    # 1 word substitution in 4 words = 0.25
    assert compute_wer("the quick brown fox", "the fast brown fox") == 0.25

    # 3. Exact Field Match Rate
    gt = {"name": "Priya", "salary": "85000", "pan": "ABCDE1234F"}
    pred_all = {"name": "Priya", "salary": "85000", "pan": "ABCDE1234F"}
    pred_half = {"name": "Priya", "salary": "80000", "pan": "ABCDE1234F"}
    pred_none = {"name": "Rajesh", "salary": "90000", "pan": "XYZ"}

    assert compute_exact_field_match_rate(pred_all, gt) == 1.0
    assert compute_exact_field_match_rate(pred_half, gt) == pytest.approx(2 / 3, abs=0.01)
    assert compute_exact_field_match_rate(pred_none, gt) == 0.0

    # 4. Precision, Recall, F1
    p, r, f1 = compute_field_precision_recall(pred_half, gt)
    assert p == pytest.approx(2 / 3, abs=0.01)
    assert r == pytest.approx(2 / 3, abs=0.01)
    assert f1 == pytest.approx(2 / 3, abs=0.01)

    # 5. Box IoU on [ymin, xmin, ymax, xmax]
    box_a = [0.1, 0.1, 0.5, 0.5]  # Area = 0.4 * 0.4 = 0.16
    box_b = [0.1, 0.1, 0.5, 0.5]  # Identical box
    assert compute_box_iou(box_a, box_b) == 1.0

    box_c = [0.6, 0.6, 0.9, 0.9]  # Disjoint box
    assert compute_box_iou(box_a, box_c) == 0.0

    # Partial overlap: [0.1, 0.1, 0.5, 0.5] and [0.1, 0.3, 0.5, 0.7]
    # Inter: y in [0.1, 0.5], x in [0.3, 0.5] -> 0.4 * 0.2 = 0.08
    # Union: 0.16 + 0.16 - 0.08 = 0.24 -> IoU = 0.08 / 0.24 = 1/3
    box_d = [0.1, 0.3, 0.5, 0.7]
    assert compute_box_iou(box_a, box_d) == pytest.approx(1 / 3, abs=0.01)


def test_dataset_categories_complete(tmp_path: Path):
    """Verify that the benchmark dataset contains exactly 30 documents spanning CAT-01 to CAT-07."""
    dataset_dir = tmp_path / "benchmark_data"
    samples = generate_benchmark_dataset(dataset_dir)

    assert len(samples) == 30

    categories = {s.category_id for s in samples}
    expected_categories = {
        "CAT-01",
        "CAT-02",
        "CAT-03",
        "CAT-04",
        "CAT-05",
        "CAT-06",
        "CAT-07",
    }
    assert categories == expected_categories

    for cat_id in expected_categories:
        cat_samples = [s for s in samples if s.category_id == cat_id]
        assert len(cat_samples) >= 4, f"{cat_id} has fewer than 4 samples"


def test_ocr_benchmark_smoke_test(tmp_path: Path):
    """Execute the mandatory 10-document development smoke-test."""
    dataset_dir = tmp_path / "smoke_data"
    all_samples = generate_benchmark_dataset(dataset_dir)
    smoke_samples = all_samples[:10]  # First 10 documents

    harness = OcrBenchmarkHarness(extractor=PdfDigitalTextExtractor())
    report = harness.run_benchmark(smoke_samples)

    assert report.total_samples == 10
    assert report.overall_mean_latency_ms < 500.0, "Mean latency per page exceeds 500ms"
    assert report.overall_peak_rss_mb > 0.0, "Peak RSS was not tracked"
    assert len(report.sample_evaluations) == 10


def test_ocr_benchmark_full_30_documents(tmp_path: Path):
    """Execute the complete 30-document benchmark suite across CAT-01 to CAT-07."""
    dataset_dir = tmp_path / "full_benchmark_data"
    samples = generate_benchmark_dataset(dataset_dir)

    harness = OcrBenchmarkHarness(extractor=PdfDigitalTextExtractor())
    report = harness.run_benchmark(samples)

    # Assert all 30 documents evaluated
    assert report.total_samples == 30
    assert len(report.category_summaries) == 7

    # Assert clean digital vector PDFs (CAT-01) achieve high extraction fidelity
    cat1_summary = next(c for c in report.category_summaries if c.category_id == "CAT-01")
    assert cat1_summary.mean_cer <= 0.05, f"CAT-01 CER too high: {cat1_summary.mean_cer}"
    assert cat1_summary.mean_field_match >= 0.85, (
        f"CAT-01 field match too low: {cat1_summary.mean_field_match}"
    )

    # Overall field match across 30 documents
    assert report.overall_field_match >= 0.80

    # Print summary table to test stdout
    markdown_table = report.print_summary_table()
    print("\n\n" + markdown_table + "\n")
    assert "CAT-01" in markdown_table
    assert "CAT-07" in markdown_table
