"""
Document Structure Analysis Engine for SpecGuard.
Parses heading hierarchies, checks for broken numbering sequences (e.g. 3.1 -> 3.3),
depth jumps, duplicate section headers, and missing mandatory engineering sections.
"""

import re
from typing import List, Dict, Tuple, Optional, Any
import logging

from specguard.analyzers.base import BaseAnalyzer
from specguard.core.models import DocumentModel, Finding, FindingCategory, SeverityLevel, BBox

logger = logging.getLogger(__name__)

# Standard engineering specification mandatory sections
REQUIRED_SECTIONS = [
    "Scope",
    "Requirements",
    "Testing"
]


class StructureAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Structure Analyzer"

    @property
    def category(self) -> FindingCategory:
        return FindingCategory.STRUCTURE

    def analyze(self, doc: DocumentModel, context: Dict[str, Any] = None) -> List[Finding]:
        findings: List[Finding] = []
        headings: List[Tuple[str, List[int], int, BBox, str]] = []  # (raw_text, [num_parts], page, bbox, title)

        # Regex for section numbers e.g. "1", "1.1", "2.3.4", "Section 3.1"
        num_pattern = re.compile(r'^(?:(?:Section|Clause)\s+)?(\d+(?:\.\d+)*)\s+([A-Za-z0-9\s,\-\(\)]+)$', re.IGNORECASE)

        for page in doc.pages:
            for block in page.blocks:
                txt = block.text.strip()
                if not txt:
                    continue

                # Check if block looks like a heading (bold, larger font, or explicit section numbering)
                match = num_pattern.match(txt)
                if match:
                    num_str = match.group(1)
                    title = match.group(2).strip()
                    parts = [int(p) for p in num_str.split(".")]
                    headings.append((txt, parts, page.page_num, block.bbox, title))
                elif (block.is_bold or block.font_size >= 13.0) and len(txt) < 80 and not txt.endswith("."):
                    # Standalone title without numbering
                    headings.append((txt, [], page.page_num, block.bbox, txt))

        finding_counter = 1

        # 1. Check for broken sequence numbers (e.g., 3.1 -> 3.3)
        for i in range(len(headings) - 1):
            curr_txt, curr_parts, curr_page, curr_bbox, _ = headings[i]
            next_txt, next_parts, next_page, next_bbox, _ = headings[i + 1]

            if curr_parts and next_parts:
                # Same hierarchy prefix (e.g. 3.1 and 3.3)
                if len(curr_parts) == len(next_parts) and curr_parts[:-1] == next_parts[:-1]:
                    curr_last = curr_parts[-1]
                    next_last = next_parts[-1]
                    if next_last > curr_last + 1:
                        missing_sec = ".".join(str(p) for p in curr_parts[:-1] + [curr_last + 1])
                        findings.append(Finding(
                            finding_id=f"STR-NUM-{finding_counter:03d}",
                            category=self.category.value,
                            domain="General",
                            location=f"Page {next_page}",
                            page=next_page,
                            bbox=next_bbox,
                            original_content=next_txt,
                            detected_value=f"Section {'.'.join(str(p) for p in next_parts)}",
                            expected_value=f"Section {missing_sec}",
                            deviation=f"Missing section sequence {missing_sec}",
                            severity=SeverityLevel.HIGH.value,
                            confidence=0.95,
                            explanation=f"Section numbering jump detected from {'.'.join(str(p) for p in curr_parts)} directly to {'.'.join(str(p) for p in next_parts)}, skipping Section {missing_sec}.",
                            suggested_correction=f"Insert Section {missing_sec} or renumber {'.'.join(str(p) for p in next_parts)} to {missing_sec}.",
                            rule_reference="Engineering Documentation Hierarchy Standard §2.1",
                            priority_score=6.5
                        ))
                        finding_counter += 1

                # Check depth jumps (e.g. 1 -> 1.1.1 without 1.1)
                elif len(next_parts) > len(curr_parts) + 1 and next_parts[:len(curr_parts)] == curr_parts:
                    findings.append(Finding(
                        finding_id=f"STR-DEP-{finding_counter:03d}",
                        category=self.category.value,
                        domain="General",
                        location=f"Page {next_page}",
                        page=next_page,
                        bbox=next_bbox,
                        original_content=next_txt,
                        detected_value=f"Depth level {len(next_parts)}",
                        expected_value=f"Depth level {len(curr_parts) + 1}",
                        deviation="Hierarchy depth jump",
                        severity=SeverityLevel.MEDIUM.value,
                        confidence=0.90,
                        explanation=f"Heading jump from depth {len(curr_parts)} ({curr_txt}) directly to depth {len(next_parts)} ({next_txt}) without intermediate level.",
                        suggested_correction="Add intermediate section or adjust outline depth.",
                        rule_reference="ISO/IEC Document Structure Guide §3.4",
                        priority_score=4.5
                    ))
                    finding_counter += 1

        # 2. Check for duplicate headings
        seen_headings: Dict[str, Tuple[int, BBox]] = {}
        for raw_txt, parts, p_num, bbox, title in headings:
            norm_key = re.sub(r'\s+', ' ', raw_txt.lower())
            if norm_key in seen_headings:
                prev_page, prev_bbox = seen_headings[norm_key]
                findings.append(Finding(
                    finding_id=f"STR-DUP-{finding_counter:03d}",
                    category=self.category.value,
                    domain="General",
                    location=f"Page {p_num}",
                    page=p_num,
                    bbox=bbox,
                    original_content=raw_txt,
                    detected_value=raw_txt,
                    expected_value="Unique section title",
                    deviation="Duplicate section heading",
                    severity=SeverityLevel.MEDIUM.value,
                    confidence=0.92,
                    explanation=f"Duplicate section header '{raw_txt}' already defined on Page {prev_page}.",
                    suggested_correction=f"Disambiguate or merge with Page {prev_page} section.",
                    rule_reference="Engineering Documentation Standard §2.4",
                    priority_score=4.0
                ))
                finding_counter += 1
            else:
                seen_headings[norm_key] = (p_num, bbox)

        # 3. Check for mandatory engineering sections
        all_titles_lower = " ".join(h[4].lower() for h in headings)
        for req in REQUIRED_SECTIONS:
            if req.lower() not in all_titles_lower:
                findings.append(Finding(
                    finding_id=f"STR-REQ-{finding_counter:03d}",
                    category=self.category.value,
                    domain="General",
                    location="Document Outline",
                    page=1,
                    bbox=None,
                    original_content="[Document Structure]",
                    detected_value="Section Missing",
                    expected_value=f"Mandatory Section: '{req}'",
                    deviation=f"Absence of required section '{req}'",
                    severity=SeverityLevel.HIGH.value,
                    confidence=0.88,
                    explanation=f"Engineering specification is missing mandatory standard section '{req}'.",
                    suggested_correction=f"Add a '{req}' section outlining engineering constraints and criteria.",
                    rule_reference="ISO 9001 / IEEE 830 Engineering Specification Standard §5.1",
                    priority_score=6.0
                ))
                finding_counter += 1

        return findings
