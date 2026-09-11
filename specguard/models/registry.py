"""
Local Model Management and Service Interfaces for SpecGuard.
Enables pluggable PyTorch / ONNX models with deterministic local fallbacks.
Strictly offline: Zero automatic downloads.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import logging
from pathlib import Path
from specguard.core.config import MODELS_DIR

logger = logging.getLogger(__name__)


class BaseModelService(ABC):
    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def get_status(self) -> str:
        pass


class NLPModelService(BaseModelService):
    """Local NLP and Entity Recognition Service."""
    def __init__(self, model_name: str = "specguard-nlp-v1"):
        self.model_name = model_name
        self.model_path = MODELS_DIR / f"{model_name}.onnx"

    def is_available(self) -> bool:
        return self.model_path.exists()

    def get_status(self) -> str:
        if self.is_available():
            return "Active (Local Model Loaded)"
        return "Not Installed (Using Deterministic Fallback)"


class EngineeringModelService(BaseModelService):
    """Local Deep Learning Parameter & Relation Extraction Service."""
    def __init__(self, model_name: str = "specguard-eng-v1"):
        self.model_name = model_name
        self.model_path = MODELS_DIR / f"{model_name}.onnx"

    def is_available(self) -> bool:
        return self.model_path.exists()

    def get_status(self) -> str:
        if self.is_available():
            return "Active (Local Model Loaded)"
        return "Not Installed (Using Deterministic Rule Engine)"


class ModelRegistry:
    """Registry maintaining metadata and status of all local AI models."""
    def __init__(self):
        self.nlp = NLPModelService()
        self.engineering = EngineeringModelService()

    def get_all_statuses(self) -> Dict[str, str]:
        return {
            "NLP Entity Model": self.nlp.get_status(),
            "Engineering Extraction Model": self.engineering.get_status()
        }
