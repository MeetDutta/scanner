"""
SpecGuard Centralized Runtime Path Resolution Utility.
Supports Development Mode, PyInstaller Frozen Mode (onedir & onefile),
and Portable Zero-Install Windows Deployments.

Distinguishes between:
- Immutable Read-Only Application Resources (standards, rules, models, templates, web)
- Mutable Persistent User Data (database, uploads, reports, logs, cache)
"""

import os
import sys
import shutil
import logging
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger("SpecGuard.RuntimePaths")


def is_frozen() -> bool:
    """Returns True if the application is running inside a frozen PyInstaller bundle."""
    return getattr(sys, "frozen", False)


def get_app_dir() -> Path:
    """
    Returns the root directory where the application is installed or running.
    - Frozen: Parent directory of the executable (e.g. C:\\SpecGuard).
    - Development: Root workspace directory containing app.py and pyproject.toml.
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent
    # In development mode, walk up from this file: specguard/core/runtime_paths.py -> root
    return Path(__file__).resolve().parent.parent.parent


def get_bundle_dir() -> Path:
    """
    Returns the internal PyInstaller extraction directory (_MEIPASS or _internal),
    or the repo root in development mode.
    """
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass).resolve()
        # In onedir mode without _MEIPASS set, check _internal
        internal_dir = get_app_dir() / "_internal"
        if internal_dir.exists():
            return internal_dir
        return get_app_dir()
    return get_app_dir()


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
    1. `DOCREADY_DATA_DIR` environment variable (if specified for Render/Docker persistent mounts)
    2. `<app_dir>/data` (Ideal for portable USB / folder installation)
    3. `%LOCALAPPDATA%/DocReady/data` (Fallback if app_dir is read-only, e.g. Program Files)
    4. `~/.docready/data` (Linux/macOS fallback if app_dir is read-only)
    5. Automatically migrates/preserves existing data from SpecGuard if present
    """
    env_data_dir = os.environ.get("DOCREADY_DATA_DIR")
    if env_data_dir:
        target = Path(env_data_dir).resolve()
        target.mkdir(parents=True, exist_ok=True)
        if subdir:
            sub = target / subdir
            sub.mkdir(parents=True, exist_ok=True)
            return sub
        return target

    app_dir = get_app_dir()
    candidate = app_dir / "data"

    if _is_writable(candidate):
        target = candidate
    else:
        # Fallback to user profile directory
        if sys.platform == "win32":
            local_appdata = Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local")))
            target = local_appdata / "DocReady" / "data"
            legacy_target = local_appdata / "SpecGuard" / "data"
            # Migrate legacy if exists and new does not
            if legacy_target.exists() and not target.exists():
                try:
                    shutil.copytree(legacy_target, target)
                except Exception:
                    target = legacy_target
        else:
            home = Path.home()
            target = home / ".docready" / "data"
            legacy_target = home / ".specguard" / "data"
            if legacy_target.exists() and not target.exists():
                try:
                    shutil.copytree(legacy_target, target)
                except Exception:
                    target = legacy_target
        target.mkdir(parents=True, exist_ok=True)

    if subdir:
        sub = target / subdir
        sub.mkdir(parents=True, exist_ok=True)
        return sub
    return target


def get_resource_dir(resource_name: str) -> Path:
    """
    Locates an immutable application resource directory (models, standards, templates, web, etc.).
    Searches:
    1. `<app_dir>/resources/<resource_name>`
    2. `<bundle_dir>/resources/<resource_name>`
    3. `<app_dir>/<resource_name>`
    4. `<bundle_dir>/<resource_name>`
    5. `<bundle_dir>/specguard/<resource_name>`
    """
    app_dir = get_app_dir()
    bundle_dir = get_bundle_dir()

    candidates = [
        app_dir / "resources" / resource_name,
        bundle_dir / "resources" / resource_name,
        app_dir / resource_name,
        bundle_dir / resource_name,
        bundle_dir / "specguard" / resource_name,
    ]

    for cand in candidates:
        if cand.exists():
            return cand

    # Default fallback: return primary expected path even if empty/pending creation
    return app_dir / "resources" / resource_name if is_frozen() else app_dir / resource_name


def get_database_path() -> Path:
    """
    Returns the persistent SQLite database path.
    Preserves existing data in data/database/docready.db, data/docready.db,
    or legacy data/database/specguard.db, data/specguard.db.
    """
    data_dir = get_data_dir()
    db_folder = data_dir / "database"
    
    # Priority order for database resolution
    candidates = [
        db_folder / "docready.db",
        data_dir / "docready.db",
        db_folder / "specguard.db",
        data_dir / "specguard.db",
    ]
    for c in candidates:
        if c.exists():
            return c

    # Default for new installations
    db_folder.mkdir(parents=True, exist_ok=True)
    return db_folder / "docready.db"


def get_log_file_path() -> Path:
    """Returns the path to the primary runtime log file."""
    logs_dir = get_data_dir("logs")
    # If legacy log exists, prefer it or use docready.log
    if (logs_dir / "docready.log").exists():
        return logs_dir / "docready.log"
    if (logs_dir / "specguard.log").exists():
        return logs_dir / "specguard.log"
    return logs_dir / "docready.log"


def get_reports_dir() -> Path:
    """Returns the persistent reports output directory."""
    data_dir = get_data_dir()
    reports_dir = data_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    return reports_dir


def get_repository_dir() -> Path:
    """
    Returns the persistent document comparison repository directory.
    Preserves existing repository in app_dir if present and writable,
    otherwise uses data_dir/repository.
    """
    base_repo = get_app_dir() / "repository"
    if base_repo.exists() and _is_writable(base_repo):
        return base_repo
    data_repo = get_data_dir() / "repository"
    data_repo.mkdir(parents=True, exist_ok=True)
    return data_repo


def get_uploads_dir() -> Path:
    """Returns the persistent uploaded files directory."""
    data_dir = get_data_dir()
    uploads_dir = data_dir / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    return uploads_dir


def get_web_dir() -> Path:
    """Locates the bundled offline web frontend directory (static, templates)."""
    bundle_dir = get_bundle_dir()
    candidates = [
        get_app_dir() / "resources" / "web",
        bundle_dir / "resources" / "web",
        bundle_dir / "web",
        bundle_dir / "specguard" / "web",
        get_app_dir() / "specguard" / "web",
    ]
    for cand in candidates:
        if cand.exists() and (cand / "templates" / "index.html").exists():
            return cand
    return get_app_dir() / "specguard" / "web"


def detect_tesseract() -> Optional[Path]:
    """
    Safely locates a local portable or system Tesseract OCR executable.
    Does NOT require Tesseract for normal operation (OpenCV morphological engine is built-in).
    """
    app_dir = get_app_dir()
    candidates: List[Path] = [
        app_dir / "resources" / "tesseract" / ("tesseract.exe" if sys.platform == "win32" else "tesseract"),
        app_dir / "tesseract" / ("tesseract.exe" if sys.platform == "win32" else "tesseract"),
    ]
    for cand in candidates:
        if cand.exists() and os.access(cand, os.X_OK):
            return cand

    # Check system PATH
    system_tess = shutil.which("tesseract")
    if system_tess:
        return Path(system_tess)

    return None
