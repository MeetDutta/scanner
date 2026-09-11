"""
Audit logger and SHA-256 integrity verifier for SpecGuard.
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict
from specguard.storage.database import DatabaseManager

logger = logging.getLogger(__name__)


class AuditLogger:
    """Records local audit trails for all operations, analysis, and exports."""
    def __init__(self, db: DatabaseManager):
        self.db = db

    def log(self, user_action: str, document_hash: Optional[str] = None, details: str = ""):
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO audit_logs (user_action, document_hash, details)
                    VALUES (?, ?, ?)
                """, (user_action, document_hash, details))
                conn.commit()
            logger.info("AUDIT: action=%s, doc=%s, details=%s", user_action, document_hash, details)
        except Exception as e:
            logger.error("Audit logging failed: %s", e)


class IntegrityVerifier:
    """Calculates and verifies SHA-256 digests for documents, models, and standards."""

    @staticmethod
    def calculate_file_hash(file_path: Path) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def verify_file(file_path: Path, expected_hash: str) -> bool:
        if not file_path.exists():
            return False
        return IntegrityVerifier.calculate_file_hash(file_path).lower() == expected_hash.lower()
