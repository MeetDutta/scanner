"""
Annotation Management Engine for SpecGuard.
Persists and versions rich engineering annotations (NER entities, classification,
logical consistency, visual bounding boxes, and human-in-the-loop active learning corrections).
"""

import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict, field
import logging

from specguard.core.config import DATASETS_DIR
from specguard.core.models import Finding

logger = logging.getLogger(__name__)

SUPPORTED_ENTITY_LABELS = [
    "COMPONENT", "PARAMETER", "VALUE", "UNIT", "TOLERANCE",
    "MATERIAL", "PRESSURE", "TEMPERATURE", "VOLTAGE", "CURRENT",
    "POWER", "FREQUENCY", "DIMENSION", "CONCENTRATION", "RATING",
    "STANDARD_REFERENCE", "REQUIREMENT"
]

SUPPORTED_CLASSIFICATION_LABELS = ["MECHANICAL", "CHEMICAL", "ELECTRICAL", "GENERAL"]
SUPPORTED_LOGICAL_LABELS = ["CONSISTENT", "CONTRADICTORY", "UNCERTAIN"]
SUPPORTED_VISUAL_LABELS = ["TEXT", "HEADING", "TABLE", "DRAWING", "FIGURE", "DIAGRAM", "CAPTION", "SYMBOL"]


@dataclass
class EntityAnnotation:
    label: str
    text: str
    start_char: int
    end_char: int
    bbox: Optional[Dict[str, float]] = None


@dataclass
class DocumentAnnotation:
    annotation_id: str
    document_id: str
    domain: str
    page: int
    text: str
    entities: List[EntityAnnotation] = field(default_factory=list)
    classification_label: str = "GENERAL"
    logical_label: Optional[str] = None
    statement_b: Optional[str] = None  # Second sentence for pair contradiction labeling
    error_category: Optional[str] = None
    severity: Optional[str] = None
    annotated_by: str = "engineer"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    version: int = 1


class AnnotationManager:
    """Stores, queries, and versions local engineering annotations."""

    def __init__(self, base_dir: Path = DATASETS_DIR):
        self.base_dir = base_dir

    def save_annotation(self, annot: DocumentAnnotation) -> str:
        """Saves or non-destructively versions an annotation entry."""
        dom = annot.domain.lower()
        annot_dir = self.base_dir / dom / "annotated"
        annot_dir.mkdir(parents=True, exist_ok=True)

        file_path = annot_dir / f"{annot.annotation_id}.json"
        if file_path.exists():
            # If already exists, increment version
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                    annot.version = old_data.get("version", 1) + 1
            except Exception:
                annot.version += 1

        data = {
            "annotation_id": annot.annotation_id,
            "document_id": annot.document_id,
            "domain": annot.domain,
            "page": annot.page,
            "text": annot.text,
            "entities": [asdict(e) for e in annot.entities],
            "classification_label": annot.classification_label,
            "logical_label": annot.logical_label,
            "statement_b": annot.statement_b,
            "error_category": annot.error_category,
            "severity": annot.severity,
            "annotated_by": annot.annotated_by,
            "created_at": annot.created_at,
            "version": annot.version
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info("Saved annotation %s (v%d) for document %s", annot.annotation_id, annot.version, annot.document_id)
        return str(file_path)

    def list_annotations(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves all annotations across or within a specific domain."""
        domains = [domain.lower()] if domain else ["mechanical", "chemical", "electrical"]
        results = []

        for dom in domains:
            annot_dir = self.base_dir / dom / "annotated"
            if not annot_dir.exists():
                continue
            for f in annot_dir.glob("*.json"):
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        results.append(json.load(fp))
                except Exception as e:
                    logger.error("Error loading annotation %s: %s", f, e)

        return results

    def export_correction_as_annotation(self, finding: Finding, document_id: str, corrected_text: str) -> str:
        """
        Human-in-the-loop: Converts an accepted user correction from the analysis review
        into a ground-truth training annotation sample.
        """
        annot_id = f"HIL_{uuid.uuid4().hex[:8].upper()}"
        annot = DocumentAnnotation(
            annotation_id=annot_id,
            document_id=document_id,
            domain=finding.domain.lower(),
            page=finding.page,
            text=corrected_text or finding.original_content,
            entities=[
                EntityAnnotation(
                    label="PARAMETER",
                    text=str(finding.detected_value),
                    start_char=0,
                    end_char=len(str(finding.detected_value)),
                    bbox=finding.bbox.to_dict() if finding.bbox else None
                )
            ],
            classification_label=finding.domain.upper(),
            logical_label="CONSISTENT",
            error_category=finding.category,
            severity=finding.severity,
            annotated_by="user_correction"
        )
        return self.save_annotation(annot)
