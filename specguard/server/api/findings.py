"""
Findings Management and Search API for SpecGuard.
Provides multi-criteria filtering, search, pagination, and detailed remediation guidance
strictly from the verified local SQLite findings repository.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
import json
import logging

from specguard.storage.database import DatabaseManager
from specguard.core.models import Finding, BBox
from specguard.repository.manager import RepositoryManager

logger = logging.getLogger("SpecGuard.API.Findings")
router = APIRouter(prefix="/findings", tags=["findings"])


@router.get("")
def list_findings(
    session_id: Optional[str] = Query(None),
    comparison_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    page: Optional[int] = Query(None),
    domain: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("priority_score"),
    sort_dir: str = Query("desc"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """Retrieves ranked findings with search and multi-criteria filtering."""
    db = DatabaseManager()
    target_id = comparison_id or session_id

    # If no session or comparison ID provided, get the latest comparison ID
    if not target_id:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT comparison_id FROM repo_comparisons ORDER BY rowid DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                target_id = row["comparison_id"]

    if not target_id:
        return {
            "findings": [],
            "total_count": 0,
            "session_id": None,
            "severity_summary": {}
        }

    with db.get_connection() as conn:
        cursor = conn.cursor()

        # Check whether target_id is in repo_findings or findings
        cursor.execute("SELECT COUNT(*) FROM repo_findings WHERE comparison_id = ?", (target_id,))
        is_repo = (cursor.fetchone()[0] > 0)

        table_name = "repo_findings" if is_repo else "findings"
        id_col = "comparison_id" if is_repo else "session_id"

        where_clauses = [f"{id_col} = ?"]
        params: List[Any] = [target_id]

        if severity:
            where_clauses.append("LOWER(severity) = LOWER(?)")
            params.append(severity)
        if category:
            where_clauses.append("LOWER(category) = LOWER(?)")
            params.append(category)
        if page:
            where_clauses.append("page = ?")
            params.append(page)
        if domain:
            where_clauses.append("LOWER(domain) = LOWER(?)")
            params.append(domain)
        if search:
            s_param = f"%{search.lower()}%"
            where_clauses.append(
                "(LOWER(finding_id) LIKE ? OR LOWER(explanation) LIKE ? OR LOWER(detected_value) LIKE ? OR LOWER(location) LIKE ? OR LOWER(rule_reference) LIKE ?)"
            )
            params.extend([s_param, s_param, s_param, s_param, s_param])

        where_sql = " AND ".join(where_clauses)

        # Count total matching
        cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {where_sql}", tuple(params))
        total_count = cursor.fetchone()[0]

        # Valid sort columns
        valid_sort_cols = {
            "priority_score": "priority_score",
            "severity": "priority_score",  # higher priority first
            "page": "page",
            "category": "category",
            "finding_id": "finding_id"
        }
        col = valid_sort_cols.get(sort_by, "priority_score")
        direction = "ASC" if sort_dir.lower() == "asc" else "DESC"

        # Fetch page of findings
        query = f"""
            SELECT * FROM {table_name}
            WHERE {where_sql}
            ORDER BY {col} {direction}, id ASC
            LIMIT ? OFFSET ?
        """
        cursor.execute(query, tuple(params + [limit, offset]))
        rows = cursor.fetchall()

        findings = []
        for r in rows:
            bbox_dict = None
            if r["bbox_json"]:
                try:
                    bbox_dict = json.loads(r["bbox_json"])
                except Exception:
                    bbox_dict = None

            findings.append({
                "id": r["id"],
                "session_id": target_id,
                "finding_id": r["finding_id"],
                "category": r["category"],
                "domain": r["domain"],
                "location": r["location"] or "",
                "page": r["page"],
                "bbox": bbox_dict,
                "original_content": r["original_content"] or "",
                "detected_value": r["detected_value"] or "",
                "expected_value": r["expected_value"] or "",
                "deviation": r["deviation"] or "",
                "severity": r["severity"],
                "confidence": r["confidence"],
                "explanation": r["explanation"] or "",
                "suggested_correction": r["suggested_correction"] or "",
                "rule_reference": r["rule_reference"] or "",
                "priority_score": r["priority_score"]
            })

        # Severity summary for current session
        cursor.execute(f"""
            SELECT severity, COUNT(*) as count 
            FROM {table_name} 
            WHERE {id_col} = ? 
            GROUP BY severity
        """, (target_id,))
        sev_counts = {row["severity"]: row["count"] for row in cursor.fetchall()}

        # Category summary for current session
        cursor.execute(f"""
            SELECT category, COUNT(*) as count 
            FROM {table_name} 
            WHERE {id_col} = ? 
            GROUP BY category
        """, (target_id,))
        cat_counts = {row["category"]: row["count"] for row in cursor.fetchall()}

    return {
        "session_id": target_id,
        "total_count": total_count,
        "offset": offset,
        "limit": limit,
        "findings": findings,
        "severity_summary": sev_counts,
        "category_summary": cat_counts
    }


@router.get("/{finding_id}")
def get_finding_detail(finding_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves full explanation, coordinate bounding box, and remediation for a finding."""
    db = DatabaseManager()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        params: List[Any] = [finding_id]
        sql = "SELECT * FROM repo_findings WHERE finding_id = ?"
        if session_id:
            sql += " AND comparison_id = ?"
            params.append(session_id)
        sql += " ORDER BY id DESC LIMIT 1"

        cursor.execute(sql, tuple(params))
        row = cursor.fetchone()

        if not row:
            # Fallback to findings table
            sql = "SELECT * FROM findings WHERE finding_id = ?"
            params = [finding_id]
            if session_id:
                sql += " AND session_id = ?"
                params.append(session_id)
            sql += " ORDER BY id DESC LIMIT 1"
            cursor.execute(sql, tuple(params))
            row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Finding {finding_id} not found.")

        bbox_dict = None
        if row["bbox_json"]:
            try:
                bbox_dict = json.loads(row["bbox_json"])
            except Exception:
                bbox_dict = None

        return {
            "finding_id": row["finding_id"],
            "session_id": row["comparison_id"] if "comparison_id" in row.keys() else row["session_id"],
            "category": row["category"],
            "domain": row["domain"],
            "location": row["location"] or "",
            "page": row["page"],
            "bbox": bbox_dict,
            "original_content": row["original_content"] or "",
            "detected_value": row["detected_value"] or "",
            "expected_value": row["expected_value"] or "",
            "deviation": row["deviation"] or "",
            "severity": row["severity"],
            "confidence": row["confidence"],
            "explanation": row["explanation"] or "",
            "suggested_correction": row["suggested_correction"] or "",
            "rule_reference": row["rule_reference"] or "",
            "priority_score": row["priority_score"]
        }
