"""
Pre-flight Startup Verification and Diagnostics for SpecGuard.
Performs 100% offline verification of Python runtime, essential packages,
hardware acceleration (MPS/CUDA/CPU), local storage, and database paths.
"""

import sys
import os
import shutil
import importlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple
import logging

from specguard.core.config import (
    BASE_DIR, DATA_DIR, MODELS_DIR, STANDARDS_DIR, REPORTS_DIR
)

logger = logging.getLogger(__name__)

REPO_DIR = BASE_DIR / "repository"
DATASETS_DIR = BASE_DIR / "datasets"

REQUIRED_PACKAGES = [
    ("PySide6", "PySide6 GUI Framework"),
    ("fitz", "PyMuPDF Document Parser"),
    ("cv2", "OpenCV Computer Vision Engine"),
    ("docx", "python-docx Document Parser"),
    ("openpyxl", "OpenPyXL Spreadsheet Parser"),
    ("numpy", "NumPy Numerical Computing"),
    ("pandas", "Pandas Tabular Processing"),
    ("yaml", "PyYAML Standards & Template Parser"),
]

OPTIONAL_PACKAGES = [
    ("torch", "PyTorch Deep Learning Engine (Optional ML)"),
    ("onnx", "ONNX Model Serialization (Optional ML)"),
    ("onnxruntime", "ONNX Runtime Offline Inference Engine (Optional ML)"),
    ("sklearn", "Scikit-Learn Evaluation Tools (Research)"),
    ("scipy", "SciPy Scientific Algorithms (Research)"),
    ("psutil", "Hardware Telemetry (Research)"),
]


@dataclass
class StartupReport:
    """Structured pre-flight diagnostic report."""
    is_ready: bool
    python_version: str
    packages: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    hardware: Dict[str, Any] = field(default_factory=dict)
    directories: Dict[str, bool] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def verify_environment() -> StartupReport:
    """
    Executes a complete offline pre-flight verification.
    Guaranteed zero external network calls.
    """
    errors: List[str] = []
    warnings: List[str] = []
    pkg_status: Dict[str, Dict[str, Any]] = {}

    # 1. Python Version Check
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info < (3, 9):
        errors.append(f"Python 3.9+ required. Detected version: {py_ver}")

    # 2. Package Verification
    for mod_name, desc in REQUIRED_PACKAGES:
        try:
            mod = importlib.import_module(mod_name)
            ver = getattr(mod, "__version__", "Installed")
            pkg_status[mod_name] = {"installed": True, "version": ver, "description": desc}
        except ImportError as e:
            pkg_status[mod_name] = {"installed": False, "version": None, "description": desc}
            errors.append(f"Required package missing: {mod_name} ({desc}) - Error: {e}")

    for mod_name, desc in OPTIONAL_PACKAGES:
        try:
            mod = importlib.import_module(mod_name)
            ver = getattr(mod, "__version__", "Installed")
            pkg_status[mod_name] = {"installed": True, "version": ver, "description": desc}
        except ImportError:
            pkg_status[mod_name] = {"installed": False, "version": None, "description": desc}
            warnings.append(f"Optional package '{mod_name}' not installed. Associated features will use local fallbacks.")

    # 3. Hardware Acceleration
    hw_info: Dict[str, Any] = {
        "device": "cpu",
        "device_name": "CPU",
        "cuda_available": False,
        "mps_available": False,
        "cpu_cores": os.cpu_count() or 1,
    }

    try:
        import torch
        if torch.cuda.is_available():
            hw_info["cuda_available"] = True
            hw_info["device"] = "cuda"
            hw_info["device_name"] = torch.cuda.get_device_name(0)
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            hw_info["mps_available"] = True
            hw_info["device"] = "mps"
            hw_info["device_name"] = "Apple Silicon MPS (Metal Performance Shaders)"
        else:
            hw_info["device"] = "cpu"
            hw_info["device_name"] = f"CPU ({hw_info['cpu_cores']} cores)"
    except Exception as e:
        warnings.append(f"Could not probe PyTorch hardware backend: {e}")

    # 4. Storage and Directory Structure
    dir_status: Dict[str, bool] = {}
    crucial_dirs = [
        ("Base", BASE_DIR),
        ("Data", DATA_DIR),
        ("Models", MODELS_DIR),
        ("Standards", STANDARDS_DIR),
        ("Reports", REPORTS_DIR),
        ("Repository", REPO_DIR),
        ("Datasets", DATASETS_DIR),
    ]

    for name, p in crucial_dirs:
        try:
            p.mkdir(parents=True, exist_ok=True)
            dir_status[name] = p.exists() and os.access(p, os.W_OK)
            if not dir_status[name]:
                errors.append(f"Directory {name} ({p}) is not writable.")
        except Exception as e:
            dir_status[name] = False
            errors.append(f"Failed to create/access directory {name} ({p}): {e}")

    # Check disk space
    try:
        total, used, free = shutil.disk_usage(BASE_DIR)
        free_gb = free / (1024 ** 3)
        hw_info["free_storage_gb"] = round(free_gb, 2)
        if free_gb < 1.0:
            warnings.append(f"Low local disk space: {free_gb:.1f} GB remaining.")
    except Exception:
        hw_info["free_storage_gb"] = "Unknown"

    is_ready = len(errors) == 0

    if not is_ready:
        logger.error("Startup verification failed with %d errors:\n%s", len(errors), "\n".join(errors))
    else:
        logger.info("Startup verification passed: 100%% offline environment verified on %s.", hw_info["device_name"])

    return StartupReport(
        is_ready=is_ready,
        python_version=py_ver,
        packages=pkg_status,
        hardware=hw_info,
        directories=dir_status,
        warnings=warnings,
        errors=errors
    )
