"""
Hardware Awareness and Device Detection for SpecGuard Deep Learning Engine.
Detects CPU, Apple Silicon (MPS), or CUDA GPU, and recommends optimal batch sizes and device parameters.
"""

import os
try:
    import psutil
except ImportError:
    psutil = None
import torch
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class HardwareProfile:
    device: str
    device_name: str
    cpu_cores: int
    ram_gb: float
    gpu_available: bool
    gpu_name: str
    recommended_batch_size: int
    recommendations: str


class HardwareManager:
    """Provides local hardware profiling and training parameter recommendations."""

    @staticmethod
    def get_profile() -> HardwareProfile:
        cpu_cores = os.cpu_count() or 4
        if psutil:
            ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 1)
        else:
            try:
                ram_gb = round((os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')) / (1024 ** 3), 1)
            except Exception:
                ram_gb = 16.0

        # Detect optimal computing device
        if torch.cuda.is_available():
            device = "cuda"
            gpu_name = torch.cuda.get_device_name(0)
            gpu_available = True
            batch_size = 16
            recommendations = f"NVIDIA GPU detected ({gpu_name}). CUDA acceleration active."
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            device = "mps"
            gpu_name = "Apple Silicon GPU (Metal Performance Shaders)"
            gpu_available = True
            batch_size = 8
            recommendations = "Apple Silicon MPS acceleration active. Hardware acceleration enabled."
        else:
            device = "cpu"
            gpu_name = "None (CPU Only)"
            gpu_available = False
            batch_size = 4
            recommendations = "No GPU detected. Training will run locally on CPU (recommend batch size 4)."

        return HardwareProfile(
            device=device,
            device_name=gpu_name if gpu_available else "CPU",
            cpu_cores=cpu_cores,
            ram_gb=ram_gb,
            gpu_available=gpu_available,
            gpu_name=gpu_name,
            recommended_batch_size=batch_size,
            recommendations=recommendations
        )

    @staticmethod
    def get_torch_device(preferred: str = "auto") -> torch.device:
        if preferred == "auto":
            if torch.cuda.is_available():
                return torch.device("cuda")
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return torch.device("mps")
            return torch.device("cpu")
        return torch.device(preferred)
