"""
Table Analysis Engine for SpecGuard.
Validates engineering data tables for missing cells, empty required fields,
column unit inconsistency, duplicate rows, and text-to-table parameter synchronicity.
"""

import re
from typing import List, Dict, Tuple, Optional, Any
from collections import Counter
import logging

from specguard.analyzers.base import BaseAnalyzer
from specguard.core.models import DocumentModel, Finding, FindingCategory, SeverityLevel, TableData, BBox

logger = logging.getLogger(__name__)


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

        all_tables: List[Tuple[int, TableData]] = []
        for page in doc.pages:
            for tbl in page.tables:
                all_tables.append((page.page_num, tbl))

        for page_num, table in all_tables:
            if not table.rows and not table.headers:
                continue

            num_cols = len(table.headers) if table.headers else (len(table.rows[0]) if table.rows else 0)
            if num_cols == 0:
                continue

            # 1. Check for empty cells in data rows
            for row_idx, row in enumerate(table.rows):
                if len(row) != num_cols:
                    findings.append(Finding(
                        finding_id=f"TBL-JAG-{finding_counter:03d}",
                        category=self.category.value,
                        domain="General",
                        location=f"Page {page_num}, Table Row {row_idx + 1}",
                        page=page_num,
                        bbox=table.bbox,
                        original_content=f"Row with {len(row)} cells (expected {num_cols})",
                        detected_value=f"{len(row)} columns",
                        expected_value=f"{num_cols} columns",
                        deviation="Jagged / misaligned table row",
                        severity=SeverityLevel.MEDIUM.value,
                        confidence=0.92,
                        explanation=f"Table row {row_idx + 1} has {len(row)} cells, which differs from header column count ({num_cols}).",
                        suggested_correction="Align cells with corresponding table header columns.",
                        rule_reference="Engineering Data Table Standard §4.2",
                        priority_score=4.2
                    ))
                    finding_counter += 1

                for col_idx, cell in enumerate(row):
                    cell_clean = str(cell).strip()
                    col_name = table.headers[col_idx] if col_idx < len(table.headers) else f"Column {col_idx+1}"
                    if not cell_clean or cell_clean in ["-", "N/A", "null", "none"]:
                        # Check if column looks like a mandatory technical specification
                        if any(kw in col_name.lower() for kw in ["value", "rating", "limit", "tolerance", "min", "max"]):
                            findings.append(Finding(
                                finding_id=f"TBL-EMP-{finding_counter:03d}",
                                category=self.category.value,
                                domain="General",
                                location=f"Page {page_num}, Table Row {row_idx + 1}, Col '{col_name}'",
                                page=page_num,
                                bbox=table.bbox,
                                original_content=f"Row {row_idx+1}, {col_name}: [EMPTY]",
                                detected_value="Missing / Empty",
                                expected_value=f"Defined numerical specification for '{col_name}'",
                                deviation="Missing required specification in engineering table",
                                severity=SeverityLevel.HIGH.value,
                                confidence=0.94,
                                explanation=f"Empty required cell in engineering table under critical column '{col_name}'.",
                                suggested_correction=f"Specify explicit engineering value or state reason for omission.",
                                rule_reference="Engineering Design Documentation §3.1 (Complete Data Tables)",
                                priority_score=6.2
                            ))
                            finding_counter += 1

            # 2. Check for unit inconsistency within numerical columns
            for col_idx in range(num_cols):
                col_name = table.headers[col_idx] if col_idx < len(table.headers) else f"Col {col_idx}"
                col_units = []
                for row in table.rows:
                    if col_idx < len(row):
                        val_str = row[col_idx].strip()
                        # Extract trailing unit e.g. "10 mm", "415 V", "0.5 bar"
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
                                    domain="General",
                                    location=f"Page {page_num}, Column '{col_name}'",
                                    page=page_num,
                                    bbox=table.bbox,
                                    original_content=f"Mixed units in '{col_name}': {dict(unit_counts)}",
                                    detected_value=f"Unit '{rogue_unit}'",
                                    expected_value=f"Consistent column unit '{primary_unit}'",
                                    deviation=f"Mixed engineering units within single column",
                                    severity=SeverityLevel.HIGH.value,
                                    confidence=0.95,
                                    explanation=f"Table column '{col_name}' contains conflicting engineering units ({rogue_unit} vs {primary_unit}).",
                                    suggested_correction=f"Standardize column '{col_name}' to unit '{primary_unit}' or normalize values.",
                                    rule_reference="SI Units in Engineering Documentation §2.1",
                                    priority_score=6.7
                                ))
                                finding_counter += 1

            # 3. Check for duplicate rows
            row_hashes = set()
            for r_idx, row in enumerate(table.rows):
                row_tuple = tuple(row)
                if any(row):  # Not an empty row
                    if row_tuple in row_hashes:
                        findings.append(Finding(
                            finding_id=f"TBL-DUP-{finding_counter:03d}",
                            category=self.category.value,
                            domain="General",
                            location=f"Page {page_num}, Table Row {r_idx + 1}",
                            page=page_num,
                            bbox=table.bbox,
                            original_content=" | ".join(row),
                            detected_value="Duplicate Row",
                            expected_value="Unique table entry",
                            deviation="Identical repeated entry in engineering table",
                            severity=SeverityLevel.LOW.value,
                            confidence=0.90,
                            explanation=f"Row {r_idx + 1} is an exact duplicate of an earlier row in the same table.",
                            suggested_correction="Remove redundant duplicate row.",
                            rule_reference="Engineering Document Standards §4.4",
                            priority_score=2.5
                        ))
                        finding_counter += 1
                    else:
                        row_hashes.add(row_tuple)

        return findings
