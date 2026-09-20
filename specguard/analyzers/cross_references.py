"""
Citation and Cross-Reference Analysis Engine for SpecGuard.

Builds a document-wide cross-reference graph:
- Tracks textual references to Figures, Tables, Equations, Sections, and Citations:
  * "Fig. 1", "Figure 2", "Figs. 3-4"
  * "Table I", "Table 2", "TABLE 3"
  * "Eq. (1)", "Equation (4)", "Eqs. (2)-(3)"
  * "Section II", "Section 3.1"
  * "[1]", "[2], [3]", "[4]-[7]"
- Verifies whether referenced targets exist in the document
- Flags dangling/unresolved cross-references with page and bbox evidence
- Flags unreferenced figures and tables
- Populates DocumentModel.cross_references and DocumentModel.references
"""

import re
from typing import List, Dict, Tuple, Optional, Any, Set
import logging

from specguard.analyzers.base import BaseAnalyzer
from specguard.core.models import (
    DocumentModel, Finding, FindingCategory, SeverityLevel,
    CrossReferenceItem, ReferenceItem, BBox, FigureData, TableData, EquationData
)
from specguard.core.profiles import ProfileRegistry
from specguard.core.location_mapper import LocationMapper

logger = logging.getLogger(__name__)

ROMAN_VALS = {'i': 1, 'v': 5, 'x': 10, 'l': 50, 'c': 100}

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


class CrossReferenceAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Cross-Reference Analyzer"

    @property
    def category(self) -> FindingCategory:
        return FindingCategory.CROSS_REFERENCE

    def analyze(self, doc: DocumentModel, context: Dict[str, Any] = None) -> List[Finding]:
        findings: List[Finding] = []
        finding_counter = 1
        context = context or {}
        profile_id = context.get("profile", getattr(doc, "profile_name", "mechanical"))
        profile = ProfileRegistry.get_profile(profile_id)

        # 1. Extract Bibliography / References list if present
        ref_items: List[ReferenceItem] = []
        ref_bracket_re = re.compile(r'^\[(\d+)\]\s+(.*)$')

        in_references_section = False
        for page in doc.pages:
            for b in page.blocks:
                txt = b.text.strip()
                if txt.lower() in ["references", "bibliography", "works cited"]:
                    in_references_section = True
                    continue

                if in_references_section:
                    # Stop if we enter Appendix or Acknowledgment
                    if re.match(r'^(?:Appendix|Acknowledgment)', txt, re.IGNORECASE) and b.is_bold:
                        in_references_section = False
                        break

                    m = ref_bracket_re.match(txt)
                    if m:
                        ref_items.append(ReferenceItem(
                            ref_id=f"ref_{m.group(1)}",
                            label=f"[{m.group(1)}]",
                            raw_text=txt,
                            page_num=page.page_num
                        ))

        doc.references = ref_items
        declared_citation_ids = {int(re.search(r'\d+', r.label).group(0)) for r in ref_items}

        # 2. Gather declared document assets
        declared_figures: Dict[int, FigureData] = {}
        for fig in doc.figures:
            if fig.label:
                m = re.search(r'\d+', fig.label)
                if m:
                    declared_figures[int(m.group(0))] = fig

        declared_tables: Dict[int, TableData] = {}
        for tbl in doc.tables:
            if tbl.label:
                m = re.search(r'\b([0-9]+|[IVXLCDM]+)\b', tbl.label)
                if m:
                    val_str = m.group(1)
                    if val_str.isdigit():
                        declared_tables[int(val_str)] = tbl
                    else:
                        r_int = roman_to_int(val_str)
                        if r_int:
                            declared_tables[r_int] = tbl

        declared_equations: Dict[str, EquationData] = {}
        for eq in doc.equations:
            m = re.search(r'\d+', eq.label)
            if m:
                declared_equations[m.group(0)] = eq

        # 3. Scan body text for cross-references
        cross_refs: List[CrossReferenceItem] = []
        referenced_figure_ids: Set[int] = set()
        referenced_table_ids: Set[int] = set()
        referenced_equation_ids: Set[str] = set()
        referenced_citation_ids: Set[int] = set()

        # Regex patterns for mentions
        fig_ref_re = re.compile(r'\b(?:Fig(?:ure)?s?\.?)\s*([0-9]+(?:[a-z]|(?:\s*(?:and|to|-|–)\s*[0-9]+))?)', re.IGNORECASE)
        tbl_ref_re = re.compile(r'\b(?:Table|TABLE)s?\s+([0-9]+|[IVXLCDM]+)', re.IGNORECASE)
        eq_ref_re = re.compile(r'\b(?:Eq(?:uation)?s?\.?)\s*\(([0-9]+(?:\.[0-9]+)*)\)', re.IGNORECASE)
        cite_ref_re = re.compile(r'\[([0-9]+(?:(?:\s*,\s*|\s*[-–]\s*)[0-9]+)*)\]')

        for page in doc.pages:
            for b in page.blocks:
                txt = b.text.strip()
                # Skip checking caption blocks as their own reference
                if any(txt == f.caption for f in doc.figures if f.caption):
                    continue
                if any(txt == t.caption for t in doc.tables if t.caption):
                    continue
                if any(txt == r.raw_text for r in ref_items):
                    continue

                # Scan Figures
                for m in fig_ref_re.finditer(txt):
                    digits = re.findall(r'\d+', m.group(1))
                    mention_str = m.group(0)
                    m_boxes = LocationMapper.find_phrase_bboxes(page, mention_str, block_id=b.block_id)
                    m_bbox = m_boxes[0] if m_boxes else b.bbox
                    m_prec = "EXACT_PHRASE" if m_boxes else "APPROXIMATE"

                    for d_str in digits:
                        f_id = int(d_str)
                        referenced_figure_ids.add(f_id)
                        is_resolved = f_id in declared_figures
                        cross_refs.append(CrossReferenceItem(
                            ref_type="figure",
                            source_page=page.page_num,
                            source_bbox=m_bbox,
                            mention_text=mention_str,
                            target_id=f"fig_{f_id}",
                            is_resolved=is_resolved
                        ))

                        if not is_resolved:
                            findings.append(Finding(
                                finding_id=f"XREF-FIG-{finding_counter:03d}",
                                category=self.category.value,
                                domain=profile.domain,
                                location=f"Page {page.page_num}",
                                page=page.page_num,
                                bbox=m_bbox,
                                bounding_boxes=m_boxes if m_boxes else ([m_bbox] if m_bbox else []),
                                location_precision=m_prec,
                                matched_text=mention_str,
                                expected_text=f"Figure {f_id}",
                                issue_type="UNRESOLVED_FIGURE_REFERENCE",
                                target_object_id=f"fig_{f_id}",
                                original_content=txt,
                                detected_value=f"Reference to Figure {f_id}",
                                expected_value=f"Figure {f_id} defined in document",
                                deviation=f"Unresolved cross-reference: Figure {f_id} does not exist",
                                severity=SeverityLevel.HIGH.value,
                                confidence=0.96,
                                explanation=f"Text on Page {page.page_num} references '{mention_str}', but no Figure with label {f_id} exists in the analyzed document.",
                                suggested_correction=f"Insert Figure {f_id} or update the citation in text.",
                                suggested_fix=f"Add Figure {f_id} or correct reference '{mention_str}'.",
                                rule_reference="Document Integrity Standards §5.3 (Cross-Reference Resolution)",
                                priority_score=7.0,
                                evidence=f"Mention: '{mention_str}' on Page {page.page_num}",
                                detection_method="reference_graph"
                            ))
                            finding_counter += 1

                # Scan Tables
                for m in tbl_ref_re.finditer(txt):
                    t_str = m.group(1)
                    t_id = int(t_str) if t_str.isdigit() else roman_to_int(t_str)
                    mention_str = m.group(0)
                    m_boxes = LocationMapper.find_phrase_bboxes(page, mention_str, block_id=b.block_id)
                    m_bbox = m_boxes[0] if m_boxes else b.bbox
                    m_prec = "EXACT_PHRASE" if m_boxes else "APPROXIMATE"

                    if t_id:
                        referenced_table_ids.add(t_id)
                        is_resolved = t_id in declared_tables
                        cross_refs.append(CrossReferenceItem(
                            ref_type="table",
                            source_page=page.page_num,
                            source_bbox=m_bbox,
                            mention_text=mention_str,
                            target_id=f"tbl_{t_id}",
                            is_resolved=is_resolved
                        ))

                        if not is_resolved:
                            findings.append(Finding(
                                finding_id=f"XREF-TBL-{finding_counter:03d}",
                                category=self.category.value,
                                domain=profile.domain,
                                location=f"Page {page.page_num}",
                                page=page.page_num,
                                bbox=m_bbox,
                                bounding_boxes=m_boxes if m_boxes else ([m_bbox] if m_bbox else []),
                                location_precision=m_prec,
                                matched_text=mention_str,
                                expected_text=f"Table {t_str}",
                                issue_type="UNRESOLVED_TABLE_REFERENCE",
                                target_object_id=f"tbl_{t_id}",
                                original_content=txt,
                                detected_value=f"Reference to Table {t_str}",
                                expected_value=f"Table {t_str} defined in document",
                                deviation=f"Unresolved cross-reference: Table {t_str} does not exist",
                                severity=SeverityLevel.HIGH.value,
                                confidence=0.96,
                                explanation=f"Text on Page {page.page_num} references '{mention_str}', but no Table with label '{t_str}' was detected.",
                                suggested_correction=f"Add Table {t_str} or update the in-text reference.",
                                suggested_fix=f"Add Table {t_str} or correct reference '{mention_str}'.",
                                rule_reference="Document Integrity Standards §5.3 (Cross-Reference Resolution)",
                                priority_score=7.0,
                                evidence=f"Mention: '{mention_str}' on Page {page.page_num}",
                                detection_method="reference_graph"
                            ))
                            finding_counter += 1

                # Scan Equations
                for m in eq_ref_re.finditer(txt):
                    eq_num = m.group(1)
                    mention_str = m.group(0)
                    m_boxes = LocationMapper.find_phrase_bboxes(page, mention_str, block_id=b.block_id)
                    m_bbox = m_boxes[0] if m_boxes else b.bbox
                    m_prec = "EXACT_PHRASE" if m_boxes else "APPROXIMATE"

                    referenced_equation_ids.add(eq_num)
                    is_resolved = eq_num in declared_equations
                    cross_refs.append(CrossReferenceItem(
                        ref_type="equation",
                        source_page=page.page_num,
                        source_bbox=m_bbox,
                        mention_text=mention_str,
                        target_id=f"eq_{eq_num}",
                        is_resolved=is_resolved
                    ))

                    if not is_resolved and declared_equations:
                        findings.append(Finding(
                            finding_id=f"XREF-EQ-{finding_counter:03d}",
                            category=self.category.value,
                            domain=profile.domain,
                            location=f"Page {page.page_num}",
                            page=page.page_num,
                            bbox=m_bbox,
                            bounding_boxes=m_boxes if m_boxes else ([m_bbox] if m_bbox else []),
                            location_precision=m_prec,
                            matched_text=mention_str,
                            expected_text=f"Equation ({eq_num})",
                            issue_type="UNRESOLVED_EQUATION_REFERENCE",
                            target_object_id=f"eq_{eq_num}",
                            original_content=txt,
                            detected_value=f"Reference to Eq. ({eq_num})",
                            expected_value=f"Equation ({eq_num}) defined in document",
                            deviation=f"Unresolved cross-reference: Equation ({eq_num}) does not exist",
                            severity=SeverityLevel.MEDIUM.value,
                            confidence=0.90,
                            explanation=f"Text on Page {page.page_num} references Equation ({eq_num}), but no corresponding numbered equation was detected.",
                            suggested_correction=f"Ensure equation ({eq_num}) is properly numbered or update text.",
                            suggested_fix=f"Number equation ({eq_num}) or update text reference.",
                            rule_reference="Mathematical Formatting Standards §2.2",
                            priority_score=5.5,
                            evidence=f"Mention: '{mention_str}' on Page {page.page_num}",
                            detection_method="reference_graph"
                        ))
                        finding_counter += 1

                # Scan Citations
                for m in cite_ref_re.finditer(txt):
                    raw_bracket = m.group(1)
                    # Expand citations like "1, 3" or "4-6"
                    for part in re.split(r'[,;]', raw_bracket):
                        part = part.strip()
                        if not part:
                            continue
                        dash_match = re.match(r'(\d+)\s*[-–]\s*(\d+)', part)
                        if dash_match:
                            start_c, end_c = int(dash_match.group(1)), int(dash_match.group(2))
                            c_range = list(range(start_c, end_c + 1))
                        elif part.isdigit():
                            c_range = [int(part)]
                        else:
                            c_range = []

                        for c_num in c_range:
                            referenced_citation_ids.add(c_num)
                            is_resolved = c_num in declared_citation_ids if declared_citation_ids else True
                            cite_str = f"[{c_num}]"
                            c_boxes = LocationMapper.find_token_in_text(txt, cite_str, b.words) or LocationMapper.find_phrase_bboxes(page, cite_str, block_id=b.block_id)
                            c_bbox = c_boxes[0] if c_boxes else b.bbox
                            c_prec = "EXACT_TOKEN" if c_boxes else "APPROXIMATE"

                            cross_refs.append(CrossReferenceItem(
                                ref_type="citation",
                                source_page=page.page_num,
                                source_bbox=c_bbox,
                                mention_text=cite_str,
                                target_id=f"ref_{c_num}",
                                is_resolved=is_resolved
                            ))

                            if declared_citation_ids and not is_resolved:
                                findings.append(Finding(
                                    finding_id=f"XREF-CIT-{finding_counter:03d}",
                                    category=self.category.value,
                                    domain=profile.domain,
                                    location=f"Page {page.page_num}",
                                    page=page.page_num,
                                    bbox=c_bbox,
                                    bounding_boxes=c_boxes if c_boxes else ([c_bbox] if c_bbox else []),
                                    location_precision=c_prec,
                                    matched_text=cite_str,
                                    expected_text=f"Reference [{c_num}] in bibliography",
                                    issue_type="UNRESOLVED_CITATION",
                                    target_object_id=f"ref_{c_num}",
                                    original_content=f"[{raw_bracket}]",
                                    detected_value=f"Citation [{c_num}]",
                                    expected_value=f"Bibliography entry [{c_num}]",
                                    deviation=f"Unresolved citation: [{c_num}] missing from References",
                                    severity=SeverityLevel.HIGH.value,
                                    confidence=0.95,
                                    explanation=f"Text on Page {page.page_num} cites [{c_num}], but no matching entry was found in the References list.",
                                    suggested_correction=f"Add bibliographic entry for [{c_num}] in References.",
                                    suggested_fix=f"Add entry for [{c_num}] in bibliography.",
                                    rule_reference="Academic Citation Standards §1.1",
                                    priority_score=6.8,
                                    evidence=f"Citation: [{c_num}] on Page {page.page_num}",
                                    detection_method="citation_graph"
                                ))
                                finding_counter += 1

        doc.cross_references = cross_refs

        # 4. Check for unreferenced Figures and Tables
        for fig_num, fig in declared_figures.items():
            if fig_num not in referenced_figure_ids:
                findings.append(Finding(
                    finding_id=f"XREF-UNREF-FIG-{finding_counter:03d}",
                    category=self.category.value,
                    domain=profile.domain,
                    location=f"Page {fig.page_num}",
                    page=fig.page_num,
                    bbox=fig.bbox,
                    original_content=fig.caption or fig.label,
                    detected_value=f"Figure {fig_num} (Unreferenced)",
                    expected_value=f"Textual cross-reference to Figure {fig_num}",
                    deviation=f"Figure {fig_num} is defined but never cited or discussed in document text",
                    severity=SeverityLevel.LOW.value,
                    confidence=0.90,
                    explanation=f"Figure {fig_num} is included on Page {fig.page_num}, but is never cited in the body of the document.",
                    suggested_correction=f"Add a textual reference (e.g. 'as shown in Fig. {fig_num}') in the preceding section.",
                    rule_reference="Engineering Document Standards §5.3 (Asset Referencing)",
                    priority_score=3.5,
                    evidence=f"Figure on Page {fig.page_num}: '{fig.caption or fig.label}'",
                    detection_method="reference_graph"
                ))
                finding_counter += 1

        for tbl_num, tbl in declared_tables.items():
            if tbl_num not in referenced_table_ids:
                findings.append(Finding(
                    finding_id=f"XREF-UNREF-TBL-{finding_counter:03d}",
                    category=self.category.value,
                    domain=profile.domain,
                    location=f"Page {tbl.page_num}",
                    page=tbl.page_num,
                    bbox=tbl.bbox,
                    original_content=tbl.caption or tbl.label,
                    detected_value=f"Table {tbl_num} (Unreferenced)",
                    expected_value=f"Textual cross-reference to Table {tbl_num}",
                    deviation=f"Table {tbl_num} is defined but never cited in document text",
                    severity=SeverityLevel.LOW.value,
                    confidence=0.90,
                    explanation=f"Table {tbl_num} appears on Page {tbl.page_num}, but is not mentioned or discussed in the text.",
                    suggested_correction=f"Cite Table {tbl_num} in the appropriate descriptive paragraph.",
                    rule_reference="Engineering Document Standards §4.3 (Asset Referencing)",
                    priority_score=3.5,
                    evidence=f"Table on Page {tbl.page_num}: '{tbl.caption or tbl.label}'",
                    detection_method="reference_graph"
                ))
                finding_counter += 1

        return findings
