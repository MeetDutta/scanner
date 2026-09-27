"""
SpecGuard Document Inspection & Publication Readiness Report Generator.
Produces formal, publication-quality Tolerance Reports in PDF, HTML, JSON, and DOCX formats.
100% offline, zero external dependencies, no telemetry.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any, Union
import logging

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import pymupdf

from specguard.core.models import DocumentModel, Finding
from specguard.core.tolerance import ToleranceResult, ToleranceCalculator

logger = logging.getLogger(__name__)


class DOCXAnnotator:
    """Creates a formal DOCX Document Inspection Report with tolerance metrics."""

    @staticmethod
    def create_annotated_docx(
        original_docx_path: str,
        output_path: str,
        findings: List[Finding],
        tolerance_result: Optional[ToleranceResult] = None
    ) -> str:
        doc = docx.Document(original_docx_path)

        # Prepend Executive Inspection & Tolerance Summary
        p_title = doc.paragraphs[0].insert_paragraph_before("SpecGuard Document Inspection Report")
        p_title.style = 'Heading 1'

        res = tolerance_result
        if not res:
            doc_model = DocumentModel(
                file_path=original_docx_path,
                file_type="DOCX",
                file_hash="docx_hash",
                file_size=Path(original_docx_path).stat().st_size if Path(original_docx_path).exists() else 0,
                page_count=max(1, len(doc.paragraphs) // 15),
                pages=[]
            )
            res = ToleranceCalculator.calculate("SG-DOCX", doc_model, findings, "publication")

        meta_p = p_title.insert_paragraph_before(
            f"Session ID: {res.session_id} | Document No.: {res.document_no} | "
            f"Profile: {res.inspection_profile} | Inspection Date: {res.inspection_date}"
        )
        meta_p.runs[0].font.italic = True

        # Tolerance decision callout
        tol_p = p_title.insert_paragraph_before(
            f"Tolerance Assessment: {res.acceptance_status} | Tolerance Index: {res.tolerance_index} / "
            f"Max Acceptable: {res.maximum_acceptable_tolerance} (Utilization: {res.tolerance_utilization}%)"
        )
        tol_p.runs[0].font.bold = True

        # Category summary table
        table = doc.add_table(rows=1, cols=2)
        table.style = 'Table Grid'
        hdr = table.rows[0].cells
        hdr[0].text = "Issue Category"
        hdr[1].text = "Finding Count"
        for cat, count in res.category_summary.items():
            row = table.add_row().cells
            row[0].text = cat
            row[1].text = str(count)

        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(out_file))
        logger.info("Saved inspection DOCX to %s", out_file)
        return str(out_file)


class ReportGenerator:
    """Generates formal Document Inspection / Publication Readiness Reports in PDF, HTML, and JSON."""

    @staticmethod
    def _resolve_tolerance_result(
        doc_or_tol: Union[ToleranceResult, DocumentModel],
        findings: Optional[List[Finding]] = None,
        session_id: Optional[str] = None,
        profile_identifier: Optional[str] = None,
        custom_meta: Optional[Dict[str, str]] = None,
        custom_max_tolerance: Optional[float] = None
    ) -> ToleranceResult:
        if isinstance(doc_or_tol, ToleranceResult):
            return doc_or_tol

        doc = doc_or_tol
        f_list = findings or []
        s_id = session_id or "SG-INSPECTION"
        return ToleranceCalculator.calculate(
            session_id=s_id,
            doc=doc,
            findings=f_list,
            profile_identifier=profile_identifier,
            custom_meta=custom_meta,
            custom_max_tolerance=custom_max_tolerance
        )

    @classmethod
    def generate_pdf_report(
        cls,
        doc_or_tol: Union[ToleranceResult, DocumentModel],
        output_path: str,
        findings: Optional[List[Finding]] = None,
        session_id: Optional[str] = None,
        profile_identifier: Optional[str] = None,
        custom_meta: Optional[Dict[str, str]] = None,
        custom_max_tolerance: Optional[float] = None
    ) -> str:
        """Generates a crisp, vector A4 Publication Inspection Report PDF using PyMuPDF."""
        res = cls._resolve_tolerance_result(
            doc_or_tol, findings, session_id, profile_identifier, custom_meta, custom_max_tolerance
        )

        doc = pymupdf.open()
        page = doc.new_page(width=595, height=842)

        DARK_NAVY = (0.08, 0.16, 0.28)
        LIGHT_BG = (0.97, 0.98, 0.99)
        CARD_BORDER = (0.82, 0.86, 0.91)
        TEXT_MAIN = (0.09, 0.13, 0.20)
        TEXT_MUTED = (0.42, 0.48, 0.58)

        is_within = res.acceptance_status == "WITHIN ACCEPTABLE TOLERANCE"
        is_not_eligible = res.acceptance_status == "NOT ELIGIBLE"
        status_color = (0.06, 0.60, 0.35) if is_within else ((0.85, 0.15, 0.15) if is_not_eligible else (0.85, 0.45, 0.10))
        status_bg = (0.94, 0.98, 0.95) if is_within else ((0.99, 0.94, 0.94) if is_not_eligible else (0.99, 0.97, 0.93))

        # 1. Header Banner
        page.draw_rect(pymupdf.Rect(45, 35, 550, 100), color=None, fill=DARK_NAVY)
        page.insert_text((60, 56), "SPECGuard", fontsize=16, fontname="helv", color=(1, 1, 1))
        page.insert_text((60, 71), "ENGINEERING DOCUMENT QUALITY & COMPLIANCE INSPECTION", fontsize=8.5, fontname="helv", color=(0.7, 0.8, 0.92))
        page.insert_text((60, 89), "DOCUMENT INSPECTION REPORT", fontsize=12, fontname="helv", color=(0.35, 0.80, 0.98))

        # 2. Document Identification Table
        y = 112
        page.draw_rect(pymupdf.Rect(45, y, 550, y + 115), color=CARD_BORDER, fill=LIGHT_BG)
        page.insert_text((60, y + 18), "DOCUMENT IDENTIFICATION", fontsize=9.5, fontname="helv", color=TEXT_MAIN)
        page.draw_line(pymupdf.Point(60, y + 24), pymupdf.Point(535, y + 24), color=CARD_BORDER)

        meta = [
            ("Session ID:", res.session_id, "Inspection Date:", res.inspection_date),
            ("Document No.:", res.document_no, "Inspection Profile:", res.inspection_profile),
            ("Document Title:", res.document_title, "Pages Inspected:", str(res.pages_inspected)),
            ("Revision:", res.revision, "Engine Version:", res.engine_version)
        ]
        for idx, (l1, v1, l2, v2) in enumerate(meta):
            ry = y + 40 + (idx * 18)
            page.insert_text((60, ry), l1, fontsize=8.5, fontname="helv", color=TEXT_MUTED)
            page.insert_text((150, ry), str(v1)[:30], fontsize=8.5, fontname="helv", color=TEXT_MAIN)
            page.insert_text((320, ry), l2, fontsize=8.5, fontname="helv", color=TEXT_MUTED)
            page.insert_text((425, ry), str(v2)[:25], fontsize=8.5, fontname="helv", color=TEXT_MAIN)

        # 3. Tolerance Assessment Decision Block (Prominent)
        y = 240
        page.draw_rect(pymupdf.Rect(45, y, 550, y + 140), color=status_color, fill=status_bg)
        page.insert_text((60, y + 20), "TOLERANCE ASSESSMENT", fontsize=11, fontname="helv", color=TEXT_MAIN)
        page.draw_line(pymupdf.Point(60, y + 26), pymupdf.Point(535, y + 26), color=status_color)

        # Metrics Columns
        page.insert_text((60, y + 46), "TOLERANCE INDEX", fontsize=8.5, fontname="helv", color=TEXT_MUTED)
        page.insert_text((60, y + 74), f"{res.tolerance_index}", fontsize=22, fontname="helv", color=status_color)
        page.insert_text((60, y + 88), "(Lower is better)", fontsize=7.5, fontname="helv", color=TEXT_MUTED)

        page.insert_text((220, y + 46), "MAX ACCEPTABLE", fontsize=8.5, fontname="helv", color=TEXT_MUTED)
        page.insert_text((220, y + 72), f"{res.maximum_acceptable_tolerance}", fontsize=18, fontname="helv", color=TEXT_MAIN)
        page.insert_text((220, y + 88), "Configured threshold", fontsize=7.5, fontname="helv", color=TEXT_MUTED)

        page.insert_text((380, y + 46), "TOLERANCE UTILIZATION", fontsize=8.5, fontname="helv", color=TEXT_MUTED)
        page.insert_text((380, y + 72), f"{res.tolerance_utilization}%", fontsize=18, fontname="helv", color=TEXT_MAIN)
        page.insert_text((380, y + 88), "Index / Max x 100", fontsize=7.5, fontname="helv", color=TEXT_MUTED)

        # Status Banner
        status_icon = "✓" if is_within else ("❌" if is_not_eligible else "⚠️")
        status_text = f"{status_icon} {res.acceptance_status}"
        page.draw_rect(pymupdf.Rect(60, y + 102, 535, y + 128), color=status_color, fill=(1, 1, 1))
        page.insert_text((75, y + 119), status_text, fontsize=11, fontname="helv", color=status_color)

        # 4. Inspection Summary & Categories
        y = 395
        page.draw_rect(pymupdf.Rect(45, y, 290, y + 130), color=CARD_BORDER, fill=LIGHT_BG)
        page.insert_text((55, y + 18), "INSPECTION SUMMARY", fontsize=9.5, fontname="helv", color=TEXT_MAIN)
        page.draw_line(pymupdf.Point(55, y + 24), pymupdf.Point(280, y + 24), color=CARD_BORDER)

        sum_items = [
            ("Total Findings:", str(res.total_findings)),
            ("Critical:", str(res.critical_count)),
            ("High:", str(res.high_count)),
            ("Medium:", str(res.medium_count)),
            ("Low:", str(res.low_count)),
            ("Informational:", str(res.info_count))
        ]
        for idx, (lbl, val) in enumerate(sum_items):
            ry = y + 40 + (idx * 14)
            c = (0.85, 0.15, 0.15) if lbl == "Critical:" and int(val) > 0 else TEXT_MAIN
            page.insert_text((55, ry), lbl, fontsize=8, fontname="helv", color=TEXT_MUTED)
            page.insert_text((180, ry), val, fontsize=8, fontname="helv", color=c)

        # Category Summary Table (Right)
        page.draw_rect(pymupdf.Rect(305, y, 550, y + 130), color=CARD_BORDER, fill=LIGHT_BG)
        page.insert_text((315, y + 18), "CATEGORY SUMMARY", fontsize=9.5, fontname="helv", color=TEXT_MAIN)
        page.draw_line(pymupdf.Point(315, y + 24), pymupdf.Point(540, y + 24), color=CARD_BORDER)

        cats = list(res.category_summary.items())[:8]
        col1 = cats[:4]
        col2 = cats[4:8]
        for idx, (cat, cnt) in enumerate(col1):
            ry = y + 42 + (idx * 18)
            page.insert_text((315, ry), cat[:14], fontsize=8, fontname="helv", color=TEXT_MUTED)
            page.insert_text((400, ry), str(cnt), fontsize=8, fontname="helv", color=TEXT_MAIN)
        for idx, (cat, cnt) in enumerate(col2):
            ry = y + 42 + (idx * 18)
            page.insert_text((435, ry), cat[:14], fontsize=8, fontname="helv", color=TEXT_MUTED)
            page.insert_text((520, ry), str(cnt), fontsize=8, fontname="helv", color=TEXT_MAIN)

        # 5. Inspection Result Narrative
        y = 540
        page.draw_rect(pymupdf.Rect(45, y, 550, y + 120), color=CARD_BORDER, fill=LIGHT_BG)
        page.insert_text((55, y + 18), "INSPECTION RESULT", fontsize=9.5, fontname="helv", color=TEXT_MAIN)
        page.draw_line(pymupdf.Point(55, y + 24), pymupdf.Point(540, y + 24), color=CARD_BORDER)

        lines = [
            f"The analyzed document has a calculated Tolerance Index of {res.tolerance_index}",
            f"against a configured maximum acceptable tolerance of {res.maximum_acceptable_tolerance} ({res.inspection_profile}).",
            "",
            f"Result: {res.status_reason}",
            "",
            "Detailed findings and their exact document defect locations are available in the",
            f"SpecGuard inspection interface using Session ID: {res.session_id}"
        ]
        for idx, line in enumerate(lines):
            page.insert_text((55, y + 40 + (idx * 11)), line, fontsize=8, fontname="helv", color=TEXT_MAIN)

        # 6. Disclaimer & Footer
        page.draw_line(pymupdf.Point(45, 775), pymupdf.Point(550, 775), color=CARD_BORDER)
        page.insert_textbox(pymupdf.Rect(45, 782, 550, 810), res.human_disclaimer, fontsize=7.2, fontname="helv", color=TEXT_MUTED)
        page.insert_text((45, 820), f"SpecGuard — Engineering Document Quality & Compliance Inspection • Session ID: {res.session_id}", fontsize=7.5, fontname="helv", color=TEXT_MUTED)

        out_path = Path(output_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(out_path))
        doc.close()
        logger.info("Generated PDF report at %s", out_path)
        return str(out_path)

    @classmethod
    def generate_html_report(
        cls,
        doc_or_tol: Union[ToleranceResult, DocumentModel],
        findings_or_path: Optional[Any] = None,
        session_id: Optional[str] = None,
        output_path: Optional[str] = None,
        profile_identifier: Optional[str] = None,
        custom_meta: Optional[Dict[str, str]] = None,
        custom_max_tolerance: Optional[float] = None
    ) -> str:
        """Generates formal standalone HTML Document Inspection Report."""
        # Support both (res, out_path) and (doc, findings, session_id, out_path)
        if isinstance(doc_or_tol, ToleranceResult):
            res = doc_or_tol
            out_file_str = findings_or_path if isinstance(findings_or_path, str) else output_path
        else:
            doc = doc_or_tol
            f_list = findings_or_path if isinstance(findings_or_path, list) else []
            s_id = session_id or "SG-INSPECTION"
            out_file_str = output_path
            res = ToleranceCalculator.calculate(
                session_id=s_id,
                doc=doc,
                findings=f_list,
                profile_identifier=profile_identifier,
                custom_meta=custom_meta,
                custom_max_tolerance=custom_max_tolerance
            )

        is_within = res.acceptance_status == "WITHIN ACCEPTABLE TOLERANCE"
        is_not_eligible = res.acceptance_status == "NOT ELIGIBLE"
        status_color = "#10b981" if is_within else ("#ef4444" if is_not_eligible else "#f59e0b")
        status_bg = "rgba(16, 185, 129, 0.10)" if is_within else ("rgba(239, 68, 68, 0.10)" if is_not_eligible else "rgba(245, 158, 11, 0.10)")
        status_icon = "✓" if is_within else ("❌" if is_not_eligible else "⚠️")

        # Category table rows
        cat_rows = []
        for cat, cnt in res.category_summary.items():
            cat_rows.append(f"""
            <tr>
                <td style="padding: 8px 12px; border-bottom: 1px solid #334155; color: #cbd5e1;">{cat}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #334155; text-align: right; font-weight: 700; color: #f8fafc;">{cnt}</td>
            </tr>
            """)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SpecGuard — Document Inspection Report — {res.document_title}</title>
<style>
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        background: #0f172a;
        color: #f8fafc;
        margin: 0;
        padding: 40px 20px;
    }}
    .report-card {{
        max-width: 860px;
        margin: 0 auto;
        background: #1e293b;
        border-radius: 12px;
        padding: 36px 40px;
        border: 1px solid #334155;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5);
    }}
    .report-header {{
        border-bottom: 2px solid #38bdf8;
        padding-bottom: 16px;
        margin-bottom: 24px;
    }}
    .brand-title {{
        font-size: 22px;
        font-weight: 900;
        color: #38bdf8;
        letter-spacing: 0.5px;
        margin: 0 0 4px 0;
    }}
    .brand-sub {{
        font-size: 11px;
        font-weight: 700;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin: 0 0 12px 0;
    }}
    .report-type-badge {{
        display: inline-block;
        font-size: 13px;
        font-weight: 800;
        color: #f8fafc;
        background: #0284c7;
        padding: 4px 10px;
        border-radius: 4px;
        letter-spacing: 0.5px;
    }}
    .table-id {{
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 24px;
        background: #0f172a;
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid #334155;
        font-size: 13px;
    }}
    .table-id td {{
        padding: 10px 14px;
        border-bottom: 1px solid #1e293b;
    }}
    .table-id .label {{
        color: #94a3b8;
        font-weight: 600;
        width: 22%;
    }}
    .table-id .val {{
        color: #f8fafc;
        font-weight: 700;
        width: 28%;
    }}
    .tolerance-block {{
        background: {status_bg};
        border: 2px solid {status_color};
        border-radius: 10px;
        padding: 24px;
        margin-bottom: 28px;
        text-align: center;
    }}
    .tolerance-title {{
        font-size: 12px;
        font-weight: 800;
        color: #94a3b8;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 14px;
    }}
    .tolerance-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 16px;
        margin-bottom: 20px;
    }}
    .tol-metric {{
        background: rgba(15, 23, 42, 0.6);
        padding: 14px;
        border-radius: 8px;
        border: 1px solid rgba(255,255,255,0.05);
    }}
    .tol-lbl {{
        font-size: 11px;
        color: #94a3b8;
        font-weight: 700;
        text-transform: uppercase;
    }}
    .tol-val {{
        font-size: 28px;
        font-weight: 900;
        margin-top: 4px;
    }}
    .tol-sub {{
        font-size: 11px;
        color: #64748b;
        margin-top: 2px;
    }}
    .decision-banner {{
        background: #0f172a;
        border: 1.5px solid {status_color};
        color: {status_color};
        font-size: 15px;
        font-weight: 800;
        padding: 10px 16px;
        border-radius: 6px;
        display: inline-block;
        margin-bottom: 8px;
    }}
    .reason-text {{
        font-size: 12.5px;
        color: #cbd5e1;
        max-width: 650px;
        margin: 6px auto 0 auto;
    }}
    .two-col {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 20px;
        margin-bottom: 24px;
    }}
    .section-card {{
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 16px 20px;
    }}
    .section-title {{
        font-size: 12px;
        font-weight: 800;
        color: #38bdf8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        border-bottom: 1px solid #334155;
        padding-bottom: 8px;
        margin-bottom: 12px;
    }}
    .summary-row {{
        display: flex;
        justify-content: space-between;
        padding: 6px 0;
        font-size: 13px;
        border-bottom: 1px solid #1e293b;
    }}
    .category-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 12.5px;
    }}
    .narrative-block {{
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 18px 20px;
        margin-bottom: 24px;
        font-size: 13px;
        line-height: 1.6;
        color: #cbd5e1;
    }}
    .disclaimer-footer {{
        border-top: 1px solid #334155;
        padding-top: 16px;
        font-size: 11.5px;
        color: #64748b;
        line-height: 1.5;
        text-align: center;
    }}
    @media print {{
        body {{ background: #fff; color: #000; padding: 0; }}
        .report-card {{ border: none; box-shadow: none; padding: 10px; background: #fff; color: #000; }}
        .brand-title {{ color: #0369a1; }}
        .table-id {{ background: #f8fafc; border-color: #cbd5e1; color: #000; }}
        .table-id td {{ border-color: #e2e8f0; }}
        .table-id .label {{ color: #475569; }}
        .table-id .val {{ color: #000; }}
        .tolerance-block {{ background: #f8fafc; border-color: #94a3b8; }}
        .tol-metric {{ background: #fff; border: 1px solid #cbd5e1; }}
        .tol-val {{ color: #000; }}
        .section-card {{ background: #f8fafc; border-color: #cbd5e1; }}
        .narrative-block {{ background: #f8fafc; border-color: #cbd5e1; color: #000; }}
        .disclaimer-footer {{ border-color: #cbd5e1; color: #475569; }}
    }}
</style>
</head>
<body>
<div class="report-card">
    <div class="report-header">
        <div class="brand-title">SPECGuard</div>
        <div class="brand-sub">ENGINEERING DOCUMENT QUALITY & COMPLIANCE INSPECTION</div>
        <div class="report-type-badge">DOCUMENT INSPECTION REPORT</div>
    </div>

    <!-- 1. Document Identification -->
    <table class="table-id">
        <tr>
            <td class="label">SESSION ID</td>
            <td class="val" style="font-family: monospace;">{res.session_id}</td>
            <td class="label">INSPECTION DATE</td>
            <td class="val">{res.inspection_date}</td>
        </tr>
        <tr>
            <td class="label">DOCUMENT NO.</td>
            <td class="val">{res.document_no}</td>
            <td class="label">INSPECTION PROFILE</td>
            <td class="val">{res.inspection_profile}</td>
        </tr>
        <tr>
            <td class="label">DOCUMENT TITLE</td>
            <td class="val">{res.document_title}</td>
            <td class="label">PAGES INSPECTED</td>
            <td class="val">{res.pages_inspected}</td>
        </tr>
        <tr>
            <td class="label">REVISION</td>
            <td class="val">{res.revision}</td>
            <td class="label">ENGINE VERSION</td>
            <td class="val">{res.engine_version}</td>
        </tr>
    </table>

    <!-- 2. Tolerance Assessment Decision Block -->
    <div class="tolerance-block">
        <div class="tolerance-title">TOLERANCE ASSESSMENT</div>
        <div class="tolerance-grid">
            <div class="tol-metric">
                <div class="tol-lbl">Tolerance Index</div>
                <div class="tol-val" style="color: {status_color};">{res.tolerance_index}</div>
                <div class="tol-sub">Lower is better</div>
            </div>
            <div class="tol-metric">
                <div class="tol-lbl">Maximum Acceptable</div>
                <div class="tol-val" style="color: #f8fafc;">{res.maximum_acceptable_tolerance}</div>
                <div class="tol-sub">Configured threshold</div>
            </div>
            <div class="tol-metric">
                <div class="tol-lbl">Tolerance Utilization</div>
                <div class="tol-val" style="color: #f8fafc;">{res.tolerance_utilization}%</div>
                <div class="tol-sub">Index / Max &times; 100</div>
            </div>
        </div>

        <div class="decision-banner">{status_icon} {res.acceptance_status}</div>
        <div class="reason-text">{res.status_reason}</div>
    </div>

    <!-- 3. Summary & Category Breakdown -->
    <div class="two-col">
        <div class="section-card">
            <div class="section-title">Inspection Summary</div>
            <div class="summary-row">
                <span style="color: #94a3b8;">Total Findings</span>
                <span style="font-weight: 700; color: #f8fafc;">{res.total_findings}</span>
            </div>
            <div class="summary-row">
                <span style="color: #ef4444; font-weight: 600;">Critical</span>
                <span style="font-weight: 700; color: #ef4444;">{res.critical_count}</span>
            </div>
            <div class="summary-row">
                <span style="color: #f97316; font-weight: 600;">High Severity</span>
                <span style="font-weight: 700; color: #f97316;">{res.high_count}</span>
            </div>
            <div class="summary-row">
                <span style="color: #eab308; font-weight: 600;">Medium Severity</span>
                <span style="font-weight: 700; color: #eab308;">{res.medium_count}</span>
            </div>
            <div class="summary-row">
                <span style="color: #3b82f6; font-weight: 600;">Low Severity</span>
                <span style="font-weight: 700; color: #3b82f6;">{res.low_count}</span>
            </div>
            <div class="summary-row">
                <span style="color: #64748b;">Informational</span>
                <span style="font-weight: 700; color: #94a3b8;">{res.info_count}</span>
            </div>
        </div>

        <div class="section-card">
            <div class="section-title">Category Summary</div>
            <table class="category-table">
                <tbody>
                    {"".join(cat_rows)}
                </tbody>
            </table>
        </div>
    </div>

    <!-- 4. Inspection Result Narrative -->
    <div class="narrative-block">
        <strong style="color: #38bdf8;">Inspection Result:</strong> The analyzed document has a calculated
        Tolerance Index of <strong>{res.tolerance_index}</strong> against a configured maximum acceptable
        tolerance of <strong>{res.maximum_acceptable_tolerance}</strong> under the <em>{res.inspection_profile}</em> profile.
        <br><br>
        Detailed Findings and Suggested Corrective Actions are available in the SpecGuard
        Inspection Findings interface using Session ID: <strong style="font-family: monospace; color: #38bdf8;">{res.session_id}</strong>.
    </div>

    <!-- 5. Disclaimer & Footer -->
    <div class="disclaimer-footer">
        {res.human_disclaimer}
        <br><br>
        SpecGuard &mdash; Engineering Document Quality & Compliance Inspection &bull; Session ID: {res.session_id}
    </div>
</div>
</body>
</html>"""

        out_path = Path(out_file_str).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info("Generated HTML report at %s", out_path)
        return str(out_path)

    @classmethod
    def generate_json_report(
        cls,
        doc_or_tol: Union[ToleranceResult, DocumentModel],
        findings_or_path: Optional[Any] = None,
        session_id: Optional[str] = None,
        output_path: Optional[str] = None,
        profile_identifier: Optional[str] = None,
        custom_meta: Optional[Dict[str, str]] = None,
        custom_max_tolerance: Optional[float] = None
    ) -> str:
        """Generates structured JSON tolerance inspection report."""
        if isinstance(doc_or_tol, ToleranceResult):
            res = doc_or_tol
            out_file_str = findings_or_path if isinstance(findings_or_path, str) else output_path
        else:
            doc = doc_or_tol
            f_list = findings_or_path if isinstance(findings_or_path, list) else []
            s_id = session_id or "SG-INSPECTION"
            out_file_str = output_path
            res = ToleranceCalculator.calculate(
                session_id=s_id,
                doc=doc,
                findings=f_list,
                profile_identifier=profile_identifier,
                custom_meta=custom_meta,
                custom_max_tolerance=custom_max_tolerance
            )

        report_data = res.to_dict()
        out_path = Path(out_file_str).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
        logger.info("Generated JSON report at %s", out_path)
        return str(out_path)
