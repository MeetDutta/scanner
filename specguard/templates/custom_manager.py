"""
Custom Template Management Engine for SpecGuard.
Provides isolated, versioned storage and lifecycle management for user-defined
document compliance templates without modifying built-in engineering profiles.
Strictly 100% offline.
"""

import os
import re
import json
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict, field

from specguard.core.config import TEMPLATES_DIR, DATA_DIR

logger = logging.getLogger(__name__)

VALID_STATUSES = ["DRAFT", "LEARNING", "PENDING_REVIEW", "TRAINING", "VALIDATION", "APPROVED", "ACTIVE", "ARCHIVED", "FAILED"]


@dataclass
class CustomTemplateMetadata:
    template_id: str
    name: str
    description: str
    category: str
    supported_file_types: List[str] = field(default_factory=lambda: ["pdf", "docx"])
    organization: Optional[str] = None
    version: str = "1.0.0"
    status: str = "DRAFT"  # DRAFT, TRAINING, VALIDATION, APPROVED, ACTIVE, ARCHIVED, FAILED
    sample_count: int = 0
    has_learned_profile: bool = False
    has_active_model: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class CustomTemplateManager:
    """
    Manages custom templates in an isolated directory structure:
    templates/custom/<template_id>/
      ├── metadata.json
      ├── profile.json
      ├── samples/
      ├── annotations/
      ├── models/
      ├── versions/
      └── reports/
    """

    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            # Prefer writable user data templates/custom, fallback to TEMPLATES_DIR/custom
            self.base_dir = DATA_DIR / "templates" / "custom"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _validate_template_id(self, template_id: str) -> str:
        clean_id = template_id.strip().lower()
        if not re.match(r"^[a-z0-9_-]{3,64}$", clean_id):
            raise ValueError(
                f"Invalid template ID '{template_id}'. Must be 3-64 alphanumeric characters, hyphens, or underscores."
            )
        # Check against reserved built-in domain names
        reserved = {"mechanical", "electrical", "chemical", "ieee_research", "generic_academic", "built_in"}
        if clean_id in reserved:
            raise ValueError(f"Template ID '{clean_id}' is reserved for built-in profiles.")
        return clean_id

    def get_template_dir(self, template_id: str) -> Path:
        clean_id = self._validate_template_id(template_id)
        path = (self.base_dir / clean_id).resolve()
        # Path traversal guard
        if not str(path).startswith(str(self.base_dir.resolve())):
            raise ValueError("Path traversal attempt detected.")
        return path

    def create_template(
        self,
        template_id: str,
        name: str,
        description: str,
        category: str = "Engineering Specification",
        supported_file_types: Optional[List[str]] = None,
        organization: Optional[str] = None,
        version: str = "1.0.0"
    ) -> CustomTemplateMetadata:
        clean_id = self._validate_template_id(template_id)
        tmpl_dir = self.get_template_dir(clean_id)
        if tmpl_dir.exists():
            raise FileExistsError(f"Template with ID '{clean_id}' already exists.")

        # Create isolated subdirectories
        for sub in ["samples", "annotations", "models", "versions", "reports"]:
            (tmpl_dir / sub).mkdir(parents=True, exist_ok=True)

        metadata = CustomTemplateMetadata(
            template_id=clean_id,
            name=name.strip(),
            description=description.strip(),
            category=category.strip(),
            supported_file_types=supported_file_types or ["pdf", "docx"],
            organization=organization.strip() if organization else None,
            version=version.strip(),
            status="DRAFT"
        )

        self._save_metadata(tmpl_dir, metadata)

        # Initial blank profile
        initial_profile = {
            "template_id": clean_id,
            "version": version,
            "display_name": name,
            "category": category,
            "status": "DRAFT",
            "is_approved": False,
            "layout": {},
            "typography": {},
            "structure": {
                "required_sections": [],
                "optional_sections": [],
                "heading_style": "any"
            },
            "objects": {
                "require_figures": False,
                "require_tables": False,
                "table_caption_position": "above",
                "figure_caption_position": "below"
            },
            "rules": [],
            "learned_properties": {},
            "tolerances": {
                "font_size_pt": 1.0,
                "margin_mm": 5.0,
                "column_width_mm": 10.0
            }
        }
        with open(tmpl_dir / "profile.json", "w", encoding="utf-8") as f:
            json.dump(initial_profile, f, indent=2)

        # Create baseline v1 snapshot
        self.create_version_snapshot(clean_id, note="Initial template creation")

        logger.info("Created custom template '%s' at %s", clean_id, tmpl_dir)
        return metadata

    def _save_metadata(self, tmpl_dir: Path, metadata: CustomTemplateMetadata) -> None:
        metadata.updated_at = datetime.now().isoformat()
        with open(tmpl_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(asdict(metadata), f, indent=2)

    def get_template(self, template_id: str) -> Optional[CustomTemplateMetadata]:
        tmpl_dir = self.get_template_dir(template_id)
        meta_file = tmpl_dir / "metadata.json"
        if not meta_file.exists():
            return None
        with open(meta_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return CustomTemplateMetadata(**data)

    def get_profile(self, template_id: str) -> Optional[Dict[str, Any]]:
        tmpl_dir = self.get_template_dir(template_id)
        prof_file = tmpl_dir / "profile.json"
        if not prof_file.exists():
            return None
        with open(prof_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_profile(self, template_id: str, profile_data: Dict[str, Any]) -> None:
        tmpl_dir = self.get_template_dir(template_id)
        with open(tmpl_dir / "profile.json", "w", encoding="utf-8") as f:
            json.dump(profile_data, f, indent=2)
        meta = self.get_template(template_id)
        if meta:
            meta.has_learned_profile = bool(profile_data.get("learned_properties"))
            self._save_metadata(tmpl_dir, meta)

    def list_templates(self, status: Optional[str] = None) -> List[CustomTemplateMetadata]:
        templates = []
        if not self.base_dir.exists():
            return templates
        for p in self.base_dir.iterdir():
            if p.is_dir() and (p / "metadata.json").exists():
                try:
                    with open(p / "metadata.json", "r", encoding="utf-8") as f:
                        meta = CustomTemplateMetadata(**json.load(f))
                    if status and meta.status.upper() != status.upper():
                        continue
                    templates.append(meta)
                except Exception as e:
                    logger.warning("Skipping corrupt template metadata at %s: %s", p, e)
        return sorted(templates, key=lambda t: t.created_at, reverse=True)

    def update_status(self, template_id: str, new_status: str) -> CustomTemplateMetadata:
        status_upper = new_status.upper().strip()
        if status_upper not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{new_status}'. Allowed: {VALID_STATUSES}")
        tmpl_dir = self.get_template_dir(template_id)
        meta = self.get_template(template_id)
        if not meta:
            raise FileNotFoundError(f"Template '{template_id}' not found.")
        meta.status = status_upper
        self._save_metadata(tmpl_dir, meta)
        return meta

    def create_version_snapshot(self, template_id: str, note: str = "") -> str:
        """Saves an immutable version snapshot of metadata and profile for rollback."""
        tmpl_dir = self.get_template_dir(template_id)
        meta = self.get_template(template_id)
        if not meta:
            raise FileNotFoundError(f"Template '{template_id}' not found.")

        versions_dir = tmpl_dir / "versions"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        version_tag = f"v{meta.version}_{timestamp}"
        snap_dir = versions_dir / version_tag
        snap_dir.mkdir(parents=True, exist_ok=True)

        # Copy metadata and profile
        if (tmpl_dir / "metadata.json").exists():
            shutil.copy2(tmpl_dir / "metadata.json", snap_dir / "metadata.json")
        if (tmpl_dir / "profile.json").exists():
            shutil.copy2(tmpl_dir / "profile.json", snap_dir / "profile.json")

        snap_info = {
            "version_tag": version_tag,
            "version": meta.version,
            "status": meta.status,
            "note": note,
            "created_at": datetime.now().isoformat()
        }
        with open(snap_dir / "version_info.json", "w", encoding="utf-8") as f:
            json.dump(snap_info, f, indent=2)

        logger.info("Created version snapshot '%s' for template '%s'", version_tag, template_id)
        return version_tag

    def list_versions(self, template_id: str) -> List[Dict[str, Any]]:
        tmpl_dir = self.get_template_dir(template_id)
        versions_dir = tmpl_dir / "versions"
        if not versions_dir.exists():
            return []
        versions = []
        for v in versions_dir.iterdir():
            if v.is_dir() and (v / "version_info.json").exists():
                try:
                    with open(v / "version_info.json", "r", encoding="utf-8") as f:
                        versions.append(json.load(f))
                except Exception:
                    pass
        return sorted(versions, key=lambda x: x.get("created_at", ""), reverse=True)

    def rollback_version(self, template_id: str, version_tag: str) -> CustomTemplateMetadata:
        """Restores a previous version snapshot."""
        tmpl_dir = self.get_template_dir(template_id)
        snap_dir = tmpl_dir / "versions" / version_tag
        if not snap_dir.exists():
            raise FileNotFoundError(f"Version snapshot '{version_tag}' not found.")

        # Create a backup of current state before rollback
        self.create_version_snapshot(template_id, note=f"Pre-rollback backup before restoring {version_tag}")

        if (snap_dir / "metadata.json").exists():
            shutil.copy2(snap_dir / "metadata.json", tmpl_dir / "metadata.json")
        if (snap_dir / "profile.json").exists():
            shutil.copy2(snap_dir / "profile.json", tmpl_dir / "profile.json")

        meta = self.get_template(template_id)
        if meta:
            meta.updated_at = datetime.now().isoformat()
            self._save_metadata(tmpl_dir, meta)
            return meta
        raise RuntimeError("Rollback failed to restore valid metadata.")

    def delete_template(self, template_id: str) -> bool:
        tmpl_dir = self.get_template_dir(template_id)
        if tmpl_dir.exists():
            shutil.rmtree(tmpl_dir)
            logger.info("Deleted custom template '%s'", template_id)
            return True
        return False
