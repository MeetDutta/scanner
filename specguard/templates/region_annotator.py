"""
Region Annotation Management for SpecGuard Custom Templates.
Supports human-in-the-loop region labeling (Title, Heading, Body, Caption, Table, Figure, Equation, etc.)
with bounding box coordinates, versioning, and document-level grouping.
Strictly 100% offline.
"""

import os
import json
import uuid
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict, field

from specguard.templates.custom_manager import CustomTemplateManager

logger = logging.getLogger(__name__)

SUPPORTED_REGION_LABELS = [
    "TITLE", "HEADING", "BODY", "CAPTION", "TABLE",
    "FIGURE", "EQUATION", "HEADER", "FOOTER", "REFERENCE", "OTHER"
]


@dataclass
class RegionAnnotation:
    annotation_id: str
    template_id: str
    sample_id: str
    page_number: int
    label: str  # Must be one of SUPPORTED_REGION_LABELS
    bbox: Dict[str, float]  # {"x0": ..., "y0": ..., "x1": ..., "y1": ...}
    text_content: Optional[str] = None
    annotator: str = "engineer"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    version: int = 1


class RegionAnnotator:
    """Manages region annotations for a custom template."""

    def __init__(self, template_manager: Optional[CustomTemplateManager] = None):
        self.template_manager = template_manager or CustomTemplateManager()

    def get_annotations_dir(self, template_id: str) -> Path:
        tmpl_dir = self.template_manager.get_template_dir(template_id)
        annot_dir = tmpl_dir / "annotations"
        annot_dir.mkdir(parents=True, exist_ok=True)
        return annot_dir

    def add_annotation(
        self,
        template_id: str,
        sample_id: str,
        page_number: int,
        label: str,
        bbox: Dict[str, float],
        text_content: Optional[str] = None,
        annotator: str = "engineer"
    ) -> RegionAnnotation:
        clean_label = label.upper().strip()
        if clean_label not in SUPPORTED_REGION_LABELS:
            raise ValueError(
                f"Invalid region label '{label}'. Allowed: {SUPPORTED_REGION_LABELS}"
            )

        annot_id = f"REG-{uuid.uuid4().hex[:10]}"
        annot = RegionAnnotation(
            annotation_id=annot_id,
            template_id=template_id,
            sample_id=sample_id,
            page_number=page_number,
            label=clean_label,
            bbox=bbox,
            text_content=text_content,
            annotator=annotator
        )

        annot_file = self.get_annotations_dir(template_id) / f"{annot_id}.json"
        with open(annot_file, "w", encoding="utf-8") as f:
            json.dump(asdict(annot), f, indent=2)

        logger.info("Saved region annotation '%s' (%s) for template '%s'", annot_id, clean_label, template_id)
        return annot

    def list_annotations(
        self,
        template_id: str,
        sample_id: Optional[str] = None,
        page_number: Optional[int] = None
    ) -> List[RegionAnnotation]:
        annot_dir = self.get_annotations_dir(template_id)
        results = []
        for f in annot_dir.glob("REG-*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                annot = RegionAnnotation(**data)
                if sample_id and annot.sample_id != sample_id:
                    continue
                if page_number is not None and annot.page_number != page_number:
                    continue
                results.append(annot)
            except Exception as e:
                logger.warning("Failed reading annotation %s: %s", f, e)
        return sorted(results, key=lambda a: (a.sample_id, a.page_number, a.created_at))

    def delete_annotation(self, template_id: str, annotation_id: str) -> bool:
        annot_file = self.get_annotations_dir(template_id) / f"{annotation_id}.json"
        if annot_file.exists():
            annot_file.unlink()
            return True
        return False

    def get_dataset_summary(self, template_id: str) -> Dict[str, Any]:
        """Returns class distributions, sample diversity, and readiness for supervised training."""
        annots = self.list_annotations(template_id)
        class_counts: Dict[str, int] = {}
        samples_covered: set = set()

        for a in annots:
            class_counts[a.label] = class_counts.get(a.label, 0) + 1
            samples_covered.add(a.sample_id)

        # Minimum criteria: At least 2 distinct sample documents, >= 3 distinct classes, >= 15 total annotations
        is_sufficient = (len(samples_covered) >= 2 and len(class_counts) >= 3 and len(annots) >= 15)
        insufficient_reasons = []
        if len(samples_covered) < 2:
            insufficient_reasons.append(
                f"Document Diversity: Need annotations from at least 2 distinct sample documents (currently {len(samples_covered)})."
            )
        if len(class_counts) < 3:
            insufficient_reasons.append(
                f"Class Diversity: Need at least 3 labeled region classes (currently {len(class_counts)}: {list(class_counts.keys())})."
            )
        if len(annots) < 15:
            insufficient_reasons.append(
                f"Sample Size: Need at least 15 labeled regions for supervised cross-validation (currently {len(annots)})."
            )

        return {
            "template_id": template_id,
            "total_annotations": len(annots),
            "samples_covered": list(samples_covered),
            "class_distribution": class_counts,
            "is_sufficient_for_ml": is_sufficient,
            "insufficient_reasons": insufficient_reasons,
            "recommendation": "Proceed with local ML training" if is_sufficient else "Use local statistical Profile Learning (recommended)"
        }
