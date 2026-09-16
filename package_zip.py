"""
SpecGuard Portable ZIP Packager and Checksum Generator.
Assembles the complete portable distribution folder and creates a timestamped,
SHA-256 verified ZIP archive ready for release.
"""

import os
import sys
import shutil
import zipfile
import hashlib
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DIST_DIR = ROOT_DIR / "dist"
VERSION = "1.0.0"
PACKAGE_NAME = f"SpecGuard-v{VERSION}-Windows-x64-Portable"
ZIP_FILENAME = f"{PACKAGE_NAME}.zip"
SHA_FILENAME = f"{PACKAGE_NAME}.zip.sha256"


def calculate_sha256(file_path: Path) -> str:
    """Computes SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def copy_tree_filtered(src: Path, dst: Path, ignore_patterns=None):
    """Copies directory recursively while excluding dev caches, git, and pyc files."""
    if not src.exists():
        return
    if ignore_patterns is None:
        ignore_patterns = ["__pycache__", "*.pyc", "*.pyo", ".DS_Store", ".git*"]

    def _ignore(folder, names):
        ignored = set()
        for name in names:
            if name in ["__pycache__", ".git", ".pytest_cache", ".venv"]:
                ignored.add(name)
            elif name.endswith((".pyc", ".pyo", ".DS_Store")):
                ignored.add(name)
        return ignored

    shutil.copytree(src, dst, ignore=_ignore, dirs_exist_ok=True)


def assemble_portable_directory():
    """Assembles the final portable folder structure."""
    print("=" * 64)
    print("   SpecGuard Portable Package Assembler & ZIP Generator")
    print("=" * 64)

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    staging_root = DIST_DIR / "staging"
    target_app_dir = staging_root / "SpecGuard"

    if staging_root.exists():
        shutil.rmtree(staging_root)
    target_app_dir.mkdir(parents=True, exist_ok=True)

    print(f"Staging Directory: {target_app_dir}")

    # 1. Copy PyInstaller onedir output if exists
    pyinstaller_dist = DIST_DIR / "SpecGuard"
    if pyinstaller_dist.exists():
        print("Copying compiled PyInstaller binary and _internal dependencies...")
        for item in pyinstaller_dist.iterdir():
            dest = target_app_dir / item.name
            if item.is_dir():
                copy_tree_filtered(item, dest)
            else:
                shutil.copy2(item, dest)
        if (target_app_dir / "SpecGuard").exists() and not (target_app_dir / "SpecGuard.exe").exists():
            shutil.copy2(target_app_dir / "SpecGuard", target_app_dir / "SpecGuard.exe")
        shutil.copy2(ROOT_DIR / "portable_launcher.py", target_app_dir / "portable_launcher.py")
    else:
        print("Note: dist/SpecGuard not compiled yet. Assembling portable layout with launcher...")
        shutil.copy2(ROOT_DIR / "portable_launcher.py", target_app_dir / "portable_launcher.py")


    # 2. Copy Root User Files
    files_to_copy = [
        ("Launch_SpecGuard.bat", "Launch_SpecGuard.bat"),
        ("README.txt", "README.txt"),
        ("LICENSE.txt", "LICENSE.txt"),
        ("PORTABLE_DEPLOYMENT.md", "PORTABLE_DEPLOYMENT.md"),
        ("TROUBLESHOOTING.md", "TROUBLESHOOTING.md"),
    ]
    for src_name, dst_name in files_to_copy:
        src_path = ROOT_DIR / src_name
        if src_path.exists():
            shutil.copy2(src_path, target_app_dir / dst_name)
            print(f"  Copied {src_name}")

    # 3. Create Resources Folder
    resources_dir = target_app_dir / "resources"
    resources_dir.mkdir(parents=True, exist_ok=True)

    resource_mappings = [
        (ROOT_DIR / "models", resources_dir / "models"),
        (ROOT_DIR / "standards", resources_dir / "standards"),
        (ROOT_DIR / "rules", resources_dir / "rules"),
        (ROOT_DIR / "templates", resources_dir / "templates"),
        (ROOT_DIR / "specguard" / "web", resources_dir / "web"),
        (ROOT_DIR / "demo_samples", resources_dir / "demo_samples"),
    ]
    for src, dst in resource_mappings:
        if src.exists():
            copy_tree_filtered(src, dst)
            print(f"  Bundled resource: {src.name} -> resources/{src.name}")

    # 4. Initialize Data Folders (with .gitkeep for archive retention)
    data_dir = target_app_dir / "data"
    subdirs = ["database", "uploads", "reports", "logs", "cache"]
    for s in subdirs:
        sub_path = data_dir / s
        sub_path.mkdir(parents=True, exist_ok=True)
        (sub_path / ".gitkeep").write_text("", encoding="utf-8")
    print("  Initialized persistent writable data/ subdirectories.")

    # 5. Copy Uninstall Utilities
    uninstall_dir = target_app_dir / "uninstall"
    uninstall_dir.mkdir(parents=True, exist_ok=True)
    uninst_script = ROOT_DIR / "uninstall" / "Remove_UserData.bat"
    if uninst_script.exists():
        shutil.copy2(uninst_script, uninstall_dir / "Remove_UserData.bat")
        print("  Copied uninstallation utility: uninstall/Remove_UserData.bat")

    # 6. Create ZIP Archive
    zip_path = DIST_DIR / ZIP_FILENAME
    if zip_path.exists():
        zip_path.unlink()

    print(f"\nCompressing portable archive to {ZIP_FILENAME}...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
        for file in staging_root.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(staging_root)
                zipf.write(file, arcname)

    # 7. Compute SHA-256 Checksum
    sha256 = calculate_sha256(zip_path)
    sha_path = DIST_DIR / SHA_FILENAME
    sha_path.write_text(f"{sha256}  {ZIP_FILENAME}\n", encoding="utf-8")

    # 8. Clean Staging
    shutil.rmtree(staging_root)

    zip_size_mb = zip_path.stat().st_size / (1024 * 1024)

    print("\n" + "=" * 64)
    print("   PORTABLE DISTRIBUTION PACKAGE CREATED SUCCESSFULLY")
    print("=" * 64)
    print(f"Archive File : {zip_path}")
    print(f"Archive Size : {zip_size_mb:.2f} MB")
    print(f"SHA-256 Hash : {sha256}")
    print(f"Checksum File: {sha_path}")
    print("=" * 64)
    return zip_path, sha_path, sha256


if __name__ == "__main__":
    assemble_portable_directory()
