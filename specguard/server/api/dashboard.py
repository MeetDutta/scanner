"""
Dashboard API Endpoints for SpecGuard.
Provides real summary statistics, severity distributions, domain breakdown,
and recent comparison records strictly from the local SQLite repository.
"""

from fastapi import APIRouter
from typing import Dict, Any, List
import sqlite3
import logging

from specguard.storage.database import DatabaseManager
from specguard.storage.repositories import SessionRepository, DocumentRepository
from specguard.core.config import DB_PATH

logger = logging.getLogger("SpecGuard.API.Dashboard")
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
def get_dashboard_stats() -> Dict[str, Any]:
    """Returns real operational statistics from the SQLite database."""
    db = DatabaseManager()
    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Overall counts from repo_comparisons if available, fallback to analysis_sessions
        cursor.execute("""
            SELECT 
                COUNT(*) as total_comparisons,
                COALESCE(SUM(total_findings), 0) as total_findings,
                COALESCE(SUM(critical_count), 0) as total_critical,
                COALESCE(SUM(high_count), 0) as total_high,
                COALESCE(SUM(medium_count), 0) as total_medium,
                COALESCE(SUM(low_count), 0) as total_low,
                COALESCE(SUM(info_count), 0) as total_info
            FROM repo_comparisons
        """)
        repo_row = dict(cursor.fetchone() or {})

        # Total unique documents in repository
        cursor.execute("SELECT COUNT(*) FROM repo_documents")
        total_docs = cursor.fetchone()[0]

        # Domain breakdown from repo_comparisons
        cursor.execute("""
            SELECT domain, COUNT(*) as count, COALESCE(SUM(total_findings), 0) as findings
            FROM repo_comparisons
            GROUP BY domain
        """)
        domain_rows = cursor.fetchall()
        domain_stats = {}
        for row in domain_rows:
            domain_name = row["domain"].capitalize() if row["domain"] else "Unknown"
            domain_stats[domain_name] = {
                "comparisons": row["count"],
                "findings": row["findings"]
            }

        # Ensure primary domains are represented
        for d in ["Mechanical", "Electrical", "Chemical"]:
            if d not in domain_stats:
                domain_stats[d] = {"comparisons": 0, "findings": 0}

        # Average duration of completed comparisons
        cursor.execute("SELECT COALESCE(AVG(duration_ms), 0) FROM repo_comparisons WHERE duration_ms > 0")
        avg_duration = round(cursor.fetchone()[0])

    return {
        "offline_mode": True,
        "system_status": "Ready",
        "total_documents": total_docs,
        "total_analyses": repo_row.get("total_comparisons", 0),
        "total_findings": repo_row.get("total_findings", 0),
        "severity_distribution": {
            "Critical": repo_row.get("total_critical", 0),
            "High": repo_row.get("total_high", 0),
            "Medium": repo_row.get("total_medium", 0),
            "Low": repo_row.get("total_low", 0),
            "Informational": repo_row.get("total_info", 0)
        },
        "domain_distribution": domain_stats,
        "avg_duration_ms": avg_duration
    }


@router.get("/recent")
def get_recent_activity(limit: int = 8) -> Dict[str, Any]:
    """Returns recent comparisons and recently added documents."""
    db = DatabaseManager()
    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Recent comparisons
        cursor.execute("""
            SELECT 
                comparison_id, document_id, document_filename, document_sha256,
                domain, status, analysis_completed_at, duration_ms,
                total_findings, critical_count, high_count, medium_count, low_count, info_count
            FROM repo_comparisons
            ORDER BY rowid DESC
            LIMIT ?
        """, (limit,))
        recent_comparisons = [dict(r) for r in cursor.fetchall()]

        # Recent documents
        cursor.execute("""
            SELECT document_id, filename, file_type, file_size, page_count, created_at, sha256
            FROM repo_documents
            ORDER BY rowid DESC
            LIMIT ?
        """, (limit,))
        recent_documents = [dict(r) for r in cursor.fetchall()]

    return {
        "recent_comparisons": recent_comparisons,
        "recent_documents": recent_documents
    }
