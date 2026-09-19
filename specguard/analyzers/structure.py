"""
Document Structure Analysis Engine for SpecGuard.

Parses heading hierarchies, Roman and numeric numbering schemes (e.g. 1., 1.1 or I., A.),
checks for broken numbering sequences, depth jumps, duplicate section headers,
and profile-aware mandatory sections. Populates DocumentModel.sections.
"""

import re
from typing import List, Dict, Tuple, Optional, Any
import logging

from specguard.analyzers.base import BaseAnalyzer
from specguard.core.models import (
    DocumentModel, Finding, FindingCategory, SeverityLevel, BBox, SectionNode
)
from specguard.core.profiles import ProfileRegistry
from specguard.core.location_mapper import LocationMapper

logger = logging.getLogger(__name__)

ROMAN_VALS = {
    'i': 1, 'v': 5, 'x': 10, 'l': 50, 'c': 100, 'd': 500, 'm': 1000
}

def roman_to_int(s: str) -> Optional[int]:
    s = s.lower().strip()
    if not all(c in ROMAN_VALS for c in s):
        return None
    total = 0
    prev = 0
    for c in reversed(s):
        curr = ROMAN_VALS[c]
        if curr >= prev:
            total += curr
        else:
            total -= curr
        prev = curr
    return total if total > 0 else None


class StructureAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Structure Analyzer"

    @property
    def category(self) -> FindingCategory:
        return FindingCategory.STRUCTURE

    def analyze(self, doc: DocumentModel, context: Dict[str, Any] = None) -> List[Finding]:
        findings: List[Finding] = []
        context = context or {}
        profile_id = context.get("profile", getattr(doc, "profile_name", "mechanical"))
        profile = ProfileRegistry.get_profile(profile_id)

        headings: List[Tuple[str, List[int], int, BBox, str, str]] = []
        # (raw_text, [num_parts], page, bbox, title, numbering_style)

        # Regex for standard numeric headings: "1", "1.1", "2.3.4", "Section 3.1"
        num_pattern = re.compile(
            r'^(?:(?:Section|Clause)\s+)?(\d+(?:\.\d+)*)\s*[\.:\-]?\s+([A-Za-z0-9\s,\-\(\):]{3,})$',
            re.IGNORECASE
        )
        # Regex for Roman numeral headings (IEEE style): "I. INTRODUCTION", "II. METHODOLOGY"
        roman_pattern = re.compile(
            r'^([IVXLCDM]+)\.\s+([A-Za-z0-9\s,\-\(\):]{3,})$',
            re.IGNORECASE
        )
        # Regex for letter subheadings: "A. System Architecture", "B. Implementation"
        letter_pattern = re.compile(
            r'^([A-Z])\.\s+([A-Za-z0-9\s,\-\(\):]{3,})$'
        )

        section_nodes: List[SectionNode] = []
        sec_idx = 0

        for page in doc.pages:
            for block in page.blocks:
                txt = block.text.strip()
                if not txt or len(txt) > 100:
                    continue

                is_prominent = (
                    block.is_bold or
                    block.font_size >= 12.0 or
                    (block.font_size > 11.0 and block.is_bold)
                )

                # Check Roman numerals
                r_match = roman_pattern.match(txt)
                if r_match and (is_prominent or txt.isupper()):
                    r_str = r_match.group(1).upper()
                    r_title = r_match.group(2).strip()
                    val = roman_to_int(r_str)
                    if val is not None:
                        headings.append((txt, [val], page.page_num, block.bbox, r_title, "roman"))
                        sec_idx += 1
                        section_nodes.append(SectionNode(
                            section_id=f"sec_{sec_idx}",
                            title=r_title,
                            level=1,
                            number_str=r_str,
                            page_num=page.page_num,
                            bbox=block.bbox
                        ))
                        continue

                # Check letter subheadings
                l_match = letter_pattern.match(txt)
                if l_match and is_prominent:
                    letter_str = l_match.group(1).upper()
                    l_title = l_match.group(2).strip()
                    l_val = ord(letter_str) - ord('A') + 1
                    headings.append((txt, [999, l_val], page.page_num, block.bbox, l_title, "letter"))
                    sec_idx += 1
                    section_nodes.append(SectionNode(
                        section_id=f"sec_{sec_idx}",
                        title=l_title,
                        level=2,
                        number_str=letter_str,
                        page_num=page.page_num,
                        bbox=block.bbox
                    ))
                    continue

                # Check numeric headings
                n_match = num_pattern.match(txt)
                if n_match:
                    num_str = n_match.group(1)
                    title = n_match.group(2).strip()
                    parts = [int(p) for p in num_str.split(".")]
                    headings.append((txt, parts, page.page_num, block.bbox, title, "numeric"))
                    sec_idx += 1
                    section_nodes.append(SectionNode(
                        section_id=f"sec_{sec_idx}",
                        title=title,
                        level=len(parts),
                        number_str=num_str,
                        page_num=page.page_num,
                        bbox=block.bbox
                    ))
                    continue

                # Standalone unnumbered prominent headings (e.g., Abstract, References, Introduction)
                if is_prominent and len(txt) < 60 and not txt.endswith((".", ":", ";", ",")):
                    clean_norm = txt.strip().lower()
                    academic_keywords = [
                        "abstract", "keywords", "introduction", "conclusion",
                        "references", "bibliography", "acknowledgment", "appendix",
                        "scope", "requirements", "testing", "methodology"
                    ]
                    if any(clean_norm == kw or clean_norm.startswith(kw + " ") for kw in academic_keywords):
                        headings.append((txt, [], page.page_num, block.bbox, txt, "none"))
                        sec_idx += 1
                        section_nodes.append(SectionNode(
                            section_id=f"sec_{sec_idx}",
                            title=txt,
                            level=1,
                            number_str="",
                            page_num=page.page_num,
                            bbox=block.bbox
                        ))

        # Save extracted section hierarchy to doc
        if not doc.sections:
            doc.sections = section_nodes

        finding_counter = 1

        # 1. Check for broken sequence numbers (e.g. 3.1 -> 3.3 or I -> III)
        numeric_headings = [h for h in headings if h[5] == "numeric"]
        for i in range(len(numeric_headings) - 1):
            curr_txt, curr_parts, curr_page, curr_bbox, _, _ = numeric_headings[i]
            next_txt, next_parts, next_page, next_bbox, _, _ = numeric_headings[i + 1]

            if curr_parts and next_parts:
                pg_next = next((p for p in doc.pages if p.page_num == next_page), None)
                num_token = ".".join(str(p) for p in next_parts)
                sec_boxes = LocationMapper.find_phrase_bboxes(pg_next, num_token) if pg_next else []
                sec_bbox = sec_boxes[0] if sec_boxes else next_bbox
                sec_prec = "EXACT_NUMBER" if sec_boxes else "APPROXIMATE"

                # Same hierarchy prefix (e.g. 3.1 and 3.3)
                if len(curr_parts) == len(next_parts) and curr_parts[:-1] == next_parts[:-1]:
                    curr_last = curr_parts[-1]
                    next_last = next_parts[-1]
                    if next_last > curr_last + 1:
                        missing_sec = ".".join(str(p) for p in curr_parts[:-1] + [curr_last + 1])
                        findings.append(Finding(
                            finding_id=f"STR-NUM-{finding_counter:03d}",
                            category=self.category.value,
                            domain=profile.domain,
                            location=f"Page {next_page}",
                            page=next_page,
                            bbox=sec_bbox,
                            bounding_boxes=sec_boxes if sec_boxes else ([sec_bbox] if sec_bbox else []),
                            location_precision=sec_prec,
                            matched_text=num_token,
                            expected_text=missing_sec,
                            issue_type="SECTION_NUMBER_GAP",
                            original_content=next_txt,
                            detected_value=f"Section {num_token}",
                            expected_value=f"Section {missing_sec}",
                            deviation=f"Missing section sequence {missing_sec}",
                            severity=SeverityLevel.HIGH.value,
                            confidence=0.95,
                            explanation=f"Section numbering jump detected from {'.'.join(str(p) for p in curr_parts)} directly to {num_token}, skipping Section {missing_sec}.",
                            suggested_correction=f"Insert Section {missing_sec} or renumber {num_token} to {missing_sec}.",
                            suggested_fix=f"Renumber to Section {missing_sec}.",
                            rule_reference="Engineering Documentation Hierarchy Standard §2.1",
                            priority_score=6.5,
                            evidence=f"Preceding: '{curr_txt}' on Page {curr_page} -> Following: '{next_txt}' on Page {next_page}",
                            detection_method="sequence_continuity"
                        ))
                        finding_counter += 1

                # Check depth jumps (e.g. 1 -> 1.1.1 without 1.1)
                elif len(next_parts) > len(curr_parts) + 1 and next_parts[:len(curr_parts)] == curr_parts:
                    findings.append(Finding(
                        finding_id=f"STR-DEP-{finding_counter:03d}",
                        category=self.category.value,
                        domain=profile.domain,
                        location=f"Page {next_page}",
                        page=next_page,
                        bbox=sec_bbox,
                        bounding_boxes=sec_boxes if sec_boxes else ([sec_bbox] if sec_bbox else []),
                        location_precision=sec_prec,
                        matched_text=num_token,
                        expected_text=f"Depth {len(curr_parts) + 1}",
                        issue_type="SECTION_DEPTH_JUMP",
                        original_content=next_txt,
                        detected_value=f"Depth level {len(next_parts)}",
                        expected_value=f"Depth level {len(curr_parts) + 1}",
                        deviation="Hierarchy depth jump",
                        severity=SeverityLevel.MEDIUM.value,
                        confidence=0.90,
                        explanation=f"Heading jump from depth {len(curr_parts)} ({curr_txt}) directly to depth {len(next_parts)} ({next_txt}) without intermediate level.",
                        suggested_correction="Add intermediate section or adjust outline depth.",
                        suggested_fix="Insert intermediate section level.",
                        rule_reference="ISO/IEC Document Structure Guide §3.4",
                        priority_score=4.5,
                        evidence=f"From '{curr_txt}' (depth {len(curr_parts)}) to '{next_txt}' (depth {len(next_parts)})",
                        detection_method="structural_hierarchy"
                    ))
                    finding_counter += 1

        # Check Roman sequence jumps (e.g. I -> III)
        roman_headings = [h for h in headings if h[5] == "roman"]
        for i in range(len(roman_headings) - 1):
            curr_txt, curr_parts, curr_page, curr_bbox, _, _ = roman_headings[i]
            next_txt, next_parts, next_page, next_bbox, _, _ = roman_headings[i + 1]
            if curr_parts and next_parts:
                curr_val = curr_parts[0]
                next_val = next_parts[0]
                if next_val > curr_val + 1:
                    pg_next = next((p for p in doc.pages if p.page_num == next_page), None)
                    r_tok = next_txt.split()[0] if next_txt.split() else next_txt
                    r_boxes = LocationMapper.find_phrase_bboxes(pg_next, r_tok) if pg_next else []
                    r_bbox = r_boxes[0] if r_boxes else next_bbox
                    r_prec = "EXACT_NUMBER" if r_boxes else "APPROXIMATE"

                    findings.append(Finding(
                        finding_id=f"STR-ROM-{finding_counter:03d}",
                        category=self.category.value,
                        domain=profile.domain,
                        location=f"Page {next_page}",
                        page=next_page,
                        bbox=r_bbox,
                        bounding_boxes=r_boxes if r_boxes else ([r_bbox] if r_bbox else []),
                        location_precision=r_prec,
                        matched_text=r_tok,
                        expected_text=f"Section {curr_val + 1}",
                        issue_type="SECTION_ROMAN_GAP",
                        original_content=next_txt,
                        detected_value=next_txt,
                        expected_value=f"Section {curr_val + 1}",
                        deviation=f"Roman numeral sequence jump from {curr_val} to {next_val}",
                        severity=SeverityLevel.HIGH.value,
                        confidence=0.94,
                        explanation=f"Section sequence jump from Roman numeral heading {curr_txt} to {next_txt}.",
                        suggested_correction="Verify missing section or correct Roman numeral numbering.",
                        suggested_fix=f"Renumber Roman numeral sequence.",
                        rule_reference="IEEE Publication Style Manual §III",
                        priority_score=6.2,
                        evidence=f"Preceding: '{curr_txt}' -> Following: '{next_txt}'",
                        detection_method="sequence_continuity"
                    ))
                    finding_counter += 1

        # 2. Check for duplicate headings
        seen_headings: Dict[str, Tuple[int, BBox, str]] = {}
        for raw_txt, parts, p_num, bbox, title, _ in headings:
            norm_key = re.sub(r'\s+', ' ', raw_txt.lower()).strip()
            pg_curr = next((p for p in doc.pages if p.page_num == p_num), None)
            dup_boxes = LocationMapper.find_phrase_bboxes(pg_curr, title) if pg_curr else []
            dup_bbox = dup_boxes[0] if dup_boxes else bbox
            dup_prec = "EXACT_PHRASE" if dup_boxes else "APPROXIMATE"

            if norm_key in seen_headings:
                prev_page, prev_bbox, prev_fid = seen_headings[norm_key]
                curr_fid = f"STR-DUP-{finding_counter:03d}"

                findings.append(Finding(
                    finding_id=curr_fid,
                    category=self.category.value,
                    domain=profile.domain,
                    location=f"Page {p_num}",
                    page=p_num,
                    bbox=dup_bbox,
                    bounding_boxes=dup_boxes if dup_boxes else ([dup_bbox] if dup_bbox else []),
                    location_precision=dup_prec,
                    matched_text=title,
                    expected_text="Unique section title",
                    issue_type="DUPLICATE_SECTION_HEADING",
                    related_finding_ids=[prev_fid],
                    original_content=raw_txt,
                    detected_value=raw_txt,
                    expected_value="Unique section title",
                    deviation="Duplicate section heading",
                    severity=SeverityLevel.MEDIUM.value,
                    confidence=0.92,
                    explanation=f"Duplicate section header '{raw_txt}' already defined on Page {prev_page}.",
                    suggested_correction=f"Disambiguate or merge with Page {prev_page} section.",
                    suggested_fix=f"Rename heading to disambiguate from Page {prev_page}.",
                    rule_reference="Engineering Documentation Standard §2.4",
                    priority_score=4.0,
                    evidence=f"Duplicate header: '{raw_txt}' on Page {p_num} matches Page {prev_page}",
                    detection_method="deterministic"
                ))
                finding_counter += 1
            else:
                assigned_fid = f"STR-DECL-{finding_counter:03d}"
                seen_headings[norm_key] = (p_num, bbox, assigned_fid)

        # 3. Check for profile-specific mandatory sections
        all_titles_lower = " ".join(h[4].lower() for h in headings)
        # Also check raw page text for unformatted or inline occurrences
        full_text_lower = doc.full_text.lower()

        for req in profile.required_sections:
            req_lower = req.lower()
            # Match either in extracted section titles or prominently in text
            found_in_titles = req_lower in all_titles_lower
            found_in_text = bool(re.search(rf'\b{re.escape(req_lower)}\b', full_text_lower))

            if not found_in_titles and not found_in_text:
                findings.append(Finding(
                    finding_id=f"STR-REQ-{finding_counter:03d}",
                    category=self.category.value,
                    domain=profile.domain,
                    location="Document Outline",
                    page=1,
                    bbox=None,
                    original_content="[Document Structure]",
                    detected_value="Section Missing",
                    expected_value=f"Mandatory Section: '{req}'",
                    deviation=f"Absence of required section '{req}' for profile '{profile.display_name}'",
                    severity=SeverityLevel.HIGH.value,
                    confidence=0.90,
                    explanation=f"The document under profile '{profile.display_name}' is missing mandatory standard section '{req}'.",
                    suggested_correction=f"Add a '{req}' section outlining required criteria.",
                    rule_reference=f"{profile.display_name} Structure Rules",
                    priority_score=6.0,
                    evidence=f"Searched document outline for mandatory section: '{req}'",
                    detection_method="profile_compliance"
                ))
                finding_counter += 1

        return findings
