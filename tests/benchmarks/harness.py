"""Empirical OCR & Extraction Benchmark Execution Harness.

Coordinates the evaluation of text extractors across the 30-document
benchmark dataset, recording latency, memory RSS, CER, WER, and field IoU.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any

import psutil

from tests.benchmarks.dataset import BenchmarkDocumentSample
from tests.benchmarks.metrics import (
    BenchmarkSampleEvaluation,
    compute_box_iou,
    compute_cer,
    compute_exact_field_match_rate,
    compute_field_precision_recall,
    compute_wer,
)
from veritrace.capabilities.extraction.pdf_text_extractor import PdfDigitalTextExtractor


@dataclass(slots=True)
class CategoryBenchmarkSummary:
    """Consolidated metrics for an individual operational category."""

    category_id: str
    category_name: str
    sample_count: int
    mean_cer: float
    mean_wer: float
    mean_field_match: float
    mean_precision: float
    mean_recall: float
    mean_f1: float
    mean_box_iou: float
    iou_pass_rate: float  # Percentage of samples with IoU >= 0.70
    mean_latency_ms: float
    p95_latency_ms: float
    peak_rss_mb: float


@dataclass(slots=True)
class BenchmarkReport:
    """Complete multi-dimensional benchmark report."""

    total_samples: int
    overall_mean_cer: float
    overall_mean_wer: float
    overall_field_match: float
    overall_mean_iou: float
    overall_mean_latency_ms: float
    overall_peak_rss_mb: float
    category_summaries: list[CategoryBenchmarkSummary] = field(default_factory=list)
    sample_evaluations: list[BenchmarkSampleEvaluation] = field(default_factory=list)

    def print_summary_table(self) -> str:
        """Format a clean markdown table summarizing benchmark results."""
        header_col = (
            "| Category | Category Name | Samples | Mean CER | Mean WER "
            "| Field Match | Mean IoU | Latency (ms) | Peak RSS (MB) |"
        )
        lines = [
            header_col,
            "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
        ]
        for c in self.category_summaries:
            lines.append(
                f"| **{c.category_id}** | {c.category_name} | {c.sample_count} | "
                f"{c.mean_cer:.3f} | {c.mean_wer:.3f} | {c.mean_field_match * 100:.1f}% | "
                f"{c.mean_box_iou:.3f} | {c.mean_latency_ms:.1f} ms | {c.peak_rss_mb:.1f} MB |"
            )
        lines.append(
            f"| **ALL** | **Overall Aggregate** | {self.total_samples} | "
            f"**{self.overall_mean_cer:.3f}** | **{self.overall_mean_wer:.3f}** | "
            f"**{self.overall_field_match * 100:.1f}%** | **{self.overall_mean_iou:.3f}** | "
            f"**{self.overall_mean_latency_ms:.1f} ms** | **{self.overall_peak_rss_mb:.1f} MB** |"
        )
        return "\n".join(lines)


class OcrBenchmarkHarness:
    """Orchestrates empirical benchmark execution across candidate extractors."""

    def __init__(self, extractor: Any | None = None) -> None:
        self.extractor = extractor or PdfDigitalTextExtractor()
        self.process = psutil.Process(os.getpid())

    def run_benchmark(
        self,
        samples: list[BenchmarkDocumentSample],
    ) -> BenchmarkReport:
        """Execute full benchmark evaluation across provided samples."""
        evaluations: list[BenchmarkSampleEvaluation] = []
        process = self.process

        for sample in samples:
            # Baseline memory
            rss_before = process.memory_info().rss / (1024 * 1024)

            t0 = time.perf_counter()
            extraction = self.extractor.extract(str(sample.file_path))
            t1 = time.perf_counter()

            latency_ms = (t1 - t0) * 1000.0
            rss_after = process.memory_info().rss / (1024 * 1024)
            peak_rss_mb = max(rss_before, rss_after)

            # Extract full text
            extracted_text = " ".join(p.extracted_text for p in extraction.pages)

            # Compute CER and WER
            cer = compute_cer(sample.ground_truth_text, extracted_text)
            wer = compute_wer(sample.ground_truth_text, extracted_text)

            # Predict key-value fields from text
            pred_fields: dict[str, str] = {}
            for k, expected_val in sample.ground_truth_fields.items():
                if expected_val in extracted_text:
                    pred_fields[k] = expected_val

            field_match = compute_exact_field_match_rate(pred_fields, sample.ground_truth_fields)
            prec, rec, f1 = compute_field_precision_recall(pred_fields, sample.ground_truth_fields)

            # Compute box IoU
            ious: list[float] = []
            extracted_boxes = []
            for p in extraction.pages:
                for b in p.blocks:
                    if b.normalized_bbox:
                        extracted_boxes.append(
                            [
                                b.normalized_bbox.ymin,
                                b.normalized_bbox.xmin,
                                b.normalized_bbox.ymax,
                                b.normalized_bbox.xmax,
                            ]
                        )

            for gt_box in sample.ground_truth_boxes.values():
                if extracted_boxes:
                    best_iou = max(compute_box_iou(gt_box, ebox) for ebox in extracted_boxes)
                    ious.append(best_iou)
                else:
                    ious.append(0.0)

            mean_iou = sum(ious) / len(ious) if ious else 1.0
            target_met = mean_iou >= 0.70

            evaluations.append(
                BenchmarkSampleEvaluation(
                    sample_id=sample.sample_id,
                    category_id=sample.category_id,
                    cer=round(cer, 4),
                    wer=round(wer, 4),
                    exact_field_match_rate=round(field_match, 4),
                    precision=round(prec, 4),
                    recall=round(rec, 4),
                    f1=round(f1, 4),
                    mean_box_iou=round(mean_iou, 4),
                    target_iou_met=target_met,
                    latency_ms=round(latency_ms, 2),
                    peak_rss_mb=round(peak_rss_mb, 2),
                )
            )

        return self._aggregate_report(evaluations, samples)

    def _aggregate_report(
        self,
        evaluations: list[BenchmarkSampleEvaluation],
        samples: list[BenchmarkDocumentSample],
    ) -> BenchmarkReport:
        """Group sample metrics by category and compute aggregate report."""
        cat_map: dict[str, str] = {s.category_id: s.category_name for s in samples}
        summaries: list[CategoryBenchmarkSummary] = []

        categories = sorted({e.category_id for e in evaluations})
        for cat_id in categories:
            cat_evals = [e for e in evaluations if e.category_id == cat_id]
            n = len(cat_evals)

            latencies = sorted(e.latency_ms for e in cat_evals)
            p95_idx = int(0.95 * n) if n > 1 else 0

            summaries.append(
                CategoryBenchmarkSummary(
                    category_id=cat_id,
                    category_name=cat_map.get(cat_id, cat_id),
                    sample_count=n,
                    mean_cer=sum(e.cer for e in cat_evals) / n,
                    mean_wer=sum(e.wer for e in cat_evals) / n,
                    mean_field_match=sum(e.exact_field_match_rate for e in cat_evals) / n,
                    mean_precision=sum(e.precision for e in cat_evals) / n,
                    mean_recall=sum(e.recall for e in cat_evals) / n,
                    mean_f1=sum(e.f1 for e in cat_evals) / n,
                    mean_box_iou=sum(e.mean_box_iou for e in cat_evals) / n,
                    iou_pass_rate=sum(1 for e in cat_evals if e.target_iou_met) / n,
                    mean_latency_ms=sum(latencies) / n,
                    p95_latency_ms=latencies[p95_idx],
                    peak_rss_mb=max(e.peak_rss_mb for e in cat_evals),
                )
            )

        total_n = len(evaluations)
        return BenchmarkReport(
            total_samples=total_n,
            overall_mean_cer=sum(e.cer for e in evaluations) / total_n,
            overall_mean_wer=sum(e.wer for e in evaluations) / total_n,
            overall_field_match=sum(e.exact_field_match_rate for e in evaluations) / total_n,
            overall_mean_iou=sum(e.mean_box_iou for e in evaluations) / total_n,
            overall_mean_latency_ms=sum(e.latency_ms for e in evaluations) / total_n,
            overall_peak_rss_mb=max(e.peak_rss_mb for e in evaluations),
            category_summaries=summaries,
            sample_evaluations=evaluations,
        )
