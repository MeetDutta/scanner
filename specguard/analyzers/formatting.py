"""
Formatting Analysis Engine for SpecGuard.
Checks font consistency, font-size outliers, heading styles, margins, and page layout anomalies.
"""

from typing import List, Dict, Any
from collections import Counter
import logging

from specguard.analyzers.base import BaseAnalyzer
from specguard.core.models import DocumentModel, Finding, FindingCategory, SeverityLevel, BBox

logger = logging.getLogger(__name__)


class FormattingAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Formatting Analyzer"

    @property
    def category(self) -> FindingCategory:
        return FindingCategory.FORMATTING

    def analyze(self, doc: DocumentModel, context: Dict[str, Any] = None) -> List[Finding]:
        findings: List[Finding] = []
        if not doc.pages:
            return findings

        # Collect body font names and sizes
        body_fonts = Counter()
        body_sizes = Counter()
        heading_fonts = Counter()

        for page in doc.pages:
            for block in page.blocks:
                # Disregard single character or tiny artifacts
                if len(block.text.strip()) < 4:
                    continue
                if block.font_size > 13.0 or block.is_bold:
                    heading_fonts[block.font_name] += 1
                else:
                    body_fonts[block.font_name] += 1
                    body_sizes[block.font_size] += 1

        primary_body_font = body_fonts.most_common(1)[0][0] if body_fonts else "Unknown"
        primary_body_size = body_sizes.most_common(1)[0][0] if body_sizes else 11.0

        finding_counter = 1

        # Check font consistency and font size outliers
        for page in doc.pages:
            for block in page.blocks:
                txt = block.text.strip()
                if len(txt) < 15:
                    continue

                # Flag rogue body fonts
                if not block.is_bold and block.font_size <= 13.0:
                    if block.font_name != primary_body_font and body_fonts[block.font_name] < max(2, len(doc.pages)):
                        findings.append(Finding(
                            finding_id=f"FMT-FNT-{finding_counter:03d}",
                            category=self.category.value,
                            domain="General",
                            location=f"Page {page.page_num}, Line {block.line_num or block.block_id}",
                            page=page.page_num,
                            bbox=block.bbox,
                            original_content=txt[:80] + ("..." if len(txt) > 80 else ""),
                            detected_value=f"Font: {block.font_name}",
                            expected_value=f"Primary Body Font: {primary_body_font}",
                            deviation=f"Mismatched typeface '{block.font_name}'",
                            severity=SeverityLevel.LOW.value,
                            confidence=0.88,
                            explanation=f"Text paragraph is formatted with '{block.font_name}' instead of the document standard font '{primary_body_font}'.",
                            suggested_correction=f"Normalize font to '{primary_body_font}'.",
                            rule_reference="ISO 216 / Style Guide §4.1 (Font Uniformity)",
                            priority_score=2.2
                        ))
                        finding_counter += 1

                    # Flag abnormal body font sizes (e.g. 8pt or 16pt body text)
                    if abs(block.font_size - primary_body_size) >= 2.5:
                        findings.append(Finding(
                            finding_id=f"FMT-SIZ-{finding_counter:03d}",
                            category=self.category.value,
                            domain="General",
                            location=f"Page {page.page_num}, Block {block.block_id}",
                            page=page.page_num,
                            bbox=block.bbox,
                            original_content=txt[:80] + ("..." if len(txt) > 80 else ""),
                            detected_value=f"{block.font_size:.1f} pt",
                            expected_value=f"{primary_body_size:.1f} pt",
                            deviation=f"{block.font_size - primary_body_size:+.1f} pt deviation",
                            severity=SeverityLevel.LOW.value,
                            confidence=0.85,
                            explanation=f"Body paragraph size ({block.font_size:.1f} pt) deviates significantly from primary document size ({primary_body_size:.1f} pt).",
                            suggested_correction=f"Adjust text size to standard {primary_body_size:.1f} pt.",
                            rule_reference="Engineering Document Standard §3.2",
                            priority_score=2.0
                        ))
                        finding_counter += 1

        # Check page margin consistency
        page_margins = []
        for page in doc.pages:
            if page.blocks:
                left_m = min(b.bbox.x0 for b in page.blocks)
                right_m = max(0.0, page.width - max(b.bbox.x1 for b in page.blocks))
                page_margins.append((page.page_num, left_m, right_m))

        if len(page_margins) > 1:
            base_left = page_margins[0][1]
            for p_num, l_m, r_m in page_margins[1:]:
                if abs(l_m - base_left) > 25.0:
                    findings.append(Finding(
                        finding_id=f"FMT-MRG-{finding_counter:03d}",
                        category=self.category.value,
                        domain="General",
                        location=f"Page {p_num}",
                        page=p_num,
                        bbox=BBox(x0=l_m, y0=40.0, x1=l_m + 50.0, y1=80.0),
                        original_content=f"Left Margin: {l_m:.1f} pt",
                        detected_value=f"{l_m:.1f} pt",
                        expected_value=f"{base_left:.1f} pt",
                        deviation=f"{l_m - base_left:+.1f} pt shift",
                        severity=SeverityLevel.LOW.value,
                        confidence=0.90,
                        explanation=f"Page {p_num} left margin deviates by {abs(l_m - base_left):.1f} pt from page 1 standard margin ({base_left:.1f} pt).",
                        suggested_correction=f"Align page margins to {base_left:.1f} pt.",
                        rule_reference="Document Layout Guide §2 (Margins)",
                        priority_score=2.1
                    ))
                    finding_counter += 1

        return findings
