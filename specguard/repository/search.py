"""
Offline Search and Filtering Engine for SpecGuard Document Repository.
Provides fast multi-field full-text and metadata queries against local SQLite database.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from specguard.storage.database import DatabaseManager
from specguard.repository.models import ComparisonRecord


class RepositorySearchEngine:
    """Executes multi-criteria local search queries across historical comparisons and findings."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def search(
        self,
        query: str = "",
        domain: Optional[str] = None,
        severity: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        critical_only: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        conditions = []
        params = []

        if query.strip():
            # Search filename, document_id, comparison_id, domain, model_version
            pattern = f"%{query.strip()}%"
            conditions.append("""(
                c.comparison_id LIKE ? OR 
                c.document_id LIKE ? OR 
                c.document_filename LIKE ? OR 
                c.domain LIKE ? OR 
                c.model_version LIKE ? OR
                EXISTS (
                    SELECT 1 FROM repo_findings f 
                    WHERE f.comparison_id = c.comparison_id AND 
                    (f.explanation LIKE ? OR f.finding_id LIKE ? OR f.detected_value LIKE ? OR f.rule_reference LIKE ?)
                )
            )""")
            params.extend([pattern] * 9)

        if domain and domain.lower() != "all":
            conditions.append("LOWER(c.domain) = ?")
            params.append(domain.lower())

        if critical_only:
            conditions.append("c.critical_count > 0")

        if severity and severity.lower() != "all":
            col_map = {
                "critical": "c.critical_count > 0",
                "high": "c.high_count > 0",
                "medium": "c.medium_count > 0",
                "low": "c.low_count > 0"
            }
            if severity.lower() in col_map:
                conditions.append(col_map[severity.lower()])

        if date_from:
            conditions.append("c.analysis_completed_at >= ?")
            params.append(date_from)

        if date_to:
            conditions.append("c.analysis_completed_at <= ?")
            params.append(date_to)

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        sql = f"""
            SELECT c.*, d.file_size, d.page_count, d.revision_number
            FROM repo_comparisons c
            LEFT JOIN repo_documents d ON c.document_id = d.document_id
            {where_clause}
            ORDER BY c.analysis_completed_at DESC
            LIMIT ?
        """
        params.append(limit)

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
