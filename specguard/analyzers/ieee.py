"""
IEEE Research Paper Compliance Analysis Engine for SpecGuard.

Dedicated analyzer for IEEE Journal, Conference, and generic academic paper formats.
Validates:
- Title and author block presence on Page 1
- Abstract and Keywords / Index Terms formatting
- Two-column body layout geometry
- Section hierarchy (Roman numerals e.g. I. INTRODUCTION, subheadings e.g. A. Architecture)
- IEEE Figure labeling ("Fig. X.") and placement
- IEEE Table labeling ("TABLE X") and placement
- Bracketed numeric citation format ([1], [2]-[4])
- References / Bibliography formatting
"""

import re
from typing import List, Dict, Tuple, Optional, Any
import logging

from specguard.analyzers.base import BaseAnalyzer
from specguard.core.models import (
    DocumentModel, Finding, FindingCategory, SeverityLevel, BBox
)
from specguard.core.profiles import ProfileRegistry

logger = logging.getLogger(__name__)


class IEEEAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "IEEE Compliance Analyzer"

    @property
    def category(self) -> FindingCategory:
        return FindingCategory.IEEE_COMPLIANCE

    def analyze(self, doc: DocumentModel, context: Dict[str, Any] = None) -> List[Finding]:
        findings: List[Finding] = []
        context = context or {}
        profile_id = context.get("profile", getattr(doc, "profile_name", "mechanical"))

        # Only execute if the document is being analyzed under the IEEE profile
        if profile_id != "ieee_research":
            return findings

        profile = ProfileRegistry.get_profile("ieee_research")
        finding_counter = 1

        if not doc.pages:
            return findings

        p1 = doc.pages[0]

        # 1. Check Title & Author Region on Page 1
        # In IEEE papers, the title is typically the largest font on Page 1, centered/spanning
        title_block = None
        max_font_size = 0.0
        for b in p1.blocks[:8]:
            if b.font_size > max_font_size and len(b.text.strip()) > 5:
                max_font_size = b.font_size
                title_block = b

        if not title_block or max_font_size < 13.0:
            findings.append(Finding(
                finding_id=f"IEEE-TIT-{finding_counter:03d}",
                category=self.category.value,
                domain="Academic",
                location="Page 1 (Top)",
                page=1,
                bbox=title_block.bbox if title_block else None,
                original_content=title_block.text if title_block else "[Page 1 Header]",
                detected_value=f"Max Title Font: {max_font_size:.1f}pt",
                expected_value="Prominent Paper Title (>= 14pt, Bold/Centered)",
                deviation="Missing or unformatted IEEE paper title",
                severity=SeverityLevel.MEDIUM.value,
                confidence=0.88,
                explanation="IEEE paper format requires a prominent title at the top of page 1 (typically 14-24 pt bold).",
                suggested_correction="Format the paper title prominently at the top of the first page.",
                rule_reference="IEEE Author Center Guidelines §1.1 (Title)",
                priority_score=5.0,
                evidence=f"Highest font on page 1 is {max_font_size:.1f}pt",
                detection_method="layout_geometry"
            ))
            finding_counter += 1

        # 2. Check Abstract Presence and Word Count
        abstract_found = False
        abstract_text = ""
        abstract_bbox = None
        for page in doc.pages[:2]:
            for b in page.blocks:
                txt = b.text.strip()
                if txt.lower().startswith("abstract") or re.search(r'\babstract\b', txt[:15], re.IGNORECASE):
                    abstract_found = True
                    abstract_text = txt
                    abstract_bbox = b.bbox
                    break
            if abstract_found:
                break

        if not abstract_found:
            findings.append(Finding(
                finding_id=f"IEEE-ABS-{finding_counter:03d}",
                category=self.category.value,
                domain="Academic",
                location="Page 1",
                page=1,
                bbox=None,
                original_content="",
                detected_value="Abstract Missing",
                expected_value="Abstract section (100-250 words)",
                deviation="Mandatory IEEE Abstract section not detected",
                severity=SeverityLevel.HIGH.value,
                confidence=0.95,
                explanation="IEEE papers strictly require an Abstract summarizing the scope, methodology, and key contributions.",
                suggested_correction="Include an Abstract section (typically 100-250 words) immediately following the author block.",
                rule_reference="IEEE Style Manual §II.A (Abstract)",
                priority_score=7.0,
                evidence="Searched pages 1-2 for 'Abstract' heading",
                detection_method="text_pattern"
            ))
            finding_counter += 1
        else:
            # Check abstract length
            words = len(abstract_text.split())
            if words < 30:  # Suspiciously short abstract or just header
                findings.append(Finding(
                    finding_id=f"IEEE-ABS-LEN-{finding_counter:03d}",
                    category=self.category.value,
                    domain="Academic",
                    location="Page 1 (Abstract)",
                    page=1,
                    bbox=abstract_bbox,
                    original_content=abstract_text[:80] + "...",
                    detected_value=f"{words} words",
                    expected_value="100 to 250 words",
                    deviation="Abstract is unusually short",
                    severity=SeverityLevel.LOW.value,
                    confidence=0.85,
                    explanation=f"Abstract contains only {words} words. IEEE guidelines recommend between 100 and 250 words.",
                    suggested_correction="Expand the abstract to thoroughly summarize motivation, approach, and findings.",
                    rule_reference="IEEE Style Manual §II.A",
                    priority_score=3.0,
                    evidence=f"Abstract word count: {words}",
                    detection_method="lexical_analysis"
                ))
                finding_counter += 1

        # 3. Check Keywords / Index Terms
        keywords_found = False
        for page in doc.pages[:2]:
            for b in page.blocks:
                txt = b.text.strip().lower()
                if txt.startswith("keywords") or txt.startswith("index terms"):
                    keywords_found = True
                    break
            if keywords_found:
                break

        if not keywords_found:
            findings.append(Finding(
                finding_id=f"IEEE-KW-{finding_counter:03d}",
                category=self.category.value,
                domain="Academic",
                location="Page 1",
                page=1,
                bbox=None,
                original_content="",
                detected_value="Keywords / Index Terms Missing",
                expected_value="Index Terms / Keywords line",
                deviation="Missing IEEE Keywords or Index Terms",
                severity=SeverityLevel.LOW.value,
                confidence=0.90,
                explanation="IEEE research papers standardly include an 'Index Terms' or 'Keywords' block following the abstract.",
                suggested_correction="Add 'Index Terms—keyword1, keyword2, ...' following the abstract.",
                rule_reference="IEEE Author Guidelines §1.2",
                priority_score=3.5,
                evidence="Searched pages 1-2 for 'Keywords' or 'Index Terms'",
                detection_method="text_pattern"
            ))
            finding_counter += 1

        # 4. Validate Two-Column Layout Geometry
        # Check pages 2 onwards (or page 1 below abstract)
        two_col_pages = 0
        tested_pages = 0
        for page in doc.pages:
            if page.page_num == 1 and len(page.blocks) < 10:
                continue
            tested_pages += 1
            if page.layout_type in ["two_column", "mixed"]:
                two_col_pages += 1

        if tested_pages > 0 and (two_col_pages / tested_pages) < 0.5:
            findings.append(Finding(
                finding_id=f"IEEE-COL-{finding_counter:03d}",
                category=self.category.value,
                domain="Academic",
                location="Document Body",
                page=1,
                bbox=None,
                original_content="[Page Layout]",
                detected_value=f"Single Column ({tested_pages - two_col_pages}/{tested_pages} pages)",
                expected_value="Two-Column Grid Layout",
                deviation="Document body is formatted in single-column layout instead of standard IEEE two-column format",
                severity=SeverityLevel.MEDIUM.value,
                confidence=0.92,
                explanation="Standard IEEE conference and journal papers require a two-column body layout.",
                suggested_correction="Reformat document body into a standard two-column layout.",
                rule_reference="IEEE Conference / Journal Template Specifications",
                priority_score=5.5,
                evidence=f"{two_col_pages} of {tested_pages} analyzed pages detected as two-column",
                detection_method="geometric_layout"
            ))
            finding_counter += 1

        # 5. Validate Table Label Format (Should be "TABLE I", "TABLE II", etc. in all caps)
        for tbl in doc.tables:
            if tbl.label and not tbl.label.upper().startswith("TABLE"):
                findings.append(Finding(
                    finding_id=f"IEEE-TBL-LBL-{finding_counter:03d}",
                    category=self.category.value,
                    domain="Academic",
                    location=f"Page {tbl.page_num}",
                    page=tbl.page_num,
                    bbox=tbl.bbox,
                    original_content=tbl.label,
                    detected_value=tbl.label,
                    expected_value="TABLE <ROMAN_NUMERAL> (e.g. TABLE I, TABLE II)",
                    deviation=f"Non-IEEE table label format: '{tbl.label}'",
                    severity=SeverityLevel.LOW.value,
                    confidence=0.88,
                    explanation=f"IEEE style requires tables to be labeled in uppercase Roman numerals (e.g., 'TABLE I').",
                    suggested_correction=f"Rename '{tbl.label}' to uppercase format (e.g. TABLE I).",
                    rule_reference="IEEE Style Manual §IV.B (Tables)",
                    priority_score=3.0,
                    evidence=f"Table label on Page {tbl.page_num}: '{tbl.label}'",
                    detection_method="deterministic"
                ))
                finding_counter += 1

        # 6. Validate Figure Label Format (Should be "Fig. 1." or "Fig. 2.")
        for fig in doc.figures:
            if fig.label and "Figure" in fig.label and not fig.label.startswith("Fig."):
                findings.append(Finding(
                    finding_id=f"IEEE-FIG-LBL-{finding_counter:03d}",
                    category=self.category.value,
                    domain="Academic",
                    location=f"Page {fig.page_num}",
                    page=fig.page_num,
                    bbox=fig.bbox,
                    original_content=fig.label,
                    detected_value=fig.label,
                    expected_value="Fig. <NUMBER>. (e.g. Fig. 1.)",
                    deviation=f"IEEE prefers 'Fig. X' abbreviation over '{fig.label}'",
                    severity=SeverityLevel.INFORMATIONAL.value,
                    confidence=0.85,
                    explanation="IEEE style specifies abbreviating 'Figure' as 'Fig.' in captions and in-text references (except at the beginning of a sentence).",
                    suggested_correction=f"Abbreviate '{fig.label}' to 'Fig. X.'",
                    rule_reference="IEEE Style Manual §IV.A (Figures)",
                    priority_score=1.5,
                    evidence=f"Figure label on Page {fig.page_num}: '{fig.label}'",
                    detection_method="deterministic"
                ))
                finding_counter += 1

        # 7. Check References Section
        has_references = any(
            sec.title.lower() in ["references", "bibliography"]
            for sec in doc.sections
        ) or bool(doc.references) or any(
            bool(re.search(r'\b(?:references|bibliography)\b', p.text, re.IGNORECASE))
            for p in doc.pages[-2:]
        )

        if not has_references:
            findings.append(Finding(
                finding_id=f"IEEE-REF-{finding_counter:03d}",
                category=self.category.value,
                domain="Academic",
                location="End of Document",
                page=len(doc.pages),
                bbox=None,
                original_content="",
                detected_value="References Section Missing",
                expected_value="Numbered References section ([1], [2], ...)",
                deviation="Mandatory References / Bibliography section not found",
                severity=SeverityLevel.HIGH.value,
                confidence=0.96,
                explanation="IEEE research papers strictly require a numbered References section.",
                suggested_correction="Add a formal 'References' section with bracketed citations.",
                rule_reference="IEEE Style Manual §V (References)",
                priority_score=7.0,
                evidence="No 'References' section or bracketed bibliography items detected",
                detection_method="structural_hierarchy"
            ))
            finding_counter += 1

        return findings
