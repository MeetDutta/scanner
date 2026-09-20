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
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
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
            """)
            conn.commit()
            logger.info("SQLite database schema initialized at %s", self.db_path)

