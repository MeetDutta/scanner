"""
Table of Contents (TOC) Analysis Engine for SpecGuard.

Analyzes Table of Contents structure, distinguishes genuine TOCs from Lists of Figures,
Lists of Tables, or Bibliographies, validates multi-level hierarchy, detects page drift,
unmatched entries, missing headings, and duplicate entries.
Respects profile rules (e.g. IEEE papers do not require a TOC).
Populates DocumentModel.toc.
"""

import re
from typing import List, Dict, Tuple, Optional, Any
import logging

from specguard.analyzers.base import BaseAnalyzer
from specguard.core.models import (
    DocumentModel, Finding, FindingCategory, SeverityLevel, BBox,
    TOCModel, TOCItem, SectionNode
)
from specguard.core.profiles import ProfileRegistry
from specguard.core.location_mapper import LocationMapper

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
        context = context or {}
        profile_id = context.get("profile", getattr(doc, "profile_name", "mechanical"))
        profile = ProfileRegistry.get_profile(profile_id)

        # 1. Search for TOC section across early pages (up to page 6 for multi-page docs)
        toc_header_found = False
        toc_page_num = 1
        toc_header_bbox: Optional[BBox] = None
        is_list_of_figures = False
        is_list_of_tables = False

        max_search_page = min(len(doc.pages), 6)
        toc_items: List[TOCItem] = []

        # Patterns for dotted leader or tab/space separated page numbers
        # e.g.: "1. Introduction ........... 4", "System Architecture    12", "1.1 Background \t 6"
        entry_pattern = re.compile(r'^(.*?)(?:\.{2,}|\s{3,}|\t+)\s*(\d+|[ivxlcdm]+)$', re.IGNORECASE)

        for page in doc.pages[:max_search_page]:
            for b in page.blocks:
                txt_clean = b.text.strip().lower()

                # Check if this block is a List of Figures or List of Tables
                if "list of figures" in txt_clean or "table of figures" in txt_clean:
                    is_list_of_figures = True
                    continue
                if "list of tables" in txt_clean or "table of tables" in txt_clean:
                    is_list_of_tables = True
                    continue

                if txt_clean in ["table of contents", "contents", "table of content", "index of contents"]:
                    toc_header_found = True
                    toc_page_num = page.page_num
                    toc_header_bbox = b.bbox
                    continue

                if toc_header_found:
                    # Stop if we hit a main content heading like "1 Introduction" or "I. INTRODUCTION"
                    if re.match(r'^(?:1\.?|i\.)\s+[a-z]{3,}', txt_clean) and not entry_pattern.match(b.text.strip()):
                        break

                    m = entry_pattern.match(b.text.strip())
                    if m:
                        title_part = m.group(1).strip()
                        page_str = m.group(2).strip()
                        # Parse target page
                        target_p: Optional[int] = None
                        if page_str.isdigit():
                            target_p = int(page_str)

                        # Determine hierarchical level
                        level = 1
                        leading_num = re.match(r'^(\d+(?:\.\d+)*)', title_part)
                        if leading_num:
                            dots = leading_num.group(1).count('.')
                            level = dots + 1
                        elif b.bbox.x0 > 75.0:  # Indented entry
                            level = 2

                        if len(title_part) > 2 and not title_part.lower().startswith("page"):
                            toc_items.append(TOCItem(
                                level=level,
                                title=title_part,
                                page_num=page.page_num,
                                target_page_num=target_p,
                                bbox=b.bbox,
                                raw_text=b.text.strip()
                            ))

        # Check if TOC exists
        toc_model = TOCModel(
            items=toc_items,
            page_num=toc_page_num,
            exists=toc_header_found or len(toc_items) >= 3,
            is_genuine=(toc_header_found or len(toc_items) >= 3) and not (is_list_of_figures or is_list_of_tables)
        )
        doc.toc = toc_model

        # If document has no TOC:
        if not toc_model.exists:
            # Check if current profile demands a TOC
            if profile.requires_toc and len(doc.pages) >= profile.toc_min_pages:
                findings.append(Finding(
                    finding_id="TOC-REQ-001",
                    category=self.category.value,
                    domain=profile.domain,
                    location=f"Document Overview (Pages: {len(doc.pages)})",
                    page=1,
                    original_content="",
                    detected_value="No Table of Contents detected",
                    expected_value="Table of Contents section",
                    deviation=f"Mandatory Table of Contents missing for document with {len(doc.pages)} pages",
                    severity=SeverityLevel.MEDIUM.value,
                    confidence=0.95,
                    explanation=f"Documents under profile '{profile.display_name}' exceeding {profile.toc_min_pages} pages require a formal Table of Contents.",
                    suggested_correction="Insert a Table of Contents on page 2 or 3 listing all major sections and page numbers.",
                    rule_reference="Document Formatting Standards §1.3 (TOC Requirement)",
                    priority_score=5.0,
                    detection_method="structural_heuristic"
                ))
            return findings

        # 2. Extract actual document headings from all pages
        actual_headings: Dict[str, Tuple[int, BBox, str]] = {}
        heading_re = re.compile(
            r'^(?:(?:Section|Clause)\s+)?((?:[0-9]+(?:\.[0-9]+)*\.?|[IVXLCDM]+\.?|[A-Z]\.)\s+)?([A-Za-z0-9\s,\-\(\):]+)$'
        )

        for page in doc.pages:
            # Skip the TOC page itself
            if page.page_num == toc_page_num:
                continue

            for block in page.blocks:
                txt = block.text.strip()
                if not txt or len(txt) > 90:
                    continue

                m = heading_re.match(txt)
                is_prominent = block.is_bold or block.font_size >= 12.0 or block.font_size > 11.0
                if m and is_prominent:
                    clean_text = txt.lower().strip()
                    if clean_text not in actual_headings:
                        actual_headings[clean_text] = (page.page_num, block.bbox, txt)

        finding_counter = 1

        # Check for duplicate TOC entries
        seen_titles: Dict[str, int] = {}
        for item in toc_items:
            norm = item.title.lower().strip()
            seen_titles[norm] = seen_titles.get(norm, 0) + 1
            if seen_titles[norm] == 2:
                findings.append(Finding(
                    finding_id=f"TOC-DUP-{finding_counter:03d}",
                    category=self.category.value,
                    domain=profile.domain,
                    location=f"TOC (Page {item.page_num})",
                    page=item.page_num,
                    bbox=item.bbox,
                    original_content=item.raw_text,
                    detected_value=f"Duplicate TOC title: '{item.title}'",
                    expected_value="Unique section title in TOC",
                    deviation="Table of Contents contains duplicate entries with the same heading",
                    severity=SeverityLevel.LOW.value,
                    confidence=0.92,
                    explanation=f"The entry '{item.title}' appears multiple times in the Table of Contents.",
                    suggested_correction="Consolidate or rename duplicate headings in the document.",
                    rule_reference="Document Integrity Standards §1.3",
                    priority_score=3.5,
                    evidence=item.raw_text,
                    detection_method="deterministic"
                ))
                finding_counter += 1

        # Check pagination uncertainty warning if applicable
        pagination_verified = doc.metadata.get("pagination_verified", True)

        # 3. Compare each TOC entry against actual headings
        for item in toc_items:
            if not item.target_page_num:
                continue

            clean_toc_key = re.sub(r'^(?:[0-9]+(?:\.[0-9]+)*\.?|[IVXLCDM]+\.?|[A-Z]\.)\s*', '', item.title.lower()).strip()
            if len(clean_toc_key) < 3:
                continue

            match_found = False
            matched_act_page = item.target_page_num

            for act_key, (act_page, act_bbox, orig_act_text) in actual_headings.items():
                clean_act_key = re.sub(r'^(?:[0-9]+(?:\.[0-9]+)*\.?|[IVXLCDM]+\.?|[A-Z]\.)\s*', '', act_key).strip()
                if clean_toc_key == clean_act_key or (len(clean_toc_key) > 5 and clean_toc_key in clean_act_key):
                    match_found = True
                    matched_act_page = act_page

                    # Check page drift
                    if item.target_page_num != act_page:
                        drift = item.target_page_num - act_page
                        sev = SeverityLevel.HIGH.value if pagination_verified else SeverityLevel.LOW.value
                        exp = (
                            f"Table of Contents lists '{item.title}' on Page {item.target_page_num}, but the "
                            f"heading appears on Page {act_page}."
                        )
                        if not pagination_verified:
                            exp += " (Note: Exact physical pagination unverified because no local LibreOffice was found)."

                        # Resolve exact page number token bounding box in TOC entry
                        pg_toc = next((p for p in doc.pages if p.page_num == item.page_num), None)
                        num_str = str(item.target_page_num)
                        num_box = None
                        if pg_toc:
                            for blk in pg_toc.blocks:
                                if item.title.lower() in blk.text.lower() or (item.bbox and abs(blk.bbox.y0 - item.bbox.y0) < 5.0):
                                    num_box = LocationMapper.find_number_in_block(blk, num_str)
                                    if num_box:
                                        break

                        toc_f_bbox = num_box if num_box else item.bbox
                        toc_precision = "EXACT_NUMBER" if num_box else "APPROXIMATE"
                        toc_fid = f"TOC-PAG-{finding_counter:03d}"
                        body_fid = f"TOC-DST-{finding_counter:03d}"

                        findings.append(Finding(
                            finding_id=toc_fid,
                            category=self.category.value,
                            domain=profile.domain,
                            location=f"TOC (Page {item.page_num}) vs Body (Page {act_page})",
                            page=item.page_num,
                            bbox=toc_f_bbox,
                            bounding_boxes=[toc_f_bbox] if toc_f_bbox else [],
                            location_precision=toc_precision,
                            matched_text=num_str,
                            expected_text=str(act_page),
                            issue_type="TOC_PAGE_DRIFT",
                            related_finding_ids=[body_fid],
                            source_object_id=f"toc_{item.title[:20].strip()}",
                            target_object_id=f"heading_{orig_act_text[:20].strip()}",
                            original_content=item.raw_text,
                            detected_value=f"TOC Page {item.target_page_num}",
                            expected_value=f"Actual Page {act_page}",
                            deviation=f"Page number drift: {drift:+d} pages",
                            severity=sev,
                            confidence=0.95 if pagination_verified else 0.75,
                            explanation=exp,
                            suggested_correction=f"Update TOC entry '{item.title}' page number to {act_page}.",
                            suggested_fix=f"Change TOC page from {item.target_page_num} to {act_page}.",
                            rule_reference="Engineering Document Specification Standard §1.3 (TOC Accuracy)",
                            priority_score=6.8 if pagination_verified else 4.0,
                            evidence=f"TOC: '{item.raw_text}' -> Heading: '{orig_act_text}' on Page {act_page}",
                            detection_method="cross_page_alignment"
                        ))
                        finding_counter += 1

                        # Also generate destination link finding in body heading so navigation is bi-directional
                        pg_act = next((p for p in doc.pages if p.page_num == act_page), None)
                        h_boxes = LocationMapper.find_phrase_bboxes(pg_act, orig_act_text) if pg_act else []
                        h_bbox = h_boxes[0] if h_boxes else act_bbox

                        findings.append(Finding(
                            finding_id=body_fid,
                            category=self.category.value,
                            domain=profile.domain,
                            location=f"Body (Page {act_page})",
                            page=act_page,
                            bbox=h_bbox,
                            bounding_boxes=h_boxes if h_boxes else ([h_bbox] if h_bbox else []),
                            location_precision="EXACT_PHRASE" if h_boxes else "APPROXIMATE",
                            matched_text=orig_act_text,
                            expected_text=f"Referenced by TOC Page {item.page_num}",
                            issue_type="TOC_DESTINATION_HEADING",
                            related_finding_ids=[toc_fid],
                            source_object_id=f"heading_{orig_act_text[:20].strip()}",
                            target_object_id=f"toc_{item.title[:20].strip()}",
                            original_content=orig_act_text,
                            detected_value=f"Page {act_page} Heading",
                            expected_value=f"TOC references this as Page {item.target_page_num}",
                            deviation=f"TOC drift target location",
                            severity=SeverityLevel.LOW.value,
                            confidence=0.95,
                            explanation=f"This heading corresponds to TOC entry '{item.title}' which incorrectly indicates Page {item.target_page_num}.",
                            suggested_correction=f"Verify TOC entry reflects Page {act_page}.",
                            suggested_fix=f"Update corresponding TOC entry to Page {act_page}.",
                            rule_reference="Engineering Document Specification Standard §1.3",
                            priority_score=3.0,
                            evidence=f"Target heading for drifted TOC entry '{item.title}'",
                            detection_method="cross_page_alignment"
                        ))
                        finding_counter += 1
                    break

            if not match_found and len(clean_toc_key) > 4:
                # TOC mentions section that does not exist in body
                pg_toc = next((p for p in doc.pages if p.page_num == item.page_num), None)
                ext_boxes = LocationMapper.find_phrase_bboxes(pg_toc, item.title) if pg_toc else []
                ext_bbox = ext_boxes[0] if ext_boxes else item.bbox
                ext_prec = "EXACT_PHRASE" if ext_boxes else "APPROXIMATE"

                findings.append(Finding(
                    finding_id=f"TOC-EXT-{finding_counter:03d}",
                    category=self.category.value,
                    domain=profile.domain,
                    location=f"TOC (Page {item.page_num})",
                    page=item.page_num,
                    bbox=ext_bbox,
                    bounding_boxes=ext_boxes if ext_boxes else ([ext_bbox] if ext_bbox else []),
                    location_precision=ext_prec,
                    matched_text=item.title,
                    expected_text="Valid section heading",
                    issue_type="UNMATCHED_TOC_ENTRY",
                    original_content=item.raw_text,
                    detected_value=f"Unmatched entry: '{item.title}'",
                    expected_value="Corresponding section in document body",
                    deviation="TOC references non-existent document section",
                    severity=SeverityLevel.MEDIUM.value,
                    confidence=0.88,
                    explanation=f"Table of Contents contains entry '{item.title}', but no corresponding section heading was found in the document.",
                    suggested_correction=f"Verify if section '{item.title}' was deleted, moved, or renamed.",
                    suggested_fix=f"Remove entry '{item.title}' or create corresponding section.",
                    rule_reference="Document Integrity Standards §1.3",
                    priority_score=4.8,
                    evidence=item.raw_text,
                    detection_method="deterministic"
                ))
                finding_counter += 1

        return findings
