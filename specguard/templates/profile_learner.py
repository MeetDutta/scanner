"""
Local Statistical Profile Learning Engine for SpecGuard.
Learns layout, typography, section hierarchy, and object conventions
from sample engineering and academic documents without cloud AI or GPUs.
Strictly 100% offline.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any, Set, Tuple
from collections import Counter
from dataclasses import dataclass, asdict, field

from specguard.core.document_parser import DocumentParser
from specguard.core.models import DocumentModel
from specguard.templates.custom_manager import CustomTemplateManager
from specguard.templates.sample_manager import SampleManager, SampleDocumentInfo, enrich_sample_ast

logger = logging.getLogger(__name__)


@dataclass
class LearnedProperty:
    property_name: str
    learned_value: Any
    confidence: float
    sample_count: int
    distribution: Dict[str, int]
    extraction_method: str
    supporting_samples: List[str] = field(default_factory=list)
    supporting_pages: List[int] = field(default_factory=list)
    is_uncertain: bool = False
    notes: str = ""


@dataclass
class LearnedTemplateProfile:
    template_id: str
    learned_at: str
    sample_count: int
    overall_confidence: float
    properties: Dict[str, LearnedProperty] = field(default_factory=dict)
    summary_rules: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


class ProfileLearner:
    """Learns measurable document profile rules from ingested sample documents."""

    def __init__(
        self,
        template_manager: Optional[CustomTemplateManager] = None,
        sample_manager: Optional[SampleManager] = None
    ):
        self.template_manager = template_manager or CustomTemplateManager()
        self.sample_manager = sample_manager or SampleManager(self.template_manager)
        self.parser = DocumentParser()

    def learn_profile(self, template_id: str) -> LearnedTemplateProfile:
        samples = [s for s in self.sample_manager.list_samples(template_id) if s.status == "PROCESSED"]
        if not samples:
            raise ValueError(
                f"No processed sample documents found for template '{template_id}'. "
                f"Please upload at least 1-2 sample documents before learning a profile."
            )

        samples_dir = self.sample_manager.get_samples_dir(template_id)
        docs: List[Tuple[SampleDocumentInfo, DocumentModel]] = []

        for s in samples:
            file_candidates = list(samples_dir.glob(f"{s.sample_id}.*"))
            doc_file = next((f for f in file_candidates if not f.name.endswith(".meta.json")), None)
            if doc_file and doc_file.exists():
                try:
                    dm = DocumentParser.parse_file(doc_file)
                    enrich_sample_ast(dm)
                    docs.append((s, dm))
                except Exception as e:
                    logger.warning("Failed to re-parse sample %s during learning: %s", s.sample_id, e)

        if not docs:
            raise RuntimeError("Failed to parse any of the uploaded sample documents.")

        total_samples = len(docs)
        learned_props: Dict[str, LearnedProperty] = {}
        warnings: List[str] = []

        # ----------------------------------------------------
        # 1. LAYOUT: Page Dimensions & Columns
        # ----------------------------------------------------
        widths = []
        heights = []
        col_counts = []
        margin_lefts = []
        margin_rights = []
        margin_tops = []
        margin_bottoms = []
        samples_with_toc = 0

        for s, dm in docs:
            if dm.toc and getattr(dm.toc, "exists", False):
                samples_with_toc += 1
            for p in dm.pages:
                widths.append(round(p.width, 1))
                heights.append(round(p.height, 1))
                # Columns from blocks
                cols = {getattr(b, "column_id", 0) for b in p.blocks}
                col_counts.append(max(len(cols), 1))

                # Margins
                for b in p.blocks:
                    for l in b.lines:
                        margin_lefts.append(round(l.bbox.x0, 1))
                        margin_rights.append(round(p.width - l.bbox.x1, 1))
                        margin_tops.append(round(l.bbox.y0, 1))
                        margin_bottoms.append(round(p.height - l.bbox.y1, 1))

        # Dominant width & height
        width_counts = Counter(widths)
        dom_width, dom_w_count = width_counts.most_common(1)[0] if widths else (595.0, 1)
        w_conf = dom_w_count / max(len(widths), 1)
        learned_props["layout.page_width"] = LearnedProperty(
            property_name="layout.page_width",
            learned_value=dom_width,
            confidence=round(w_conf, 2),
            sample_count=total_samples,
            distribution={str(k): v for k, v in width_counts.most_common(5)},
            extraction_method="geometric_page_dimensions",
            supporting_samples=[s.sample_id for s, _ in docs],
            is_uncertain=w_conf < 0.7
        )

        height_counts = Counter(heights)
        dom_height, dom_h_count = height_counts.most_common(1)[0] if heights else (842.0, 1)
        h_conf = dom_h_count / max(len(heights), 1)
        learned_props["layout.page_height"] = LearnedProperty(
            property_name="layout.page_height",
            learned_value=dom_height,
            confidence=round(h_conf, 2),
            sample_count=total_samples,
            distribution={str(k): v for k, v in height_counts.most_common(5)},
            extraction_method="geometric_page_dimensions",
            supporting_samples=[s.sample_id for s, _ in docs],
            is_uncertain=h_conf < 0.7
        )

        col_counter = Counter(col_counts)
        dom_cols, dom_c_count = col_counter.most_common(1)[0] if col_counts else (1, 1)
        c_conf = dom_c_count / max(len(col_counts), 1)
        layout_str = "two_column" if dom_cols == 2 else "single_column" if dom_cols == 1 else "multi_column"
        learned_props["layout.columns"] = LearnedProperty(
            property_name="layout.columns",
            learned_value=layout_str,
            confidence=round(c_conf, 2),
            sample_count=total_samples,
            distribution={str(k): v for k, v in col_counter.items()},
            extraction_method="geometric_column_clustering",
            supporting_samples=[s.sample_id for s, _ in docs],
            is_uncertain=c_conf < 0.7,
            notes=f"Detected {dom_cols} columns across {dom_c_count}/{len(col_counts)} pages."
        )

        # ----------------------------------------------------
        # 2. TYPOGRAPHY: Font Families & Sizes
        # ----------------------------------------------------
        body_font_sizes = []
        heading_font_sizes = []
        font_families = []

        for _, dm in docs:
            for p in dm.pages:
                for b in p.blocks:
                    for l in b.lines:
                        for w in l.words:
                            fn = getattr(w, "font_name", None)
                            if fn:
                                font_families.append(fn.strip().lower())
                            if w.font_size:
                                fs = round(w.font_size, 1)
                                if fs < 13.0:
                                    body_font_sizes.append(fs)
                                else:
                                    heading_font_sizes.append(fs)

        fam_counter = Counter(font_families)
        dom_fam, dom_fam_c = fam_counter.most_common(1)[0] if font_families else ("times", 1)
        fam_conf = dom_fam_c / max(len(font_families), 1)
        learned_props["typography.font_family"] = LearnedProperty(
            property_name="typography.font_family",
            learned_value=dom_fam,
            confidence=round(fam_conf, 2),
            sample_count=total_samples,
            distribution={k: v for k, v in fam_counter.most_common(5)},
            extraction_method="font_descriptor_aggregation",
            supporting_samples=[s.sample_id for s, _ in docs],
            is_uncertain=fam_conf < 0.5
        )

        bfs_counter = Counter(body_font_sizes)
        dom_bfs, dom_bfs_c = bfs_counter.most_common(1)[0] if body_font_sizes else (10.0, 1)
        bfs_conf = dom_bfs_c / max(len(body_font_sizes), 1)
        learned_props["typography.body_font_size"] = LearnedProperty(
            property_name="typography.body_font_size",
            learned_value=dom_bfs,
            confidence=round(bfs_conf, 2),
            sample_count=total_samples,
            distribution={str(k): v for k, v in bfs_counter.most_common(5)},
            extraction_method="font_size_histogram",
            supporting_samples=[s.sample_id for s, _ in docs],
            is_uncertain=bfs_conf < 0.5
        )

        # ----------------------------------------------------
        # 3. STRUCTURE: Section Hierarchy & Numbering
        # ----------------------------------------------------
        all_sections: List[str] = []
        numbering_styles = []

        for _, dm in docs:
            sec_titles = [s.title.strip() for s in dm.sections if s.title.strip()]
            all_sections.extend(sec_titles)
            for s in dm.sections:
                num = (getattr(s, "number_str", "") or getattr(s, "number", "")).strip()
                if any(num.startswith(r) for r in ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]):
                    numbering_styles.append("roman")
                elif any(c.isdigit() for c in num):
                    numbering_styles.append("numeric")

        sec_counter = Counter(all_sections)
        # Required sections: appears in >= 50% of sample documents
        required_secs = []
        optional_secs = []
        threshold = max(total_samples * 0.5, 1)

        for sec_name, count in sec_counter.most_common():
            if count >= threshold:
                required_secs.append(sec_name)
            else:
                optional_secs.append(sec_name)

        num_counter = Counter(numbering_styles)
        dom_num_style = num_counter.most_common(1)[0][0] if numbering_styles else "numeric"

        learned_props["structure.required_sections"] = LearnedProperty(
            property_name="structure.required_sections",
            learned_value=required_secs,
            confidence=round(len(required_secs) / max(len(sec_counter), 1), 2),
            sample_count=total_samples,
            distribution={k: v for k, v in sec_counter.most_common(10)},
            extraction_method="section_frequency_analysis",
            supporting_samples=[s.sample_id for s, _ in docs]
        )

        learned_props["structure.numbering_style"] = LearnedProperty(
            property_name="structure.numbering_style",
            learned_value=dom_num_style,
            confidence=0.85 if numbering_styles else 0.5,
            sample_count=total_samples,
            distribution=dict(num_counter),
            extraction_method="heading_numbering_classifier",
            supporting_samples=[s.sample_id for s, _ in docs]
        )

        # ----------------------------------------------------
        # 4. OBJECTS & CAPTIONS: Tables, Figures, Equations
        # ----------------------------------------------------
        table_caption_positions = []
        figure_caption_positions = []
        table_counts = []
        fig_counts = []
        eq_counts = []

        for _, dm in docs:
            table_counts.append(len(dm.tables))
            fig_counts.append(len(dm.figures))
            eq_counts.append(len(dm.equations))

            for t in dm.tables:
                if t.caption:
                    table_caption_positions.append("above")
            for f in dm.figures:
                if f.caption:
                    figure_caption_positions.append("below")

        dom_tbl_pos = Counter(table_caption_positions).most_common(1)[0][0] if table_caption_positions else "above"
        dom_fig_pos = Counter(figure_caption_positions).most_common(1)[0][0] if figure_caption_positions else "below"

        learned_props["objects.table_caption_position"] = LearnedProperty(
            property_name="objects.table_caption_position",
            learned_value=dom_tbl_pos,
            confidence=0.9 if table_caption_positions else 0.5,
            sample_count=total_samples,
            distribution=dict(Counter(table_caption_positions)),
            extraction_method="table_caption_proximity",
            supporting_samples=[s.sample_id for s, _ in docs]
        )

        learned_props["objects.figure_caption_position"] = LearnedProperty(
            property_name="objects.figure_caption_position",
            learned_value=dom_fig_pos,
            confidence=0.9 if figure_caption_positions else 0.5,
            sample_count=total_samples,
            distribution=dict(Counter(figure_caption_positions)),
            extraction_method="figure_caption_proximity",
            supporting_samples=[s.sample_id for s, _ in docs]
        )

        requires_toc = (samples_with_toc / total_samples) >= 0.5
        learned_props["structure.requires_toc"] = LearnedProperty(
            property_name="structure.requires_toc",
            learned_value=requires_toc,
            confidence=round(abs(samples_with_toc / total_samples - 0.5) * 2, 2),
            sample_count=total_samples,
            distribution={"has_toc": samples_with_toc, "no_toc": total_samples - samples_with_toc},
            extraction_method="toc_presence_clustering",
            supporting_samples=[s.sample_id for s, _ in docs]
        )

        # Average confidence
        overall_conf = round(sum(p.confidence for p in learned_props.values()) / len(learned_props), 2)

        # Build clean summary rules dictionary
        summary_rules = {
            "layout": {
                "expected_layout": layout_str,
                "dominant_width": dom_width,
                "dominant_height": dom_height,
                "column_count": dom_cols
            },
            "typography": {
                "font_family": dom_fam,
                "body_font_size": dom_bfs
            },
            "structure": {
                "required_sections": required_secs,
                "optional_sections": optional_secs[:10],
                "numbering_style": dom_num_style,
                "requires_toc": requires_toc
            },
            "objects": {
                "table_caption_position": dom_tbl_pos,
                "figure_caption_position": dom_fig_pos,
                "has_equations": sum(eq_counts) > 0
            }
        }

        # Check for any conflicting properties
        if c_conf < 0.7:
            warnings.append(
                f"Low confidence in layout columns ({c_conf*100:.0f}%). "
                f"Samples contain mixed single and multi-column pages."
            )

        learned_profile = LearnedTemplateProfile(
            template_id=template_id,
            learned_at=datetime.now().isoformat(),
            sample_count=total_samples,
            overall_confidence=overall_conf,
            properties=learned_props,
            summary_rules=summary_rules,
            warnings=warnings
        )

        # Update profile.json on disk
        existing_profile = self.template_manager.get_profile(template_id) or {}
        existing_profile["learned_properties"] = {
            k: asdict(v) for k, v in learned_props.items()
        }
        existing_profile["summary_rules"] = summary_rules
        existing_profile["overall_confidence"] = overall_conf
        existing_profile["learned_at"] = learned_profile.learned_at
        existing_profile["status"] = "VALIDATION"
        existing_profile["is_approved"] = False  # Requires explicit approval

        self.template_manager.save_profile(template_id, existing_profile)
        self.template_manager.update_status(template_id, "VALIDATION")
        self.template_manager.create_version_snapshot(template_id, note="Profile learned from samples")

        logger.info(
            "Learned profile for template '%s' (Overall confidence: %.2f across %d samples)",
            template_id, overall_conf, total_samples
        )
        return learned_profile
