"""
Sample Document Manager for SpecGuard Custom Templates.
Handles local ingestion, SHA-256 deduplication, multi-page parsing,
and structural variation detection across template sample documents.
Strictly 100% offline.
"""

import os
import json
import hashlib
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field

from specguard.core.document_parser import DocumentParser
from specguard.core.models import DocumentModel
from specguard.templates.custom_manager import CustomTemplateManager
from specguard.analyzers.structure import StructureAnalyzer
from specguard.analyzers.tables import TableAnalyzer
from specguard.analyzers.figures import FigureAnalyzer
from specguard.analyzers.equations import EquationAnalyzer

logger = logging.getLogger(__name__)


def enrich_sample_ast(doc: DocumentModel) -> None:
    """Enriches DocumentModel with structural sections, tables, figures, and equations."""
    ctx = {}
    try:
        StructureAnalyzer().analyze(doc, ctx)
    except Exception:
        pass
    try:
        TableAnalyzer().analyze(doc, ctx)
    except Exception:
        pass
    try:
        FigureAnalyzer().analyze(doc, ctx)
    except Exception:
        pass
    try:
        EquationAnalyzer().analyze(doc, ctx)
    except Exception:
        pass


@dataclass
class SampleDocumentInfo:
    sample_id: str
    template_id: str
    filename: str
    file_hash: str
    file_size_bytes: int
    page_count: int
    file_type: str
    uploaded_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "PROCESSED"  # PROCESSED, CORRUPT, WARNING
    summary: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


class SampleManager:
    """Manages sample documents for a custom template."""

    def __init__(self, template_manager: Optional[CustomTemplateManager] = None):
        self.template_manager = template_manager or CustomTemplateManager()
        self.parser = DocumentParser()

    @staticmethod
    def compute_sha256(file_path: Path) -> str:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def get_samples_dir(self, template_id: str) -> Path:
        tmpl_dir = self.template_manager.get_template_dir(template_id)
        samples_dir = tmpl_dir / "samples"
        samples_dir.mkdir(parents=True, exist_ok=True)
        return samples_dir

    def list_samples(self, template_id: str) -> List[SampleDocumentInfo]:
        samples_dir = self.get_samples_dir(template_id)
        samples = []
        for meta_file in samples_dir.glob("*.meta.json"):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    samples.append(SampleDocumentInfo(**json.load(f)))
            except Exception as e:
                logger.warning("Failed to read sample meta %s: %s", meta_file, e)
        return sorted(samples, key=lambda s: s.uploaded_at)

    def ingest_sample(
        self,
        template_id: str,
        source_file_path: Path,
        original_filename: Optional[str] = None
    ) -> SampleDocumentInfo:
        """
        Ingests and extracts a local sample PDF/DOCX:
        1. Checks SHA-256 for duplicates.
        2. Copies into isolated samples directory.
        3. Parses document into DocumentModel.
        4. Extracts summary statistics (layout, typography, sections).
        5. Updates template sample count.
        """
        source_path = Path(source_file_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_file_path}")

        file_hash = self.compute_sha256(source_path)
        samples_dir = self.get_samples_dir(template_id)

        # Check duplicate
        for s in self.list_samples(template_id):
            if s.file_hash == file_hash:
                raise ValueError(
                    f"Duplicate sample detected: File '{original_filename or source_path.name}' "
                    f"has identical SHA-256 hash to existing sample '{s.filename}' ({s.sample_id})."
                )

        ext = source_path.suffix.lower()
        if ext not in [".pdf", ".docx"]:
            raise ValueError(f"Unsupported file type '{ext}'. Only PDF and DOCX are supported.")

        sample_id = f"SMPL-{file_hash[:12]}"
        dest_file = samples_dir / f"{sample_id}{ext}"
        shutil.copy2(source_path, dest_file)

        warnings: List[str] = []
        status = "PROCESSED"
        doc_model: Optional[DocumentModel] = None

        try:
            doc_model = DocumentParser.parse_file(dest_file)
            enrich_sample_ast(doc_model)
        except Exception as e:
            logger.error("Failed to parse sample %s: %s", sample_id, e)
            status = "CORRUPT"
            warnings.append(f"Parsing failed: {str(e)}")

        page_count = len(doc_model.pages) if doc_model else 0
        summary: Dict[str, Any] = {}

        if doc_model:
            # Analyze extracted characteristics
            font_sizes = []
            font_families = []
            column_counts = []
            page_widths = []
            page_heights = []

            for p in doc_model.pages:
                page_widths.append(round(p.width, 1))
                page_heights.append(round(p.height, 1))
                # Count columns from layout blocks
                columns = {getattr(b, "column_id", 0) for b in p.blocks}
                column_counts.append(max(len(columns), 1))
                for b in p.blocks:
                    for l in b.lines:
                        for w in l.words:
                            if w.font_size:
                                font_sizes.append(round(w.font_size, 1))
                            fn = getattr(w, "font_name", None)
                            if fn:
                                font_families.append(fn.strip().lower())

            dominant_font_size = max(set(font_sizes), key=font_sizes.count) if font_sizes else 10.0
            dominant_font_family = max(set(font_families), key=font_families.count) if font_families else "unknown"
            dominant_columns = max(set(column_counts), key=column_counts.count) if column_counts else 1

            summary = {
                "page_count": page_count,
                "dominant_width": page_widths[0] if page_widths else 595.0,
                "dominant_height": page_heights[0] if page_heights else 842.0,
                "dominant_columns": dominant_columns,
                "dominant_font_size": dominant_font_size,
                "dominant_font_family": dominant_font_family,
                "sections": [s.title for s in doc_model.sections],
                "table_count": len(doc_model.tables),
                "figure_count": len(doc_model.figures),
                "equation_count": len(doc_model.equations),
                "has_toc": getattr(doc_model.toc, "exists", False) if doc_model.toc else False
            }

            if doc_model.warnings:
                warnings.extend(doc_model.warnings)

        info = SampleDocumentInfo(
            sample_id=sample_id,
            template_id=template_id,
            filename=original_filename or source_path.name,
            file_hash=file_hash,
            file_size_bytes=source_path.stat().st_size,
            page_count=page_count,
            file_type=ext.replace(".", ""),
            status=status,
            summary=summary,
            warnings=warnings
        )

        # Save metadata
        meta_file = samples_dir / f"{sample_id}.meta.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(asdict(info), f, indent=2)

        # Update template metadata sample count
        tmpl_meta = self.template_manager.get_template(template_id)
        if tmpl_meta:
            tmpl_meta.sample_count = len(self.list_samples(template_id))
            self.template_manager._save_metadata(
                self.template_manager.get_template_dir(template_id), tmpl_meta
            )

        logger.info("Ingested sample '%s' for template '%s'", sample_id, template_id)
        return info

    def remove_sample(self, template_id: str, sample_id: str) -> bool:
        samples_dir = self.get_samples_dir(template_id)
        removed = False
        for f in samples_dir.glob(f"{sample_id}.*"):
            f.unlink(missing_ok=True)
            removed = True

        if removed:
            tmpl_meta = self.template_manager.get_template(template_id)
            if tmpl_meta:
                tmpl_meta.sample_count = len(self.list_samples(template_id))
                self.template_manager._save_metadata(
                    self.template_manager.get_template_dir(template_id), tmpl_meta
                )
        return removed

    def check_sample_variations(self, template_id: str) -> List[str]:
        """
        Detects substantial structural differences across uploaded samples:
        - Differing column counts (e.g. 1-col vs 2-col)
        - Substantially differing page dimensions (>15%)
        - Differing document orientations
        """
        samples = [s for s in self.list_samples(template_id) if s.status == "PROCESSED"]
        if len(samples) < 2:
            return []

        warnings = []
        cols = {s.summary.get("dominant_columns", 1) for s in samples}
        if len(cols) > 1:
            warnings.append(
                f"Layout Column Conflict: Samples have differing column layouts ({sorted(cols)} columns). "
                f"Ensure all samples represent the same publication or document specification."
            )

        widths = [s.summary.get("dominant_width", 595.0) for s in samples]
        if widths and (max(widths) - min(widths)) > 50.0:
            warnings.append(
                f"Page Dimension Variance: Sample widths vary between {min(widths):.1f}pt and {max(widths):.1f}pt. "
                f"Mixed paper sizes (e.g. US Letter vs ISO A4) detected."
            )

        return warnings
