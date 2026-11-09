"""IBM Docling layout and document structure extraction adapter.

Provides optional deep structural understanding, reading order determination,
hierarchical element extraction (headers, paragraphs, tables, footers),
and table grid conversion without requiring Docling as a mandatory dependency.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from veritrace.capabilities.extraction.table_extractor import ExtractedTable, TableCell
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox

logger = logging.getLogger("veritrace.capabilities.extraction.docling_adapter")

# Safe import check for docling
try:
    import docling  # type: ignore[import-not-found,import-untyped]

    _DOCLING_AVAILABLE = True
except (ImportError, Exception):
    docling = None
    _DOCLING_AVAILABLE = False


@dataclass(slots=True)
class DoclingLayoutElement:
    """Individual structural document element with reading order and coordinates."""

    element_id: str
    element_type: str  # e.g., 'header', 'paragraph', 'table', 'footer', 'caption'
    text: str
    reading_order_index: int
    page_number: int
    normalized_bbox: NormalizedBoundingBox | None = None
    confidence: float = 1.0
    parent_section: str | None = None


@dataclass(slots=True)
class DoclingDocumentResult:
    """Structured document analysis result produced by Docling."""

    filename: str
    page_count: int
    elements: list[DoclingLayoutElement] = field(default_factory=list)
    tables: list[ExtractedTable] = field(default_factory=list)
    reading_order_text: str = ""
    is_fallback: bool = False
    warnings: list[str] = field(default_factory=list)


class DoclingLayoutAdapter:
    """Optional adapter for IBM Docling document understanding engine."""

    def __init__(
        self,
        custom_parser: Callable[[Path], Any] | None = None,
        extract_tables: bool = True,
    ) -> None:
        self._custom_parser = custom_parser
        self._extract_tables = extract_tables

    def is_available(self) -> bool:
        """Return True if Docling is installed or a custom parser is provided."""
        if self._custom_parser is not None:
            return True
        return _DOCLING_AVAILABLE and docling is not None

    def parse_document(self, file_path: Path | str) -> DoclingDocumentResult:
        """Parse document structure, reading order, and tables.

        Falls back gracefully when Docling is not installed.
        """
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Document file not found: {path}")

        if not self.is_available():
            return DoclingDocumentResult(
                filename=path.name,
                page_count=0,
                elements=[],
                tables=[],
                reading_order_text="",
                is_fallback=True,
                warnings=[
                    "IBM Docling package is not installed on this host. "
                    "Deep layout and reading-order extraction bypassed; "
                    "standard PyMuPDF vector and table extraction remain active."
                ],
            )

        try:
            if self._custom_parser is not None:
                parsed_data = self._custom_parser(path)
                return self._convert_custom_parsed_data(path.name, parsed_data)

            # Native Docling extraction pipeline
            from docling.document_converter import (
                DocumentConverter,  # type: ignore[import-not-found,import-untyped]
            )

            converter = DocumentConverter()
            result = converter.convert(str(path))
            doc = result.document

            elements: list[DoclingLayoutElement] = []
            tables: list[ExtractedTable] = []
            reading_order_parts: list[str] = []

            # Extract layout elements and reading order
            order_idx = 0
            for item in getattr(doc, "body", []):
                item_type = getattr(item, "label", "paragraph")
                item_text = getattr(item, "text", "").strip()
                if not item_text:
                    continue

                page_num = getattr(item, "page_no", 1)
                bbox = None
                if hasattr(item, "prov") and item.prov and hasattr(item.prov[0], "bbox"):
                    raw_b = item.prov[0].bbox
                    bbox = NormalizedBoundingBox(
                        ymin=max(0.0, min(1.0, float(raw_b.t))),
                        xmin=max(0.0, min(1.0, float(raw_b.l))),
                        ymax=max(0.0, min(1.0, float(raw_b.b))),
                        xmax=max(0.0, min(1.0, float(raw_b.r))),
                    )

                elem = DoclingLayoutElement(
                    element_id=f"docling_elem_{order_idx}",
                    element_type=str(item_type),
                    text=item_text,
                    reading_order_index=order_idx,
                    page_number=int(page_num),
                    normalized_bbox=bbox,
                )
                elements.append(elem)
                reading_order_parts.append(item_text)
                order_idx += 1

            # Extract tables if requested
            if self._extract_tables and hasattr(doc, "tables"):
                for t_idx, tbl in enumerate(doc.tables):
                    tbl_page = getattr(tbl, "page_no", 1)
                    headers: list[str] = []
                    rows: list[list[str]] = []
                    cells: list[TableCell] = []

                    df = tbl.export_to_dataframe()
                    headers = [str(c) for c in df.columns]
                    for r_idx, row in df.iterrows():
                        row_vals = [str(val) for val in row.values]
                        rows.append(row_vals)
                        for c_idx, val_str in enumerate(row_vals):
                            cells.append(
                                TableCell(
                                    row_index=r_idx,
                                    col_index=c_idx,
                                    text=val_str,
                                    normalized_bbox=NormalizedBoundingBox(
                                        ymin=0.0, xmin=0.0, ymax=1.0, xmax=1.0
                                    ),
                                )
                            )

                    extracted_tbl = ExtractedTable(
                        table_index=t_idx,
                        page_number=int(tbl_page),
                        normalized_bbox=NormalizedBoundingBox(
                            ymin=0.0, xmin=0.0, ymax=1.0, xmax=1.0
                        ),
                        headers=headers,
                        rows=rows,
                        cells=cells,
                    )
                    tables.append(extracted_tbl)

            return DoclingDocumentResult(
                filename=path.name,
                page_count=max(1, max((e.page_number for e in elements), default=1)),
                elements=elements,
                tables=tables,
                reading_order_text="\n\n".join(reading_order_parts),
                is_fallback=False,
            )

        except Exception as exc:
            logger.error("Docling document processing error on '%s': %s", path.name, exc)
            return DoclingDocumentResult(
                filename=path.name,
                page_count=0,
                elements=[],
                tables=[],
                reading_order_text="",
                is_fallback=True,
                warnings=[f"Docling parsing error: {exc}"],
            )

    def _convert_custom_parsed_data(
        self, filename: str, data: dict[str, Any]
    ) -> DoclingDocumentResult:
        """Convert dictionary data from custom test parser into DoclingDocumentResult."""
        raw_elements = data.get("elements", [])
        elements: list[DoclingLayoutElement] = []
        reading_order_parts: list[str] = []

        for idx, item in enumerate(raw_elements):
            text = str(item.get("text", "")).strip()
            page_no = int(item.get("page_number", 1))
            elem_type = str(item.get("element_type", "paragraph"))
            bbox_dict = item.get("bbox")
            bbox = None
            if bbox_dict and isinstance(bbox_dict, dict):
                bbox = NormalizedBoundingBox(
                    ymin=float(bbox_dict.get("ymin", 0.0)),
                    xmin=float(bbox_dict.get("xmin", 0.0)),
                    ymax=float(bbox_dict.get("ymax", 1.0)),
                    xmax=float(bbox_dict.get("xmax", 1.0)),
                )

            elem = DoclingLayoutElement(
                element_id=f"docling_elem_{idx}",
                element_type=elem_type,
                text=text,
                reading_order_index=idx,
                page_number=page_no,
                normalized_bbox=bbox,
                confidence=float(item.get("confidence", 1.0)),
            )
            elements.append(elem)
            reading_order_parts.append(text)

        raw_tables = data.get("tables", [])
        tables: list[ExtractedTable] = []
        for t_idx, tbl_data in enumerate(raw_tables):
            headers = [str(h) for h in tbl_data.get("headers", [])]
            rows = tbl_data.get("rows", [])
            cells: list[TableCell] = []
            for r_idx, r in enumerate(rows):
                for c_idx, val in enumerate(r):
                    cells.append(
                        TableCell(
                            row_index=r_idx,
                            col_index=c_idx,
                            text=str(val),
                            normalized_bbox=NormalizedBoundingBox(
                                ymin=0.0, xmin=0.0, ymax=1.0, xmax=1.0
                            ),
                        )
                    )
            tables.append(
                ExtractedTable(
                    table_index=t_idx,
                    page_number=int(tbl_data.get("page_number", 1)),
                    normalized_bbox=NormalizedBoundingBox(ymin=0.0, xmin=0.0, ymax=1.0, xmax=1.0),
                    headers=headers,
                    rows=rows,
                    cells=cells,
                )
            )

        return DoclingDocumentResult(
            filename=filename,
            page_count=max(1, max((e.page_number for e in elements), default=1)),
            elements=elements,
            tables=tables,
            reading_order_text="\n\n".join(reading_order_parts),
            is_fallback=False,
        )
