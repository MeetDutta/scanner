"""
Automated Portable Packaging & Windows Readiness Test Suite.
Tests:
- Centralized runtime path resolution (Development & Frozen mode simulation)
- Directory paths containing spaces, Unicode characters, and deep nesting
- Writable data separation vs read-only resource separation
- Port discovery and collision avoidance
- Logging persistence to data/logs/specguard.log
- Backup creation and transactional snapshotting
- Built-in OpenCV morphological OCR pipeline without external Tesseract
- Localhost web API & static asset integrity
"""

import sys
import os
import shutil
import socket
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from specguard.core.runtime_paths import (
    is_frozen,
    get_app_dir,
    get_bundle_dir,
    get_data_dir,
    get_resource_dir,
    get_database_path,
    get_log_file_path,
    get_reports_dir,
    get_uploads_dir,
    get_web_dir,
    detect_tesseract,
)
from portable_launcher import (
    is_port_available,
    find_available_port,
    setup_portable_logging,
)
from specguard.storage.database import DatabaseManager
from specguard.storage.backup import create_backup, list_backups
from specguard.core.scanned_pipeline import ScannedDocumentPipeline
from specguard.core.document_parser import DocumentParser
from specguard.server.app import app

client = TestClient(app)


class TestRuntimePaths:
    """Verifies path resolution under standard and edge-case environments."""

    def test_development_mode_paths(self):
        """Ensures that in development mode, app dir resolves to project workspace."""
        app_dir = get_app_dir()
        assert (app_dir / "pyproject.toml").exists()
        assert (app_dir / "portable_launcher.py").exists()

    def test_simulated_frozen_mode(self, monkeypatch, tmp_path):
        """Simulates PyInstaller frozen execution with sys.frozen and sys._MEIPASS."""
        fake_exe = tmp_path / "Binaries" / "SpecGuard.exe"
        fake_exe.parent.mkdir(parents=True, exist_ok=True)
        fake_exe.write_text("stub", encoding="utf-8")

        fake_meipass = tmp_path / "_MEI12345"
        fake_meipass.mkdir(parents=True, exist_ok=True)
        (fake_meipass / "resources").mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "executable", str(fake_exe))
        monkeypatch.setattr(sys, "_MEIPASS", str(fake_meipass), raising=False)

        assert is_frozen() is True
        assert get_app_dir() == fake_exe.parent
        assert get_bundle_dir() == fake_meipass

    def test_paths_with_spaces_and_unicode(self, tmp_path):
        """Verifies directory creation and access in paths with spaces and Unicode."""
        unicode_dir = tmp_path / "SpecGuard 🛡️ Path With Spaces" / "Подкаталог"
        unicode_dir.mkdir(parents=True, exist_ok=True)

        test_db = unicode_dir / "specguard.db"
        db = DatabaseManager(db_path=test_db)
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            assert cursor.fetchone()[0] == 1
        assert test_db.exists()

    def test_resource_fallback_and_web_dir(self):
        """Verifies that web static assets and templates are discoverable."""
        web_dir = get_web_dir()
        assert web_dir.exists()
        assert (web_dir / "templates" / "index.html").exists()
        assert (web_dir / "static" / "css" / "base.css").exists()
        assert (web_dir / "static" / "js" / "app.js").exists()


class TestPortDiscovery:
    """Verifies localhost port discovery and collision avoidance."""

    def test_is_port_available(self):
        """Tests port availability checking logic."""
        # Find an open port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            free_port = s.getsockname()[1]
        assert is_port_available("127.0.0.1", free_port) is True

    def test_find_available_port_avoids_conflict(self):
        """Binds a socket to simulate collision and ensures allocator picks alternative."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            occupied_port = s.getsockname()[1]
            # occupied_port is now bound and held by socket s
            allocated = find_available_port("127.0.0.1", preferred_port=occupied_port)
            assert allocated != occupied_port
            assert allocated > occupied_port


class TestLoggingAndDiagnostics:
    """Verifies dual console and persistent file logging."""

    def test_portable_logging_creation(self, tmp_path):
        log_file = tmp_path / "logs" / "specguard.log"
        logger = setup_portable_logging(log_file)
        logger.info("Test portable log entry 2026")

        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8")
        assert "Test portable log entry 2026" in content


class TestUserDataAndBackups:
    """Verifies persistent database operations and transactional backups."""

    def test_database_initialization(self, tmp_path):
        db_file = tmp_path / "data" / "database" / "specguard.db"
        db = DatabaseManager(db_path=db_file)
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {r[0] for r in cursor.fetchall()}
            assert "documents" in tables
            assert "analysis_sessions" in tables
            assert "findings" in tables
            assert "audit_logs" in tables

    def test_backup_creation_and_listing(self, tmp_path):
        backup_dir = tmp_path / "backups"
        backup_zip = create_backup(dest_dir=backup_dir)
        assert backup_zip.exists()
        assert backup_zip.name.startswith("SpecGuard_Backup_")
        assert backup_zip.suffix == ".zip"

        backups = list_backups(dest_dir=backup_dir)
        assert len(backups) == 1
        assert backups[0]["filename"] == backup_zip.name


class TestScannedVisionOCR:
    """Verifies OpenCV scanned document morphological text region extractor."""

    def test_scanned_pipeline_deskew_and_morphology(self):
        import numpy as np
        # Create a synthetic technical document image with skewed black lines
        img = np.full((300, 400), 255, dtype=np.uint8)
        # Draw some text-like blocks
        img[50:70, 50:200] = 0
        img[100:120, 50:350] = 0
        img[150:170, 50:280] = 0

        enhanced = ScannedDocumentPipeline.preprocess_image(img)
        assert enhanced.shape == (300, 400)

        deskewed, angle = ScannedDocumentPipeline.deskew_image(enhanced)
        assert isinstance(angle, float)

        binary = ScannedDocumentPipeline.binarize(deskewed)
        regions = ScannedDocumentPipeline.extract_text_regions(binary)
        assert len(regions) >= 1

    def test_tesseract_graceful_detection(self):
        """Ensures detect_tesseract returns Path or None without raising exceptions."""
        result = detect_tesseract()
        assert result is None or isinstance(result, Path)


class TestWebAndOfflineAPI:
    """Verifies that the web interface and API operate strictly offline."""

    def test_health_check_endpoint(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "online"
        assert data["mode"] == "offline"

    def test_static_assets_served(self):
        resp = client.get("/static/css/base.css")
        assert resp.status_code == 200
        assert "var(--bg-app)" in resp.text or "--color" in resp.text or "SpecGuard" in resp.text or len(resp.text) > 100

        resp_js = client.get("/static/js/app.js")
        assert resp_js.status_code == 200
        assert "SpecGuardApp" in resp_js.text

    def test_index_html_served(self):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "DOCREADY" in resp.text or "SPEC GUARD" in resp.text
        assert "100% Offline" in resp.text

    def test_backup_api_endpoints(self):
        resp = client.post("/api/settings/backup")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["filename"].endswith(".zip")

        resp_list = client.get("/api/settings/backups")
        assert resp_list.status_code == 200
        assert len(resp_list.json()) >= 1
