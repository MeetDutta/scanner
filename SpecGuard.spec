# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Specification for SpecGuard Windows Portable Edition.
Builds an onedir distribution containing SpecGuard.exe, Python runtime,
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
    "anyio._backends._asyncio",
    # Core Parsers & Math
    "fitz",
    "cv2",
    "docx",
    "openpyxl",
    "numpy",
    "pandas",
    "yaml",
    # ML & Inference (if installed)
    "torch",
    "onnx",
    "onnxruntime",
    "sklearn",
    "scipy",
    # SpecGuard Internal Modules
    "specguard",
    "specguard.core",
    "specguard.core.models",
    "specguard.core.runtime_paths",
    "specguard.core.config",
    "specguard.core.startup",
    "specguard.core.document_parser",
    "specguard.core.scanned_pipeline",
    "specguard.core.analyzers",
    "specguard.core.standards_engine",
    "specguard.core.compliance_engine",
    "specguard.core.drawing_engine",
    "specguard.core.cross_doc_comparator",
    "specguard.core.priority_scorer",
    "specguard.storage.database",
    "specguard.repository.manager",
    "specguard.repository.models",
    "specguard.templates.manager",
    "specguard.training.dataset_generator",
    "specguard.training.train_models",
    "specguard.training.onnx_exporter",
    "specguard.training.model_registry",
    "specguard.server.app",
    "specguard.server.api.dashboard",
    "specguard.server.api.analysis",
    "specguard.server.api.documents",
    "specguard.server.api.findings",
    "specguard.server.api.history",
    "specguard.server.api.reports",
    "specguard.server.api.standards",
    "specguard.server.api.models_api",
    "specguard.server.api.settings_api",
]

# Collect metadata and hooks for packages
packages_to_collect = ["uvicorn", "fastapi", "fitz", "cv2"]
for pkg in packages_to_collect:
    try:
        tmp_datas, tmp_binaries, tmp_hidden = collect_all(pkg)
        datas += tmp_datas
        binaries += tmp_binaries
        hiddenimports += tmp_hidden
    except Exception:
        pass

# Add metadata for starlette and anyio
for pkg in ["starlette", "anyio", "pydantic"]:
    try:
        datas += copy_metadata(pkg)
    except Exception:
        pass

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
    name='SpecGuard',
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
    name='SpecGuard',
)
