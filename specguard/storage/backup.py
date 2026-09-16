"""
SpecGuard User Data Backup & Migration Manager.
Safely creates transactional snapshots of the SQLite database, uploaded documents,
and verification reports for offline data protection and portable migration.
"""

import os
import shutil
import sqlite3
import zipfile
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

from specguard.core.config import DATA_DIR, DB_PATH, REPORTS_DIR, UPLOADS_DIR, LOGS_DIR

logger = logging.getLogger("SpecGuard.Storage.Backup")


def create_backup(dest_dir: Optional[Path] = None) -> Path:
    """
    Creates a complete, consistent backup of all user data.
    Uses SQLite online backup API to ensure 100% database consistency even if active.
    """
    if dest_dir is None:
        dest_dir = DATA_DIR / "backups"
    dest_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_zip_path = dest_dir / f"SpecGuard_Backup_{timestamp}.zip"
    temp_snapshot_db = dest_dir / f"temp_snapshot_{timestamp}.db"

    # 1. Consistent SQLite Snapshot
    if DB_PATH.exists():
        try:
            with sqlite3.connect(DB_PATH) as src_conn:
                with sqlite3.connect(temp_snapshot_db) as dst_conn:
                    src_conn.backup(dst_conn)
        except Exception as e:
            logger.error("Failed to snapshot SQLite database: %s", e)
            if DB_PATH.exists():
                shutil.copy2(DB_PATH, temp_snapshot_db)

    # 2. Package into ZIP
    with zipfile.ZipFile(backup_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Add DB snapshot
        if temp_snapshot_db.exists():
            zipf.write(temp_snapshot_db, "specguard.db")
            temp_snapshot_db.unlink(missing_ok=True)

        # Add uploads
        if UPLOADS_DIR.exists():
            for f in UPLOADS_DIR.rglob("*"):
                if f.is_file() and not f.name.startswith("."):
                    zipf.write(f, Path("uploads") / f.relative_to(UPLOADS_DIR))

        # Add reports
        if REPORTS_DIR.exists():
            for f in REPORTS_DIR.rglob("*"):
                if f.is_file() and not f.name.startswith("."):
                    zipf.write(f, Path("reports") / f.relative_to(REPORTS_DIR))

    logger.info("Created backup snapshot: %s (%d bytes)", backup_zip_path.name, backup_zip_path.stat().st_size)
    return backup_zip_path


def list_backups(dest_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Lists existing backup files with metadata."""
    if dest_dir is None:
        dest_dir = DATA_DIR / "backups"
    if not dest_dir.exists():
        return []

    backups = []
    for f in sorted(dest_dir.glob("SpecGuard_Backup_*.zip"), reverse=True):
        stat = f.stat()
        backups.append({
            "filename": f.name,
            "path": str(f),
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
        })
    return backups
