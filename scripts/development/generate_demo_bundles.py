#!/usr/bin/env python3
"""Generate Curated Hackathon Demonstration Datasets for VeriTrace.

Creates realistic sample PDF bundles specified in dev/24_TESTING_AND_DEMO_STRATEGY.md:
1. CASE-2026-IND-01: Industrial Manufacturing Procurement Bundle
   - PO_SteelTubes_AutoCorp.pdf (Genuine Purchase Order)
   - DeliveryChallan_SteelTubes_Tampered.pdf (Manipulated Delivery Challan)
   - MillTestCert_Grade_ForgedSig.pdf (Cloned Signature Certificate)
2. CASE-2026-0891: Financial Banking & Loan Application Bundle
   - National_ID_RajeshSharma.pdf (Genuine Identity Card)
   - SalarySlip_Nov2023_Tampered.pdf (Spliced Amount Salary Slip)
   - BankStatement_Nov2023_Conflicting.pdf (Cross-Document Conflicting Bank Statement)

Usage:
    python scripts/development/generate_demo_bundles.py
"""

from __future__ import annotations

import logging
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("generate_demo_bundles")

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SAMPLES_DIR = ROOT_DIR / "samples"


def _create_doc(dest_path: Path) -> SimpleDocTemplate:
    """Helper to create standardized A4 document template."""
    return SimpleDocTemplate(
        str(dest_path),
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )


def build_po_pdf(dest_path: Path) -> None:
    """Generate genuine Purchase Order: PO_SteelTubes_AutoCorp.pdf."""
    doc = _create_doc(dest_path)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "POTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1e293b"),
    )
    body_style = ParagraphStyle(
        "POBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155"),
    )

    elements = [
        Paragraph("AUTOCORP MANUFACTURING PVT. LTD.", title_style),
        Paragraph(
            "Industrial Estate, Phase II, Pune, Maharashtra 411018 | GSTIN: 27AABCA1234F1Z5",
            body_style,
        ),
        HRFlowable(width="100%", thickness=2, color=colors.HexColor("#3b82f6"), spaceAfter=15),
        Paragraph(
            "<b>PURCHASE ORDER</b> &nbsp;&nbsp; | &nbsp;&nbsp; <b>PO Number:</b> PO-2026-ST-0089",
            body_style,
        ),
        Paragraph(
            "<b>Date of Issue:</b> 12-Jan-2026 &nbsp;&nbsp; | &nbsp;&nbsp; "
            "<b>Delivery Due:</b> 28-Jan-2026",
            body_style,
        ),
        Paragraph("<b>Vendor:</b> Bharat Seamless Tubes Ltd., Pimpri MIDC, Pune", body_style),
        Spacer(1, 15),
    ]

    # Line items table
    data = [
        ["Item #", "Description & Specifications", "Qty", "Unit Rate (₹)", "Taxable Amount (₹)"],
        [
            "1",
            "Seamless Steel Tubes Grade SS-304 (OD 50mm, Thick 3mm)",
            "500 MT",
            "1,200.00",
            "6,00,000.00",
        ],
        ["", "Subtotal:", "", "", "6,00,000.00"],
        ["", "Applicable GST (18%):", "", "", "1,08,000.00"],
        ["", "Grand Total (INR):", "", "", "7,08,000.00"],
    ]
    t = Table(data, colWidths=[0.8 * inch, 3.4 * inch, 0.8 * inch, 1.1 * inch, 1.4 * inch])
    t.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f8fafc")),
            ("FONTNAME", (0, 2), (-1, -1), "Helvetica-Bold"),
        ])
    )
    elements.append(t)
    elements.append(Spacer(1, 40))
    elements.append(Paragraph("<b>Authorized Procurement Signatory:</b>", body_style))
    elements.append(Paragraph("<i>Amitabh Sen</i> — Lead Procurement Officer", body_style))
    elements.append(Paragraph("Signature Reference: AUTH-SEN-0891", body_style))

    doc.build(elements)
    logger.info("Generated: %s", dest_path.name)


def build_challan_pdf(dest_path: Path) -> None:
    """Generate manipulated Delivery Challan: DeliveryChallan_SteelTubes_Tampered.pdf."""
    doc = _create_doc(dest_path)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ChallanTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1e293b"),
    )
    body_style = ParagraphStyle(
        "ChallanBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155"),
    )

    elements = [
        Paragraph("BHARAT SEAMLESS TUBES LTD.", title_style),
        Paragraph("Factory & Dispatch Yard, MIDC Pimpri, Pune 411018", body_style),
        HRFlowable(width="100%", thickness=2, color=colors.HexColor("#e05252"), spaceAfter=15),
        Paragraph("<b>DELIVERY CHALLAN & DISPATCH NOTE</b>", body_style),
        Paragraph(
            "<b>Challan No:</b> DC-2026-9042 &nbsp;&nbsp; | &nbsp;&nbsp; "
            "<b>Dispatch Date:</b> 20-Jan-2026",
            body_style,
        ),
        Paragraph("<b>Against Purchase Order:</b> PO-2026-ST-0089", body_style),
        Paragraph("<b>Consignee:</b> AutoCorp Manufacturing Pvt. Ltd., Pune", body_style),
        Spacer(1, 15),
    ]

    # Manipulated delivered quantity (stated 500 MT, actual batch 450 MT)
    data = [
        ["Item #", "Description of Dispatched Goods", "Dispatched Qty", "Vehicle #", "Remarks"],
        [
            "1",
            "Seamless Steel Tubes SS-304 (50mm x 3mm)",
            "500 MT",
            "MH-12-QZ-4590",
            "Full Delivery",
        ],
        ["", "Gross Weighbridge Weight:", "42,500 KG", "", ""],
        ["", "Tare Vehicle Weight:", "14,000 KG", "", ""],
        ["", "Net Dispatched Weight:", "28,500 KG", "", "Weight Mismatch with 500 MT"],
    ]
    t = Table(data, colWidths=[0.8 * inch, 3.2 * inch, 1.1 * inch, 1.1 * inch, 1.3 * inch])
    t.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ALIGN", (2, 0), (2, -1), "RIGHT"),
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#fff1f2")),
        ])
    )
    elements.append(t)
    elements.append(Spacer(1, 40))
    elements.append(Paragraph("<b>Warehouse Logistics Officer:</b>", body_style))
    elements.append(Paragraph("<i>K. R. Patil</i> — Dispatch In-Charge", body_style))

    doc.build(elements)
    logger.info("Generated: %s", dest_path.name)


def build_test_cert_pdf(dest_path: Path) -> None:
    """Generate Mill Test Certificate: MillTestCert_Grade_ForgedSig.pdf."""
    doc = _create_doc(dest_path)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CertTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1e293b"),
    )
    body_style = ParagraphStyle(
        "CertBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155"),
    )

    elements = [
        Paragraph("NATIONAL METALLURGICAL TEST LABORATORY", title_style),
        Paragraph("NABL Accredited Facility, Chakan Industrial Corridor, Pune", body_style),
        HRFlowable(width="100%", thickness=2, color=colors.HexColor("#059669"), spaceAfter=15),
        Paragraph("<b>MILL TEST CERTIFICATE (EN 10204 Type 3.1)</b>", body_style),
        Paragraph(
            "<b>Certificate No:</b> MTC-2026-SS-419 &nbsp;&nbsp; | &nbsp;&nbsp; "
            "<b>Test Date:</b> 18-Jan-2026",
            body_style,
        ),
        Paragraph(
            "<b>Heat Number:</b> HT-9942A &nbsp;&nbsp; | &nbsp;&nbsp; "
            "<b>Specification:</b> ASTM A312 SS-304",
            body_style,
        ),
        Spacer(1, 15),
    ]

    # Metallurgical composition table
    data = [
        ["Element", "C (%)", "Mn (%)", "Si (%)", "P (%)", "S (%)", "Cr (%)", "Ni (%)"],
        ["Specification", "≤ 0.08", "≤ 2.00", "≤ 0.75", "≤ 0.045", "≤ 0.030", "18-20", "8-10.5"],
        ["Observed Assay", "0.05", "1.65", "0.48", "0.031", "0.015", "18.25", "8.15"],
        ["Compliance", "PASS", "PASS", "PASS", "PASS", "PASS", "PASS", "PASS"],
    ]
    t = Table(data, colWidths=[1.4 * inch] + [0.85 * inch] * 7)
    t.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ])
    )
    elements.append(t)
    elements.append(Spacer(1, 50))
    elements.append(Paragraph("<b>Certified Metallurgist & Quality Head:</b>", body_style))
    elements.append(
        Paragraph("<i>Dr. R. K. Deshmukh</i>, Chief Metallurgical Inspector", body_style)
    )
    elements.append(
        Paragraph("<b>Attestation Seal:</b> [OFFICIAL METALLURGICAL STAMP APPLIED]", body_style)
    )

    doc.build(elements)
    logger.info("Generated: %s", dest_path.name)


def build_national_id_pdf(dest_path: Path) -> None:
    """Generate genuine Identity Proof: National_ID_RajeshSharma.pdf."""
    doc = _create_doc(dest_path)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "IDTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#1e293b"),
    )
    body_style = ParagraphStyle(
        "IDBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=16,
        textColor=colors.HexColor("#334155"),
    )

    elements = [
        Paragraph("INCOME TAX DEPARTMENT, GOVERNMENT OF INDIA", title_style),
        Paragraph("PERMANENT ACCOUNT NUMBER (PAN) CARD", body_style),
        HRFlowable(width="100%", thickness=2, color=colors.HexColor("#3b82f6"), spaceAfter=20),
        Paragraph("<b>Full Name:</b> Rajesh Kumar Sharma", body_style),
        Paragraph("<b>Father's Name:</b> Ram Mohan Sharma", body_style),
        Paragraph("<b>Date of Birth:</b> 12/04/1988", body_style),
        Paragraph("<b>PAN Number:</b> ABCDE1234F", body_style),
        Paragraph("<b>Nationality:</b> Indian", body_style),
        Spacer(1, 40),
        Paragraph(
            "<i>Digitally signed by Income Tax Department under IT Act 2000.</i>",
            body_style,
        ),
    ]

    doc.build(elements)
    logger.info("Generated: %s", dest_path.name)


def build_salary_slip_pdf(dest_path: Path) -> None:
    """Generate manipulated Salary Slip: SalarySlip_Nov2023_Tampered.pdf."""
    doc = _create_doc(dest_path)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "SalTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1e293b"),
    )
    body_style = ParagraphStyle(
        "SalBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155"),
    )

    elements = [
        Paragraph("APEX SOLUTIONS PRIVATE LIMITED", title_style),
        Paragraph("Plot 42, Cyber City, Gurugram, Haryana 122002", body_style),
        HRFlowable(width="100%", thickness=2, color=colors.HexColor("#f59e0b"), spaceAfter=15),
        Paragraph("<b>PAYSLIP FOR THE MONTH OF NOVEMBER 2023</b>", body_style),
        Paragraph(
            "<b>Employee Name:</b> Rajesh Kumar Sharma &nbsp;&nbsp; | &nbsp;&nbsp; "
            "<b>Emp ID:</b> AS-8814",
            body_style,
        ),
        Paragraph(
            "<b>Designation:</b> Senior Software Engineer &nbsp;&nbsp; | &nbsp;&nbsp; "
            "<b>PAN:</b> ABCDE1234F",
            body_style,
        ),
        Spacer(1, 15),
    ]

    # Arithmetic mismatch: Basic 50,000 + HRA 25,000 + Allowances 10,000 = 85,000.
    data = [
        ["Earnings Component", "Amount (₹)", "Deductions Component", "Amount (₹)"],
        ["Basic Salary", "50,000.00", "Provident Fund (PF)", "0.00"],
        ["House Rent Allowance (HRA)", "25,000.00", "Professional Tax (PT)", "0.00"],
        ["Special Allowance", "10,000.00", "TDS Income Tax", "0.00"],
        ["Sum of Earnings", "85,000.00", "Total Deductions", "0.00"],
        ["STATED NET PAYABLE", "1,85,000.00", "ARITHMETIC ERROR", "₹1,00,000 Spliced"],
    ]
    t = Table(data, colWidths=[2.2 * inch, 1.5 * inch, 2.2 * inch, 1.5 * inch])
    t.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("ALIGN", (3, 0), (3, -1), "RIGHT"),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#fee2e2")),
            ("TEXTCOLOR", (0, -1), (-1, -1), colors.HexColor("#b91c1c")),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ])
    )
    elements.append(t)
    elements.append(Spacer(1, 30))
    elements.append(
        Paragraph("<i>Note: This is a computer generated pay advice slip.</i>", body_style)
    )

    doc.build(elements)
    logger.info("Generated: %s", dest_path.name)


def build_bank_statement_pdf(dest_path: Path) -> None:
    """Generate conflicting Bank Statement: BankStatement_Nov2023_Conflicting.pdf."""
    doc = _create_doc(dest_path)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "BankTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1e293b"),
    )
    body_style = ParagraphStyle(
        "BankBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155"),
    )

    elements = [
        Paragraph("HDFC BANK LIMITED", title_style),
        Paragraph(
            "Account Statement & Transaction Ledger | Branch: Connaught Place, New Delhi",
            body_style,
        ),
        HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1d4ed8"), spaceAfter=15),
        Paragraph(
            "<b>Account Holder:</b> Rakesh K. Sharma &nbsp;&nbsp; | &nbsp;&nbsp; "
            "<b>Account:</b> 50100492817401",
            body_style,
        ),
        Paragraph(
            "<b>Statement Period:</b> 01-Nov-2023 to 30-Nov-2023 &nbsp;&nbsp; | &nbsp;&nbsp; "
            "<b>Currency:</b> INR",
            body_style,
        ),
        Spacer(1, 15),
    ]

    # Transaction ledger showing genuine deposit of 85,000 contradicting salary slip stated 1,85,000
    data = [
        ["Txn Date", "Narration", "Ref #", "Withdrawal (₹)", "Deposit (₹)", "Balance (₹)"],
        ["01-Nov-2023", "Opening Balance", "-", "-", "-", "24,500.00"],
        ["05-Nov-2023", "ACH CR - SALARY", "ACH994201", "-", "85,000.00", "1,09,500.00"],
        ["12-Nov-2023", "UPI/Merchant/Store", "UPI419082", "4,200.00", "-", "1,05,300.00"],
        ["20-Nov-2023", "ATM Withdrawal", "ATM00129", "10,000.00", "-", "95,300.00"],
        ["30-Nov-2023", "Closing Balance", "-", "-", "-", "95,300.00"],
    ]
    col_w = [1.0 * inch, 2.7 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch]
    t = Table(data, colWidths=col_w)
    t.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
            ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#dbeafe")),
            ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
        ])
    )
    elements.append(t)
    elements.append(Spacer(1, 30))
    elements.append(
        Paragraph(
            "<i>Official electronic bank statement generated by HDFC Core Banking.</i>",
            body_style,
        )
    )

    doc.build(elements)
    logger.info("Generated: %s", dest_path.name)


def generate_all_demo_bundles() -> None:
    """Generate all demo case directories and test files."""
    case1_dir = SAMPLES_DIR / "CASE-2026-IND-01"
    case2_dir = SAMPLES_DIR / "CASE-2026-0891"

    case1_dir.mkdir(parents=True, exist_ok=True)
    case2_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Generating Case 1: Industrial Manufacturing Procurement (%s)...", case1_dir)
    build_po_pdf(case1_dir / "PO_SteelTubes_AutoCorp.pdf")
    build_challan_pdf(case1_dir / "DeliveryChallan_SteelTubes_Tampered.pdf")
    build_test_cert_pdf(case1_dir / "MillTestCert_Grade_ForgedSig.pdf")

    logger.info("Generating Case 2: Financial Banking & Loan Application (%s)...", case2_dir)
    build_national_id_pdf(case2_dir / "National_ID_RajeshSharma.pdf")
    build_salary_slip_pdf(case2_dir / "SalarySlip_Nov2023_Tampered.pdf")
    build_bank_statement_pdf(case2_dir / "BankStatement_Nov2023_Conflicting.pdf")

    logger.info("★ All 6 demonstration documents successfully compiled in %s!", SAMPLES_DIR)


if __name__ == "__main__":
    generate_all_demo_bundles()
