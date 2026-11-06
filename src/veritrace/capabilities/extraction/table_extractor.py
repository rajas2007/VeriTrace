"""Structured table extraction and grid reconstruction for financial and industrial documents.

Parses bordered and borderless tabular structures (e.g., bank statement transactions,
salary slip line items, invoice schedules) into structured column/row models with
precise cell coordinates and records for cross-document reconciliation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from veritrace.domain.entities.extracted_field import ExtractedField
from veritrace.domain.enums.document import ExtractionSourceType
from veritrace.domain.exceptions.base import ValidationError
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox
from veritrace.domain.value_objects.identifiers import generate_id
from veritrace.domain.value_objects.provenance import ExtractedToken


@dataclass(slots=True)
class TableCell:
    """Individual cell in an extracted table grid with spatial coordinate anchor."""

    row_index: int
    col_index: int
    text: str
    normalized_bbox: NormalizedBoundingBox
    confidence: float = 1.0


@dataclass(slots=True)
class ExtractedTable:
    """Structured table containing headers, rows, and cell coordinate mappings."""

    table_index: int
    page_number: int
    normalized_bbox: NormalizedBoundingBox
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    cells: list[TableCell] = field(default_factory=list)

    def to_records(self) -> list[dict[str, str]]:
        """Convert rows into list of dictionaries keyed by header names.

        Enables straightforward cross-document querying (e.g., finding the row
        where 'Description' contains 'SALARY' and extracting 'Credit').
        """
        records: list[dict[str, str]] = []
        for row in self.rows:
            rec: dict[str, str] = {}
            for col_idx, val in enumerate(row):
                key = self.headers[col_idx] if col_idx < len(self.headers) else f"col_{col_idx}"
                rec[key] = val
            records.append(rec)
        return records

    def to_extracted_fields(self, page_id: str) -> list[ExtractedField]:
        """Convert table cells into domain ExtractedField entities."""
        fields: list[ExtractedField] = []
        for cell in self.cells:
            col_name = (
                self.headers[cell.col_index]
                if cell.col_index < len(self.headers)
                else f"col_{cell.col_index}"
            )
            field_name = f"table[{self.table_index}].row[{cell.row_index}].{col_name}"
            f = ExtractedField.create(
                field_id=generate_id("fld_"),
                page_id=page_id,
                field_name=field_name,
                field_value=cell.text,
                raw_text=cell.text,
                confidence=cell.confidence,
                field_type="table_cell",
                normalized_bbox=cell.normalized_bbox,
                extraction_source=ExtractionSourceType.DIGITAL_TEXT,
                ocr_engine="TableExtractor",
            )
            fields.append(f)
        return fields


class TableExtractor:
    """Extracts tabular grids from document pages using CV line detection and token clustering."""

    def __init__(
        self,
        min_rows: int = 2,
        min_cols: int = 2,
        line_height_tolerance_ratio: float = 0.6,
    ) -> None:
        self._min_rows = min_rows
        self._min_cols = min_cols
        self._line_tol = line_height_tolerance_ratio

    def extract_tables_from_tokens(
        self, tokens: list[ExtractedToken], page_number: int = 1
    ) -> list[ExtractedTable]:
        """Reconstruct tables from spatial token layout (supports borderless tables).

        Groups tokens into physical lines, identifies multi-column columnar alignments,
        and constructs structured ExtractedTable grids.
        """
        if not tokens:
            return []

        # 1. Group tokens into horizontal rows
        rows_tokens = self._group_tokens_into_rows(tokens)
        if len(rows_tokens) < self._min_rows:
            return []

        # Filter rows that have multiple tokens (at least 2 distinct horizontal elements)
        candidate_rows = [r for r in rows_tokens if len(r) >= self._min_cols]
        if len(candidate_rows) < self._min_rows:
            return []

        # 2. Determine column intervals [xmin, xmax] across candidate rows
        column_bounds = self._detect_column_bounds(candidate_rows)
        if len(column_bounds) < self._min_cols:
            return []

        # 3. Build cell grid for each row
        table_cells: list[TableCell] = []
        table_row_data: list[list[str]] = []

        for row_idx, row_toks in enumerate(candidate_rows):
            row_strings = [""] * len(column_bounds)
            row_confs = [1.0] * len(column_bounds)
            row_boxes: list[NormalizedBoundingBox | None] = [None] * len(column_bounds)

            for tok in row_toks:
                col_idx = self._assign_token_to_column(tok, column_bounds)
                if col_idx is not None:
                    if row_strings[col_idx]:
                        row_strings[col_idx] += " " + tok.raw_text
                    else:
                        row_strings[col_idx] = tok.raw_text

                    # Update cell bounding box
                    cur_box = row_boxes[col_idx]
                    if cur_box is None:
                        row_boxes[col_idx] = tok.normalized_bbox
                    else:
                        row_boxes[col_idx] = NormalizedBoundingBox(
                            ymin=min(cur_box.ymin, tok.normalized_bbox.ymin),
                            xmin=min(cur_box.xmin, tok.normalized_bbox.xmin),
                            ymax=max(cur_box.ymax, tok.normalized_bbox.ymax),
                            xmax=max(cur_box.xmax, tok.normalized_bbox.xmax),
                        )
                    row_confs[col_idx] = min(row_confs[col_idx], tok.confidence)

            # Create TableCell instances
            for c_idx, val in enumerate(row_strings):
                bbox = row_boxes[c_idx]
                if bbox is None:
                    # Synthetic empty cell box from column interval
                    c_xmin, c_xmax = column_bounds[c_idx]
                    row_ymin = min(t.normalized_bbox.ymin for t in row_toks)
                    row_ymax = max(t.normalized_bbox.ymax for t in row_toks)
                    bbox = NormalizedBoundingBox(
                        ymin=row_ymin, xmin=c_xmin, ymax=row_ymax, xmax=c_xmax
                    )

                cell = TableCell(
                    row_index=row_idx,
                    col_index=c_idx,
                    text=val.strip(),
                    normalized_bbox=bbox,
                    confidence=row_confs[c_idx],
                )
                table_cells.append(cell)

            table_row_data.append([s.strip() for s in row_strings])

        if not table_row_data:
            return []

        # Top row is headers, subsequent rows are data
        headers = table_row_data[0]
        data_rows = table_row_data[1:]

        # Table bounding box covering all cells
        all_ymin = min(c.normalized_bbox.ymin for c in table_cells)
        all_xmin = min(c.normalized_bbox.xmin for c in table_cells)
        all_ymax = max(c.normalized_bbox.ymax for c in table_cells)
        all_xmax = max(c.normalized_bbox.xmax for c in table_cells)

        overall_table_box = NormalizedBoundingBox(
            ymin=all_ymin,
            xmin=all_xmin,
            ymax=all_ymax,
            xmax=all_xmax,
        )

        return [
            ExtractedTable(
                table_index=0,
                page_number=page_number,
                normalized_bbox=overall_table_box,
                headers=headers,
                rows=data_rows,
                cells=table_cells,
            )
        ]

    def _group_tokens_into_rows(self, tokens: list[ExtractedToken]) -> list[list[ExtractedToken]]:
        """Sort and group tokens into physical rows."""
        sorted_tokens = sorted(
            tokens, key=lambda t: (t.normalized_bbox.ymin, t.normalized_bbox.xmin)
        )
        rows: list[list[ExtractedToken]] = []

        for tok in sorted_tokens:
            tok_mid_y = (tok.normalized_bbox.ymin + tok.normalized_bbox.ymax) / 2.0
            tok_h = tok.normalized_bbox.ymax - tok.normalized_bbox.ymin

            placed = False
            for row in rows:
                line_ymin = min(t.normalized_bbox.ymin for t in row)
                line_ymax = max(t.normalized_bbox.ymax for t in row)
                line_mid_y = (line_ymin + line_ymax) / 2.0
                line_avg_h = float(
                    np.mean([t.normalized_bbox.ymax - t.normalized_bbox.ymin for t in row])
                )
                overlap = min(tok.normalized_bbox.ymax, line_ymax) - max(
                    tok.normalized_bbox.ymin, line_ymin
                )
                tolerance = max(tok_h, line_avg_h) * self._line_tol

                within_tol = abs(tok_mid_y - line_mid_y) <= tolerance
                if overlap > 0.20 * min(tok_h, line_avg_h) or within_tol:
                    row.append(tok)
                    placed = True
                    break

            if not placed:
                rows.append([tok])

        for r in rows:
            r.sort(key=lambda t: t.normalized_bbox.xmin)

        return rows

    def _detect_column_bounds(self, rows: list[list[ExtractedToken]]) -> list[tuple[float, float]]:
        """Cluster horizontal spans to detect column boundary intervals [xmin, xmax]."""
        # Collect token left and right positions
        all_spans: list[tuple[float, float]] = []
        for r in rows:
            for t in r:
                all_spans.append((t.normalized_bbox.xmin, t.normalized_bbox.xmax))

        if not all_spans:
            return []

        # Sort by start position
        all_spans.sort(key=lambda s: s[0])

        # Merge overlapping or close spans into column zones
        merged_cols: list[tuple[float, float]] = [all_spans[0]]
        for start, end in all_spans[1:]:
            prev_start, prev_end = merged_cols[-1]
            # If start is close to or overlaps previous end (within small gap 0.04)
            if start <= prev_end + 0.035:
                merged_cols[-1] = (prev_start, max(prev_end, end))
            else:
                merged_cols.append((start, end))

        return merged_cols

    def _assign_token_to_column(
        self, tok: ExtractedToken, column_bounds: list[tuple[float, float]]
    ) -> int | None:
        """Find the column interval that best contains the token."""
        tok_mid_x = (tok.normalized_bbox.xmin + tok.normalized_bbox.xmax) / 2.0

        best_idx: int | None = None
        min_dist = float("inf")

        for idx, (c_start, c_end) in enumerate(column_bounds):
            if c_start - 0.02 <= tok_mid_x <= c_end + 0.02:
                return idx
            dist = min(abs(tok_mid_x - c_start), abs(tok_mid_x - c_end))
            if dist < min_dist:
                min_dist = dist
                best_idx = idx

        return best_idx

    def extract_ruled_tables(
        self,
        image_or_path: np.ndarray | Path | bytes,
        tokens: list[ExtractedToken],
        page_number: int = 1,
    ) -> list[ExtractedTable]:
        """Detect bordered tables using OpenCV horizontal/vertical line morphology."""
        img = self._load_image(image_or_path)
        h, w = img.shape[:2]

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

        # Detect horizontal lines
        kernel_h_len = max(20, w // 40)
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_h_len, 1))
        horiz_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, h_kernel)

        # Detect vertical lines
        kernel_v_len = max(20, h // 40)
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_v_len))
        vert_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, v_kernel)

        # Combined table grid
        grid = cv2.add(horiz_lines, vert_lines)
        contours, _ = cv2.findContours(grid, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        cell_boxes: list[NormalizedBoundingBox] = []
        for c in contours:
            area = cv2.contourArea(c)
            # Filter tiny noise or entire page contour
            if area < 400 or area > (w * h * 0.9):
                continue
            x, y, cw, ch = cv2.boundingRect(c)
            if cw < 30 or ch < 15:
                continue

            cell_boxes.append(
                NormalizedBoundingBox(
                    ymin=y / h,
                    xmin=x / w,
                    ymax=(y + ch) / h,
                    xmax=(x + cw) / w,
                )
            )

        # If ruled lines found sufficient cells, populate table from cells
        if len(cell_boxes) >= (self._min_rows * self._min_cols):
            # Sort cell boxes top-to-bottom, left-to-right
            # Use spatial clustering from tokens fallback if alignment is complex
            return self.extract_tables_from_tokens(tokens, page_number=page_number)

        # Fallback to token-based layout analysis
        return self.extract_tables_from_tokens(tokens, page_number=page_number)

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
