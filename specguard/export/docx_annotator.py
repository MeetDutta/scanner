"""
Annotated DOCX Generator for SpecGuard.
Embeds engineering findings, in-line paragraph error highlights, 
and compliance appendices into DOCX documents.
"""

from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Union
import logging
import docx
from docx.enum.text import WD_COLOR_INDEX
from docx.shared import RGBColor, Pt

from specguard.core.models import Finding, SeverityLevel

logger = logging.getLogger(__name__)

DOCX_HIGHLIGHT_MAP = {
    SeverityLevel.CRITICAL.value: WD_COLOR_INDEX.RED,
    SeverityLevel.HIGH.value: WD_COLOR_INDEX.PINK,
    SeverityLevel.MEDIUM.value: WD_COLOR_INDEX.YELLOW,
    SeverityLevel.LOW.value: WD_COLOR_INDEX.TURQUOISE,
    SeverityLevel.INFORMATIONAL.value: WD_COLOR_INDEX.GRAY_25,
}

DOCX_RGB_MAP = {
    SeverityLevel.CRITICAL.value: RGBColor(200, 30, 30),
    SeverityLevel.HIGH.value: RGBColor(220, 80, 20),
    SeverityLevel.MEDIUM.value: RGBColor(180, 130, 10),
    SeverityLevel.LOW.value: RGBColor(30, 100, 200),
    SeverityLevel.INFORMATIONAL.value: RGBColor(100, 100, 100),
}


def _get_val(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class DOCXAnnotator:
    """Creates an annotated DOCX with finding callouts and compliance appendices."""

    @staticmethod
    def create_annotated_docx(
        original_docx_path: str,
        output_path: str,
        findings: List[Union[Finding, Dict[str, Any]]]
    ) -> str:
        doc = docx.Document(original_docx_path)

        # 1. Add an executive compliance summary section at the start
        if doc.paragraphs:
            p_head = doc.paragraphs[0].insert_paragraph_before("SpecGuard Engineering Compliance Audit Summary")
            p_head.style = 'Heading 1'
            meta_p = p_head.insert_paragraph_before(
                f"Audit Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Offline Analysis Mode | Total Findings: {len(findings)}"
            )
            meta_p.runs[0].font.italic = True
            meta_p.runs[0].font.size = Pt(9.5)
        else:
            p_head = doc.add_paragraph("SpecGuard Engineering Compliance Audit Summary")
            p_head.style = 'Heading 1'

        # Insert findings summary table
        table = doc.add_table(rows=1, cols=5)
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = "Finding ID"
        hdr_cells[1].text = "Severity"
        hdr_cells[2].text = "Category"
        hdr_cells[3].text = "Deviation"
        hdr_cells[4].text = "Correction"

        for cell in hdr_cells:
            for p in cell.paragraphs:
                for r in p.runs:
                    r.bold = True

        matched_findings = set()

        for f in findings[:40]:  # Top prioritized findings
            f_id = str(_get_val(f, "finding_id", "FINDING"))
            sev = str(_get_val(f, "severity", "Medium")).title()
            cat = str(_get_val(f, "category", "Compliance"))
            dev = str(_get_val(f, "deviation", "") or _get_val(f, "detected_value", "Deviation detected"))
            corr = str(_get_val(f, "suggested_correction", "") or "Review specification")

            row_cells = table.add_row().cells
            row_cells[0].text = f_id
            row_cells[1].text = sev
            row_cells[2].text = cat
            row_cells[3].text = dev[:120]
            row_cells[4].text = corr[:120]

        # 2. In-line text highlighting across document body paragraphs
        for p in doc.paragraphs[3:]:  # Skip the audit header and table paragraphs
            p_text_lower = p.text.lower()
            if not p_text_lower.strip():
                continue

            for f in findings:
                f_id = str(_get_val(f, "finding_id", "FINDING"))
                sev = str(_get_val(f, "severity", "Medium")).title()
                hl_color = DOCX_HIGHLIGHT_MAP.get(sev, WD_COLOR_INDEX.YELLOW)
                tag_rgb = DOCX_RGB_MAP.get(sev, RGBColor(200, 30, 30))

                orig = str(_get_val(f, "original_content", "") or "").strip()
                detected = str(_get_val(f, "detected_value", "") or "").strip()
                corr = str(_get_val(f, "suggested_correction", "") or "").strip()
                expl = str(_get_val(f, "explanation", "") or "").strip()

                candidates = []
                if detected and len(detected) >= 3 and detected.lower() not in ["parameter absent", "section absent", "missing", "absent", "[document structure]"]:
                    candidates.append(detected)
                if orig and len(orig) >= 3 and orig.lower() not in ["[document structure]", "missing", "absent"]:
                    candidates.append(orig[:50])

                hit = False
                for cand in candidates:
                    if cand.lower() in p_text_lower:
                        hit = True
                        break

                if hit and f_id not in matched_findings:
                    matched_findings.add(f_id)
                    # Highlight all runs containing target text
                    for run in p.runs:
                        for cand in candidates:
                            if cand.lower() in run.text.lower():
                                run.font.highlight_color = hl_color
                                break
                    # Append an inline callout badge at the end of the paragraph
                    callout_run = p.add_run(f" [⚠️ SpecGuard {sev.upper()} ({f_id}): {corr or expl}] ")
                    callout_run.bold = True
                    callout_run.font.size = Pt(9)
                    callout_run.font.color.rgb = tag_rgb

        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(out_file))
        logger.info("Saved annotated DOCX to %s with %d in-line highlights", out_file, len(matched_findings))
        return str(out_file)

