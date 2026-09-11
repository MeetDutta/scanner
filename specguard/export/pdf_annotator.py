"""
Native PDF Annotation Engine for SpecGuard.
Embeds color-coded vector highlight bounding boxes and comment popups into the original PDF.
"""

import pymupdf
from pathlib import Path
from typing import List
import logging

from specguard.core.models import Finding, SeverityLevel

logger = logging.getLogger(__name__)

SEVERITY_RGB = {
    SeverityLevel.CRITICAL.value: (0.86, 0.15, 0.15),  # Crimson Red
    SeverityLevel.HIGH.value: (0.92, 0.35, 0.05),      # Orange
    SeverityLevel.MEDIUM.value: (0.92, 0.70, 0.03),    # Amber
    SeverityLevel.LOW.value: (0.23, 0.51, 0.96),       # Blue
    SeverityLevel.INFORMATIONAL.value: (0.42, 0.45, 0.50) # Gray
}


class PDFAnnotator:
    """Generates an annotated PDF document with visual finding overlays."""

    @staticmethod
    def create_annotated_pdf(original_pdf_path: str, output_path: str, findings: List[Finding]) -> str:
        doc = pymupdf.open(original_pdf_path)

        for finding in findings:
            if not finding.bbox:
                continue

            page_idx = finding.page - 1
            if 0 <= page_idx < len(doc):
                page = doc[page_idx]
                color = SEVERITY_RGB.get(finding.severity, (0.5, 0.5, 0.5))

                rect = pymupdf.Rect(
                    finding.bbox.x0,
                    finding.bbox.y0,
                    finding.bbox.x1,
                    finding.bbox.y1
                )

                # Add visual highlight annotation
                annot = page.add_rect_annot(rect)
                annot.set_colors(stroke=color)
                annot.set_border(width=1.5, dashes=[2, 2] if finding.severity in ["Low", "Informational"] else None)
                annot.set_info(
                    title=f"SpecGuard [{finding.severity}]: {finding.category}",
                    content=(
                        f"ID: {finding.finding_id}\n"
                        f"Deviation: {finding.deviation or 'N/A'}\n"
                        f"Explanation: {finding.explanation}\n"
                        f"Suggested Correction: {finding.suggested_correction}\n"
                        f"Reference: {finding.rule_reference or 'Internal'}"
                    )
                )
                annot.update()

        output_file = Path(output_path).resolve()
        output_file.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_file))
        doc.close()
        logger.info("Saved annotated PDF to %s", output_file)
        return str(output_file)
