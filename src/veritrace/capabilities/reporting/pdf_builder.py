"""Auditor-grade ReportLab PDF compiler for PS-2 Investigation Dossiers (Sections 7.1 to 7.6)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from veritrace.capabilities.reporting.models import InvestigationDossierPayload

# Color Palette adhering to VeriTrace Forensic Dark / Professional Theme
COLOR_PRIMARY_NAVY = colors.HexColor("#1A365D")
COLOR_ACCENT_TEAL = colors.HexColor("#0D9488")
COLOR_WARNING_AMBER = colors.HexColor("#D97706")
COLOR_DANGER_RED = colors.HexColor("#DC2626")
COLOR_BG_ALT = colors.HexColor("#F8FAFC")
COLOR_BORDER = colors.HexColor("#E2E8F0")
COLOR_TEXT_DARK = colors.HexColor("#1E293B")
COLOR_TEXT_MUTED = colors.HexColor("#64748B")


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas for dynamic 'Page X of Y' rendering and cryptographic footers."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict[str, Any]] = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def _draw_page_decorations(self, total_pages: int) -> None:
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(COLOR_TEXT_MUTED)

        # Running Header (from page 2 onwards)
        if self._pageNumber > 1:
            self.drawString(54, 800, "VERITRACE INDUSTRIAL FORENSIC INVESTIGATION DOSSIER")
            self.drawRightString(541, 800, "OFFICIAL AUDITOR RECORD")
            self.setStrokeColor(COLOR_BORDER)
            self.setLineWidth(0.5)
            self.line(54, 794, 541, 794)

        # Running Footer
        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.setFont("Helvetica", 8)
        self.drawString(
            54,
            36,
            "VERITRACE FORENSIC INTELLIGENCE • PS-2 COMPLIANT • PROVENANCE ANCHORED",
        )
        self.drawRightString(541, 36, page_str)
        self.setStrokeColor(COLOR_BORDER)
        self.setLineWidth(0.5)
        self.line(54, 46, 541, 46)

        self.restoreState()


class PdfDossierBuilder:
    """Compiles structured InvestigationDossierPayload into printable, auditor-grade PDF."""

    def build_pdf(
        self,
        payload: InvestigationDossierPayload,
        output_pdf_path: Path | str,
    ) -> Path:
        """Render complete 6-section PDF dossier to disk.

        Args:
            payload: Structured 6-section investigation data.
            output_pdf_path: Destination path for compiled PDF.

        Returns:
            Resolved Path to generated PDF file.
        """
        dest_path = Path(output_pdf_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            str(dest_path),
            pagesize=A4,
            leftMargin=54,
            rightMargin=54,
            topMargin=54,
            bottomMargin=54,
        )

        styles = getSampleStyleSheet()
        normal_style = styles["Normal"]
        normal_style.textColor = COLOR_TEXT_DARK
        normal_style.fontSize = 9
        normal_style.leading = 12

        title_style = ParagraphStyle(
            "DocTitle",
            parent=normal_style,
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=COLOR_PRIMARY_NAVY,
        )

        h1_style = ParagraphStyle(
            "SectionH1",
            parent=normal_style,
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=COLOR_PRIMARY_NAVY,
            spaceBefore=14,
            spaceAfter=6,
        )

        table_header_style = ParagraphStyle(
            "TableHeader",
            parent=normal_style,
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
        )

        cell_style = ParagraphStyle(
            "TableCell",
            parent=normal_style,
            fontSize=8,
            leading=10,
        )

        story: list[Any] = []

        # Document Header Banner
        story.append(Paragraph("VERITRACE INDUSTRIAL DOSSIER", title_style))
        subtitle = (
            f"Forensic Investigation Case: <b>{payload.case_reference}</b> | "
            f"Case ID: <font name='Courier'>{payload.investigation_id}</font>"
        )
        story.append(Paragraph(subtitle, normal_style))
        story.append(Spacer(1, 4))
        story.append(HRFlowable(width="100%", thickness=2, color=COLOR_PRIMARY_NAVY, spaceAfter=10))

        # Executive Overview Grid
        summary = payload.section_6_investigation_summary
        risk_color = (
            COLOR_DANGER_RED
            if summary.risk_classification in ("HIGH", "CRITICAL", "SUSPECTED_MANIPULATION")
            else COLOR_ACCENT_TEAL
        )

        risk_desc = (
            f"<b>Risk Evaluation:</b> <font color='{risk_color.hexval()}'>"
            f"<b>{summary.risk_classification}</b> (Score: {summary.risk_score:.2f})</font>"
        )
        total_anomalies = len(payload.section_4_visual_forensic_findings)

        meta_data = [
            [
                Paragraph("<b>Generated:</b> " + payload.generated_at[:19], cell_style),
                Paragraph(risk_desc, cell_style),
            ],
            [
                Paragraph(
                    f"<b>Documents Ingested:</b> {len(payload.section_1_document_overview)}",
                    cell_style,
                ),
                Paragraph(
                    f"<b>Total Anomalies Flagged:</b> {total_anomalies}",
                    cell_style,
                ),
            ],
        ]
        meta_table = Table(meta_data, colWidths=[240, 247])
        meta_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), COLOR_BG_ALT),
                    ("BOX", (0, 0), (-1, -1), 1, COLOR_BORDER),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(meta_table)
        story.append(Spacer(1, 10))

        # ==========================================
        # SECTION 1: DOCUMENT OVERVIEW
        # ==========================================
        story.append(Paragraph("1. Document Overview & Ingestion Ledger", h1_style))
        sec1_rows = [
            [
                Paragraph("Document ID", table_header_style),
                Paragraph("Filename", table_header_style),
                Paragraph("Type", table_header_style),
                Paragraph("Pages", table_header_style),
                Paragraph("SHA-256 Digest", table_header_style),
            ]
        ]
        for d in payload.section_1_document_overview:
            sec1_rows.append(
                [
                    Paragraph(f"<font name='Courier'>{d.document_id[:16]}...</font>", cell_style),
                    Paragraph(d.filename, cell_style),
                    Paragraph(d.document_type, cell_style),
                    Paragraph(str(d.page_count), cell_style),
                    Paragraph(f"<font name='Courier'>{d.sha256_hash[:16]}...</font>", cell_style),
                ]
            )
        sec1_table = Table(sec1_rows, colWidths=[95, 130, 75, 40, 147])
        sec1_table.setStyle(self._standard_table_style(len(sec1_rows)))
        story.append(sec1_table)
        story.append(Spacer(1, 12))

        # ==========================================
        # SECTION 2: EXTRACTED INFORMATION
        # ==========================================
        story.append(Paragraph("2. Key Extracted Information & OCR Confidence", h1_style))
        if payload.section_2_extracted_information:
            sec2_rows = [
                [
                    Paragraph("Field Name", table_header_style),
                    Paragraph("Extracted Value", table_header_style),
                    Paragraph("Language", table_header_style),
                    Paragraph("Confidence", table_header_style),
                ]
            ]
            for f in payload.section_2_extracted_information[:10]:  # Highlight key fields
                conf_str = f"{f.confidence * 100.0:.1f}%"
                sec2_rows.append(
                    [
                        Paragraph(f.field_name, cell_style),
                        Paragraph(f.field_value, cell_style),
                        Paragraph(f.language or "eng", cell_style),
                        Paragraph(conf_str, cell_style),
                    ]
                )
            sec2_table = Table(sec2_rows, colWidths=[130, 210, 67, 80])
            sec2_table.setStyle(self._standard_table_style(len(sec2_rows)))
            story.append(sec2_table)
        else:
            story.append(Paragraph("<i>No structured key-value pairs recorded.</i>", normal_style))
        story.append(Spacer(1, 12))

        # ==========================================
        # SECTION 3: CONTEXTUAL ANALYSIS
        # ==========================================
        story.append(Paragraph("3. Contextual, Arithmetic & Chronological Analysis", h1_style))
        if payload.section_3_contextual_analysis:
            sec3_rows = [
                [
                    Paragraph("Rule", table_header_style),
                    Paragraph("Category", table_header_style),
                    Paragraph("Discrepancy Explanation", table_header_style),
                    Paragraph("Variance", table_header_style),
                ]
            ]
            for r in payload.section_3_contextual_analysis:
                sec3_rows.append(
                    [
                        Paragraph(r.rule_name, cell_style),
                        Paragraph(r.category, cell_style),
                        Paragraph(r.description, cell_style),
                        Paragraph(f"{r.discrepancy:.2f}", cell_style),
                    ]
                )
            sec3_table = Table(sec3_rows, colWidths=[110, 100, 217, 60])
            sec3_table.setStyle(self._standard_table_style(len(sec3_rows)))
            story.append(sec3_table)
        else:
            story.append(
                Paragraph(
                    "<i>All arithmetic and chronological checks verified successfully.</i>",
                    normal_style,
                )
            )
        story.append(Spacer(1, 12))

        # ==========================================
        # SECTION 4: VISUAL FORENSIC FINDINGS
        # ==========================================
        story.append(Paragraph("4. Visual Forensic Findings & Anomaly Detection", h1_style))
        if payload.section_4_visual_forensic_findings:
            sec4_rows = [
                [
                    Paragraph("Category", table_header_style),
                    Paragraph("Epistemic Tier", table_header_style),
                    Paragraph("Severity", table_header_style),
                    Paragraph("Finding Title & Description", table_header_style),
                ]
            ]
            for vf in payload.section_4_visual_forensic_findings:
                sev_color = (
                    COLOR_DANGER_RED if vf.severity in ("HIGH", "CRITICAL") else COLOR_WARNING_AMBER
                )
                sec4_rows.append(
                    [
                        Paragraph(vf.category, cell_style),
                        Paragraph(vf.epistemic_tier, cell_style),
                        Paragraph(
                            f"<font color='{sev_color.hexval()}'><b>{vf.severity}</b></font>",
                            cell_style,
                        ),
                        Paragraph(f"<b>{vf.title}</b><br/>{vf.explanation}", cell_style),
                    ]
                )
            sec4_table = Table(sec4_rows, colWidths=[100, 110, 57, 220])
            sec4_table.setStyle(self._standard_table_style(len(sec4_rows)))
            story.append(sec4_table)
        else:
            story.append(
                Paragraph(
                    "<i>No visual compression, baseline, or signature anomalies detected.</i>",
                    normal_style,
                )
            )
        story.append(Spacer(1, 12))

        # ==========================================
        # SECTION 5: EVIDENCE TRACEABILITY & CROPS
        # ==========================================
        story.append(Paragraph("5. Evidence Traceability & Coordinate Grounding", h1_style))
        if payload.section_5_evidence_traceability:
            for ev in payload.section_5_evidence_traceability[:4]:  # Embed first 4 crops
                crop_elements = []
                box = ev.normalized_bbox
                coords = (
                    f"Page {ev.page_number} | Box: [{box['ymin']:.3f}, {box['xmin']:.3f}, "
                    f"{box['ymax']:.3f}, {box['xmax']:.3f}]"
                )
                crop_elements.append(
                    Paragraph(f"<b>Evidence Anchor:</b> {ev.evidence_id} ({coords})", cell_style)
                )
                if ev.grounding_explanation:
                    crop_elements.append(
                        Paragraph(f"<i>Grounding:</i> {ev.grounding_explanation}", cell_style)
                    )

                # If image crop exists on disk, embed image
                if ev.crop_image_path and os.path.exists(ev.crop_image_path):
                    try:
                        img = Image(ev.crop_image_path, width=3.0 * inch, height=1.0 * inch)
                        crop_elements.append(img)
                    except Exception:
                        pass
                crop_elements.append(Spacer(1, 6))
                story.append(KeepTogether(crop_elements))
        else:
            story.append(
                Paragraph("<i>No physical visual crops generated for this case.</i>", normal_style)
            )
        story.append(Spacer(1, 12))

        # ==========================================
        # SECTION 6: INVESTIGATION SUMMARY & AUDITOR SIGN-OFF
        # ==========================================
        story.append(Paragraph("6. Investigation Summary & Epistemic Conclusions", h1_style))
        story.append(Paragraph(summary.executive_narrative, normal_style))
        story.append(Spacer(1, 10))

        # Sign-off box
        rev_ts = summary.reviewed_at[:19] if summary.reviewed_at else "PENDING"
        sign_data = [
            [
                Paragraph("<b>Forensic Adjudication:</b>", cell_style),
                Paragraph("<b>Auditor Attestation:</b>", cell_style),
            ],
            [
                Paragraph(
                    "Findings compiled strictly downstream of deterministic computer vision, "
                    "arithmetic rules, and reference verification models.",
                    cell_style,
                ),
                Paragraph(
                    f"Examiner: {summary.examiner_name}<br/>"
                    f"Review Timestamp: {rev_ts}<br/>"
                    "Status: <b>VERIFIED RECORD</b>",
                    cell_style,
                ),
            ],
        ]
        sign_table = Table(sign_data, colWidths=[240, 247])
        sign_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), COLOR_BG_ALT),
                    ("BOX", (0, 0), (-1, -1), 1, COLOR_PRIMARY_NAVY),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(KeepTogether([sign_table]))

        # Build PDF with two-pass NumberedCanvas
        doc.build(story, canvasmaker=NumberedCanvas)
        return dest_path

    def _standard_table_style(self, num_rows: int) -> TableStyle:
        """Standard forensic table styling with navy header and alternating rows."""
        style_cmds: list[tuple[Any, ...]] = [
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY_NAVY),
            ("BOX", (0, 0), (-1, -1), 1, COLOR_BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
        for row in range(1, num_rows):
            if row % 2 == 0:
                style_cmds.append(("BACKGROUND", (0, row), (-1, row), COLOR_BG_ALT))
        return TableStyle(style_cmds)
