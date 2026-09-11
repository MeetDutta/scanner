"""
Engineering Dataset Manager for SpecGuard.
Manages domain datasets (mechanical, chemical, electrical), directory structures,
multi-format ingestion, tokenization, and dataset versioning with SHA-256 checksums.
"""

import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
import logging

from specguard.core.config import DATASETS_DIR
from specguard.core.document_parser import DocumentParser
from specguard.core.models import DocumentModel

logger = logging.getLogger(__name__)

DOMAINS = ["mechanical", "chemical", "electrical"]
SUBDIRS = ["raw", "processed", "annotated", "train", "validation", "test"]


class DatasetManager:
    """Manages local engineering training datasets, formats, and versioning."""

    def __init__(self, base_dir: Path = DATASETS_DIR):
        self.base_dir = base_dir
        self.ensure_structure()

    def ensure_structure(self):
        """Initializes the dataset directory hierarchy for all engineering domains."""
        for dom in DOMAINS:
            for sub in SUBDIRS:
                (self.base_dir / dom / sub).mkdir(parents=True, exist_ok=True)

    def import_document(self, file_path: str, domain: str) -> Dict[str, Any]:
        """
        Imports a real engineering document into the domain's raw directory,
        processes it, and creates a tokenized document representation.
        """
        src_path = Path(file_path).resolve()
        if not src_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        dom = domain.lower()
        if dom not in DOMAINS:
            dom = "mechanical"

        # Calculate file hash
        sha256 = hashlib.sha256()
        with open(src_path, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        doc_hash = sha256.hexdigest()

        # Copy original file to raw directory
        raw_dest = self.base_dir / dom / "raw" / f"{doc_hash[:10]}_{src_path.name}"
        if not raw_dest.exists():
            shutil.copy2(src_path, raw_dest)

        # Parse document to extract pages, blocks, tables, and bounding boxes
        doc_model = DocumentParser.parse_file(str(raw_dest))

        # Save processed JSON representation
        processed_data = {
            "document_id": f"{dom.upper()[:3]}_{doc_hash[:8]}",
            "filename": src_path.name,
            "domain": dom,
            "sha256": doc_hash,
            "page_count": doc_model.page_count,
            "file_size": doc_model.file_size,
            "imported_at": datetime.now().isoformat(),
            "pages": [
                {
                    "page_num": p.page_num,
                    "width": p.width,
                    "height": p.height,
                    "text": p.text,
                    "blocks": [
                        {
                            "text": b.text,
                            "bbox": b.bbox.to_dict() if b.bbox else None,
                            "font_name": b.font_name,
                            "font_size": b.font_size,
                            "is_bold": b.is_bold
                        }
                        for b in p.blocks
                    ]
                }
                for p in doc_model.pages
            ]
        }

        proc_dest = self.base_dir / dom / "processed" / f"{processed_data['document_id']}.json"
        with open(proc_dest, "w", encoding="utf-8") as f:
            json.dump(processed_data, f, indent=2)

        logger.info("Imported and processed document %s into %s", src_path.name, dom)
        return processed_data

    def list_processed_documents(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists all ingested and processed documents across domains."""
        domains_to_scan = [domain.lower()] if domain and domain.lower() in DOMAINS else DOMAINS
        docs = []

        for dom in domains_to_scan:
            proc_dir = self.base_dir / dom / "processed"
            for json_file in proc_dir.glob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        docs.append({
                            "document_id": data.get("document_id"),
                            "filename": data.get("filename"),
                            "domain": data.get("domain"),
                            "page_count": data.get("page_count", 1),
                            "file_path": str(json_file),
                            "sha256": data.get("sha256")
                        })
                except Exception as e:
                    logger.error("Failed reading processed doc %s: %s", json_file, e)

        return docs

    def get_document_details(self, document_id: str, domain: str) -> Optional[Dict[str, Any]]:
        proc_file = self.base_dir / domain.lower() / "processed" / f"{document_id}.json"
        if not proc_file.exists():
            return None
        with open(proc_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def create_dataset_version(self, domain: str, version_tag: str, description: str = "") -> Dict[str, Any]:
        """Creates a versioned snapshot manifest of current annotations and processed documents."""
        dom = domain.lower()
        annot_dir = self.base_dir / dom / "annotated"
        annotations = list(annot_dir.glob("*.json"))

        manifest = {
            "version": version_tag,
            "domain": dom,
            "created_at": datetime.now().isoformat(),
            "description": description,
            "document_count": len(list((self.base_dir / dom / "processed").glob("*.json"))),
            "annotation_count": len(annotations),
            "annotation_files": [f.name for f in annotations]
        }

        # Save manifest in domain directory
        manifest_file = self.base_dir / dom / f"manifest_{version_tag}.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return manifest
