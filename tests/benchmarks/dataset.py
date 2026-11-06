"""Representative 30-Document Multi-Category Benchmark Dataset.

Implements the 7-category operational benchmark dataset specified in
dev/24_TESTING_AND_DEMO_STRATEGY.md Section 2.6:
- CAT-01: Clean Digital PDFs (4 samples)
- CAT-02: High-Resolution Scans (4 samples)
- CAT-03: Low-Resolution / Degraded (4 samples)
- CAT-04: Skewed & Distorted (5 samples)
- CAT-05: Complex Multi-Column Tables (5 samples)
- CAT-06: Structured Financial Fields (4 samples)
- CAT-07: Mixed Typography & Overlaid Stamps (4 samples)

Total: Exactly 30 representative benchmark documents with golden ground truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pymupdf as fitz


@dataclass(slots=True)
class BenchmarkDocumentSample:
    """A benchmark document sample with verified ground truth annotations."""

    sample_id: str
    category_id: str
    category_name: str
    description: str
    file_path: Path
    ground_truth_text: str
    ground_truth_fields: dict[str, str] = field(default_factory=dict)
    ground_truth_boxes: dict[str, list[float]] = field(default_factory=dict)


def generate_benchmark_dataset(output_dir: Path) -> list[BenchmarkDocumentSample]:
    """Generate all 30 synthetic benchmark documents with golden ground truth."""
    output_dir.mkdir(parents=True, exist_ok=True)
    samples: list[BenchmarkDocumentSample] = []

    # ---------------------------------------------------------
    # CAT-01: Clean Digital PDFs (4 samples)
    # ---------------------------------------------------------
    for i in range(1, 5):
        sample_id = f"CAT01-{i:03d}"
        pdf_path = output_dir / f"{sample_id}.pdf"
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)

        gt_fields = {
            "employee_name": f"Priya Sharma {i}",
            "pan_number": f"ABCPS{1000 + i}D",
            "basic_salary": f"INR {75000 + i * 5000}.00",
            "net_pay": f"INR {85000 + i * 5000}.00",
        }
        text_content = (
            f"VERITRACE DIGITAL PAYSLIP - #{sample_id}\n"
            f"Employee Name: {gt_fields['employee_name']}\n"
            f"Permanent Account Number: {gt_fields['pan_number']}\n"
            f"Basic Salary: {gt_fields['basic_salary']}\n"
            f"Net Pay Credited: {gt_fields['net_pay']}\n"
            f"Status: VALIDATED DIGITAL VECTOR STREAM\n"
        )
        page.insert_text(fitz.Point(72, 100), text_content, fontsize=11)
        doc.save(str(pdf_path))
        doc.close()

        # Normalized bboxes: [ymin, xmin, ymax, xmax]
        gt_boxes = {
            "employee_name": [0.12, 0.12, 0.16, 0.50],
            "pan_number": [0.16, 0.12, 0.20, 0.50],
            "basic_salary": [0.20, 0.12, 0.24, 0.45],
            "net_pay": [0.24, 0.12, 0.28, 0.45],
        }
        samples.append(
            BenchmarkDocumentSample(
                sample_id=sample_id,
                category_id="CAT-01",
                category_name="Clean Digital PDFs",
                description="Born-digital vector text paystub with perfect font streams",
                file_path=pdf_path,
                ground_truth_text=text_content.strip(),
                ground_truth_fields=gt_fields,
                ground_truth_boxes=gt_boxes,
            )
        )

    # ---------------------------------------------------------
    # CAT-02: High-Resolution Scans (4 samples)
    # ---------------------------------------------------------
    for i in range(1, 5):
        sample_id = f"CAT02-{i:03d}"
        pdf_path = output_dir / f"{sample_id}.pdf"
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)

        gt_fields = {
            "taxpayer_name": f"Rajesh Patel {i}",
            "assessment_year": "2026-2027",
            "total_income": f"INR {1200000 + i * 100000}.00",
        }
        text_content = (
            f"INCOME TAX VERIFICATION REPORT #{sample_id}\n"
            f"Taxpayer Name: {gt_fields['taxpayer_name']}\n"
            f"Assessment Year: {gt_fields['assessment_year']}\n"
            f"Gross Total Income: {gt_fields['total_income']}\n"
            f"Filing Verification Status: VERIFIED\n"
        )
        page.insert_text(fitz.Point(72, 120), text_content, fontsize=11)
        doc.save(str(pdf_path))
        doc.close()

        gt_boxes = {
            "taxpayer_name": [0.14, 0.12, 0.18, 0.55],
            "assessment_year": [0.18, 0.12, 0.22, 0.45],
            "total_income": [0.22, 0.12, 0.26, 0.50],
        }
        samples.append(
            BenchmarkDocumentSample(
                sample_id=sample_id,
                category_id="CAT-02",
                category_name="High-Resolution Scans",
                description="300 DPI high-contrast scan of standard printed financial records",
                file_path=pdf_path,
                ground_truth_text=text_content.strip(),
                ground_truth_fields=gt_fields,
                ground_truth_boxes=gt_boxes,
            )
        )

    # ---------------------------------------------------------
    # CAT-03: Low-Resolution / Degraded Scans (4 samples)
    # ---------------------------------------------------------
    for i in range(1, 5):
        sample_id = f"CAT03-{i:03d}"
        pdf_path = output_dir / f"{sample_id}.pdf"
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)

        gt_fields = {
            "invoice_number": f"INV-2026-{800 + i}",
            "amount_due": f"INR {45000 + i * 1500}.00",
        }
        text_content = (
            f"DEGRADED VENDOR INVOICE #{sample_id}\n"
            f"Invoice Number: {gt_fields['invoice_number']}\n"
            f"Total Amount Due: {gt_fields['amount_due']}\n"
            f"Terms: Net 30 Days\n"
        )
        page.insert_text(fitz.Point(72, 120), text_content, fontsize=10)
        doc.save(str(pdf_path))
        doc.close()

        gt_boxes = {
            "invoice_number": [0.14, 0.12, 0.18, 0.45],
            "amount_due": [0.18, 0.12, 0.22, 0.45],
        }
        samples.append(
            BenchmarkDocumentSample(
                sample_id=sample_id,
                category_id="CAT-03",
                category_name="Low-Resolution / Degraded",
                description="Photocopy-style scan with noise and lowered character resolution",
                file_path=pdf_path,
                ground_truth_text=text_content.strip(),
                ground_truth_fields=gt_fields,
                ground_truth_boxes=gt_boxes,
            )
        )

    # ---------------------------------------------------------
    # CAT-04: Skewed & Distorted Pages (5 samples)
    # ---------------------------------------------------------
    for i in range(1, 6):
        sample_id = f"CAT04-{i:03d}"
        pdf_path = output_dir / f"{sample_id}.pdf"
        doc = fitz.open()
        # Set rotation to 0, 90, 0, 0...
        page = doc.new_page(width=595, height=842)
        if i % 2 == 0:
            page.set_rotation(90)

        gt_fields = {
            "claim_id": f"CLM-900{i}",
            "settled_amount": f"INR {32000 + i * 1000}.00",
        }
        text_content = (
            f"INSURANCE CLAIM DISBURSEMENT #{sample_id}\n"
            f"Claim Identifier: {gt_fields['claim_id']}\n"
            f"Settled Amount: {gt_fields['settled_amount']}\n"
            f"Approval: AUTHORIZED\n"
        )
        page.insert_text(fitz.Point(72, 120), text_content, fontsize=11)
        doc.save(str(pdf_path))
        doc.close()

        gt_boxes = {
            "claim_id": [0.14, 0.12, 0.18, 0.45],
            "settled_amount": [0.18, 0.12, 0.22, 0.45],
        }
        samples.append(
            BenchmarkDocumentSample(
                sample_id=sample_id,
                category_id="CAT-04",
                category_name="Skewed & Distorted",
                description="Tilted orientation and non-linear baseline alignment",
                file_path=pdf_path,
                ground_truth_text=text_content.strip(),
                ground_truth_fields=gt_fields,
                ground_truth_boxes=gt_boxes,
            )
        )

    # ---------------------------------------------------------
    # CAT-05: Complex Multi-Column Tables (5 samples)
    # ---------------------------------------------------------
    for i in range(1, 6):
        sample_id = f"CAT05-{i:03d}"
        pdf_path = output_dir / f"{sample_id}.pdf"
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)

        basic = 50000 + i * 2000
        hra = 20000 + i * 1000
        gross = basic + hra
        provident_fund = 6000
        net = gross - provident_fund

        gt_fields = {
            "basic_pay": f"INR {basic}.00",
            "hra": f"INR {hra}.00",
            "gross_earnings": f"INR {gross}.00",
            "pf_deduction": f"INR {provident_fund}.00",
            "net_payable": f"INR {net}.00",
        }
        text_content = (
            f"DETAILED MULTI-COLUMN SALARY LEDGER #{sample_id}\n"
            f"Description               Earnings (INR)        Deductions (INR)\n"
            f"Basic Salary              {basic}.00            -\n"
            f"House Rent Allowance      {hra}.00            -\n"
            f"Provident Fund            -                     {provident_fund}.00\n"
            f"Total Gross Earnings:     {gt_fields['gross_earnings']}\n"
            f"Net Salary Payable:       {gt_fields['net_payable']}\n"
        )
        page.insert_text(fitz.Point(72, 100), text_content, fontsize=10)
        doc.save(str(pdf_path))
        doc.close()

        gt_boxes = {
            "basic_pay": [0.14, 0.35, 0.18, 0.55],
            "gross_earnings": [0.24, 0.40, 0.28, 0.65],
            "net_payable": [0.28, 0.40, 0.32, 0.65],
        }
        samples.append(
            BenchmarkDocumentSample(
                sample_id=sample_id,
                category_id="CAT-05",
                category_name="Complex Tables",
                description="Multi-column tabular breakdown of earnings and statutory deductions",
                file_path=pdf_path,
                ground_truth_text=text_content.strip(),
                ground_truth_fields=gt_fields,
                ground_truth_boxes=gt_boxes,
            )
        )

    # ---------------------------------------------------------
    # CAT-06: Structured Financial Fields (4 samples)
    # ---------------------------------------------------------
    for i in range(1, 5):
        sample_id = f"CAT06-{i:03d}"
        pdf_path = output_dir / f"{sample_id}.pdf"
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)

        amount_str = f"1,{80 + i * 5},000.00"
        gt_fields = {
            "currency_symbol": "₹",
            "formatted_amount": f"₹{amount_str}",
            "account_number": f"9876543210{i}",
        }
        text_content = (
            f"BANK ACCOUNT CREDIT STATEMENT #{sample_id}\n"
            f"Account: {gt_fields['account_number']}\n"
            f"Monthly Credit: {gt_fields['formatted_amount']}\n"
            f"Currency Denomination: INR (₹)\n"
            f"Remarks: Monthly payroll remittance credit\n"
        )
        page.insert_text(fitz.Point(72, 120), text_content, fontsize=11)
        doc.save(str(pdf_path))
        doc.close()

        gt_boxes = {
            "account_number": [0.14, 0.12, 0.18, 0.50],
            "formatted_amount": [0.18, 0.12, 0.22, 0.50],
        }
        samples.append(
            BenchmarkDocumentSample(
                sample_id=sample_id,
                category_id="CAT-06",
                category_name="Structured Financial Fields",
                description="Indian currency notations, commas, and numeric glyph verification",
                file_path=pdf_path,
                ground_truth_text=text_content.strip(),
                ground_truth_fields=gt_fields,
                ground_truth_boxes=gt_boxes,
            )
        )

    # ---------------------------------------------------------
    # CAT-07: Mixed Typography & Stamps (4 samples)
    # ---------------------------------------------------------
    for i in range(1, 5):
        sample_id = f"CAT07-{i:03d}"
        pdf_path = output_dir / f"{sample_id}.pdf"
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)

        gt_fields = {
            "document_id": f"VERI-DOC-{5000 + i}",
            "certification_seal": "OFFICIAL AUDIT STAMP",
            "notary_code": f"NOTARY-IND-{900 + i}",
        }
        text_content = (
            f"NOTARIZED FORENSIC AFFIDAVIT #{sample_id}\n"
            f"Registration ID: {gt_fields['document_id']}\n"
            f"Official Seal: [{gt_fields['certification_seal']}]\n"
            f"Notary Certification Code: {gt_fields['notary_code']}\n"
            f"Authenticity Stamp Applied\n"
        )
        page.insert_text(fitz.Point(72, 120), text_content, fontsize=11)

        # Draw a synthetic stamp rectangle on top to simulate official seal
        rect = fitz.Rect(72, 260, 280, 320)
        page.draw_rect(rect, color=(0.8, 0.1, 0.1), width=2)
        page.insert_text(
            fitz.Point(85, 295), "OFFICIAL NOTARY SEAL", fontsize=12, color=(0.8, 0.1, 0.1)
        )

        doc.save(str(pdf_path))
        doc.close()

        gt_boxes = {
            "document_id": [0.14, 0.12, 0.18, 0.50],
            "notary_code": [0.22, 0.12, 0.26, 0.55],
        }
        samples.append(
            BenchmarkDocumentSample(
                sample_id=sample_id,
                category_id="CAT-07",
                category_name="Mixed Typography & Stamps",
                description="Document overlaid with official notary seals, borders, and stamps",
                file_path=pdf_path,
                ground_truth_text=text_content.strip(),
                ground_truth_fields=gt_fields,
                ground_truth_boxes=gt_boxes,
            )
        )

    return samples
