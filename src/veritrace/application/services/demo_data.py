"""Application service for generating the 4-document industrial demonstration data.

Generates 4 authentic synthetic forensic documents (PDF + rendered PNG pages)
with exact bounding box coordinates and registers them in the database:
1. PO-2026-IND-001.pdf: Purchase Order (1000 KG SS 316L, Rs. 450,000)
2. DC-98741.pdf: Delivery Challan (800 KG SS 304, Heat #H-8821-A)
3. MTC-H8821.pdf: Mill Test Certificate (SS 304, Heat #H-8821-A)
4. INV-88992.pdf: Commercial Tax Invoice (1000 KG billed, Rs. 450,000 + Rs. 81,000 GST)
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pymupdf

from veritrace.domain.entities.document import Document
from veritrace.domain.entities.document_page import DocumentPage
from veritrace.domain.entities.extracted_field import ExtractedField
from veritrace.domain.entities.investigation import Investigation
from veritrace.domain.enums.audit import EntityType
from veritrace.domain.enums.document import DocumentType
from veritrace.domain.interfaces.unit_of_work import UnitOfWork
from veritrace.domain.value_objects.geometry import (
    NormalizedBoundingBox,
    PageDimensions,
)
from veritrace.domain.value_objects.identifiers import (
    DOC_PREFIX,
    INV_PREFIX,
    PAGE_PREFIX,
    generate_id,
)
from veritrace.infrastructure.storage.document_storage import (
    OriginalDocumentStorage,
)


def _draw_banner(page: Any) -> None:
    """Draw standardized synthetic demonstration alert banner."""
    r = pymupdf.Rect(36, 20, 559, 40)
    page.draw_rect(r, color=(0.85, 0.2, 0.2), fill=(0.99, 0.94, 0.94), width=1)
    page.insert_textbox(
        r,
        "SYNTHETIC DEMONSTRATION DOCUMENT - FOR AUDIT / CORRELATION TESTING ONLY",
        fontsize=8.5,
        fontname="helv",
        color=(0.8, 0.1, 0.1),
        align=pymupdf.TEXT_ALIGN_CENTER,
    )


def _draw_frame(page: Any) -> None:
    """Draw outer document border."""
    page.draw_rect(pymupdf.Rect(26, 14, 569, 828), color=(0.2, 0.3, 0.45), width=1.5)
    page.draw_rect(pymupdf.Rect(30, 18, 565, 824), color=(0.6, 0.7, 0.8), width=0.5)


def generate_po_document() -> tuple[bytes, bytes, dict[str, NormalizedBoundingBox]]:
    """Generate PO-2026-IND-001 PDF, rendered PNG, and normalized bounding boxes."""
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    _draw_frame(page)
    _draw_banner(page)

    # Header
    page.insert_text(
        (36, 68), "PURCHASE ORDER", fontsize=18, fontname="helv", color=(0.08, 0.18, 0.36)
    )
    page.insert_text(
        (36, 88), "Apex Heavy Engineering Ltd", fontsize=11, fontname="helv", color=(0.3, 0.3, 0.4)
    )
    page.insert_text(
        (36, 102),
        "Industrial Procurement & Supply Division | Plant 4, Pune",
        fontsize=8,
        fontname="helv",
        color=(0.5, 0.5, 0.6),
    )
    page.draw_line(
        pymupdf.Point(36, 112), pymupdf.Point(559, 112), color=(0.7, 0.75, 0.82), width=1
    )

    bboxes: dict[str, NormalizedBoundingBox] = {}

    def add_field(key: str, r: pymupdf.Rect) -> None:
        bboxes[key] = NormalizedBoundingBox(
            ymin=round(r.y0 / 842.0, 4),
            xmin=round(r.x0 / 595.0, 4),
            ymax=round(r.y1 / 842.0, 4),
            xmax=round(r.x1 / 595.0, 4),
        )

    # Metadata Grid
    page.insert_text((36, 138), "PO Number: ", fontsize=9.5, fontname="helv", color=(0.3, 0.3, 0.4))
    page.insert_text(
        (105, 138), "PO-2026-IND-001", fontsize=9.5, fontname="helv", color=(0.0, 0.0, 0.0)
    )
    add_field("purchase_order_number", pymupdf.Rect(100, 126, 215, 144))

    page.insert_text(
        (360, 138), "Order Date: ", fontsize=9.5, fontname="helv", color=(0.3, 0.3, 0.4)
    )
    page.insert_text((430, 138), "2026-03-01", fontsize=9.5, fontname="helv", color=(0.0, 0.0, 0.0))
    add_field("order_date", pymupdf.Rect(425, 126, 510, 144))

    page.insert_text((36, 158), "Vendor: ", fontsize=9.5, fontname="helv", color=(0.3, 0.3, 0.4))
    page.insert_text(
        (105, 158),
        "Apex Heavy Engineering Ltd",
        fontsize=9.5,
        fontname="helv",
        color=(0.0, 0.0, 0.0),
    )
    add_field("vendor_name", pymupdf.Rect(100, 146, 270, 164))

    page.insert_text(
        (360, 158), "Order Status: ", fontsize=9.5, fontname="helv", color=(0.3, 0.3, 0.4)
    )
    page.insert_text(
        (430, 158), "Open Procurement Order", fontsize=9.5, fontname="helv", color=(0.1, 0.4, 0.2)
    )

    # Table Header
    r_hdr = pymupdf.Rect(36, 185, 559, 207)
    page.draw_rect(r_hdr, color=(0.6, 0.65, 0.75), fill=(0.91, 0.93, 0.96), width=0.5)
    page.insert_text(
        (44, 200), "Item / Description", fontsize=9, fontname="helv", color=(0.2, 0.25, 0.35)
    )
    page.insert_text(
        (220, 200), "Material Grade", fontsize=9, fontname="helv", color=(0.2, 0.25, 0.35)
    )
    page.insert_text(
        (320, 200), "Ordered Qty", fontsize=9, fontname="helv", color=(0.2, 0.25, 0.35)
    )
    page.insert_text(
        (400, 200), "Unit Rate (INR)", fontsize=9, fontname="helv", color=(0.2, 0.25, 0.35)
    )
    page.insert_text(
        (485, 200), "Line Total (INR)", fontsize=9, fontname="helv", color=(0.2, 0.25, 0.35)
    )

    # Item Row
    r_row = pymupdf.Rect(36, 207, 559, 237)
    page.draw_rect(r_row, color=(0.7, 0.75, 0.85), width=0.5)
    page.insert_text(
        (44, 225), "Stainless Steel Round Bars (Austenitic)", fontsize=9, fontname="helv"
    )

    page.insert_text((220, 225), "SS 316L", fontsize=9.5, fontname="helv", color=(0.0, 0.0, 0.0))
    add_field("material_grade", pymupdf.Rect(215, 212, 280, 232))

    page.insert_text((320, 225), "1000 KG", fontsize=9.5, fontname="helv", color=(0.0, 0.0, 0.0))
    add_field("ordered_quantity", pymupdf.Rect(315, 212, 380, 232))

    page.insert_text((400, 225), "450.00", fontsize=9.5, fontname="helv", color=(0.0, 0.0, 0.0))
    add_field("unit_rate", pymupdf.Rect(395, 212, 455, 232))

    page.insert_text((485, 225), "450,000.00", fontsize=9.5, fontname="helv", color=(0.0, 0.0, 0.0))
    add_field("line_total", pymupdf.Rect(480, 212, 555, 232))

    # Total Box
    r_tot = pymupdf.Rect(360, 260, 559, 310)
    page.draw_rect(r_tot, color=(0.6, 0.65, 0.75), fill=(0.96, 0.97, 0.99), width=0.5)
    page.insert_text((370, 280), "Subtotal: Rs. 450,000.00", fontsize=9, fontname="helv")
    page.insert_text(
        (370, 300),
        "Grand Total: Rs. 450,000.00",
        fontsize=10,
        fontname="helv",
        color=(0.08, 0.18, 0.36),
    )
    add_field("total_amount", pymupdf.Rect(430, 288, 555, 306))

    pdf_bytes = doc.tobytes()
    pix = page.get_pixmap(dpi=150)
    png_bytes = pix.tobytes("png")
    doc.close()
    return pdf_bytes, png_bytes, bboxes


def generate_dc_document() -> tuple[bytes, bytes, dict[str, NormalizedBoundingBox]]:
    """Generate DC-98741 PDF, rendered PNG, and normalized bounding boxes."""
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    _draw_frame(page)
    _draw_banner(page)

    # Header
    page.insert_text(
        (36, 68),
        "DELIVERY CHALLAN & DISPATCH NOTE",
        fontsize=17,
        fontname="helv",
        color=(0.08, 0.18, 0.36),
    )
    page.insert_text(
        (36, 88),
        "Bharat Industrial Steel Corp",
        fontsize=11,
        fontname="helv",
        color=(0.3, 0.3, 0.4),
    )
    page.insert_text(
        (36, 102),
        "Warehouse Logistics Division | Logistics Park Sector 2, Mumbai",
        fontsize=8,
        fontname="helv",
        color=(0.5, 0.5, 0.6),
    )
    page.draw_line(
        pymupdf.Point(36, 112), pymupdf.Point(559, 112), color=(0.7, 0.75, 0.82), width=1
    )

    bboxes: dict[str, NormalizedBoundingBox] = {}

    def add_field(key: str, r: pymupdf.Rect) -> None:
        bboxes[key] = NormalizedBoundingBox(
            ymin=round(r.y0 / 842.0, 4),
            xmin=round(r.x0 / 595.0, 4),
            ymax=round(r.y1 / 842.0, 4),
            xmax=round(r.x1 / 595.0, 4),
        )

    # Metadata Grid
    page.insert_text(
        (36, 138), "Challan Number: ", fontsize=9.5, fontname="helv", color=(0.3, 0.3, 0.4)
    )
    page.insert_text((120, 138), "DC-98741", fontsize=9.5, fontname="helv", color=(0.0, 0.0, 0.0))
    add_field("challan_number", pymupdf.Rect(115, 126, 200, 144))

    page.insert_text(
        (360, 138), "Delivery Date: ", fontsize=9.5, fontname="helv", color=(0.3, 0.3, 0.4)
    )
    page.insert_text((435, 138), "2026-03-05", fontsize=9.5, fontname="helv", color=(0.0, 0.0, 0.0))
    add_field("delivery_date", pymupdf.Rect(430, 126, 515, 144))

    page.insert_text(
        (36, 158), "Cited PO Ref: ", fontsize=9.5, fontname="helv", color=(0.3, 0.3, 0.4)
    )
    page.insert_text(
        (120, 158), "PO-2026-IND-001", fontsize=9.5, fontname="helv", color=(0.0, 0.0, 0.0)
    )
    add_field("purchase_order_reference", pymupdf.Rect(115, 146, 220, 164))

    page.insert_text(
        (360, 158), "Consignee: ", fontsize=9.5, fontname="helv", color=(0.3, 0.3, 0.4)
    )
    page.insert_text((435, 158), "Apex Heavy Engineering", fontsize=9.5, fontname="helv")

    # Table Header
    r_hdr = pymupdf.Rect(36, 185, 559, 207)
    page.draw_rect(r_hdr, color=(0.6, 0.65, 0.75), fill=(0.91, 0.93, 0.96), width=0.5)
    page.insert_text(
        (44, 200), "Item / Description", fontsize=9, fontname="helv", color=(0.2, 0.25, 0.35)
    )
    page.insert_text(
        (210, 200), "Heat / Batch No", fontsize=9, fontname="helv", color=(0.2, 0.25, 0.35)
    )
    page.insert_text(
        (330, 200), "Material Grade", fontsize=9, fontname="helv", color=(0.2, 0.25, 0.35)
    )
    page.insert_text(
        (440, 200), "Dispatched Qty", fontsize=9, fontname="helv", color=(0.2, 0.25, 0.35)
    )

    # Item Row
    r_row = pymupdf.Rect(36, 207, 559, 237)
    page.draw_rect(r_row, color=(0.7, 0.75, 0.85), width=0.5)
    page.insert_text((44, 225), "Stainless Steel Round Bars", fontsize=9, fontname="helv")

    page.insert_text((210, 225), "H-8821-A", fontsize=9.5, fontname="helv", color=(0.0, 0.0, 0.0))
    add_field("batch_number", pymupdf.Rect(205, 212, 280, 232))

    page.insert_text((330, 225), "SS 304", fontsize=9.5, fontname="helv", color=(0.7, 0.1, 0.1))
    add_field("material_grade", pymupdf.Rect(325, 212, 395, 232))

    page.insert_text((440, 225), "800 KG", fontsize=9.5, fontname="helv", color=(0.0, 0.0, 0.0))
    add_field("delivered_quantity", pymupdf.Rect(435, 212, 510, 232))

    # Notes
    page.insert_text(
        (36, 260),
        "Dispatch Remarks: Partial delivery of 800 KG against PO-2026-IND-001 (1000 KG).",
        fontsize=8.5,
        fontname="helv",
        color=(0.4, 0.4, 0.5),
    )

    pdf_bytes = doc.tobytes()
    pix = page.get_pixmap(dpi=150)
    png_bytes = pix.tobytes("png")
    doc.close()
    return pdf_bytes, png_bytes, bboxes


def generate_mtc_document() -> tuple[bytes, bytes, dict[str, NormalizedBoundingBox]]:
    """Generate MTC-H8821 PDF, rendered PNG, and normalized bounding boxes."""
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    _draw_frame(page)
    _draw_banner(page)

    # Header
    page.insert_text(
        (36, 68),
        "MILL TEST CERTIFICATE (EN 10204 3.1)",
        fontsize=16,
        fontname="helv",
        color=(0.08, 0.18, 0.36),
    )
    page.insert_text(
        (36, 88),
        "Apex Metallurgical Laboratories & Casting Works",
        fontsize=11,
        fontname="helv",
        color=(0.3, 0.3, 0.4),
    )
    page.insert_text(
        (36, 102),
        "Accredited Testing Laboratory ISO/IEC 17025 | Certificate Division",
        fontsize=8,
        fontname="helv",
        color=(0.5, 0.5, 0.6),
    )
    page.draw_line(
        pymupdf.Point(36, 112), pymupdf.Point(559, 112), color=(0.7, 0.75, 0.82), width=1
    )

    bboxes: dict[str, NormalizedBoundingBox] = {}

    def add_field(key: str, r: pymupdf.Rect) -> None:
        bboxes[key] = NormalizedBoundingBox(
            ymin=round(r.y0 / 842.0, 4),
            xmin=round(r.x0 / 595.0, 4),
            ymax=round(r.y1 / 842.0, 4),
            xmax=round(r.x1 / 595.0, 4),
        )

    # Metadata Grid
    page.insert_text(
        (36, 138), "Certificate No: ", fontsize=9.5, fontname="helv", color=(0.3, 0.3, 0.4)
    )
    page.insert_text((120, 138), "MTC-H8821", fontsize=9.5, fontname="helv", color=(0.0, 0.0, 0.0))
    add_field("certificate_number", pymupdf.Rect(115, 126, 210, 144))

    page.insert_text(
        (360, 138), "Inspection Date: ", fontsize=9.5, fontname="helv", color=(0.3, 0.3, 0.4)
    )
    page.insert_text((445, 138), "2026-03-04", fontsize=9.5, fontname="helv", color=(0.0, 0.0, 0.0))
    add_field("inspection_date", pymupdf.Rect(440, 126, 525, 144))

    page.insert_text(
        (36, 158), "Heat / Melt No: ", fontsize=9.5, fontname="helv", color=(0.3, 0.3, 0.4)
    )
    page.insert_text((120, 158), "H-8821-A", fontsize=9.5, fontname="helv", color=(0.0, 0.0, 0.0))
    add_field("heat_number", pymupdf.Rect(115, 146, 200, 164))

    page.insert_text(
        (360, 158), "Certified Grade: ", fontsize=9.5, fontname="helv", color=(0.3, 0.3, 0.4)
    )
    page.insert_text((445, 158), "SS 304", fontsize=9.5, fontname="helv", color=(0.7, 0.1, 0.1))
    add_field("material_grade", pymupdf.Rect(440, 146, 500, 164))

    # Chemical Analysis Table
    r_hdr = pymupdf.Rect(36, 185, 559, 207)
    page.draw_rect(r_hdr, color=(0.6, 0.65, 0.75), fill=(0.91, 0.93, 0.96), width=0.5)
    page.insert_text((44, 200), "Carbon (C%)", fontsize=8.5, fontname="helv")
    page.insert_text((130, 200), "Manganese (Mn%)", fontsize=8.5, fontname="helv")
    page.insert_text((230, 200), "Silicon (Si%)", fontsize=8.5, fontname="helv")
    page.insert_text((320, 200), "Chromium (Cr%)", fontsize=8.5, fontname="helv")
    page.insert_text((410, 200), "Nickel (Ni%)", fontsize=8.5, fontname="helv")
    page.insert_text((495, 200), "Moly (Mo%)", fontsize=8.5, fontname="helv")

    r_row = pymupdf.Rect(36, 207, 559, 237)
    page.draw_rect(r_row, color=(0.7, 0.75, 0.85), width=0.5)
    page.insert_text((44, 225), "0.055%", fontsize=9, fontname="helv")
    page.insert_text((130, 225), "1.450%", fontsize=9, fontname="helv")
    page.insert_text((230, 225), "0.480%", fontsize=9, fontname="helv")
    page.insert_text((320, 225), "18.25%", fontsize=9, fontname="helv")
    page.insert_text((410, 225), "8.150%", fontsize=9, fontname="helv")
    page.insert_text((495, 225), "0.020%", fontsize=9, fontname="helv", color=(0.7, 0.1, 0.1))

    page.insert_text(
        (36, 260),
        (
            "Metallurgical Finding: Material conforms to ASTM A276 Grade SS 304 "
            "(Mo < 0.05%, not SS 316L)."
        ),
        fontsize=8.5,
        fontname="helv",
        color=(0.3, 0.3, 0.4),
    )

    pdf_bytes = doc.tobytes()
    pix = page.get_pixmap(dpi=150)
    png_bytes = pix.tobytes("png")
    doc.close()
    return pdf_bytes, png_bytes, bboxes


def generate_invoice_document() -> tuple[bytes, bytes, dict[str, NormalizedBoundingBox]]:
    """Generate INV-88992 PDF, rendered PNG, and normalized bounding boxes."""
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    _draw_frame(page)
    _draw_banner(page)

    # Header
    page.insert_text(
        (36, 68),
        "TAX INVOICE / COMMERCIAL INVOICE",
        fontsize=17,
        fontname="helv",
        color=(0.08, 0.18, 0.36),
    )
    page.insert_text(
        (36, 88),
        "Bharat Industrial Steel Corp",
        fontsize=11,
        fontname="helv",
        color=(0.3, 0.3, 0.4),
    )
    page.insert_text(
        (36, 102),
        "GSTIN: 27AABCB1234F1Z8 | Corporate Accounts Division, Mumbai",
        fontsize=8,
        fontname="helv",
        color=(0.5, 0.5, 0.6),
    )
    page.draw_line(
        pymupdf.Point(36, 112), pymupdf.Point(559, 112), color=(0.7, 0.75, 0.82), width=1
    )

    bboxes: dict[str, NormalizedBoundingBox] = {}

    def add_field(key: str, r: pymupdf.Rect) -> None:
        bboxes[key] = NormalizedBoundingBox(
            ymin=round(r.y0 / 842.0, 4),
            xmin=round(r.x0 / 595.0, 4),
            ymax=round(r.y1 / 842.0, 4),
            xmax=round(r.x1 / 595.0, 4),
        )

    # Metadata Grid
    page.insert_text(
        (36, 138), "Invoice No: ", fontsize=9.5, fontname="helv", color=(0.3, 0.3, 0.4)
    )
    page.insert_text((115, 138), "INV-88992", fontsize=9.5, fontname="helv", color=(0.0, 0.0, 0.0))
    add_field("invoice_number", pymupdf.Rect(110, 126, 195, 144))

    page.insert_text(
        (360, 138), "Invoice Date: ", fontsize=9.5, fontname="helv", color=(0.3, 0.3, 0.4)
    )
    page.insert_text((435, 138), "2026-03-06", fontsize=9.5, fontname="helv", color=(0.0, 0.0, 0.0))
    add_field("invoice_date", pymupdf.Rect(430, 126, 515, 144))

    page.insert_text(
        (36, 158), "Cited PO Ref: ", fontsize=9.5, fontname="helv", color=(0.3, 0.3, 0.4)
    )
    page.insert_text(
        (115, 158), "PO-2026-IND-001", fontsize=9.5, fontname="helv", color=(0.0, 0.0, 0.0)
    )
    add_field("purchase_order_reference", pymupdf.Rect(110, 146, 215, 164))

    page.insert_text(
        (360, 158), "Cited Challan: ", fontsize=9.5, fontname="helv", color=(0.3, 0.3, 0.4)
    )
    page.insert_text((435, 158), "DC-98741", fontsize=9.5, fontname="helv", color=(0.0, 0.0, 0.0))
    add_field("challan_reference", pymupdf.Rect(430, 146, 510, 164))

    # Table Header
    r_hdr = pymupdf.Rect(36, 185, 559, 207)
    page.draw_rect(r_hdr, color=(0.6, 0.65, 0.75), fill=(0.91, 0.93, 0.96), width=0.5)
    page.insert_text(
        (44, 200), "Item / Description", fontsize=9, fontname="helv", color=(0.2, 0.25, 0.35)
    )
    page.insert_text(
        (220, 200), "Billed Grade", fontsize=9, fontname="helv", color=(0.2, 0.25, 0.35)
    )
    page.insert_text((315, 200), "Billed Qty", fontsize=9, fontname="helv", color=(0.2, 0.25, 0.35))
    page.insert_text((400, 200), "Rate (INR)", fontsize=9, fontname="helv", color=(0.2, 0.25, 0.35))
    page.insert_text(
        (485, 200), "Line Total (INR)", fontsize=9, fontname="helv", color=(0.2, 0.25, 0.35)
    )

    # Item Row
    r_row = pymupdf.Rect(36, 207, 559, 237)
    page.draw_rect(r_row, color=(0.7, 0.75, 0.85), width=0.5)
    page.insert_text((44, 225), "Stainless Steel Round Bars", fontsize=9, fontname="helv")

    page.insert_text((220, 225), "SS 316L", fontsize=9.5, fontname="helv", color=(0.0, 0.0, 0.0))
    add_field("material_grade", pymupdf.Rect(215, 212, 280, 232))

    page.insert_text((315, 225), "1000 KG", fontsize=9.5, fontname="helv", color=(0.0, 0.0, 0.0))
    add_field("billed_quantity", pymupdf.Rect(310, 212, 380, 232))

    page.insert_text((400, 225), "450.00", fontsize=9.5, fontname="helv", color=(0.0, 0.0, 0.0))
    add_field("unit_rate", pymupdf.Rect(395, 212, 455, 232))

    page.insert_text((485, 225), "450,000.00", fontsize=9.5, fontname="helv", color=(0.0, 0.0, 0.0))
    add_field("line_total", pymupdf.Rect(480, 212, 555, 232))

    # Financial Breakdown Table
    r_tot = pymupdf.Rect(310, 260, 559, 360)
    page.draw_rect(r_tot, color=(0.6, 0.65, 0.75), fill=(0.96, 0.97, 0.99), width=0.5)

    page.insert_text((320, 280), "Taxable Subtotal:", fontsize=9, fontname="helv")
    page.insert_text((465, 280), "Rs. 450,000.00", fontsize=9, fontname="helv")
    add_field("subtotal", pymupdf.Rect(460, 268, 550, 286))

    page.insert_text((320, 302), "GST @ 18%:", fontsize=9, fontname="helv")
    page.insert_text((465, 302), "Rs.   81,000.00", fontsize=9, fontname="helv")
    add_field("tax_amount", pymupdf.Rect(460, 290, 550, 308))

    page.insert_text((320, 324), "Freight & Handling:", fontsize=9, fontname="helv")
    page.insert_text((465, 324), "Rs.    5,000.00", fontsize=9, fontname="helv")
    add_field("freight", pymupdf.Rect(460, 312, 550, 330))

    page.draw_line(
        pymupdf.Point(320, 332), pymupdf.Point(550, 332), color=(0.7, 0.7, 0.8), width=0.5
    )

    page.insert_text(
        (320, 348), "Invoice Grand Total:", fontsize=10, fontname="helv", color=(0.08, 0.18, 0.36)
    )
    page.insert_text(
        (465, 348), "Rs. 536,000.00", fontsize=10, fontname="helv", color=(0.08, 0.18, 0.36)
    )
    add_field("grand_total", pymupdf.Rect(460, 336, 555, 356))
    add_field("total_amount", pymupdf.Rect(460, 336, 555, 356))

    pdf_bytes = doc.tobytes()
    pix = page.get_pixmap(dpi=150)
    png_bytes = pix.tobytes("png")
    doc.close()
    return pdf_bytes, png_bytes, bboxes


def seed_industrial_demo(
    uow_factory: Any,
    organization_id: str = "org_11111111111111111111111111111111",
    storage: OriginalDocumentStorage | None = None,
) -> str:
    """Create or retrieve the industrial demo investigation and return its ID."""
    uow: UnitOfWork = uow_factory() if callable(uow_factory) else uow_factory
    storage_inst = storage or OriginalDocumentStorage(allow_workspace_storage=True)

    ref_code = "INV-2026-IND-001"

    with uow:
        # Check if already exists and files exist
        existing = uow.investigations.get_by_reference_code(ref_code, organization_id)
        if existing is not None:
            docs = uow.documents.list_by_investigation(existing.id, organization_id)
            pages = []
            for d in docs:
                pages.extend(uow.documents.list_pages(d.id, organization_id))
            all_exist = len(pages) == 4 and all(
                p.image_storage_path and Path(p.image_storage_path).exists() for p in pages
            )
            if all_exist:
                return existing.id

        inv_id = existing.id if existing is not None else generate_id(INV_PREFIX)
        if existing is None:
            inv = Investigation.create(
                title="Industrial Heavy Machinery - Raw Material Procurement Audit",
                reference_code=ref_code,
                organization_id=organization_id,
                investigation_id=inv_id,
            )
            uow.investigations.add(inv)

        dim = PageDimensions(width_pixels=1240, height_pixels=1755, dpi=150)

        # -------------------------------------------------------------
        # 1. Purchase Order (PO-2026-IND-001.pdf)
        # -------------------------------------------------------------
        po_pdf, po_png, po_boxes = generate_po_document()
        po_doc_id = generate_id(DOC_PREFIX)
        po_storage_path = storage_inst.store_original(
            organization_id, inv_id, po_doc_id, "PO-2026-IND-001.pdf", po_pdf
        )
        po_img_path = storage_inst.store_page_image(organization_id, inv_id, po_doc_id, 1, po_png)
        po_doc = Document.create(
            investigation_id=inv_id,
            original_filename="PO-2026-IND-001.pdf",
            file_hash_sha256=hashlib.sha256(po_pdf).hexdigest(),
            mime_type="application/pdf",
            document_type=DocumentType.PURCHASE_ORDER,
            file_size_bytes=len(po_pdf),
            storage_path=po_storage_path,
            document_id=po_doc_id,
        )
        uow.documents.add(po_doc, organization_id)

        po_page_id = generate_id(PAGE_PREFIX)
        po_page = DocumentPage.create(
            document_id=po_doc.id,
            page_number=1,
            dimensions=dim,
            image_storage_path=po_img_path,
            page_id=po_page_id,
        )
        uow.documents.add_page(po_page, organization_id)

        po_fields = [
            ExtractedField.create(
                page_id=po_page.id,
                field_name="purchase_order_number",
                field_value="PO-2026-IND-001",
                raw_text="PO-2026-IND-001",
                confidence=0.99,
                field_type=EntityType.DOCUMENT_REFERENCE.value,
                normalized_bbox=po_boxes["purchase_order_number"],
            ),
            ExtractedField.create(
                page_id=po_page.id,
                field_name="vendor_name",
                field_value="Apex Heavy Engineering Ltd",
                raw_text="Apex Heavy Engineering Ltd",
                confidence=0.98,
                field_type=EntityType.ORGANIZATION_NAME.value,
                normalized_bbox=po_boxes["vendor_name"],
            ),
            ExtractedField.create(
                page_id=po_page.id,
                field_name="order_date",
                field_value="2026-03-01",
                raw_text="2026-03-01",
                confidence=0.99,
                field_type=EntityType.DATE_OF_ISSUE.value,
                normalized_bbox=po_boxes["order_date"],
            ),
            ExtractedField.create(
                page_id=po_page.id,
                field_name="material_grade",
                field_value="SS 316L",
                raw_text="SS 316L",
                confidence=0.98,
                field_type=EntityType.MATERIAL_GRADE.value,
                normalized_bbox=po_boxes["material_grade"],
            ),
            ExtractedField.create(
                page_id=po_page.id,
                field_name="ordered_quantity",
                field_value="1000 KG",
                raw_text="1000 KG",
                confidence=0.99,
                field_type=EntityType.QUANTITY.value,
                normalized_bbox=po_boxes["ordered_quantity"],
            ),
            ExtractedField.create(
                page_id=po_page.id,
                field_name="unit_rate",
                field_value="450.00",
                raw_text="450.00",
                confidence=0.99,
                field_type=EntityType.FINANCIAL_TOTAL.value,
                normalized_bbox=po_boxes["unit_rate"],
            ),
            ExtractedField.create(
                page_id=po_page.id,
                field_name="line_total",
                field_value="450000.00",
                raw_text="450000.00",
                confidence=0.99,
                field_type=EntityType.FINANCIAL_TOTAL.value,
                normalized_bbox=po_boxes["line_total"],
            ),
            ExtractedField.create(
                page_id=po_page.id,
                field_name="total_amount",
                field_value="450000.00",
                raw_text="450000.00",
                confidence=0.99,
                field_type=EntityType.FINANCIAL_TOTAL.value,
                normalized_bbox=po_boxes["total_amount"],
            ),
        ]
        for f in po_fields:
            uow.documents.add_extracted_field(f, organization_id)

        # -------------------------------------------------------------
        # 2. Delivery Challan (DC-98741.pdf)
        # -------------------------------------------------------------
        dc_pdf, dc_png, dc_boxes = generate_dc_document()
        dc_doc_id = generate_id(DOC_PREFIX)
        dc_storage_path = storage_inst.store_original(
            organization_id, inv_id, dc_doc_id, "DC-98741.pdf", dc_pdf
        )
        dc_img_path = storage_inst.store_page_image(organization_id, inv_id, dc_doc_id, 1, dc_png)
        dc_doc = Document.create(
            investigation_id=inv_id,
            original_filename="DC-98741.pdf",
            file_hash_sha256=hashlib.sha256(dc_pdf).hexdigest(),
            mime_type="application/pdf",
            document_type=DocumentType.DELIVERY_CHALLAN,
            file_size_bytes=len(dc_pdf),
            storage_path=dc_storage_path,
            document_id=dc_doc_id,
        )
        uow.documents.add(dc_doc, organization_id)

        dc_page_id = generate_id(PAGE_PREFIX)
        dc_page = DocumentPage.create(
            document_id=dc_doc.id,
            page_number=1,
            dimensions=dim,
            image_storage_path=dc_img_path,
            page_id=dc_page_id,
        )
        uow.documents.add_page(dc_page, organization_id)

        dc_fields = [
            ExtractedField.create(
                page_id=dc_page.id,
                field_name="challan_number",
                field_value="DC-98741",
                raw_text="DC-98741",
                confidence=0.99,
                field_type=EntityType.DOCUMENT_REFERENCE.value,
                normalized_bbox=dc_boxes["challan_number"],
            ),
            ExtractedField.create(
                page_id=dc_page.id,
                field_name="purchase_order_reference",
                field_value="PO-2026-IND-001",
                raw_text="PO-2026-IND-001",
                confidence=0.99,
                field_type=EntityType.DOCUMENT_REFERENCE.value,
                normalized_bbox=dc_boxes["purchase_order_reference"],
            ),
            ExtractedField.create(
                page_id=dc_page.id,
                field_name="delivery_date",
                field_value="2026-03-05",
                raw_text="2026-03-05",
                confidence=0.99,
                field_type=EntityType.DATE_OF_ISSUE.value,
                normalized_bbox=dc_boxes["delivery_date"],
            ),
            ExtractedField.create(
                page_id=dc_page.id,
                field_name="material_grade",
                field_value="SS 304",  # CONTRADICTION vs PO SS 316L
                raw_text="SS 304",
                confidence=0.97,
                field_type=EntityType.MATERIAL_GRADE.value,
                normalized_bbox=dc_boxes["material_grade"],
            ),
            ExtractedField.create(
                page_id=dc_page.id,
                field_name="delivered_quantity",
                field_value="800 KG",  # PARTIAL DELIVERY (800 vs 1000)
                raw_text="800 KG",
                confidence=0.99,
                field_type=EntityType.QUANTITY.value,
                normalized_bbox=dc_boxes["delivered_quantity"],
            ),
            ExtractedField.create(
                page_id=dc_page.id,
                field_name="batch_number",
                field_value="H-8821-A",
                raw_text="H-8821-A",
                confidence=0.98,
                field_type=EntityType.BATCH_NUMBER.value,
                normalized_bbox=dc_boxes["batch_number"],
            ),
        ]
        for f in dc_fields:
            uow.documents.add_extracted_field(f, organization_id)

        # -------------------------------------------------------------
        # 3. Mill Test Certificate (MTC-H8821.pdf)
        # -------------------------------------------------------------
        mtc_pdf, mtc_png, mtc_boxes = generate_mtc_document()
        mtc_doc_id = generate_id(DOC_PREFIX)
        mtc_storage_path = storage_inst.store_original(
            organization_id, inv_id, mtc_doc_id, "MTC-H8821.pdf", mtc_pdf
        )
        mtc_img_path = storage_inst.store_page_image(
            organization_id, inv_id, mtc_doc_id, 1, mtc_png
        )
        mtc_doc = Document.create(
            investigation_id=inv_id,
            original_filename="MTC-H8821.pdf",
            file_hash_sha256=hashlib.sha256(mtc_pdf).hexdigest(),
            mime_type="application/pdf",
            document_type=DocumentType.MILL_TEST_CERT,
            file_size_bytes=len(mtc_pdf),
            storage_path=mtc_storage_path,
            document_id=mtc_doc_id,
        )
        uow.documents.add(mtc_doc, organization_id)

        mtc_page_id = generate_id(PAGE_PREFIX)
        mtc_page = DocumentPage.create(
            document_id=mtc_doc.id,
            page_number=1,
            dimensions=dim,
            image_storage_path=mtc_img_path,
            page_id=mtc_page_id,
        )
        uow.documents.add_page(mtc_page, organization_id)

        mtc_fields = [
            ExtractedField.create(
                page_id=mtc_page.id,
                field_name="certificate_number",
                field_value="MTC-H8821",
                raw_text="MTC-H8821",
                confidence=0.99,
                field_type=EntityType.DOCUMENT_REFERENCE.value,
                normalized_bbox=mtc_boxes["certificate_number"],
            ),
            ExtractedField.create(
                page_id=mtc_page.id,
                field_name="heat_number",
                field_value="H-8821-A",
                raw_text="H-8821-A",
                confidence=0.99,
                field_type=EntityType.BATCH_NUMBER.value,
                normalized_bbox=mtc_boxes["heat_number"],
            ),
            ExtractedField.create(
                page_id=mtc_page.id,
                field_name="inspection_date",
                field_value="2026-03-04",
                raw_text="2026-03-04",
                confidence=0.98,
                field_type=EntityType.DATE_OF_ISSUE.value,
                normalized_bbox=mtc_boxes["inspection_date"],
            ),
            ExtractedField.create(
                page_id=mtc_page.id,
                field_name="material_grade",
                field_value="SS 304",  # CORROBORATES DC SS 304, CONTRADICTS PO SS 316L
                raw_text="SS 304",
                confidence=0.99,
                field_type=EntityType.MATERIAL_GRADE.value,
                normalized_bbox=mtc_boxes["material_grade"],
            ),
        ]
        for f in mtc_fields:
            uow.documents.add_extracted_field(f, organization_id)

        # -------------------------------------------------------------
        # 4. Commercial Invoice (INV-88992.pdf)
        # -------------------------------------------------------------
        inv_pdf, inv_png, inv_boxes = generate_invoice_document()
        inv_doc_id = generate_id(DOC_PREFIX)
        inv_storage_path = storage_inst.store_original(
            organization_id, inv_id, inv_doc_id, "INV-88992.pdf", inv_pdf
        )
        inv_img_path = storage_inst.store_page_image(
            organization_id, inv_id, inv_doc_id, 1, inv_png
        )
        inv_doc = Document.create(
            investigation_id=inv_id,
            original_filename="INV-88992.pdf",
            file_hash_sha256=hashlib.sha256(inv_pdf).hexdigest(),
            mime_type="application/pdf",
            document_type=DocumentType.COMMERCIAL_INVOICE,
            file_size_bytes=len(inv_pdf),
            storage_path=inv_storage_path,
            document_id=inv_doc_id,
        )
        uow.documents.add(inv_doc, organization_id)

        inv_page_id = generate_id(PAGE_PREFIX)
        inv_page = DocumentPage.create(
            document_id=inv_doc.id,
            page_number=1,
            dimensions=dim,
            image_storage_path=inv_img_path,
            page_id=inv_page_id,
        )
        uow.documents.add_page(inv_page, organization_id)

        inv_fields = [
            ExtractedField.create(
                page_id=inv_page.id,
                field_name="invoice_number",
                field_value="INV-88992",
                raw_text="INV-88992",
                confidence=0.99,
                field_type=EntityType.DOCUMENT_REFERENCE.value,
                normalized_bbox=inv_boxes["invoice_number"],
            ),
            ExtractedField.create(
                page_id=inv_page.id,
                field_name="purchase_order_reference",
                field_value="PO-2026-IND-001",
                raw_text="PO-2026-IND-001",
                confidence=0.99,
                field_type=EntityType.DOCUMENT_REFERENCE.value,
                normalized_bbox=inv_boxes["purchase_order_reference"],
            ),
            ExtractedField.create(
                page_id=inv_page.id,
                field_name="challan_reference",
                field_value="DC-98741",
                raw_text="DC-98741",
                confidence=0.98,
                field_type=EntityType.DOCUMENT_REFERENCE.value,
                normalized_bbox=inv_boxes["challan_reference"],
            ),
            ExtractedField.create(
                page_id=inv_page.id,
                field_name="invoice_date",
                field_value="2026-03-06",
                raw_text="2026-03-06",
                confidence=0.99,
                field_type=EntityType.DATE_OF_ISSUE.value,
                normalized_bbox=inv_boxes["invoice_date"],
            ),
            ExtractedField.create(
                page_id=inv_page.id,
                field_name="material_grade",
                field_value="SS 316L",  # Billed as 316L though 304 delivered
                raw_text="SS 316L",
                confidence=0.98,
                field_type=EntityType.MATERIAL_GRADE.value,
                normalized_bbox=inv_boxes["material_grade"],
            ),
            ExtractedField.create(
                page_id=inv_page.id,
                field_name="billed_quantity",
                field_value="1000 KG",  # OVER-BILLING vs 800 KG delivered
                raw_text="1000 KG",
                confidence=0.99,
                field_type=EntityType.QUANTITY.value,
                normalized_bbox=inv_boxes["billed_quantity"],
            ),
            ExtractedField.create(
                page_id=inv_page.id,
                field_name="unit_rate",
                field_value="450.00",
                raw_text="450.00",
                confidence=0.99,
                field_type=EntityType.FINANCIAL_TOTAL.value,
                normalized_bbox=inv_boxes["unit_rate"],
            ),
            ExtractedField.create(
                page_id=inv_page.id,
                field_name="line_total",
                field_value="450000.00",
                raw_text="450000.00",
                confidence=0.99,
                field_type=EntityType.FINANCIAL_TOTAL.value,
                normalized_bbox=inv_boxes["line_total"],
            ),
            ExtractedField.create(
                page_id=inv_page.id,
                field_name="subtotal",
                field_value="450000.00",
                raw_text="450000.00",
                confidence=0.99,
                field_type=EntityType.FINANCIAL_TOTAL.value,
                normalized_bbox=inv_boxes["subtotal"],
            ),
            ExtractedField.create(
                page_id=inv_page.id,
                field_name="tax_amount",
                field_value="81000.00",  # 18% GST on 450,000
                raw_text="81000.00",
                confidence=0.99,
                field_type=EntityType.FINANCIAL_TOTAL.value,
                normalized_bbox=inv_boxes["tax_amount"],
            ),
            ExtractedField.create(
                page_id=inv_page.id,
                field_name="freight",
                field_value="5000.00",
                raw_text="5000.00",
                confidence=0.99,
                field_type=EntityType.FINANCIAL_TOTAL.value,
                normalized_bbox=inv_boxes["freight"],
            ),
            ExtractedField.create(
                page_id=inv_page.id,
                field_name="grand_total",
                field_value="536000.00",  # 450,000 + 81,000 + 5,000 = 536,000 (Reconciled!)
                raw_text="536000.00",
                confidence=0.99,
                field_type=EntityType.FINANCIAL_TOTAL.value,
                normalized_bbox=inv_boxes["grand_total"],
            ),
            ExtractedField.create(
                page_id=inv_page.id,
                field_name="total_amount",
                field_value="536000.00",
                raw_text="536000.00",
                confidence=0.99,
                field_type=EntityType.FINANCIAL_TOTAL.value,
                normalized_bbox=inv_boxes["total_amount"],
            ),
        ]
        for f in inv_fields:
            uow.documents.add_extracted_field(f, organization_id)

    return inv_id
