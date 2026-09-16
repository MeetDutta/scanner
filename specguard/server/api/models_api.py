"""
Machine Learning and Deep Learning Training Management API for SpecGuard.
Manages local model checkpoints, ONNX graphs, cryptographic SHA-256 verification,
hardware profiling, and dataset health checks without cloud AI dependencies.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from dataclasses import asdict
import logging

from specguard.models.registry import ModelRegistry
from specguard.training.hardware import HardwareManager
from specguard.training.dataset_validator import DatasetValidator
from specguard.training.annotation_manager import AnnotationManager

logger = logging.getLogger("SpecGuard.API.Models")
router = APIRouter(prefix="/models", tags=["models"])


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

    # Enrich model data with real service statuses
    for m in models:
        m["service_status"] = statuses.get(m["model_id"], "Standby")

    return models


@router.get("/hardware")
def get_hardware_profile() -> Dict[str, Any]:
    """Inspects local hardware, CPU cores, RAM, and Metal (MPS) / CUDA GPU acceleration."""
    profile = HardwareManager.get_profile()
    return asdict(profile)


@router.get("/dataset-health")
def get_dataset_health(domain: Optional[str] = Query(None)) -> Dict[str, Any]:
    """Validates local dataset health, partition integrity, and prevents synthetic leakage."""
    annot_mgr = AnnotationManager()
    validator = DatasetValidator(annot_mgr)
    report = validator.validate_dataset(domain)
    return asdict(report)


@router.post("/{model_id}/activate")
def activate_model(model_id: str) -> Dict[str, Any]:
    """Activates an offline model checkpoint in the registry."""
    registry = ModelRegistry()
    success = registry.activate_model(model_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"Could not activate model {model_id}.")
    return {"status": "success", "message": f"Model {model_id} activated."}


@router.post("/{model_id}/deactivate")
def deactivate_model(model_id: str) -> Dict[str, Any]:
    """Deactivates a model in the registry."""
    registry = ModelRegistry()
    success = registry.deactivate_model(model_id)
    return {"status": "success", "message": f"Model {model_id} deactivated."}


@router.post("/{model_id}/verify-hash")
def verify_model_integrity(model_id: str) -> Dict[str, Any]:
    """Verifies the SHA-256 cryptographic digest of a model artifact."""
    registry = ModelRegistry()
    return registry.verify_model_hash(model_id)


@router.get("/compare/{model_id_1}/{model_id_2}")
def compare_model_versions(model_id_1: str, model_id_2: str) -> Dict[str, Any]:
    """Compares metrics, architecture, and accuracy across two model versions."""
    registry = ModelRegistry()
    try:
        return registry.compare_versions(model_id_1, model_id_2)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Model comparison failed: {e}")
