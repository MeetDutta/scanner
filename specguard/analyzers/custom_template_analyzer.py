"""
Custom Template Compliance and Drift Analyzer for SpecGuard.
Evaluates incoming multi-page documents against approved custom template profiles
and flags both critical compliance violations and stylistic template drift.
Strictly 100% offline.
"""

import logging
from typing import List, Dict, Any, Optional
from collections import Counter

from specguard.core.models import DocumentModel, Finding, FindingCategory, SeverityLevel
from specguard.core.profiles import ProfileConfig
from specguard.templates.custom_manager import CustomTemplateManager

logger = logging.getLogger(__name__)


class CustomTemplateAnalyzer:
    """Evaluates documents against user-defined, learned, and approved template profiles."""

    def __init__(self, template_manager: Optional[CustomTemplateManager] = None):
        self.template_manager = template_manager or CustomTemplateManager()

    def analyze(self, document: DocumentModel, profile: ProfileConfig) -> List[Finding]:
        """
        Runs compliance and drift checks against custom template profile rules.
        """
        # If not a custom template or no custom rules, return empty
        custom_tmpl_id = profile.custom_rules.get("custom_template_id")
        if not custom_tmpl_id:
            return []

        profile_data = self.template_manager.get_profile(custom_tmpl_id)
        if not profile_data:
            return []

        findings: List[Finding] = []
        summary_rules = profile_data.get("summary_rules", {})
        learned_props = profile_data.get("learned_properties", {})
        tolerances = profile_data.get("tolerances", {
            "font_size_pt": 1.0,
            "margin_mm": 5.0,
            "column_width_mm": 10.0
        })

        layout_rules = summary_rules.get("layout", {})
        typo_rules = summary_rules.get("typography", {})
        struct_rules = summary_rules.get("structure", {})
        object_rules = summary_rules.get("objects", {})

        # ----------------------------------------------------
        # 1. LAYOUT & COLUMN DRIFT
        # ----------------------------------------------------
        expected_cols = layout_rules.get("column_count")
        if expected_cols:
            col_counts = []
            for p in document.pages:
                cols = {getattr(b, "column_id", 0) for b in p.blocks}
                col_counts.append(max(len(cols), 1))
            dom_cols = Counter(col_counts).most_common(1)[0][0] if col_counts else 1

            if dom_cols != expected_cols:
                findings.append(Finding(
                    finding_id=f"TMPL-{custom_tmpl_id.upper()}-LAYOUT-COL",
                    category=FindingCategory.FORMATTING.value,
                    domain=profile.domain,
                    location="Page Layout",
                    page=1,
                    original_content=f"{dom_cols} Columns",
                    detected_value=f"{dom_cols} column(s)",
                    expected_value=f"{expected_cols} column(s)",
                    deviation=f"Expected {expected_cols} columns, observed {dom_cols}",
                    severity=SeverityLevel.HIGH.value,
                    confidence=0.95,
                    explanation=(
                        f"Document layout has {dom_cols} column(s), but template '{profile.display_name}' "
                        f"requires {expected_cols} column(s)."
                    ),
                    suggested_correction=f"Format document using the required {expected_cols}-column layout.",
                    rule_reference=f"Template {custom_tmpl_id} Layout Rules",
                    evidence=f"Observed: {dom_cols} columns, Expected: {expected_cols} columns",
                    detection_method="custom_template_rule"
                ))

        # Page dimension drift
        expected_w = layout_rules.get("dominant_width")
        if expected_w and document.pages:
            obs_w = document.pages[0].width
            if abs(obs_w - expected_w) > 20.0:  # ~7mm
                findings.append(Finding(
                    finding_id=f"TMPL-{custom_tmpl_id.upper()}-DRIFT-PAGESIZE",
                    category=FindingCategory.FORMATTING.value,
                    domain=profile.domain,
                    location="Page Geometry",
                    page=1,
                    original_content=f"Width {obs_w:.1f}pt",
                    detected_value=f"{obs_w:.1f}pt",
                    expected_value=f"{expected_w:.1f}pt",
                    deviation=f"Page width delta: {abs(obs_w - expected_w):.1f}pt",
                    severity=SeverityLevel.LOW.value,
                    confidence=0.90,
                    explanation=(
                        f"Document page width ({obs_w:.1f}pt) differs from template baseline ({expected_w:.1f}pt). "
                        f"Check paper size settings."
                    ),
                    suggested_correction="Verify document paper size matches the approved template standard.",
                    rule_reference=f"Template {custom_tmpl_id} Dimensions",
                    evidence=f"Width delta: {abs(obs_w - expected_w):.1f}pt",
                    detection_method="custom_template_drift"
                ))

        # ----------------------------------------------------
        # 2. TYPOGRAPHY & FONT DRIFT
        # ----------------------------------------------------
        expected_bfs = typo_rules.get("body_font_size")
        if expected_bfs and document.pages:
            font_sizes = []
            for p in document.pages:
                for b in p.blocks:
                    for l in b.lines:
                        for w in l.words:
                            if w.font_size and w.font_size <= 14.0:
                                font_sizes.append(round(w.font_size, 1))
            if font_sizes:
                dom_bfs = Counter(font_sizes).most_common(1)[0][0]
                fs_tol = tolerances.get("font_size_pt", 1.0)
                if abs(dom_bfs - expected_bfs) > fs_tol:
                    findings.append(Finding(
                        finding_id=f"TMPL-{custom_tmpl_id.upper()}-DRIFT-FONTSIZE",
                        category=FindingCategory.FORMATTING.value,
                        domain=profile.domain,
                        location="Document Typography",
                        page=1,
                        original_content=f"Body Font {dom_bfs:.1f}pt",
                        detected_value=f"{dom_bfs:.1f}pt",
                        expected_value=f"{expected_bfs:.1f}pt ±{fs_tol}pt",
                        deviation=f"Font size delta: {abs(dom_bfs - expected_bfs):.1f}pt",
                        severity=SeverityLevel.MEDIUM.value,
                        confidence=0.88,
                        explanation=(
                            f"Detected body font size {dom_bfs:.1f}pt deviates from template baseline "
                            f"{expected_bfs:.1f}pt by more than allowable tolerance (±{fs_tol}pt)."
                        ),
                        suggested_correction=f"Adjust body text to {expected_bfs:.1f}pt.",
                        rule_reference=f"Template {custom_tmpl_id} Typography",
                        evidence=f"Observed: {dom_bfs:.1f}pt, Expected: {expected_bfs:.1f}pt ±{fs_tol}pt",
                        detection_method="custom_template_drift"
                    ))

        # ----------------------------------------------------
        # 3. STRUCTURE & MANDATORY SECTIONS
        # ----------------------------------------------------
        required_secs = struct_rules.get("required_sections", [])
        doc_sec_titles = [s.title.lower().strip() for s in document.sections]

        for req_sec in required_secs:
            req_clean = req_sec.lower().strip()
            found = any(req_clean in t or t in req_clean for t in doc_sec_titles)
            if not found:
                findings.append(Finding(
                    finding_id=f"TMPL-{custom_tmpl_id.upper()}-SEC-MISSING",
                    category=FindingCategory.STRUCTURE.value,
                    domain=profile.domain,
                    location="Section Outline",
                    page=1,
                    original_content="[Document Outline]",
                    detected_value="Section Missing",
                    expected_value=f"Mandatory Section: '{req_sec}'",
                    deviation=f"Missing section '{req_sec}'",
                    severity=SeverityLevel.HIGH.value,
                    confidence=0.95,
                    explanation=(
                        f"The required section '{req_sec}' defined in template '{profile.display_name}' "
                        f"was not found in the document."
                    ),
                    suggested_correction=f"Add the required section '{req_sec}' to the document outline.",
                    rule_reference=f"Template {custom_tmpl_id} Structure",
                    evidence=f"Missing Section: '{req_sec}'",
                    detection_method="custom_template_rule"
                ))

        # Numbering style
        req_num_style = struct_rules.get("numbering_style")
        if req_num_style and req_num_style != "any" and document.sections:
            num_styles = []
            for s in document.sections:
                num = (getattr(s, "number_str", "") or getattr(s, "number", "")).strip()
                if num:
                    if any(num.startswith(r) for r in ["I", "II", "III", "IV", "V", "VI"]):
                        num_styles.append("roman")
                    elif any(c.isdigit() for c in num):
                        num_styles.append("numeric")
            if num_styles:
                dom_style = Counter(num_styles).most_common(1)[0][0]
                if dom_style != req_num_style:
                    findings.append(Finding(
                        finding_id=f"TMPL-{custom_tmpl_id.upper()}-NUM-STYLE",
                        category=FindingCategory.STRUCTURE.value,
                        domain=profile.domain,
                        location="Section Headings",
                        page=1,
                        original_content=f"{dom_style} numbering",
                        detected_value=f"{dom_style}",
                        expected_value=f"{req_num_style}",
                        deviation=f"Expected {req_num_style} numbering, observed {dom_style}",
                        severity=SeverityLevel.MEDIUM.value,
                        confidence=0.85,
                        explanation=(
                            f"Document uses {dom_style} numbering, but template '{profile.display_name}' "
                            f"specifies {req_num_style} numbering."
                        ),
                        suggested_correction=f"Change section headings to use {req_num_style} numbering.",
                        rule_reference=f"Template {custom_tmpl_id} Numbering",
                        evidence=f"Observed: {dom_style}, Required: {req_num_style}",
                        detection_method="custom_template_rule"
                    ))

        # ----------------------------------------------------
        # 4. CAPTION PLACEMENT (TABLES & FIGURES)
        # ----------------------------------------------------
        exp_tbl_pos = object_rules.get("table_caption_position")
        if exp_tbl_pos:
            for tbl in document.tables:
                if tbl.caption and tbl.caption_position and tbl.caption_position != exp_tbl_pos:
                    findings.append(Finding(
                        finding_id=f"TMPL-{custom_tmpl_id.upper()}-TBL-CAPTION-POS",
                        category=FindingCategory.TABLE.value,
                        domain=profile.domain,
                        location="Table Captions",
                        page=getattr(tbl, "page_num", 1),
                        original_content=tbl.caption,
                        detected_value=tbl.caption_position,
                        expected_value=exp_tbl_pos,
                        deviation=f"Caption placed {tbl.caption_position} instead of {exp_tbl_pos}",
                        severity=SeverityLevel.LOW.value,
                        confidence=0.90,
                        explanation=(
                            f"Table caption '{tbl.caption[:30]}...' is placed {tbl.caption_position}, "
                            f"but template specifies caption {exp_tbl_pos} table."
                        ),
                        suggested_correction=f"Place table captions {exp_tbl_pos} the table.",
                        rule_reference=f"Template {custom_tmpl_id} Captions",
                        evidence=f"Observed: {tbl.caption_position}, Required: {exp_tbl_pos}",
                        detection_method="custom_template_drift"
                    ))

        return findings
