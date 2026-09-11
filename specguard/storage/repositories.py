"""
CRUD Repositories for SpecGuard SQLite database.
"""

import json
from typing import List, Dict, Optional, Any
from specguard.storage.database import DatabaseManager
from specguard.core.models import DocumentModel, Finding, BBox


class DocumentRepository:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def save_document(self, doc: DocumentModel):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO documents (file_hash, filename, file_path, file_type, size_bytes, page_count)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                doc.file_hash,
                Path(doc.file_path).name,
                doc.file_path,
                doc.file_type,
                doc.file_size,
                doc.page_count
            ))
            conn.commit()

    def get_document(self, file_hash: str) -> Optional[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE file_hash = ?", (file_hash,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_recent_documents(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents ORDER BY created_at DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]


class SessionRepository:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def save_session(self, session_id: str, doc_hash: str, domain: str, standards: List[str], findings: List[Finding], duration_ms: int):
        crit = sum(1 for f in findings if f.severity == "Critical")
        high = sum(1 for f in findings if f.severity == "High")
        med = sum(1 for f in findings if f.severity == "Medium")
        low = sum(1 for f in findings if f.severity == "Low")
        info = sum(1 for f in findings if f.severity == "Informational")

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO analysis_sessions 
                (session_id, document_hash, domain, standards_used, findings_count, critical_count, high_count, medium_count, low_count, info_count, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, doc_hash, domain, json.dumps(standards), len(findings),
                crit, high, med, low, info, duration_ms
            ))

            for f in findings:
                bbox_json = json.dumps(f.bbox.to_dict()) if f.bbox else None
                cursor.execute("""
                    INSERT INTO findings 
                    (session_id, finding_id, category, domain, location, page, bbox_json, original_content, 
                     detected_value, expected_value, deviation, severity, confidence, explanation, suggested_correction, rule_reference, priority_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id, f.finding_id, f.category, f.domain, f.location, f.page, bbox_json,
                    str(f.original_content), str(f.detected_value), str(f.expected_value), f.deviation,
                    f.severity, f.confidence, f.explanation, f.suggested_correction, f.rule_reference, f.priority_score
                ))
            conn.commit()

    def get_findings_for_session(self, session_id: str) -> List[Finding]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM findings WHERE session_id = ? ORDER BY priority_score DESC", (session_id,))
            rows = cursor.fetchall()
            findings = []
            for r in rows:
                bbox = BBox.from_dict(json.loads(r["bbox_json"])) if r["bbox_json"] else None
                findings.append(Finding(
                    finding_id=r["finding_id"],
                    category=r["category"],
                    domain=r["domain"],
                    location=r["location"] or "",
                    page=r["page"],
                    bbox=bbox,
                    original_content=r["original_content"] or "",
                    detected_value=r["detected_value"] or "",
                    expected_value=r["expected_value"] or "",
                    deviation=r["deviation"],
                    severity=r["severity"],
                    confidence=r["confidence"],
                    explanation=r["explanation"] or "",
                    suggested_correction=r["suggested_correction"] or "",
                    rule_reference=r["rule_reference"],
                    priority_score=r["priority_score"]
                ))
            return findings

    def get_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.*, d.filename FROM analysis_sessions s
                LEFT JOIN documents d ON s.document_hash = d.file_hash
                ORDER BY s.start_time DESC LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_summary_statistics(self) -> Dict[str, Any]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT document_hash) as total_docs,
                    COUNT(*) as total_sessions,
                    SUM(findings_count) as total_findings,
                    SUM(critical_count) as total_critical,
                    SUM(high_count) as total_high,
                    SUM(medium_count) as total_medium,
                    SUM(low_count) as total_low,
                    SUM(info_count) as total_info
                FROM analysis_sessions
            """)
            row = cursor.fetchone()
            res = dict(row) if row else {}
            # Clean up None values
            for k in res:
                if res[k] is None:
                    res[k] = 0
            return res


from pathlib import Path
