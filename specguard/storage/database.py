"""
Local SQLite database management for SpecGuard.
Guarantees 100% offline data integrity and session history.
"""

import sqlite3
import json
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path
from specguard.core.config import DB_PATH

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite connection lifecycle, migrations, and transactional execution."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 30000")
        conn.execute("PRAGMA synchronous = NORMAL")
        return conn

    def init_db(self):
        """Creates the required tables if they don't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                file_hash TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_type TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                page_count INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS analysis_sessions (
                session_id TEXT PRIMARY KEY,
                document_hash TEXT NOT NULL,
                domain TEXT NOT NULL,
                standards_used TEXT,
                findings_count INTEGER DEFAULT 0,
                critical_count INTEGER DEFAULT 0,
                high_count INTEGER DEFAULT 0,
                medium_count INTEGER DEFAULT 0,
                low_count INTEGER DEFAULT 0,
                info_count INTEGER DEFAULT 0,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                duration_ms INTEGER DEFAULT 0,
                status TEXT DEFAULT 'COMPLETED',
                FOREIGN KEY (document_hash) REFERENCES documents(file_hash) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                finding_id TEXT NOT NULL,
                category TEXT NOT NULL,
                domain TEXT NOT NULL,
                location TEXT,
                page INTEGER NOT NULL,
                bbox_json TEXT,
                original_content TEXT,
                detected_value TEXT,
                expected_value TEXT,
                deviation TEXT,
                severity TEXT NOT NULL,
                confidence REAL NOT NULL,
                explanation TEXT,
                suggested_correction TEXT,
                rule_reference TEXT,
                priority_score REAL DEFAULT 0.0,
                FOREIGN KEY (session_id) REFERENCES analysis_sessions(session_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS standards (
                standard_id TEXT PRIMARY KEY,
                domain TEXT NOT NULL,
                name TEXT NOT NULL,
                version TEXT,
                file_path TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS rules (
                rule_id TEXT PRIMARY KEY,
                standard_id TEXT NOT NULL,
                domain TEXT NOT NULL,
                parameter TEXT NOT NULL,
                operator TEXT NOT NULL,
                expected_value TEXT,
                allowed_range TEXT,
                unit TEXT,
                severity TEXT NOT NULL,
                description TEXT,
                FOREIGN KEY (standard_id) REFERENCES standards(standard_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS models (
                model_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                domain TEXT NOT NULL,
                version TEXT NOT NULL,
                file_path TEXT NOT NULL,
                sha256_hash TEXT NOT NULL,
                is_loaded INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'engineer',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_action TEXT NOT NULL,
                document_hash TEXT,
                details TEXT
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS repo_documents (
                document_id TEXT PRIMARY KEY,
                family_id TEXT NOT NULL,
                revision_number INTEGER DEFAULT 1,
                filename TEXT NOT NULL,
                original_path TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                page_count INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                stored_locally INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS repo_comparisons (
                comparison_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                document_filename TEXT NOT NULL,
                document_sha256 TEXT NOT NULL,
                domain TEXT NOT NULL,
                status TEXT DEFAULT 'COMPLETED',
                analysis_started_at TIMESTAMP,
                analysis_completed_at TIMESTAMP,
                duration_ms INTEGER DEFAULT 0,
                model_version TEXT NOT NULL,
                standards_used TEXT,
                total_findings INTEGER DEFAULT 0,
                critical_count INTEGER DEFAULT 0,
                high_count INTEGER DEFAULT 0,
                medium_count INTEGER DEFAULT 0,
                low_count INTEGER DEFAULT 0,
                info_count INTEGER DEFAULT 0,
                annotated_pdf_path TEXT,
                annotated_docx_path TEXT,
                report_html_path TEXT,
                findings_json_path TEXT,
                FOREIGN KEY (document_id) REFERENCES repo_documents(document_id)
            );

            CREATE TABLE IF NOT EXISTS repo_findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comparison_id TEXT NOT NULL,
                finding_id TEXT NOT NULL,
                category TEXT NOT NULL,
                domain TEXT NOT NULL,
                location TEXT,
                page INTEGER NOT NULL,
                bbox_json TEXT,
                original_content TEXT,
                detected_value TEXT,
                expected_value TEXT,
                deviation TEXT,
                severity TEXT NOT NULL,
                confidence REAL NOT NULL,
                explanation TEXT,
                suggested_correction TEXT,
                rule_reference TEXT,
                priority_score REAL DEFAULT 0.0,
                FOREIGN KEY (comparison_id) REFERENCES repo_comparisons(comparison_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_repo_doc_sha ON repo_documents(sha256);
            CREATE INDEX IF NOT EXISTS idx_repo_cmp_date ON repo_comparisons(analysis_completed_at);
            CREATE INDEX IF NOT EXISTS idx_repo_cmp_domain ON repo_comparisons(domain);

            CREATE TABLE IF NOT EXISTS document_tolerance_reports (
                session_id TEXT PRIMARY KEY,
                document_no TEXT DEFAULT 'Not Provided',
                document_title TEXT DEFAULT 'Not Provided',
                revision TEXT DEFAULT 'Not Provided',
                inspection_profile TEXT NOT NULL,
                inspection_date TEXT NOT NULL,
                pages_inspected INTEGER DEFAULT 1,
                engine_version TEXT DEFAULT 'SpecGuard 1.0.0',
                raw_tolerance REAL DEFAULT 0.0,
                normalization_factor REAL DEFAULT 1.0,
                tolerance_index REAL NOT NULL,
                maximum_acceptable_tolerance REAL NOT NULL,
                tolerance_utilization REAL NOT NULL,
                acceptance_status TEXT NOT NULL,
                status_reason TEXT,
                total_findings INTEGER DEFAULT 0,
                critical_count INTEGER DEFAULT 0,
                high_count INTEGER DEFAULT 0,
                medium_count INTEGER DEFAULT 0,
                low_count INTEGER DEFAULT 0,
                info_count INTEGER DEFAULT 0,
                category_summary_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_tolerance_session ON document_tolerance_reports(session_id);
            """)
            conn.commit()
            self._apply_migrations(conn)
            logger.info("SQLite database schema initialized at %s", self.db_path)

    def _apply_migrations(self, conn: sqlite3.Connection):
        """Applies safe, idempotent migrations preserving all existing data and sessions."""
        cursor = conn.cursor()
        try:
            # 1. Migrate misclassified spelling severities (CRITICAL -> Low)
            cursor.execute("""
                UPDATE findings 
                SET severity = 'Low' 
                WHERE (category = 'SPELLING' OR finding_id LIKE 'GRM-SPL-%') 
                  AND UPPER(severity) = 'CRITICAL'
            """)
            cursor.execute("""
                UPDATE repo_findings 
                SET severity = 'Low' 
                WHERE (category = 'SPELLING' OR finding_id LIKE 'GRM-SPL-%') 
                  AND UPPER(severity) = 'CRITICAL'
            """)

            # 2. Recalculate severity counts for repo_comparisons
            cursor.execute("SELECT DISTINCT comparison_id FROM repo_findings")
            comp_ids = [r[0] for r in cursor.fetchall()]
            for cid in comp_ids:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN UPPER(severity) = 'CRITICAL' THEN 1 ELSE 0 END) as crit,
                        SUM(CASE WHEN UPPER(severity) = 'HIGH' THEN 1 ELSE 0 END) as high,
                        SUM(CASE WHEN UPPER(severity) = 'MEDIUM' THEN 1 ELSE 0 END) as med,
                        SUM(CASE WHEN UPPER(severity) = 'LOW' THEN 1 ELSE 0 END) as low,
                        SUM(CASE WHEN UPPER(severity) IN ('INFORMATIONAL', 'INFO') THEN 1 ELSE 0 END) as info
                    FROM repo_findings
                    WHERE comparison_id = ?
                """, (cid,))
                row = cursor.fetchone()
                if row:
                    cursor.execute("""
                        UPDATE repo_comparisons
                        SET total_findings = ?, critical_count = ?, high_count = ?, medium_count = ?, low_count = ?, info_count = ?
                        WHERE comparison_id = ?
                    """, (
                        row[0],
                        row[1] or 0,
                        row[2] or 0,
                        row[3] or 0,
                        row[4] or 0,
                        row[5] or 0,
                        cid
                    ))

            # 3. Recalculate severity counts for analysis_sessions
            cursor.execute("SELECT DISTINCT session_id FROM findings")
            sess_ids = [r[0] for r in cursor.fetchall()]
            for sid in sess_ids:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN UPPER(severity) = 'CRITICAL' THEN 1 ELSE 0 END) as crit,
                        SUM(CASE WHEN UPPER(severity) = 'HIGH' THEN 1 ELSE 0 END) as high,
                        SUM(CASE WHEN UPPER(severity) = 'MEDIUM' THEN 1 ELSE 0 END) as med,
                        SUM(CASE WHEN UPPER(severity) = 'LOW' THEN 1 ELSE 0 END) as low,
                        SUM(CASE WHEN UPPER(severity) IN ('INFORMATIONAL', 'INFO') THEN 1 ELSE 0 END) as info
                    FROM findings
                    WHERE session_id = ?
                """, (sid,))
                row = cursor.fetchone()
                if row:
                    cursor.execute("""
                        UPDATE analysis_sessions
                        SET findings_count = ?, critical_count = ?, high_count = ?, medium_count = ?, low_count = ?, info_count = ?
                        WHERE session_id = ?
                    """, (
                        row[0],
                        row[1] or 0,
                        row[2] or 0,
                        row[3] or 0,
                        row[4] or 0,
                        row[5] or 0,
                        sid
                    ))

            # 4. Synchronize tolerance reports with updated severity counts
            cursor.execute("""
                SELECT session_id, maximum_acceptable_tolerance, normalization_factor
                FROM document_tolerance_reports
            """)
            tol_rows = cursor.fetchall()
            for t_row in tol_rows:
                tsid = t_row[0]
                max_tol = float(t_row[1] or 10.0)
                norm_f = float(t_row[2] or 1.0)
                
                # Check repo_comparisons first
                cursor.execute("""
                    SELECT total_findings, critical_count, high_count, medium_count, low_count, info_count
                    FROM repo_comparisons WHERE comparison_id = ?
                """, (tsid,))
                c_data = cursor.fetchone()
                if not c_data:
                    cursor.execute("""
                        SELECT findings_count, critical_count, high_count, medium_count, low_count, info_count
                        FROM analysis_sessions WHERE session_id = ?
                    """, (tsid,))
                    c_data = cursor.fetchone()
                
                if c_data:
                    tot, c_crit, c_high, c_med, c_low, c_info = c_data
                    raw = (c_crit or 0) * 8.0 + (c_high or 0) * 4.0 + (c_med or 0) * 2.0 + (c_low or 0) * 0.5 + (c_info or 0) * 0.0
                    idx = round(raw / (norm_f or 1.0), 2)
                    util = round((idx / max_tol) * 100, 1) if max_tol > 0 else 0.0
                    status = "ELIGIBLE" if (idx <= max_tol and (c_crit or 0) == 0) else "NOT ELIGIBLE"
                    reason = f"Document quality tolerance index ({idx}) is within maximum allowed ({max_tol})." if status == "ELIGIBLE" else (
                        f"Document contains {c_crit} critical finding(s). Configured profile requires at most 0 critical findings." if (c_crit or 0) > 0 else
                        f"Tolerance index ({idx}) exceeds maximum allowable tolerance ({max_tol})."
                    )
                    cursor.execute("""
                        UPDATE document_tolerance_reports
                        SET total_findings = ?, critical_count = ?, high_count = ?, medium_count = ?, low_count = ?, info_count = ?,
                            raw_tolerance = ?, tolerance_index = ?, tolerance_utilization = ?, acceptance_status = ?, status_reason = ?
                        WHERE session_id = ?
                    """, (tot, c_crit or 0, c_high or 0, c_med or 0, c_low or 0, c_info or 0, raw, idx, util, status, reason, tsid))

            # 5. Synchronize on-disk JSON files for migrated comparisons
            comps_dir = self.db_path.parent / "repository" / "comparisons"
            if comps_dir.exists():
                for cid_dir in comps_dir.iterdir():
                    if not cid_dir.is_dir():
                        continue
                    cid = cid_dir.name
                    f_json = cid_dir / "findings.json"
                    if f_json.exists():
                        try:
                            with open(f_json, "r", encoding="utf-8") as f:
                                f_list = json.load(f)
                            changed = False
                            for finding_dict in f_list:
                                cat = (finding_dict.get("category") or "").upper()
                                fid = (finding_dict.get("finding_id") or "").upper()
                                sev = (finding_dict.get("severity") or "").upper()
                                if (cat == "SPELLING" or fid.startswith("GRM-SPL")) and sev == "CRITICAL":
                                    finding_dict["severity"] = "Low"
                                    changed = True
                            if changed:
                                with open(f_json, "w", encoding="utf-8") as f:
                                    json.dump(f_list, f, indent=2)
                        except Exception as f_err:
                            logger.debug("Could not update disk findings.json for %s: %s", cid, f_err)

                    c_json = cid_dir / "comparison.json"
                    if c_json.exists():
                        try:
                            cursor.execute("SELECT total_findings, critical_count, high_count, medium_count, low_count, info_count FROM repo_comparisons WHERE comparison_id = ?", (cid,))
                            rc = cursor.fetchone()
                            if rc:
                                with open(c_json, "r", encoding="utf-8") as f:
                                    c_dict = json.load(f)
                                c_dict["total_findings"] = rc[0]
                                c_dict["critical_count"] = rc[1]
                                c_dict["high_count"] = rc[2]
                                c_dict["medium_count"] = rc[3]
                                c_dict["low_count"] = rc[4]
                                c_dict["info_count"] = rc[5]
                                with open(c_json, "w", encoding="utf-8") as f:
                                    json.dump(c_dict, f, indent=2)
                        except Exception as c_err:
                            logger.debug("Could not update disk comparison.json for %s: %s", cid, c_err)

            conn.commit()
            logger.info("Database migration check completed successfully.")
        except Exception as e:
            logger.warning("Migration failed or already applied: %s", e)

    def save_tolerance_report(self, tol_data: Dict[str, Any]):
        """Persists a calculated tolerance result to prevent re-calculation drift."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO document_tolerance_reports (
                    session_id, document_no, document_title, revision,
                    inspection_profile, inspection_date, pages_inspected,
                    engine_version, raw_tolerance, normalization_factor,
                    tolerance_index, maximum_acceptable_tolerance, tolerance_utilization,
                    acceptance_status, status_reason, total_findings,
                    critical_count, high_count, medium_count, low_count, info_count,
                    category_summary_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tol_data["session_id"],
                tol_data.get("document_no", "Not Provided"),
                tol_data.get("document_title", "Not Provided"),
                tol_data.get("revision", "Not Provided"),
                tol_data.get("inspection_profile", "Publication / Submission"),
                tol_data.get("inspection_date", ""),
                tol_data.get("pages_inspected", 1),
                tol_data.get("engine_version", "SpecGuard 1.0.0"),
                tol_data.get("raw_tolerance", 0.0),
                tol_data.get("normalization_factor", 1.0),
                tol_data["tolerance_index"],
                tol_data["maximum_acceptable_tolerance"],
                tol_data["tolerance_utilization"],
                tol_data["acceptance_status"],
                tol_data.get("status_reason", ""),
                tol_data.get("total_findings", 0),
                tol_data.get("critical_count", 0),
                tol_data.get("high_count", 0),
                tol_data.get("medium_count", 0),
                tol_data.get("low_count", 0),
                tol_data.get("info_count", 0),
                json.dumps(tol_data.get("category_summary", {}))
            ))
            conn.commit()

    def get_tolerance_report(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves persisted tolerance report for an exact session ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM document_tolerance_reports WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            if d.get("category_summary_json"):
                try:
                    d["category_summary"] = json.loads(d["category_summary_json"])
                except Exception:
                    d["category_summary"] = {}
            return d

