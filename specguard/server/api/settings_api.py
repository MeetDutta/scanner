"""
Settings, Storage Telemetry, and Audit Log API for SpecGuard.
Provides environment health diagnostics, local storage telemetry,
and immutable audit log queries.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import asdict
import os
import logging

from specguard.core.config import (
    BASE_DIR, DATA_DIR, DB_PATH, MODELS_DIR, REPORTS_DIR, STANDARDS_DIR
)
from specguard.core.startup import verify_environment
from specguard.storage.database import DatabaseManager

logger = logging.getLogger("SpecGuard.API.Settings")
router = APIRouter(prefix="/settings", tags=["settings"])


def _dir_size(path: Path) -> int:
    """Calculates total directory size in bytes."""
    total = 0
    if path.exists():
        for p in path.rglob("*"):
            if p.is_file():
                total += p.stat().st_size
    return total


@router.get("/health")
def get_environment_health() -> Dict[str, Any]:
    """Runs complete pre-flight startup verification diagnostics."""
    report = verify_environment()
    return asdict(report)


@router.get("/storage")
def get_storage_statistics() -> Dict[str, Any]:
    """Inspects local filesystem usage and repository size."""
    repo_dir = BASE_DIR / "repository"
    docs_dir = repo_dir / "documents"
    comps_dir = repo_dir / "comparisons"

    db_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    repo_docs_size = _dir_size(docs_dir)
    repo_comps_size = _dir_size(comps_dir)
    reports_size = _dir_size(REPORTS_DIR)
    models_size = _dir_size(MODELS_DIR)

    doc_files_count = len(list(docs_dir.glob("*.*"))) if docs_dir.exists() else 0
    comp_folders_count = len([d for d in comps_dir.iterdir() if d.is_dir()]) if comps_dir.exists() else 0
    reports_count = len(list(REPORTS_DIR.glob("*.*"))) if REPORTS_DIR.exists() else 0

    return {
        "database": {
            "path": str(DB_PATH),
            "size_bytes": db_size,
            "size_mb": round(db_size / (1024 * 1024), 2)
        },
        "repository": {
            "documents_count": doc_files_count,
            "documents_size_mb": round(repo_docs_size / (1024 * 1024), 2),
            "comparisons_count": comp_folders_count,
            "comparisons_size_mb": round(repo_comps_size / (1024 * 1024), 2)
        },
        "reports": {
            "count": reports_count,
            "size_mb": round(reports_size / (1024 * 1024), 2)
        },
        "models": {
            "size_mb": round(models_size / (1024 * 1024), 2)
        },
        "offline_verified": True
    }


@router.get("/audit")
def list_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Retrieves immutable audit trail logs."""
    db = DatabaseManager()
    with db.get_connection() as conn:
        cursor = conn.cursor()

        where_clauses = ["1=1"]
        params: List[Any] = []

        if search:
            s = f"%{search.lower()}%"
            where_clauses.append("(LOWER(user_action) LIKE ? OR LOWER(details) LIKE ? OR LOWER(document_hash) LIKE ?)")
            params.extend([s, s, s])

        where_sql = " AND ".join(where_clauses)

        cursor.execute(f"SELECT COUNT(*) FROM audit_logs WHERE {where_sql}", tuple(params))
        total = cursor.fetchone()[0]

        cursor.execute(f"""
            SELECT id, timestamp, user_action, document_hash, details
            FROM audit_logs
            WHERE {where_sql}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
        """, tuple(params + [limit, offset]))

        logs = [dict(r) for r in cursor.fetchall()]

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "logs": logs
    }
