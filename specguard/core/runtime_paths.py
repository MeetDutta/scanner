"""
SpecGuard Centralized Runtime Path Resolution Utility.
Standard server-side path resolution for local and containerized web deployments.

Distinguishes between:
- Immutable Read-Only Application Resources (standards, rules, models, templates, web)
- Mutable Persistent User Data (database, uploads, reports, logs, repository)
"""

import os
import sys
import shutil
import logging
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger("SpecGuard.RuntimePaths")


def get_app_dir() -> Path:
    """
    Returns the root directory where the application is installed or running.
    Resolves to the repository root directory containing app.py and pyproject.toml.
    """
    env_app_dir = os.environ.get("SPECGUARD_APP_DIR") or os.environ.get("DOCREADY_APP_DIR")
    if env_app_dir:
        return Path(env_app_dir).resolve()
    # Walk up from this file: specguard/core/runtime_paths.py -> root
    return Path(__file__).resolve().parent.parent.parent


def _is_writable(path: Path) -> bool:
    """Checks if a directory is writable by attempting to create a small test file."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        test_file = path / ".write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def get_data_dir(subdir: str = "") -> Path:
    """
    Returns the persistent writable user data directory.
    Priority:
    1. `SPECGUARD_DATA_DIR` / `DOCREADY_DATA_DIR` environment variable
    2. `<app_dir>/data`
    3. `~/.specguard/data` (fallback if app_dir is read-only)
    """
    env_data_dir = os.environ.get("SPECGUARD_DATA_DIR") or os.environ.get("DOCREADY_DATA_DIR")
    if env_data_dir:
        target = Path(env_data_dir).resolve()
    else:
        app_dir = get_app_dir()
        candidate = app_dir / "data"
        if _is_writable(candidate):
            target = candidate
        else:
            target = Path.home() / ".specguard" / "data"

    target.mkdir(parents=True, exist_ok=True)
    if subdir:
        sub = target / subdir
        sub.mkdir(parents=True, exist_ok=True)
        return sub
    return target


def get_resource_dir(resource_name: str) -> Path:
    """
    Locates an application resource directory (models, standards, templates, web, etc.).
    """
    app_dir = get_app_dir()
    candidates = [
        app_dir / resource_name,
        app_dir / "specguard" / resource_name,
        app_dir / "resources" / resource_name,
    ]

    for cand in candidates:
        if cand.exists():
            return cand

    return app_dir / resource_name


def get_database_path() -> Path:
    """
    Returns the persistent SQLite database path.
    """
    data_dir = get_data_dir()
    db_folder = data_dir / "database"

    candidates = [
        db_folder / "specguard.db",
        data_dir / "specguard.db",
        db_folder / "docready.db",
        data_dir / "docready.db",
    ]
    for c in candidates:
        if c.exists():
            return c

    db_folder.mkdir(parents=True, exist_ok=True)
    return db_folder / "specguard.db"


def get_log_file_path() -> Path:
    """Returns the path to the primary runtime log file."""
    logs_dir = get_data_dir("logs")
    if (logs_dir / "specguard.log").exists():
        return logs_dir / "specguard.log"
    if (logs_dir / "docready.log").exists():
        return logs_dir / "docready.log"
    return logs_dir / "specguard.log"


def get_reports_dir() -> Path:
    """Returns the persistent reports output directory."""
    data_dir = get_data_dir()
    reports_dir = data_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    return reports_dir


def get_repository_dir() -> Path:
    """
    Returns the persistent document comparison repository directory.
    """
    base_repo = get_app_dir() / "repository"
    if base_repo.exists() and _is_writable(base_repo):
        return base_repo
    data_repo = get_data_dir("repository")
    data_repo.mkdir(parents=True, exist_ok=True)
    return data_repo


def get_uploads_dir() -> Path:
    """Returns the persistent uploaded files directory."""
    data_dir = get_data_dir()
    uploads_dir = data_dir / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    return uploads_dir


def get_web_dir() -> Path:
    """Locates the web frontend directory (static, templates)."""
    app_dir = get_app_dir()
    candidates = [
        app_dir / "specguard" / "web",
        app_dir / "web",
    ]
    for cand in candidates:
        if cand.exists() and (cand / "templates" / "index.html").exists():
            return cand
    return app_dir / "specguard" / "web"


def detect_tesseract() -> Optional[Path]:
    """
    Safely locates a local or system Tesseract OCR executable.
    Does NOT require Tesseract for normal operation (OpenCV morphological engine is built-in).
    """
    app_dir = get_app_dir()
    candidates: List[Path] = [
        app_dir / "tesseract" / "tesseract",
    ]
    for cand in candidates:
        if cand.exists() and os.access(cand, os.X_OK):
            return cand

    # Check system PATH
    system_tess = shutil.which("tesseract")
    if system_tess:
        return Path(system_tess)

    return None
