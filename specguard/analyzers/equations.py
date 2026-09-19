"""
Equation Analysis Engine for SpecGuard.

Identifies mathematical expressions and display equations:
- Detects numbered display equations e.g. "(1)", "(2.3)"
- Validates equation numbering sequence and duplicate labels
- Associates labels with equation bounding boxes
- Populates DocumentModel.equations
"""

import re
from typing import List, Dict, Tuple, Optional, Any
import logging

from specguard.analyzers.base import BaseAnalyzer
from specguard.core.models import (
    DocumentModel, Finding, FindingCategory, SeverityLevel, EquationData, BBox
)
from specguard.core.profiles import ProfileRegistry

logger = logging.getLogger(__name__)


class EquationAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Equation Analyzer"

    @property
    def category(self) -> FindingCategory:
        return FindingCategory.EQUATION

    def analyze(self, doc: DocumentModel, context: Dict[str, Any] = None) -> List[Finding]:
        findings: List[Finding] = []
        finding_counter = 1
        context = context or {}
        profile_id = context.get("profile", getattr(doc, "profile_name", "mechanical"))
        profile = ProfileRegistry.get_profile(profile_id)

        all_equations: List[EquationData] = []

        # Regex to detect display equation label on right margin: e.g. "(1)", "(2)", "(3.1)", "(A.1)"
        eq_label_re = re.compile(r'\((\d+(?:\.\d+)*|[A-Z]\.\d+)\)\s*$')
        # Math symbols indicator
        math_symbols_re = re.compile(r'[=+\-×÷∫∑∏√∂≤≥≠≈∝∈∉⊂⊆∪∩θωπλσμΔ∇]')

        for page in doc.pages:
            page_eqs: List[EquationData] = []
            for b in page.blocks:
                txt = b.text.strip()
                if not txt:
                    continue

                # Check if block ends with or consists of equation numbering "(1)"
                m = eq_label_re.search(txt)
                has_math = bool(math_symbols_re.search(txt))

                if m and (has_math or b.bbox.x1 > page.width * 0.7 or len(txt) < 80):
                    label_str = f"({m.group(1)})"
                    eq_id = f"eq_p{page.page_num}_{m.group(1)}"
                    eq_data = EquationData(
                        equation_id=eq_id,
                        page_num=page.page_num,
                        bbox=b.bbox,
                        text=txt,
                        label=label_str,
                        is_inline=False,
                        is_numbered=True,
                        confidence=0.92
                    )
                    page_eqs.append(eq_data)
                    all_equations.append(eq_data)

            page.equations = page_eqs

        doc.equations = all_equations

        # Validate equation numbering continuity
        numbered_eqs: List[Tuple[int, EquationData]] = []
        for eq in all_equations:
            m = re.search(r'\d+', eq.label)
            if m:
                numbered_eqs.append((int(m.group(0)), eq))

        # Check duplicates
        seen_eq_nums: Dict[int, EquationData] = {}
        for num_val, eq in numbered_eqs:
            if num_val in seen_eq_nums:
                prev_eq = seen_eq_nums[num_val]
                findings.append(Finding(
                    finding_id=f"EQ-DUP-{finding_counter:03d}",
                    category=self.category.value,
                    domain=profile.domain,
                    location=f"Page {eq.page_num}",
                    page=eq.page_num,
                    bbox=eq.bbox,
                    original_content=eq.text,
                    detected_value=f"Duplicate Equation ({num_val})",
                    expected_value=f"Unique Equation Number (next: {max(seen_eq_nums.keys()) + 1})",
                    deviation=f"Duplicate Equation ({num_val}) already declared on Page {prev_eq.page_num}",
                    severity=SeverityLevel.HIGH.value,
                    confidence=0.95,
                    explanation=f"Equation numbering collision: Equation ({num_val}) appears on Page {eq.page_num}, but was already defined on Page {prev_eq.page_num}.",
                    suggested_correction=f"Renumber Equation on Page {eq.page_num} to a unique sequence index.",
                    rule_reference="Mathematical Formatting Standards §2.1",
                    priority_score=6.0,
                    evidence=f"Page {eq.page_num}: '{eq.text}' conflicts with Page {prev_eq.page_num}: '{prev_eq.text}'",
                    detection_method="sequence_tracking"
                ))
                finding_counter += 1
            else:
                seen_eq_nums[num_val] = eq

        # Check sequence jumps (e.g. Eq (1) -> Eq (3))
        sorted_nums = sorted(seen_eq_nums.keys())
        for i in range(len(sorted_nums) - 1):
            curr_n = sorted_nums[i]
            next_n = sorted_nums[i + 1]
            if next_n > curr_n + 1:
                eq = seen_eq_nums[next_n]
                findings.append(Finding(
                    finding_id=f"EQ-SEQ-{finding_counter:03d}",
                    category=self.category.value,
                    domain=profile.domain,
                    location=f"Page {eq.page_num}",
                    page=eq.page_num,
                    bbox=eq.bbox,
                    original_content=eq.text,
                    detected_value=f"Equation ({next_n})",
                    expected_value=f"Equation ({curr_n + 1})",
                    deviation=f"Equation numbering sequence jump: Equation ({curr_n + 1}) is missing",
                    severity=SeverityLevel.MEDIUM.value,
                    confidence=0.90,
                    explanation=f"Equation numbering jumps from ({curr_n}) to ({next_n}), skipping Equation ({curr_n + 1}).",
                    suggested_correction=f"Renumber Equation ({next_n}) to ({curr_n + 1}) or verify omitted equation.",
                    rule_reference="Mathematical Formatting Standards §2.1",
                    priority_score=4.8,
                    evidence=f"Jump from ({curr_n}) to ({next_n})",
                    detection_method="sequence_continuity"
                ))
                finding_counter += 1

        return findings
