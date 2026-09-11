"""
Local Repository Backup and Safe Restore Engine for SpecGuard.
Packages comparisons, documents, and findings into self-contained .sgr archives
with cryptographic SHA-256 per-file manifests and path-traversal prevention.
Strictly offline and verifiable.
"""

import os
import json
import zipfile
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, List
import logging

logger = logging.getLogger(__name__)


def _calc_sha256(data_bytes: bytes) -> str:
    sha = hashlib.sha256()
    sha.update(data_bytes)
    return sha.hexdigest()


class RestoreResult(tuple):
    """
    Subclasses tuple to remain 100% backwards compatible with existing (success, message) callers
    while also exposing structured integrity verification details via .details attribute.
    """
    def __new__(cls, success: bool, message: str, details: Dict[str, Any] = None):
        return super().__new__(cls, (success, message))

    def __init__(self, success: bool, message: str, details: Dict[str, Any] = None):
        self.success = success
        self.message = message
        self.details = details or {}


class RepositoryBackupEngine:
    """Creates verifiable offline backup packages and restores them safely with cryptographic verification."""

    @staticmethod
    def create_backup(repo_dir: Path, output_file_path: str) -> Tuple[str, str, int]:
        """
        Creates a .sgr (SpecGuard Repository) zip archive containing all repository assets.
        Generates a per-file manifest containing relative path, file size in bytes, and SHA-256.
        Returns: (output_path, overall_sha256_checksum, total_files)
        """
        out_path = Path(output_file_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        repo_dir = Path(repo_dir).resolve()

        manifest: Dict[str, Any] = {
            "app_version": "1.0.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "type": "specguard_repository_backup",
            "files": []
        }

        file_count = 0
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zip_f:
            for root, _, files in os.walk(repo_dir):
                for file in files:
                    full_p = Path(root) / file
                    rel_p = full_p.relative_to(repo_dir)

                    with open(full_p, "rb") as f:
                        content = f.read()

                    f_hash = _calc_sha256(content)
                    f_size = len(content)

                    zip_f.writestr(str(rel_p), content)
                    manifest["files"].append({
                        "path": str(rel_p),
                        "size": f_size,
                        "sha256": f_hash
                    })
                    file_count += 1

            # Store manifest inside the archive
            zip_f.writestr("backup_manifest.json", json.dumps(manifest, indent=2))

        # Calculate overall backup archive SHA-256
        sha256_overall = hashlib.sha256()
        with open(out_path, "rb") as f:
            while chunk := f.read(65536):
                sha256_overall.update(chunk)
        digest = sha256_overall.hexdigest()

        logger.info("Created hardened repository backup: %s (%d files, SHA256: %s)", out_path, file_count, digest[:12])
        return str(out_path), digest, file_count

    @staticmethod
    def restore_backup(backup_file_path: str, target_repo_dir: Path) -> RestoreResult:
        """
        Restores a .sgr archive into target repository with strict security & integrity validation:
        1. Validates backup_manifest.json presence and format
        2. Detects and rejects path traversal attempts
        3. Validates uncompressed content SHA-256 against manifest before disk writes
        4. Rejects corrupted archive files immediately
        5. Restores safely to target directory
        6. Verifies on-disk files match expected hashes
        7. Returns structured restore results via RestoreResult((success, msg), details=details)
        """
        b_path = Path(backup_file_path).resolve()
        details: Dict[str, Any] = {
            "backup_file": str(b_path),
            "target_dir": str(target_repo_dir),
            "files_evaluated": 0,
            "files_restored": 0,
            "corrupted_files": [],
            "path_traversals": []
        }

        if not b_path.exists():
            return RestoreResult(False, f"Backup file not found: {b_path}", details)

        try:
            with zipfile.ZipFile(b_path, "r") as zip_f:
                # 1. Validate manifest presence
                if "backup_manifest.json" not in zip_f.namelist():
                    return RestoreResult(False, "Corrupted archive: Missing backup_manifest.json", details)

                try:
                    manifest_raw = zip_f.read("backup_manifest.json").decode("utf-8")
                    manifest = json.loads(manifest_raw)
                except Exception as e:
                    return RestoreResult(False, f"Invalid manifest format: {e}", details)

                manifest_files: List[Dict[str, Any]] = manifest.get("files", [])
                if not manifest_files:
                    return RestoreResult(False, "Corrupted archive: Manifest file list is empty", details)

                manifest_dict = {}
                for entry in manifest_files:
                    if isinstance(entry, dict):
                        manifest_dict[entry["path"]] = entry
                    elif isinstance(entry, str):
                        manifest_dict[entry] = {"path": entry, "size": None, "sha256": None}

                target_repo_dir.mkdir(parents=True, exist_ok=True)
                target_resolved = target_repo_dir.resolve()

                # 2 & 3. Validate every member for path traversal and SHA-256 hash match
                for entry_path, meta in manifest_dict.items():
                    details["files_evaluated"] += 1
                    # Path traversal check
                    dest_path = (target_repo_dir / entry_path).resolve()
                    if not str(dest_path).startswith(str(target_resolved)):
                        details["path_traversals"].append(entry_path)
                        return RestoreResult(False, f"Security Violation: Path traversal detected in member '{entry_path}'", details)

                    if entry_path not in zip_f.namelist():
                        details["corrupted_files"].append(entry_path)
                        return RestoreResult(False, f"Archive integrity failure: Manifest file '{entry_path}' missing in zip payload", details)

                    # Read bytes and verify SHA-256
                    file_bytes = zip_f.read(entry_path)
                    expected_sha = meta.get("sha256")
                    if expected_sha:
                        actual_sha = _calc_sha256(file_bytes)
                        if actual_sha != expected_sha:
                            details["corrupted_files"].append(entry_path)
                            return RestoreResult(False, (
                                f"Corrupted file detected: '{entry_path}' has SHA-256 mismatch. "
                                f"Expected {expected_sha[:12]}, computed {actual_sha[:12]}"
                            ), details)

                # 4 & 5. Safe disk restoration
                for entry_path, meta in manifest_dict.items():
                    dest_path = (target_repo_dir / entry_path).resolve()
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    file_bytes = zip_f.read(entry_path)
                    with open(dest_path, "wb") as f:
                        f.write(file_bytes)
                    details["files_restored"] += 1

                # Retain backup_manifest.json in restored repository for auditability
                with open(target_repo_dir / "backup_manifest.json", "w", encoding="utf-8") as f:
                    f.write(manifest_raw)

                # 6. Post-restore verification on disk
                for entry_path, meta in manifest_dict.items():
                    dest_path = (target_repo_dir / entry_path).resolve()
                    if not dest_path.exists():
                        return RestoreResult(False, f"Post-restore verification failed: '{entry_path}' missing from disk", details)
                    expected_sha = meta.get("sha256")
                    if expected_sha:
                        with open(dest_path, "rb") as f:
                            disk_sha = _calc_sha256(f.read())
                        if disk_sha != expected_sha:
                            return RestoreResult(False, f"Post-restore verification failed: '{entry_path}' corrupted on disk", details)

            msg = f"Repository successfully restored and cryptographically verified ({details['files_restored']} files)."
            logger.info(msg)
            return RestoreResult(True, msg, details)
        except Exception as e:
            logger.error("Restore failed: %s", e)
            return RestoreResult(False, f"Restore failed: {str(e)}", details)
