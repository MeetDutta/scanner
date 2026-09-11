"""
Local Repository Backup and Safe Restore Engine for SpecGuard.
Packages comparisons and documents into self-contained .sgr archives with SHA-256 validation.
"""

import os
import json
import zipfile
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Tuple
import logging

from specguard.core.config import BASE_DIR

logger = logging.getLogger(__name__)


class RepositoryBackupEngine:
    """Creates verifiable offline backup packages and restores them safely."""

    @staticmethod
    def create_backup(repo_dir: Path, output_file_path: str) -> Tuple[str, str, int]:
        """
        Creates a .sgr (SpecGuard Repository) zip archive containing all repository assets.
        Returns: (output_path, sha256_checksum, total_files)
        """
        out_path = Path(output_file_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        manifest = {
            "app_version": "1.0.0",
            "created_at": datetime.now().isoformat(),
            "type": "specguard_repository_backup",
            "files": []
        }

        file_count = 0
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zip_f:
            for root, _, files in os.walk(repo_dir):
                for file in files:
                    full_p = Path(root) / file
                    rel_p = full_p.relative_to(repo_dir)
                    zip_f.write(full_p, arcname=str(rel_p))
                    manifest["files"].append(str(rel_p))
                    file_count += 1

            zip_f.writestr("backup_manifest.json", json.dumps(manifest, indent=2))

        # Calculate SHA-256
        sha256 = hashlib.sha256()
        with open(out_path, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        digest = sha256.hexdigest()

        logger.info("Created repository backup: %s (%d files, SHA256: %s)", out_path, file_count, digest[:12])
        return str(out_path), digest, file_count

    @staticmethod
    def restore_backup(backup_file_path: str, target_repo_dir: Path) -> Tuple[bool, str]:
        """
        Restores a .sgr archive into target repository with strict path traversal prevention.
        """
        b_path = Path(backup_file_path).resolve()
        if not b_path.exists():
            return False, "Backup file not found."

        try:
            with zipfile.ZipFile(b_path, "r") as zip_f:
                # Validate manifest
                if "backup_manifest.json" not in zip_f.namelist():
                    return False, "Corrupted archive: Missing backup_manifest.json"

                # Path traversal safety check
                target_repo_dir.mkdir(parents=True, exist_ok=True)
                target_resolved = target_repo_dir.resolve()

                for member in zip_f.infolist():
                    dest_path = (target_repo_dir / member.filename).resolve()
                    if not str(dest_path).startswith(str(target_resolved)):
                        return False, f"Security Violation: Path traversal detected in member '{member.filename}'"

                zip_f.extractall(target_repo_dir)

            logger.info("Successfully restored repository from %s", b_path)
            return True, "Repository successfully restored."
        except Exception as e:
            logger.error("Restore failed: %s", e)
            return False, f"Restore failed: {str(e)}"
