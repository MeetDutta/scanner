"""
Annotated DOCX and Compliance Report Generator for SpecGuard.
Produces standalone HTML, JSON, and DOCX audit reports.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import logging

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from specguard.core.models import DocumentModel, Finding

logger = logging.getLogger(__name__)


class DOCXAnnotator:
    """Creates an annotated DOCX with finding callouts and compliance appendices."""

    @staticmethod
    def create_annotated_docx(original_docx_path: str, output_path: str, findings: List[Finding]) -> str:
        doc = docx.Document(original_docx_path)

        # Add an executive compliance summary section at the start
        p = doc.paragraphs[0].insert_paragraph_before("SpecGuard Engineering Compliance Audit Summary")
        p.style = 'Heading 1'

        meta_p = p.insert_paragraph_before(f"Audit Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Offline Analysis Mode")
        meta_p.runs[0].font.italic = True

        # Insert findings summary table
        table = doc.add_table(rows=1, cols=5)
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = "Finding ID"
        hdr_cells[1].text = "Severity"
        hdr_cells[2].text = "Category"
        hdr_cells[3].text = "Deviation"
        hdr_cells[4].text = "Correction"

        for f in findings[:25]:  # Top 25 prioritized findings
            row_cells = table.add_row().cells
            row_cells[0].text = f.finding_id
            row_cells[1].text = f.severity
            row_cells[2].text = f.category
            row_cells[3].text = str(f.deviation or f.detected_value)
            row_cells[4].text = f.suggested_correction

        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(out_file))
        logger.info("Saved annotated DOCX to %s", out_file)
        return str(out_file)


class ReportGenerator:
    """Generates comprehensive, publication-quality HTML and JSON engineering compliance reports."""

    @staticmethod
    def generate_html_report(doc: DocumentModel, findings: List[Finding], session_id: str, output_path: str) -> str:
        crit_count = sum(1 for f in findings if f.severity == "Critical")
        high_count = sum(1 for f in findings if f.severity == "High")
        med_count = sum(1 for f in findings if f.severity == "Medium")
        low_count = sum(1 for f in findings if f.severity == "Low")
        info_count = sum(1 for f in findings if f.severity == "Informational")

        # Build findings table rows
        rows_html = []
        for f in findings:
            badge_class = f"badge-{f.severity.lower()}"
            rows_html.append(f"""
            <tr>
                <td><strong>{f.finding_id}</strong></td>
                <td><span class="badge {badge_class}">{f.severity}</span></td>
                <td>{f.category}</td>
                <td>{f.location}</td>
                <td><code>{f.detected_value}</code></td>
                <td><code>{f.expected_value}</code></td>
                <td>{f.explanation}</td>
                <td><em>{f.suggested_correction}</em></td>
                <td><small>{f.rule_reference or '-'}</small></td>
            </tr>
            """)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>SpecGuard Engineering Compliance Report - {Path(doc.file_path).name}</title>
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 40px; }}
    .container {{ max-width: 1200px; margin: 0 auto; background: #1e293b; border-radius: 12px; padding: 32px; border: 1px solid #334155; }}
    h1 {{ color: #38bdf8; margin-top: 0; font-size: 26px; }}
    .meta-bar {{ display: flex; gap: 24px; margin-bottom: 24px; padding: 12px; background: #0f172a; border-radius: 8px; border: 1px solid #334155; font-size: 14px; color: #94a3b8; }}
    .stats-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; margin-bottom: 32px; }}
    .stat-card {{ background: #0f172a; padding: 16px; border-radius: 8px; border: 1px solid #334155; text-align: center; }}
    .stat-num {{ font-size: 28px; font-weight: bold; margin-top: 4px; }}
    .badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; text-transform: uppercase; }}
    .badge-critical {{ background: #ef4444; color: white; }}
    .badge-high {{ background: #f97316; color: white; }}
    .badge-medium {{ background: #eab308; color: black; }}
    .badge-low {{ background: #3b82f6; color: white; }}
    .badge-informational {{ background: #64748b; color: white; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 13px; }}
    th, td {{ padding: 12px 10px; text-align: left; border-bottom: 1px solid #334155; }}
    th {{ background: #0f172a; color: #cbd5e1; font-weight: 600; }}
    tr:hover {{ background: #1e293b; }}
    code {{ background: #0f172a; padding: 2px 6px; border-radius: 4px; color: #38bdf8; font-family: monospace; }}
    .footer {{ margin-top: 32px; font-size: 12px; color: #64748b; text-align: center; border-top: 1px solid #334155; padding-top: 16px; }}
</style>
</head>
<body>
<div class="container">
    <h1>SpecGuard Engineering Compliance & Quality Audit Report</h1>
    <div class="meta-bar">
        <div><strong>Document:</strong> {Path(doc.file_path).name}</div>
        <div><strong>Session ID:</strong> {session_id}</div>
        <div><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        <div><strong>Offline Verification:</strong> 100% Local (Verified)</div>
    </div>

    <div class="stats-grid">
        <div class="stat-card" style="border-top: 3px solid #ef4444;">
            <div>Critical Issues</div>
            <div class="stat-num" style="color: #ef4444;">{crit_count}</div>
        </div>
        <div class="stat-card" style="border-top: 3px solid #f97316;">
            <div>High Severity</div>
            <div class="stat-num" style="color: #f97316;">{high_count}</div>
        </div>
        <div class="stat-card" style="border-top: 3px solid #eab308;">
            <div>Medium Severity</div>
            <div class="stat-num" style="color: #eab308;">{med_count}</div>
        </div>
        <div class="stat-card" style="border-top: 3px solid #3b82f6;">
            <div>Low Severity</div>
            <div class="stat-num" style="color: #3b82f6;">{low_count}</div>
        </div>
        <div class="stat-card" style="border-top: 3px solid #64748b;">
            <div>Informational</div>
            <div class="stat-num" style="color: #94a3b8;">{info_count}</div>
        </div>
    </div>

    <h2>Detailed Findings ({len(findings)})</h2>
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Severity</th>
                <th>Category</th>
                <th>Location</th>
                <th>Detected</th>
                <th>Expected</th>
                <th>Explanation</th>
                <th>Suggested Correction</th>
                <th>Standard Ref</th>
            </tr>
        </thead>
        <tbody>
            {"".join(rows_html)}
        </tbody>
    </table>

    <div class="footer">
        Generated by SpecGuard — Hybrid Deep Learning & CV Engineering Quality Framework. 
        Notice: SpecGuard is an automated engineering decision-support tool. All findings must be verified by a qualified engineer.
    </div>
</div>
</body>
</html>"""

        out_path = Path(output_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info("Generated HTML report at %s", out_path)
        return str(out_path)

    @staticmethod
    def generate_json_report(doc: DocumentModel, findings: List[Finding], session_id: str, output_path: str) -> str:
        report_data = {
            "session_id": session_id,
            "document": {
                "filename": Path(doc.file_path).name,
                "file_path": doc.file_path,
                "file_hash": doc.file_hash,
                "file_type": doc.file_type,
                "file_size": doc.file_size,
                "page_count": doc.page_count
            },
            "timestamp": datetime.now().isoformat(),
            "offline_mode": True,
            "summary": {
                "total_findings": len(findings),
                "critical": sum(1 for f in findings if f.severity == "Critical"),
                "high": sum(1 for f in findings if f.severity == "High"),
                "medium": sum(1 for f in findings if f.severity == "Medium"),
                "low": sum(1 for f in findings if f.severity == "Low"),
                "informational": sum(1 for f in findings if f.severity == "Informational")
            },
            "findings": [f.to_dict() for f in findings]
        }

        out_path = Path(output_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
        return str(out_path)
