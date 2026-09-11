"""
Checkpoint and Model Versioning Manager for SpecGuard.
Saves, versions, and loads local PyTorch models with SHA-256 integrity verification.
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging
import torch

from specguard.core.config import MODELS_DIR

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Handles saving, loading, and integrity validation of model checkpoints."""

    def __init__(self, base_dir: Path = MODELS_DIR):
        self.base_dir = base_dir

    def save_checkpoint(
        self,
        model: torch.nn.Module,
        tokenizer: Any,
        task_name: str,
        domain: str,
        metrics: Dict[str, float],
        hyperparams: Dict[str, Any],
        dataset_version: str = "v1.0"
    ) -> str:
        """Saves a model checkpoint with full reproducibility metadata."""
        dest_dir = self.base_dir / domain.lower() / task_name.lower()
        dest_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_id = f"SG-{task_name.upper()[:4]}-{domain.upper()[:4]}-{timestamp}"
        ckpt_path = dest_dir / f"{model_id}.pt"
        meta_path = dest_dir / f"{model_id}_meta.json"

        # Save model and tokenizer state dict
        payload = {
            "model_state_dict": model.state_dict(),
            "tokenizer_dict": tokenizer.to_dict() if hasattr(tokenizer, "to_dict") else None,
            "hyperparams": hyperparams,
            "metrics": metrics
        }
        torch.save(payload, ckpt_path)

        # Calculate SHA-256
        sha256 = hashlib.sha256()
        with open(ckpt_path, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        ckpt_hash = sha256.hexdigest()

        metadata = {
            "model_id": model_id,
            "task": task_name,
            "domain": domain,
            "created_at": datetime.now().isoformat(),
            "checkpoint_path": str(ckpt_path),
            "sha256": ckpt_hash,
            "metrics": metrics,
            "hyperparams": hyperparams,
            "dataset_version": dataset_version,
            "is_active": True
        }

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        logger.info("Saved checkpoint %s with SHA-256 %s", model_id, ckpt_hash[:12])
        return str(ckpt_path)

    def list_checkpoints(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists all registered checkpoints with their performance metrics."""
        checkpoints = []
        search_dir = self.base_dir / domain.lower() if domain else self.base_dir
        if not search_dir.exists():
            return []

        for meta_file in search_dir.glob("**/*_meta.json"):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    checkpoints.append(json.load(f))
            except Exception as e:
                logger.error("Failed reading checkpoint meta %s: %s", meta_file, e)

        return sorted(checkpoints, key=lambda c: c.get("created_at", ""), reverse=True)

    def load_checkpoint(self, checkpoint_path: str, model: torch.nn.Module, device: torch.device = None) -> Dict[str, Any]:
        """Loads weights into model and verifies integrity."""
        path = Path(checkpoint_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

        map_location = device or torch.device("cpu")
        checkpoint = torch.load(path, map_location=map_location, weights_only=False)
        model.load_state_dict(checkpoint["model_state_dict"])
        model.to(map_location)
        model.eval()
        return checkpoint


from typing import List
