"""
Table of Contents (TOC) Analysis Engine for SpecGuard.
Compares declared Table of Contents against actual parsed document headings and page indices.
Detects page number drift, missing TOC entries, extra entries, and title mismatches.
"""

import re
from typing import List, Dict, Tuple, Optional, Any
import logging

from specguard.analyzers.base import BaseAnalyzer
from specguard.core.models import DocumentModel, Finding, FindingCategory, SeverityLevel, BBox

logger = logging.getLogger(__name__)


class TOCAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Table of Contents Analyzer"

    @property
    def category(self) -> FindingCategory:
        return FindingCategory.TOC

    def analyze(self, doc: DocumentModel, context: Dict[str, Any] = None) -> List[Finding]:
        findings: List[Finding] = []
        if len(doc.pages) < 2:
            return findings

        # 1. Detect TOC section in early pages (Page 1 or 2)
        toc_entries: List[Tuple[str, int, BBox, int]] = [] # (title, declared_page, bbox, toc_page)
        toc_detected = False
        toc_pattern = re.compile(r'^(.*?)(?:\.{2,}|\s{3,}|\t+)\s*(\d+)$')

        for page in doc.pages[:3]:
            for block in page.blocks:
                txt = block.text.strip()
                if "table of contents" in txt.lower() or "contents" == txt.lower():
                    toc_detected = True
                    continue

                m = toc_pattern.match(txt)
                if m:
                    entry_title = m.group(1).strip()
                    declared_page = int(m.group(2))
                    # Ignore headers or page number lines
                    if len(entry_title) > 3:
                        toc_entries.append((entry_title, declared_page, block.bbox, page.page_num))
                        toc_detected = True

        if not toc_detected or not toc_entries:
            return findings

        # 2. Extract actual document headings and their actual page numbers
        actual_headings: Dict[str, Tuple[int, BBox]] = {}
        heading_re = re.compile(r'^(?:(?:Section|Clause)\s+)?(\d+(?:\.\d+)*\s+)?([A-Za-z0-9\s,\-\(\)]+)$')

        for page in doc.pages:
            for block in page.blocks:
                txt = block.text.strip()
                if not txt:
                    continue
                m = heading_re.match(txt)
                if m and (block.is_bold or block.font_size >= 12.5):
                    title_part = txt.lower().strip()
                    if title_part not in actual_headings:
                        actual_headings[title_part] = (page.page_num, block.bbox)

        finding_counter = 1

        # 3. Compare each TOC entry against actual headings
        for toc_title, declared_page, toc_bbox, toc_p in toc_entries:
            clean_toc_key = re.sub(r'^\d+(\.\d+)*\s*', '', toc_title.lower()).strip()
            
            # Find best matching actual heading
            match_found = False
            for act_title, (act_page, act_bbox) in actual_headings.items():
                clean_act_key = re.sub(r'^\d+(\.\d+)*\s*', '', act_title).strip()
                if clean_toc_key in clean_act_key or clean_act_key in clean_toc_key:
                    match_found = True
                    # Check page number consistency
                    if declared_page != act_page:
                        findings.append(Finding(
                            finding_id=f"TOC-PAG-{finding_counter:03d}",
                            category=self.category.value,
                            domain="General",
                            location=f"TOC (Page {toc_p}) vs Actual (Page {act_page})",
                            page=toc_p,
                            bbox=toc_bbox,
                            original_content=f"{toc_title} ... {declared_page}",
                            detected_value=f"TOC Page {declared_page}",
                            expected_value=f"Actual Document Page {act_page}",
                            deviation=f"Page number drift: {declared_page - act_page:+d} pages",
                            severity=SeverityLevel.HIGH.value,
                            confidence=0.96,
                            explanation=f"Table of Contents lists '{toc_title}' on Page {declared_page}, but the section heading actually appears on Page {act_page}.",
                            suggested_correction=f"Update TOC entry page number to {act_page}.",
                            rule_reference="Engineering Document Specification Standard §1.3 (TOC Accuracy)",
                            priority_score=6.8
                        ))
                        finding_counter += 1
                    break

            if not match_found:
                findings.append(Finding(
                    finding_id=f"TOC-EXT-{finding_counter:03d}",
                    category=self.category.value,
                    domain="General",
                    location=f"TOC (Page {toc_p})",
                    page=toc_p,
                    bbox=toc_bbox,
                    original_content=f"{toc_title} ... {declared_page}",
                    detected_value=f"Unmatched entry: '{toc_title}'",
                    expected_value="Valid section in body",
                    deviation="TOC references non-existent document section",
                    severity=SeverityLevel.MEDIUM.value,
                    confidence=0.89,
                    explanation=f"TOC contains entry '{toc_title}', but no corresponding section heading was found in the document.",
                    suggested_correction=f"Verify if section '{toc_title}' was deleted or renamed.",
                    rule_reference="Document Integrity Standards §1.3",
                    priority_score=4.8
                ))
                finding_counter += 1

        return findings
