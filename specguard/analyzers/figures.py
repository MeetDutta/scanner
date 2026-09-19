"""
Figure and Diagram Analysis Engine for SpecGuard.

Detects, associates, and validates figures, charts, and diagrams:
- Detects captions above or below figure regions
- Extracts figure labels ("Fig. 1", "Figure 2", "Figure 3a")
- Validates numbering continuity (e.g. Fig. 1 -> Fig. 3 missing Fig. 2)
- Detects duplicate figure numbers and uncaptioned figures
- Validates caption placement according to profile (e.g. below figure for IEEE)
- Populates DocumentModel.figures
"""

import re
from typing import List, Dict, Tuple, Optional, Any
import logging

from specguard.analyzers.base import BaseAnalyzer
from specguard.core.models import (
    DocumentModel, Finding, FindingCategory, SeverityLevel, FigureData, BBox
)
from specguard.core.profiles import ProfileRegistry

logger = logging.getLogger(__name__)


class FigureAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Figure Analyzer"

    @property
    def category(self) -> FindingCategory:
        return FindingCategory.FIGURE

    def analyze(self, doc: DocumentModel, context: Dict[str, Any] = None) -> List[Finding]:
        findings: List[Finding] = []
        finding_counter = 1
        context = context or {}
        profile_id = context.get("profile", getattr(doc, "profile_name", "mechanical"))
        profile = ProfileRegistry.get_profile(profile_id)

        all_figures: List[FigureData] = []
        for page in doc.pages:
            for fig in page.figures:
                all_figures.append(fig)

        # Caption regex: "Figure 1:", "Fig. 1.", "Figure 2 -", "Fig. 2b"
        fig_caption_re = re.compile(
            r'^(?:Figure|Fig\.?)\s+([0-9]+[a-z]?)[\.:\-]?\s*(.*)$',
            re.IGNORECASE
        )

        # 1. Associate captions with figures based on geometric proximity
        for fig in all_figures:
            page = next((p for p in doc.pages if p.page_num == fig.page_num), None)
            if not page:
                continue

            best_caption = ""
            best_label = ""
            best_pos = "none"

            for b in page.blocks:
                txt = b.text.strip()
                m = fig_caption_re.match(txt)
                if m:
                    # Check vertical proximity
                    # Below figure: b.bbox.y0 close to fig.bbox.y1
                    if abs(b.bbox.y0 - fig.bbox.y1) < 65.0 or (b.bbox.y0 >= fig.bbox.y1 - 10.0 and b.bbox.y0 <= fig.bbox.y1 + 50.0):
                        best_caption = txt
                        best_label = f"Figure {m.group(1)}"
                        best_pos = "below"
                        break
                    # Above figure: b.bbox.y1 close to fig.bbox.y0
                    elif abs(b.bbox.y1 - fig.bbox.y0) < 65.0:
                        best_caption = txt
                        best_label = f"Figure {m.group(1)}"
                        best_pos = "above"
                        break

            if best_caption:
                fig.caption = best_caption
                fig.label = best_label
                fig.caption_position = best_pos

        # Also search text blocks for figure captions that might not have an extracted image region
        # (e.g. vector diagrams rendered as text/paths)
        existing_labels = {f.label.lower() for f in all_figures if f.label}
        for page in doc.pages:
            for b in page.blocks:
                txt = b.text.strip()
                m = fig_caption_re.match(txt)
                if m:
                    lbl = f"Figure {m.group(1)}".lower()
                    if lbl not in existing_labels:
                        # Register as detected figure caption region
                        phantom_fig = FigureData(
                            bbox=b.bbox,
                            page_num=page.page_num,
                            caption=txt,
                            caption_position="below",
                            figure_type="vector_or_inline",
                            figure_id=f"fig_txt_p{page.page_num}_{len(all_figures) + 1}",
                            label=f"Figure {m.group(1)}",
                            confidence=0.85
                        )
                        all_figures.append(phantom_fig)
                        existing_labels.add(lbl)

        doc.figures = all_figures

        # 2. Validate numbering sequence and duplicates
        numbered_figures: List[Tuple[int, FigureData]] = []
        for fig in all_figures:
            if fig.label:
                m = re.search(r'\d+', fig.label)
                if m:
                    numbered_figures.append((int(m.group(0)), fig))

        # Check for duplicate figure labels
        seen_fig_nums: Dict[int, FigureData] = {}
        for num_val, fig in numbered_figures:
            if num_val in seen_fig_nums:
                prev_fig = seen_fig_nums[num_val]
                findings.append(Finding(
                    finding_id=f"FIG-DUP-{finding_counter:03d}",
                    category=self.category.value,
                    domain=profile.domain,
                    location=f"Page {fig.page_num}",
                    page=fig.page_num,
                    bbox=fig.bbox,
                    original_content=fig.caption or fig.label,
                    detected_value=f"Duplicate Figure {num_val}",
                    expected_value=f"Unique Figure Number (next: {max(seen_fig_nums.keys()) + 1})",
                    deviation=f"Duplicate Figure {num_val} already declared on Page {prev_fig.page_num}",
                    severity=SeverityLevel.HIGH.value,
                    confidence=0.96,
                    explanation=f"Figure numbering conflict: Figure {num_val} is declared on Page {fig.page_num}, but was already defined on Page {prev_fig.page_num}.",
                    suggested_correction=f"Renumber Figure on Page {fig.page_num} to maintain unique monotonic sequence.",
                    rule_reference="Engineering Document Standards §5.1 (Figure Numbering)",
                    priority_score=6.8,
                    evidence=f"Page {fig.page_num}: '{fig.caption}' conflicts with Page {prev_fig.page_num}: '{prev_fig.caption}'",
                    detection_method="sequence_tracking"
                ))
                finding_counter += 1
            else:
                seen_fig_nums[num_val] = fig

        # Check for sequence jumps (e.g. Figure 1 -> Figure 3)
        sorted_nums = sorted(seen_fig_nums.keys())
        for i in range(len(sorted_nums) - 1):
            curr_n = sorted_nums[i]
            next_n = sorted_nums[i + 1]
            if next_n > curr_n + 1:
                fig = seen_fig_nums[next_n]
                findings.append(Finding(
                    finding_id=f"FIG-SEQ-{finding_counter:03d}",
                    category=self.category.value,
                    domain=profile.domain,
                    location=f"Page {fig.page_num}",
                    page=fig.page_num,
                    bbox=fig.bbox,
                    original_content=fig.caption or fig.label,
                    detected_value=f"Figure {next_n}",
                    expected_value=f"Figure {curr_n + 1}",
                    deviation=f"Figure sequence gap: Figure {curr_n + 1} is missing",
                    severity=SeverityLevel.MEDIUM.value,
                    confidence=0.92,
                    explanation=f"Figure numbering jumps from Figure {curr_n} directly to Figure {next_n}, skipping Figure {curr_n + 1}.",
                    suggested_correction=f"Renumber Figure {next_n} to Figure {curr_n + 1} or insert the missing figure.",
                    rule_reference="Engineering Documentation Standard §5.1",
                    priority_score=5.0,
                    evidence=f"Jump from Figure {curr_n} to Figure {next_n}",
                    detection_method="sequence_continuity"
                ))
                finding_counter += 1

        # Check caption placement
        for fig in all_figures:
            if fig.caption and profile.figure_caption_position != "any":
                if fig.caption_position != profile.figure_caption_position and fig.caption_position != "none":
                    findings.append(Finding(
                        finding_id=f"FIG-CAP-{finding_counter:03d}",
                        category=self.category.value,
                        domain=profile.domain,
                        location=f"Page {fig.page_num}",
                        page=fig.page_num,
                        bbox=fig.bbox,
                        original_content=fig.caption,
                        detected_value=f"Caption placed {fig.caption_position}",
                        expected_value=f"Caption placed {profile.figure_caption_position}",
                        deviation=f"Figure caption placement deviation ({fig.caption_position} instead of {profile.figure_caption_position})",
                        severity=SeverityLevel.LOW.value,
                        confidence=0.88,
                        explanation=f"Under '{profile.display_name}' formatting guidelines, figure captions should be placed {profile.figure_caption_position} the figure.",
                        suggested_correction=f"Relocate caption {profile.figure_caption_position} the figure illustration.",
                        rule_reference=f"{profile.display_name} Style Guide (Figure Captions)",
                        priority_score=3.2,
                        evidence=f"Caption: '{fig.caption}' positioned {fig.caption_position}",
                        detection_method="layout_geometry"
                    ))
                    finding_counter += 1

        # Check for uncaptioned standalone figures
        for fig in all_figures:
            if not fig.caption and fig.bbox.height > 80.0 and fig.bbox.width > 120.0:
                findings.append(Finding(
                    finding_id=f"FIG-UNCAP-{finding_counter:03d}",
                    category=self.category.value,
                    domain=profile.domain,
                    location=f"Page {fig.page_num}",
                    page=fig.page_num,
                    bbox=fig.bbox,
                    original_content=f"Figure region at ({fig.bbox.x0:.0f}, {fig.bbox.y0:.0f})",
                    detected_value="Uncaptioned Figure",
                    expected_value="Figure with explicit label and caption",
                    deviation="Missing figure caption or label",
                    severity=SeverityLevel.LOW.value,
                    confidence=0.82,
                    explanation=f"A graphic or diagram region of size {fig.bbox.width:.0f}x{fig.bbox.height:.0f}pt on Page {fig.page_num} lacks a detected caption.",
                    suggested_correction="Add an explicit 'Fig. X: Description' caption beneath the graphic.",
                    rule_reference="Engineering Document Standards §5.2",
                    priority_score=2.8,
                    evidence=f"Region coordinates: {fig.bbox.to_dict()}",
                    detection_method="layout_geometry"
                ))
                finding_counter += 1

        return findings
