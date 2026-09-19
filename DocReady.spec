# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Specification for DocReady Windows Portable Edition.
Builds an onedir distribution containing DocReady.exe, Python runtime,
native DLLs, and bundled offline resources.
"""

import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata

block_cipher = None
ROOT_DIR = Path(SPECPATH).resolve()

# 1. Collect Datas & Binaries for complex native packages
datas = [
    (str(ROOT_DIR / "specguard" / "web"), "resources/web"),
    (str(ROOT_DIR / "specguard" / "web"), "specguard/web"),
    (str(ROOT_DIR / "docready"), "docready"),
    (str(ROOT_DIR / "standards"), "resources/standards"),
    (str(ROOT_DIR / "standards"), "standards"),
    (str(ROOT_DIR / "rules"), "resources/rules"),
    (str(ROOT_DIR / "rules"), "rules"),
    (str(ROOT_DIR / "templates"), "resources/templates"),
    (str(ROOT_DIR / "templates"), "templates"),
    (str(ROOT_DIR / "models"), "resources/models"),
    (str(ROOT_DIR / "demo_samples"), "resources/demo_samples"),
]

binaries = []
hiddenimports = [
    # Top-level packages
    "docready",
    "specguard",
    # Uvicorn ASGI runtime
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    # FastAPI & Starlette
    "fastapi",
    "fastapi.staticfiles",
    "fastapi.responses",
    "fastapi.middleware.cors",
    "starlette",
    "starlette.middleware",
    "starlette.middleware.cors",
    "starlette.staticfiles",
    "starlette.responses",
    "multipart",
    "python_multipart",
    # Pydantic & AnyIO
    "pydantic",
    "pydantic_core",
    "anyio",
    "anyio._backends",
    "anyio._backends._asyncio",
    "sniffio",
    # PyMuPDF
    "fitz",
    "fitz.fitz",
    # OpenCV
    "cv2",
    # Word, Excel, Data
    "docx",
    "openpyxl",
    "numpy",
    "pandas",
    "yaml",
    "sqlite3",
    # PySide6 (legacy desktop fallback)
    "PySide6",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
]

# Collect submodules and data for PyMuPDF, OpenCV, Docx, FastAPI
for pkg in ["uvicorn", "fastapi", "fitz", "docx", "specguard", "docready"]:
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
        datas.extend(pkg_datas)
        binaries.extend(pkg_binaries)
        hiddenimports.extend(pkg_hidden)
    except Exception:
        pass

# Deduplicate
hiddenimports = sorted(list(set(hiddenimports)))

a = Analysis(
    ['portable_launcher.py'],
    pathex=[str(ROOT_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "notebook",
        "ipykernel",
        "test",
        "tests",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DocReady',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Shows console window with diagnostics during startup
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT_DIR / "specguard" / "web" / "static" / "icon.ico") if (ROOT_DIR / "specguard" / "web" / "static" / "icon.ico").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DocReady',
)
