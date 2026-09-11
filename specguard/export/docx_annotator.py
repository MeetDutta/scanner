"""
Annotated DOCX Generator for SpecGuard.
Embeds engineering findings, deviations, and compliance appendices into DOCX documents.
"""

from pathlib import Path
from datetime import datetime
from typing import List
import logging
import docx

from specguard.core.models import Finding

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
