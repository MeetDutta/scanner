"""
Dataset Validation and Quality Health Check Engine for SpecGuard.
Detects invalid annotations, missing labels, overlapping entities, duplicates,
invalid bounding boxes, and severe class imbalances prior to deep learning training.
"""

from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, field
import logging

from specguard.training.annotation_manager import AnnotationManager, SUPPORTED_ENTITY_LABELS

logger = logging.getLogger(__name__)


@dataclass
class DatasetHealthReport:
    total_documents: int = 0
    total_annotations: int = 0
    mechanical_count: int = 0
    chemical_count: int = 0
    electrical_count: int = 0
    missing_labels: int = 0
    invalid_boxes: int = 0
    duplicate_samples: int = 0
    overlapping_entities: int = 0
    class_imbalance_ratio: float = 1.0
    status: str = "HEALTHY"  # HEALTHY, WARNING, CRITICAL
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def summary_text(self) -> str:
        lines = [
            "Dataset Health Report",
            "─" * 32,
            f"Total Annotations:    {self.total_annotations}",
            f"Mechanical Samples:   {self.mechanical_count}",
            f"Chemical Samples:     {self.chemical_count}",
            f"Electrical Samples:   {self.electrical_count}",
            f"Missing Labels:       {self.missing_labels}",
            f"Invalid Boxes:        {self.invalid_boxes}",
            f"Duplicate Samples:    {self.duplicate_samples}",
            f"Overlapping Entities: {self.overlapping_entities}",
            f"Status:               {self.status}",
        ]
        if self.warnings:
            lines.append("\nWarnings:")
            for w in self.warnings[:5]:
                lines.append(f"  • {w}")
        if self.errors:
            lines.append("\nErrors:")
            for e in self.errors[:5]:
                lines.append(f"  • {e}")
        return "\n".join(lines)


class DatasetValidator:
    """Performs rigorous quality and structural integrity checks on training data."""

    def __init__(self, annotation_manager: AnnotationManager):
        self.annotation_manager = annotation_manager

    def validate_dataset(self, domain: str = None) -> DatasetHealthReport:
        annotations = self.annotation_manager.list_annotations(domain)
        report = DatasetHealthReport()
        report.total_annotations = len(annotations)

        seen_texts = set()

        for annot in annotations:
            dom = annot.get("domain", "").lower()
            if dom == "mechanical":
                report.mechanical_count += 1
            elif dom == "chemical":
                report.chemical_count += 1
            elif dom == "electrical":
                report.electrical_count += 1

            txt = annot.get("text", "").strip()
            if not txt:
                report.errors.append(f"Annotation {annot.get('annotation_id')} has empty text.")
                continue

            # Check for duplicate sample texts
            if txt in seen_texts:
                report.duplicate_samples += 1
                report.warnings.append(f"Duplicate sample text: '{txt[:40]}...'")
            else:
                seen_texts.add(txt)

            # Check entities
            entities = annot.get("entities", [])
            spans: List[Tuple[int, int]] = []

            for ent in entities:
                lbl = ent.get("label")
                if not lbl or lbl not in SUPPORTED_ENTITY_LABELS:
                    report.missing_labels += 1
                    report.warnings.append(f"Invalid/Unknown entity label '{lbl}' in {annot.get('annotation_id')}")

                start = ent.get("start_char", 0)
                end = ent.get("end_char", 0)
                if start >= end or end > len(txt):
                    report.errors.append(f"Invalid character span ({start}, {end}) for text length {len(txt)}")

                # Check overlapping entities
                for s, e in spans:
                    if max(s, start) < min(e, end):
                        report.overlapping_entities += 1
                        report.warnings.append(f"Overlapping entity spans [{s}:{e}] and [{start}:{end}]")
                spans.append((start, end))

                # Check bbox validity if present
                bbox = ent.get("bbox")
                if bbox:
                    if bbox.get("x0", 0) >= bbox.get("x1", 0) or bbox.get("y0", 0) >= bbox.get("y1", 0):
                        report.invalid_boxes += 1
                        report.warnings.append(f"Inverted bounding box {bbox}")

        # Check class balance
        counts = [report.mechanical_count, report.chemical_count, report.electrical_count]
        active_counts = [c for c in counts if c > 0]
        if len(active_counts) > 1:
            imbalance = max(active_counts) / max(1, min(active_counts))
            report.class_imbalance_ratio = round(imbalance, 2)
            if imbalance > 3.0:
                report.warnings.append(f"High class imbalance detected (ratio: {imbalance:.1f}x)")

        # Determine overall health status
        if report.errors or report.missing_labels > 5 or report.invalid_boxes > 5:
            report.status = "CRITICAL"
        elif report.warnings or report.duplicate_samples > 0 or report.overlapping_entities > 0:
            report.status = "WARNING"
        else:
            report.status = "HEALTHY"

        return report
