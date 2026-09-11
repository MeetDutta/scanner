"""
Local Model Management and Dynamic Registry for SpecGuard.
Tracks trained PyTorch checkpoints and ONNX artifacts under models/ with SHA-256 integrity verification.
Supports dynamic activation, deactivation, version comparison, and inspection.
Strictly offline: Zero automatic internet downloads.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, timezone
import json
import hashlib
import shutil
import logging

from specguard.core.config import MODELS_DIR

logger = logging.getLogger(__name__)

REGISTRY_FILE = MODELS_DIR / "model_registry.json"
CHECKPOINTS_DIR = MODELS_DIR / "checkpoints"
ONNX_DIR = MODELS_DIR / "onnx"

# Ensure directories exist
for d in [MODELS_DIR, CHECKPOINTS_DIR, ONNX_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def calculate_sha256(file_path: Path) -> str:
    """Calculates the SHA-256 digest of a local file."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


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
    """
    Dynamic Registry maintaining local ML model checkpoints, ONNX graphs,
    evaluation metrics, and cryptographic integrity hashes.
    """
    def __init__(self, registry_file: Path = REGISTRY_FILE):
        self.registry_file = registry_file
        self.nlp = NLPModelService()
        self.engineering = EngineeringModelService()
        self._ensure_registry_file()
        self.scan_and_sync_artifacts()

    def _ensure_registry_file(self):
        if not self.registry_file.exists():
            initial_data = {"models": {}, "version": "1.0.0", "last_updated": datetime.now(timezone.utc).isoformat()}
            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump(initial_data, f, indent=2)

    def _read_registry(self) -> Dict[str, Any]:
        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed reading model registry: %s", e)
            return {"models": {}, "version": "1.0.0"}

    def _write_registry(self, data: Dict[str, Any]):
        data["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def scan_and_sync_artifacts(self):
        """Scans models/checkpoints and models/onnx to discover unindexed models."""
        data = self._read_registry()
        models = data.setdefault("models", {})
        updated = False

        # Scan checkpoints
        for meta_file in MODELS_DIR.glob("**/*_meta.json"):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                m_id = meta.get("model_id")
                if m_id and m_id not in models:
                    ckpt_p = meta.get("checkpoint_path")
                    sha = meta.get("sha256")
                    if ckpt_p and Path(ckpt_p).exists() and not sha:
                        sha = calculate_sha256(Path(ckpt_p))
                    
                    models[m_id] = {
                        "model_id": m_id,
                        "model_name": meta.get("model_name", m_id),
                        "task": meta.get("task", "unknown"),
                        "domain": meta.get("domain", "all"),
                        "version": meta.get("version", "1.0.0"),
                        "dataset_version": meta.get("dataset_version", "v1.0"),
                        "training_run_id": meta.get("training_run_id", "RUN-UNKNOWN"),
                        "framework": meta.get("framework", "PyTorch"),
                        "architecture": meta.get("architecture", "CustomNN"),
                        "device": meta.get("device", "cpu"),
                        "checkpoint_path": ckpt_p,
                        "onnx_path": meta.get("onnx_path"),
                        "created_at": meta.get("created_at", datetime.now(timezone.utc).isoformat()),
                        "sha256": sha or "UNVERIFIED",
                        "status": "ACTIVE" if meta.get("is_active", True) else "INACTIVE",
                        "metrics": meta.get("metrics", {}),
                        "parity_verified": meta.get("parity_verified", False),
                        "parity_max_diff": meta.get("parity_max_diff")
                    }
                    updated = True
            except Exception as e:
                logger.warning("Could not parse metadata file %s: %s", meta_file, e)

        if updated:
            self._write_registry(data)

    def register_model(
        self,
        model_id: str,
        model_name: str,
        task: str,
        domain: str,
        version: str,
        dataset_version: str,
        training_run_id: str,
        framework: str,
        architecture: str,
        device: str,
        checkpoint_path: Optional[str] = None,
        onnx_path: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
        parity_verified: bool = False,
        parity_max_diff: Optional[float] = None
    ) -> Dict[str, Any]:
        """Registers a newly trained model artifact with integrity validation."""
        sha256_hash = "NOT_STORED"
        if checkpoint_path and Path(checkpoint_path).exists():
            sha256_hash = calculate_sha256(Path(checkpoint_path))
        elif onnx_path and Path(onnx_path).exists():
            sha256_hash = calculate_sha256(Path(onnx_path))

        record = {
            "model_id": model_id,
            "model_name": model_name,
            "task": task,
            "domain": domain,
            "version": version,
            "dataset_version": dataset_version,
            "training_run_id": training_run_id,
            "framework": framework,
            "architecture": architecture,
            "device": device,
            "checkpoint_path": str(checkpoint_path) if checkpoint_path else None,
            "onnx_path": str(onnx_path) if onnx_path else None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "sha256": sha256_hash,
            "status": "ACTIVE",
            "metrics": metrics or {},
            "parity_verified": parity_verified,
            "parity_max_diff": parity_max_diff
        }

        data = self._read_registry()
        # Deactivate any other active model for the same task and domain
        for mid, m in data.get("models", {}).items():
            if m.get("task") == task and m.get("domain") == domain and m.get("status") == "ACTIVE":
                m["status"] = "INACTIVE"

        data.setdefault("models", {})[model_id] = record
        self._write_registry(data)
        logger.info("Registered model %s (%s, %s) with status ACTIVE", model_id, task, domain)
        return record

    def list_models(
        self,
        task: Optional[str] = None,
        domain: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Lists registered models matching optional filters."""
        data = self._read_registry()
        results = []
        for m in data.get("models", {}).values():
            if task and m.get("task") != task:
                continue
            if domain and m.get("domain") != domain and m.get("domain") != "all":
                continue
            if status and m.get("status") != status:
                continue
            results.append(m)
        return sorted(results, key=lambda x: x.get("created_at", ""), reverse=True)

    def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        data = self._read_registry()
        return data.get("models", {}).get(model_id)

    def get_active_model(self, task: str, domain: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Finds the currently active model for a given task and domain."""
        candidates = self.list_models(task=task, domain=domain, status="ACTIVE")
        if candidates:
            return candidates[0]
        # Try generic domain
        candidates = self.list_models(task=task, domain="all", status="ACTIVE")
        return candidates[0] if candidates else None

    def verify_model_hash(self, model_id: str) -> Dict[str, Any]:
        """Calculates actual on-disk SHA-256 and compares against registered value."""
        model = self.get_model(model_id)
        if not model:
            return {"valid": False, "reason": "Model not found in registry"}

        target_path = None
        if model.get("checkpoint_path") and Path(model["checkpoint_path"]).exists():
            target_path = Path(model["checkpoint_path"])
        elif model.get("onnx_path") and Path(model["onnx_path"]).exists():
            target_path = Path(model["onnx_path"])

        if not target_path:
            return {"valid": False, "reason": "Model artifact file missing from filesystem"}

        current_hash = calculate_sha256(target_path)
        expected_hash = model.get("sha256")

        match = (current_hash == expected_hash)
        return {
            "valid": match,
            "expected_sha256": expected_hash,
            "calculated_sha256": current_hash,
            "file_path": str(target_path),
            "reason": "OK" if match else "Cryptographic hash mismatch (corrupted or modified artifact)"
        }

    def activate_model(self, model_id: str) -> bool:
        """
        Activates a model after verifying file integrity.
        Rejects activation if file is missing or corrupted.
        """
        model = self.get_model(model_id)
        if not model:
            logger.error("Cannot activate: Model %s does not exist", model_id)
            return False

        # Verify hash before activation
        check = self.verify_model_hash(model_id)
        if not check["valid"]:
            logger.error("Cannot activate corrupted model %s: %s", model_id, check["reason"])
            return False

        data = self._read_registry()
        # Deactivate others for same task/domain
        for mid, m in data.get("models", {}).items():
            if m.get("task") == model.get("task") and m.get("domain") == model.get("domain") and mid != model_id:
                if m.get("status") == "ACTIVE":
                    m["status"] = "INACTIVE"

        data["models"][model_id]["status"] = "ACTIVE"
        self._write_registry(data)
        logger.info("Activated model %s", model_id)
        return True

    def deactivate_model(self, model_id: str) -> bool:
        data = self._read_registry()
        if model_id in data.get("models", {}):
            data["models"][model_id]["status"] = "INACTIVE"
            self._write_registry(data)
            logger.info("Deactivated model %s", model_id)
            return True
        return False

    def compare_versions(self, model_id_1: str, model_id_2: str) -> Dict[str, Any]:
        """Compares two models across hyperparameters, evaluation metrics, and integrity."""
        m1 = self.get_model(model_id_1)
        m2 = self.get_model(model_id_2)
        if not m1 or not m2:
            return {"error": "One or both models not found"}

        return {
            "model_1": {
                "id": m1["model_id"],
                "version": m1["version"],
                "created_at": m1["created_at"],
                "metrics": m1.get("metrics", {}),
                "architecture": m1.get("architecture"),
                "status": m1.get("status")
            },
            "model_2": {
                "id": m2["model_id"],
                "version": m2["version"],
                "created_at": m2["created_at"],
                "metrics": m2.get("metrics", {}),
                "architecture": m2.get("architecture"),
                "status": m2.get("status")
            }
        }

    def get_all_statuses(self) -> Dict[str, str]:
        """Backwards-compatible summary for legacy status views."""
        statuses = {
            "NLP Entity Model": self.nlp.get_status(),
            "Engineering Extraction Model": self.engineering.get_status()
        }
        for task in ["domain_classifier", "engineering_ner", "logical_contradiction"]:
            active = self.get_active_model(task)
            if active:
                statuses[task] = f"Active ({active['model_id']}, v{active['version']})"
        return statuses
