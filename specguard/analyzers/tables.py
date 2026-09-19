"""
Table Analysis Engine for SpecGuard.

Validates engineering and academic data tables for:
- Missing cells, empty required fields, column unit inconsistencies, duplicate rows
- Table caption detection, numbering continuity (e.g. Table 1, Table 2 or TABLE I, TABLE II)
- Duplicate table numbers, missing labels
- Caption placement (above vs below table)
- Multi-page table continuity (split tables across page boundaries)
- Populates DocumentModel.tables
"""

import re
from typing import List, Dict, Tuple, Optional, Any
from collections import Counter
import logging

from specguard.analyzers.base import BaseAnalyzer
from specguard.core.models import (
    DocumentModel, Finding, FindingCategory, SeverityLevel, TableData, BBox
)
from specguard.core.profiles import ProfileRegistry
from specguard.core.location_mapper import LocationMapper

logger = logging.getLogger(__name__)

ROMAN_VALS = {'i': 1, 'v': 5, 'x': 10, 'l': 50, 'c': 100}

def parse_table_number(label_str: str) -> Optional[int]:
    """Extracts integer or converts Roman numeral table number."""
    m = re.search(r'Table\s+([0-9]+|[IVXLCDM]+)', label_str, re.IGNORECASE)
    if not m:
        return None
    val_str = m.group(1).lower()
    if val_str.isdigit():
        return int(val_str)
    if all(c in ROMAN_VALS for c in val_str):
        total = 0
        prev = 0
        for c in reversed(val_str):
            curr = ROMAN_VALS[c]
            if curr >= prev:
                total += curr
            else:
                total -= curr
            prev = curr
        return total if total > 0 else None
    return None


class TableAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Table Analyzer"

    @property
    def category(self) -> FindingCategory:
        return FindingCategory.TABLE

    def analyze(self, doc: DocumentModel, context: Dict[str, Any] = None) -> List[Finding]:
        findings: List[Finding] = []
        finding_counter = 1
        context = context or {}
        profile_id = context.get("profile", getattr(doc, "profile_name", "mechanical"))
        profile = ProfileRegistry.get_profile(profile_id)

        all_tables: List[TableData] = []
        for page in doc.pages:
            for tbl in page.tables:
                all_tables.append(tbl)

        # 1. Detect captions and labels for tables by scanning nearby text blocks
        table_caption_re = re.compile(
            r'^(?:TABLE|Table)\s+([0-9]+|[IVXLCDM]+)[\.:\-]?\s*(.*)$',
            re.IGNORECASE
        )

        for tbl in all_tables:
            page = next((p for p in doc.pages if p.page_num == tbl.page_num), None)
            if not page:
                continue

            tbl_bbox = tbl.bbox or BBox(50.0, 100.0, 550.0, 300.0)

            # Search text blocks within 50pt above or below the table for caption
            best_caption = ""
            best_label = ""
            best_pos = "none"

            for b in page.blocks:
                txt = b.text.strip()
                m = table_caption_re.match(txt)
                if m:
                    # Check vertical proximity
                    # Above: b.bbox.y1 close to tbl_bbox.y0
                    if abs(b.bbox.y1 - tbl_bbox.y0) < 60.0 or (b.bbox.y0 < tbl_bbox.y0 and b.bbox.y1 <= tbl_bbox.y0 + 10.0):
                        best_caption = txt
                        best_label = f"Table {m.group(1)}"
                        best_pos = "above"
                        break
                    # Below: b.bbox.y0 close to tbl_bbox.y1
                    elif abs(b.bbox.y0 - tbl_bbox.y1) < 60.0:
                        best_caption = txt
                        best_label = f"Table {m.group(1)}"
                        best_pos = "below"
                        break

            if best_caption:
                tbl.caption = best_caption
                tbl.label = best_label
                tbl.caption_position = best_pos

        # Update doc.tables
        doc.tables = all_tables

        # 2. Check for multi-page split tables (e.g. table continuing onto next page)
        for i in range(len(all_tables) - 1):
            curr_tbl = all_tables[i]
            next_tbl = all_tables[i + 1]

            if next_tbl.page_num == curr_tbl.page_num + 1:
                # Check if headers match or if next table has matching column count without caption
                headers_match = curr_tbl.headers and next_tbl.headers and curr_tbl.headers == next_tbl.headers
                if headers_match or (curr_tbl.label and "continued" in (next_tbl.caption or "").lower()):
                    curr_tbl.is_split = True
                    curr_tbl.page_end = next_tbl.page_num
                    next_tbl.is_split = True
                    next_tbl.label = curr_tbl.label + " (Cont.)"

        # 3. Validate table captions, numbering sequence, and duplicates
        numbered_tables: List[Tuple[int, TableData]] = []
        for tbl in all_tables:
            if tbl.label:
                num_val = parse_table_number(tbl.label)
                if num_val is not None:
                    numbered_tables.append((num_val, tbl))

        # Check for duplicate table numbers
        seen_numbers: Dict[int, Tuple[TableData, str]] = {}
        for num_val, tbl in numbered_tables:
            if tbl.is_split and "Cont" in tbl.label:
                continue

            curr_lbl = tbl.label or f"Table {num_val}"
            pg_tbl = next((p for p in doc.pages if p.page_num == tbl.page_num), None)
            t_boxes = LocationMapper.find_phrase_bboxes(pg_tbl, curr_lbl) if pg_tbl else []
            t_bbox = t_boxes[0] if t_boxes else tbl.bbox
            t_precision = "EXACT_LABEL" if t_boxes else "APPROXIMATE"

            if num_val in seen_numbers:
                prev_tbl, prev_fid = seen_numbers[num_val]
                curr_fid = f"TBL-DUP-{finding_counter:03d}"
                next_expected = max(k for k in seen_numbers.keys()) + 1

                findings.append(Finding(
                    finding_id=curr_fid,
                    category=self.category.value,
                    domain=profile.domain,
                    location=f"Page {tbl.page_num}",
                    page=tbl.page_num,
                    bbox=t_bbox,
                    bounding_boxes=t_boxes if t_boxes else ([t_bbox] if t_bbox else []),
                    location_precision=t_precision,
                    matched_text=curr_lbl,
                    expected_text=f"Table {next_expected}",
                    issue_type="DUPLICATE_TABLE_LABEL",
                    related_finding_ids=[prev_fid],
                    source_object_id=tbl.table_id,
                    target_object_id=prev_tbl.table_id,
                    original_content=tbl.caption or tbl.label,
                    detected_value=f"Duplicate Table {num_val}",
                    expected_value=f"Unique Table Number (next available: {next_expected})",
                    deviation=f"Duplicate Table {num_val} already declared on Page {prev_tbl.page_num}",
                    severity=SeverityLevel.HIGH.value,
                    confidence=0.96,
                    explanation=f"Table numbering collision: Table {num_val} is declared on Page {tbl.page_num}, but was already defined on Page {prev_tbl.page_num}.",
                    suggested_correction=f"Renumber Table on Page {tbl.page_num} to a unique sequence index.",
                    suggested_fix=f"Renumber to Table {next_expected}.",
                    rule_reference="Engineering Document Standard §4.1 (Table Numbering)",
                    priority_score=6.8,
                    evidence=f"Page {tbl.page_num}: '{tbl.caption}' conflicts with Page {prev_tbl.page_num}: '{prev_tbl.caption}'",
                    detection_method="sequence_tracking"
                ))
                finding_counter += 1
            else:
                assigned_fid = f"TBL-DECL-{finding_counter:03d}"
                seen_numbers[num_val] = (tbl, assigned_fid)

        # Check for sequence jumps (e.g. Table 1 -> Table 3)
        unique_nums = sorted(seen_numbers.keys())
        for i in range(len(unique_nums) - 1):
            curr_n = unique_nums[i]
            next_n = unique_nums[i + 1]
            if next_n > curr_n + 1:
                tbl, _ = seen_numbers[next_n]
                curr_lbl = tbl.label or f"Table {next_n}"
                pg_tbl = next((p for p in doc.pages if p.page_num == tbl.page_num), None)
                j_boxes = LocationMapper.find_phrase_bboxes(pg_tbl, curr_lbl) if pg_tbl else []
                j_bbox = j_boxes[0] if j_boxes else tbl.bbox
                j_precision = "EXACT_LABEL" if j_boxes else "APPROXIMATE"

                findings.append(Finding(
                    finding_id=f"TBL-SEQ-{finding_counter:03d}",
                    category=self.category.value,
                    domain=profile.domain,
                    location=f"Page {tbl.page_num}",
                    page=tbl.page_num,
                    bbox=j_bbox,
                    bounding_boxes=j_boxes if j_boxes else ([j_bbox] if j_bbox else []),
                    location_precision=j_precision,
                    matched_text=curr_lbl,
                    expected_text=f"Table {curr_n + 1}",
                    issue_type="TABLE_SEQUENCE_GAP",
                    source_object_id=tbl.table_id,
                    original_content=tbl.caption or tbl.label,
                    detected_value=f"Table {next_n}",
                    expected_value=f"Table {curr_n + 1}",
                    deviation=f"Table numbering sequence jump: Table {curr_n + 1} is missing",
                    severity=SeverityLevel.MEDIUM.value,
                    confidence=0.92,
                    explanation=f"Table numbering jumps from Table {curr_n} to Table {next_n}, skipping Table {curr_n + 1}.",
                    suggested_correction=f"Renumber Table {next_n} to Table {curr_n + 1} or insert the missing table.",
                    suggested_fix=f"Renumber to Table {curr_n + 1}.",
                    rule_reference="Engineering Documentation Standard §4.1",
                    priority_score=5.0,
                    evidence=f"Jump from Table {curr_n} to Table {next_n}",
                    detection_method="sequence_continuity"
                ))
                finding_counter += 1

        # Check caption placement
        for tbl in all_tables:
            if tbl.caption and profile.table_caption_position != "any":
                if tbl.caption_position != profile.table_caption_position:
                    findings.append(Finding(
                        finding_id=f"TBL-CAP-{finding_counter:03d}",
                        category=self.category.value,
                        domain=profile.domain,
                        location=f"Page {tbl.page_num}",
                        page=tbl.page_num,
                        bbox=tbl.bbox,
                        original_content=tbl.caption,
                        detected_value=f"Caption placed {tbl.caption_position}",
                        expected_value=f"Caption placed {profile.table_caption_position}",
                        deviation=f"Table caption placement deviation ({tbl.caption_position} instead of {profile.table_caption_position})",
                        severity=SeverityLevel.LOW.value,
                        confidence=0.88,
                        explanation=f"According to '{profile.display_name}' formatting rules, table captions must appear {profile.table_caption_position} the table.",
                        suggested_correction=f"Move table caption {profile.table_caption_position} the table boundary.",
                        rule_reference=f"{profile.display_name} Style Guide (Table Captions)",
                        priority_score=3.2,
                        evidence=f"Caption: '{tbl.caption}' ({tbl.caption_position})",
                        detection_method="layout_geometry"
                    ))
                    finding_counter += 1

        # 4. Cell-level validations (Empty cells, jagged rows, mixed units, duplicate rows)
        for tbl in all_tables:
            if not tbl.rows and not tbl.headers:
                continue

            num_cols = len(tbl.headers) if tbl.headers else (len(tbl.rows[0]) if tbl.rows else 0)
            if num_cols == 0:
                continue

            page_num = tbl.page_num

            # Check for jagged rows
            for row_idx, row in enumerate(tbl.rows):
                if len(row) != num_cols:
                    findings.append(Finding(
                        finding_id=f"TBL-JAG-{finding_counter:03d}",
                        category=self.category.value,
                        domain=profile.domain,
                        location=f"Page {page_num}, Table Row {row_idx + 1}",
                        page=page_num,
                        bbox=tbl.bbox,
                        original_content=f"Row with {len(row)} cells (expected {num_cols})",
                        detected_value=f"{len(row)} columns",
                        expected_value=f"{num_cols} columns",
                        deviation="Jagged / misaligned table row",
                        severity=SeverityLevel.MEDIUM.value,
                        confidence=0.92,
                        explanation=f"Table row {row_idx + 1} has {len(row)} cells, which differs from header column count ({num_cols}).",
                        suggested_correction="Align cells with corresponding table header columns.",
                        rule_reference="Engineering Data Table Standard §4.2",
                        priority_score=4.2,
                        detection_method="deterministic"
                    ))
                    finding_counter += 1

                # Empty cells in critical columns
                for col_idx, cell in enumerate(row):
                    cell_clean = str(cell).strip()
                    col_name = tbl.headers[col_idx] if col_idx < len(tbl.headers) else f"Column {col_idx+1}"
                    if not cell_clean or cell_clean in ["-", "N/A", "null", "none"]:
                        if any(kw in col_name.lower() for kw in ["value", "rating", "limit", "tolerance", "min", "max", "unit"]):
                            findings.append(Finding(
                                finding_id=f"TBL-EMP-{finding_counter:03d}",
                                category=self.category.value,
                                domain=profile.domain,
                                location=f"Page {page_num}, Table Row {row_idx + 1}, Col '{col_name}'",
                                page=page_num,
                                bbox=tbl.bbox,
                                original_content=f"Row {row_idx+1}, {col_name}: [EMPTY]",
                                detected_value="Missing / Empty",
                                expected_value=f"Defined numerical specification for '{col_name}'",
                                deviation="Missing required specification in engineering table",
                                severity=SeverityLevel.HIGH.value,
                                confidence=0.94,
                                explanation=f"Empty required cell in engineering table under critical column '{col_name}'.",
                                suggested_correction="Specify explicit engineering value or state reason for omission.",
                                rule_reference="Engineering Design Documentation §3.1 (Complete Data Tables)",
                                priority_score=6.2,
                                detection_method="cell_inspection"
                            ))
                            finding_counter += 1

            # Check unit consistency
            for col_idx in range(num_cols):
                col_name = tbl.headers[col_idx] if col_idx < len(tbl.headers) else f"Col {col_idx}"
                col_units = []
                for row in tbl.rows:
                    if col_idx < len(row):
                        val_str = str(row[col_idx]).strip()
                        m = re.search(r'([0-9\.\+-]+)\s*([A-Za-z°%μ]+)$', val_str)
                        if m:
                            col_units.append(m.group(2))

                if col_units:
                    unit_counts = Counter(col_units)
                    if len(unit_counts) > 1:
                        primary_unit = unit_counts.most_common(1)[0][0]
                        for rogue_unit, cnt in unit_counts.items():
                            if rogue_unit != primary_unit:
                                findings.append(Finding(
                                    finding_id=f"TBL-UNT-{finding_counter:03d}",
                                    category=self.category.value,
                                    domain=profile.domain,
                                    location=f"Page {page_num}, Column '{col_name}'",
                                    page=page_num,
                                    bbox=tbl.bbox,
                                    original_content=f"Mixed units in '{col_name}': {dict(unit_counts)}",
                                    detected_value=f"Unit '{rogue_unit}'",
                                    expected_value=f"Consistent column unit '{primary_unit}'",
                                    deviation="Mixed engineering units within single column",
                                    severity=SeverityLevel.HIGH.value,
                                    confidence=0.95,
                                    explanation=f"Table column '{col_name}' contains conflicting engineering units ({rogue_unit} vs {primary_unit}).",
                                    suggested_correction=f"Standardize column '{col_name}' to unit '{primary_unit}' or normalize values.",
                                    rule_reference="SI Units in Engineering Documentation §2.1",
                                    priority_score=6.7,
                                    detection_method="unit_consistency"
                                ))
                                finding_counter += 1

            # Duplicate rows
            row_hashes = set()
            for r_idx, row in enumerate(tbl.rows):
                row_tuple = tuple(row)
                if any(row):
                    if row_tuple in row_hashes:
                        findings.append(Finding(
                            finding_id=f"TBL-ROW-DUP-{finding_counter:03d}",
                            category=self.category.value,
                            domain=profile.domain,
                            location=f"Page {page_num}, Table Row {r_idx + 1}",
                            page=page_num,
                            bbox=tbl.bbox,
                            original_content=" | ".join(str(c) for c in row),
                            detected_value="Duplicate Row",
                            expected_value="Unique table entry",
                            deviation="Identical repeated entry in engineering table",
                            severity=SeverityLevel.LOW.value,
                            confidence=0.90,
                            explanation=f"Row {r_idx + 1} is an exact duplicate of an earlier row in the same table.",
                            suggested_correction="Remove redundant duplicate row.",
                            rule_reference="Engineering Document Standards §4.4",
                            priority_score=2.5,
                            detection_method="deterministic"
                        ))
                        finding_counter += 1
                    else:
                        row_hashes.add(row_tuple)

        return findings
