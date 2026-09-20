"""
Test suite validating DocReady branding, package aliases, launchers, and backward compatibility.
"""

import sys
import subprocess
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from specguard.server.app import app

client = TestClient(app)
ROOT_DIR = Path(__file__).resolve().parent.parent


def test_docready_package_import():
    """Verifies that docready package is importable and exposes version and subpackages."""
    import docready
    assert docready.__version__ == "1.0.0"
    assert "DocReady" in docready.__title__

    import docready.core.pipeline as pipeline_mod
    assert hasattr(pipeline_mod, "AnalysisPipeline")

    import docready.templates.custom_manager as custom_mgr_mod
    assert hasattr(custom_mgr_mod, "CustomTemplateManager")

    import docready.server.app as server_app_mod
    assert hasattr(server_app_mod, "create_app")


def test_docready_fastapi_metadata():
    """Verifies that FastAPI server metadata and descriptions reflect DocReady branding."""
    assert "DocReady" in app.title
    assert "DocReady" in app.description


def test_docready_html_branding():
    """Verifies that index.html branding, titles, and status bar reflect DocReady."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "DOCREADY" in resp.text
    assert "DocReady Platform" in resp.text
    assert "100% Offline" in resp.text


def test_docready_runtime_paths():
    """Verifies that runtime path utilities resolve valid paths with DocReady support."""
    from docready.core.runtime_paths import (
        get_app_dir,
        get_data_dir,
        get_database_path,
        get_log_file_path,
    )
    assert get_app_dir().exists()
    assert get_data_dir().exists()
    assert get_database_path() is not None
    assert get_log_file_path().name in ["docready.log", "specguard.log"]


def test_docready_portable_artifacts_exist():
    """Verifies that DocReady launcher scripts and PyInstaller spec files exist."""
    assert (ROOT_DIR / "Launch_DocReady.bat").exists()
    assert (ROOT_DIR / "Launch_DocReady.bat").stat().st_size > 500
    assert (ROOT_DIR / "DocReady.spec").exists()
    assert "DocReady" in (ROOT_DIR / "DocReady.spec").read_text(encoding="utf-8")


def test_docready_cli_version():
    """Runs portable_launcher.py --version to ensure DocReady branding is reported."""
    cmd = [sys.executable, str(ROOT_DIR / "portable_launcher.py"), "--version"]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT_DIR))
    assert result.returncode == 0
    assert "DocReady" in result.stdout
