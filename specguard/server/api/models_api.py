"""
Model Inspection & Hardware Diagnostics API for SpecGuard.
Lists active offline inference models and reports local compute capabilities
(CPU cores, RAM, Metal/MPS, CUDA) without training laboratory endpoints.
"""

import os
from typing import Dict, Any, List, Optional
import logging
from fastapi import APIRouter, Query
import torch

try:
    import psutil
except ImportError:
    psutil = None

from specguard.models.registry import ModelRegistry

logger = logging.getLogger("SpecGuard.API.Models")
router = APIRouter(prefix="/models", tags=["models"])


def _get_hardware_profile() -> Dict[str, Any]:
    """Inspects local hardware without training-specific dependencies."""
    cpu_cores = os.cpu_count() or 4
    if psutil:
        ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 1)
    else:
        try:
            ram_gb = round((os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')) / (1024 ** 3), 1)
        except Exception:
            ram_gb = 16.0

    if torch.cuda.is_available():
        device = "cuda"
        gpu_name = torch.cuda.get_device_name(0)
        gpu_available = True
        recommendations = f"NVIDIA GPU detected ({gpu_name}). CUDA acceleration active."
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = "mps"
        gpu_name = "Apple Silicon GPU (Metal Performance Shaders)"
        gpu_available = True
        recommendations = "Apple Silicon MPS acceleration active."
    else:
        device = "cpu"
        gpu_name = "None (CPU Only)"
        gpu_available = False
        recommendations = "CPU execution active."

    return {
        "device": device,
        "device_name": gpu_name if gpu_available else "CPU",
        "cpu_cores": cpu_cores,
        "ram_gb": ram_gb,
        "gpu_available": gpu_available,
        "gpu_name": gpu_name,
        "recommendations": recommendations,
    }


@router.get("")
def list_models(
    task: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    active_only: bool = Query(False)
) -> List[Dict[str, Any]]:
    """Lists registered PyTorch and ONNX models from the local model registry."""
    registry = ModelRegistry()
    status_filter = "ACTIVE" if active_only else None
    models = registry.list_models(task=task, domain=domain, status=status_filter)
    statuses = registry.get_all_statuses()

    for m in models:
        m["service_status"] = statuses.get(m["model_id"], "Standby")

    return models


@router.get("/hardware")
def get_hardware_profile() -> Dict[str, Any]:
    """Inspects local hardware, CPU cores, RAM, and Metal (MPS) / CUDA GPU acceleration."""
    return _get_hardware_profile()
