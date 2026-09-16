"""
Document Analysis History and Revision Repository API for SpecGuard.
Manages immutable comparison archives, revision families, and diff analysis.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
import logging

from specguard.storage.database import DatabaseManager
from specguard.repository.manager import RepositoryManager

logger = logging.getLogger("SpecGuard.API.History")
router = APIRouter(prefix="/history", tags=["history"])


@router.get("")
def list_history(
    domain: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """Lists historical comparisons with pagination and filtering."""
    db = DatabaseManager()
    with db.get_connection() as conn:
        cursor = conn.cursor()

        where_clauses = ["1=1"]
        params: List[Any] = []

        if domain:
            where_clauses.append("LOWER(domain) = LOWER(?)")
            params.append(domain)
        if search:
            s = f"%{search.lower()}%"
            where_clauses.append("(LOWER(comparison_id) LIKE ? OR LOWER(document_filename) LIKE ?)")
            params.extend([s, s])

        where_sql = " AND ".join(where_clauses)

        # Count total
        cursor.execute(f"SELECT COUNT(*) FROM repo_comparisons WHERE {where_sql}", tuple(params))
        total_count = cursor.fetchone()[0]

        # Fetch records
        cursor.execute(f"""
            SELECT 
                c.comparison_id, c.document_id, c.document_filename, c.document_sha256,
                c.domain, c.status, c.analysis_completed_at, c.duration_ms,
                c.total_findings, c.critical_count, c.high_count, c.medium_count, c.low_count, c.info_count,
                d.file_type, d.file_size, d.page_count
            FROM repo_comparisons c
            LEFT JOIN repo_documents d ON c.document_id = d.document_id
            WHERE {where_sql}
            ORDER BY c.rowid DESC
            LIMIT ? OFFSET ?
        """, tuple(params + [limit, offset]))

        records = [dict(r) for r in cursor.fetchall()]

    return {
        "total_count": total_count,
        "offset": offset,
        "limit": limit,
        "comparisons": records
    }


@router.get("/{comparison_id}")
def get_comparison_detail(comparison_id: str) -> Dict[str, Any]:
    """Retrieves full details for a comparison record."""
    repo = RepositoryManager()
    rec = repo.get_comparison_record(comparison_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Comparison {comparison_id} not found.")

    findings = repo.get_comparison_findings(comparison_id)
    doc_info = repo.get_document(rec.document_id)

    return {
        "comparison_id": rec.comparison_id,
        "document_id": rec.document_id,
        "document_filename": rec.document_filename,
        "document_sha256": rec.document_sha256,
        "domain": rec.domain,
        "status": rec.status,
        "analysis_started_at": rec.analysis_started_at,
        "analysis_completed_at": rec.analysis_completed_at,
        "duration_ms": rec.duration_ms,
        "model_version": rec.model_version,
        "standards_used": rec.standards_used,
        "total_findings": rec.total_findings,
        "critical_count": rec.critical_count,
        "high_count": rec.high_count,
        "medium_count": rec.medium_count,
        "low_count": rec.low_count,
        "info_count": rec.info_count,
        "findings": [f.to_dict() for f in findings],
        "document": {
            "filename": doc_info.filename if doc_info else rec.document_filename,
            "file_type": doc_info.file_type if doc_info else "PDF",
            "file_size": doc_info.file_size if doc_info else 0,
            "page_count": doc_info.page_count if doc_info else 1,
            "original_path": doc_info.original_path if doc_info else ""
        }
    }


@router.delete("/{comparison_id}")
def delete_comparison_record(comparison_id: str) -> Dict[str, Any]:
    """Deletes a comparison record and removes its archived findings."""
    repo = RepositoryManager()
    try:
        repo.delete_comparison(comparison_id)
        return {"status": "success", "message": f"Comparison {comparison_id} deleted."}
    except Exception as e:
        logger.error("Failed deleting comparison %s: %s", comparison_id, e)
        raise HTTPException(status_code=500, detail=f"Deletion failed: {e}")


@router.get("/diff/{id1}/{id2}")
def compare_comparison_revisions(id1: str, id2: str) -> Dict[str, Any]:
    """Performs structured diff analysis across two comparison revisions."""
    repo = RepositoryManager()
    try:
        diff_result = repo.compare_revisions(id1, id2)
        return diff_result
    except Exception as e:
        logger.error("Failed comparing %s and %s: %s", id1, id2, e)
        raise HTTPException(status_code=500, detail=f"Diff failed: {e}")
