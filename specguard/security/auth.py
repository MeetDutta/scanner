"""
Local authentication and user security for SpecGuard.
Strictly offline: Passwords hashed via PBKDF2-HMAC-SHA256 with per-user salt.
"""

import hashlib
import os
import secrets
from typing import Optional, Tuple
from specguard.storage.database import DatabaseManager


class LocalAuthManager:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self._ensure_default_user()

    def _hash_password(self, password: str, salt: Optional[bytes] = None) -> str:
        if salt is None:
            salt = secrets.token_bytes(16)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return f"{salt.hex()}:{pwd_hash.hex()}"

    def _verify_password(self, password: str, stored_hash: str) -> bool:
        try:
            salt_hex, hash_hex = stored_hash.split(":")
            salt = bytes.fromhex(salt_hex)
            expected_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000).hex()
            return secrets.compare_digest(hash_hex, expected_hash)
        except Exception:
            return False

    def _ensure_default_user(self):
        """Creates default local engineer account if no users exist."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM users")
            if cursor.fetchone()["count"] == 0:
                pwd_hash = self._hash_password("admin")
                cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                               ("admin", pwd_hash, "lead_engineer"))
                conn.commit()

    def authenticate(self, username: str, password: str) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            if not row:
                return False
            return self._verify_password(password, row["password_hash"])
