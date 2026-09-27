"""
Integration Tests for SpecGuard Model Registry and Cryptographic Integrity.
Verifies:
1. Dynamic model registration with SHA-256 calculation.
2. Safe model activation (blocks corrupted or missing models).
3. Cryptographic SHA-256 integrity check.
4. Side-by-side comparison of model versions.
Strictly offline.
"""

import pytest
import tempfile
from pathlib import Path
import torch

from specguard.models.registry import ModelRegistry, calculate_sha256


def test_model_registration_and_integrity_verification():
    """Tests registering a model checkpoint and verifying its SHA-256 digest."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        reg_file = Path(tmp_dir) / "registry.json"
        registry = ModelRegistry(registry_file=reg_file)

        # Create dummy checkpoint
        ckpt_path = Path(tmp_dir) / "test_model.pt"
        torch.save({"weights": torch.randn(10, 10)}, ckpt_path)
        expected_sha = calculate_sha256(ckpt_path)

        reg_data = registry.register_model(
            model_id="SG-TEST-001",
            model_name="TestDomainModel",
            task="domain_classifier",
            domain="mechanical",
            version="1.0.0",
            dataset_version="v1.0",
            training_run_id="RUN-TEST-01",
            framework="PyTorch",
            architecture="DomainClassifierNet",
            device="cpu",
            checkpoint_path=str(ckpt_path)
        )

        assert reg_data["model_id"] == "SG-TEST-001"
        assert reg_data["sha256"] == expected_sha
        assert reg_data["status"] == "ACTIVE"

        # Verify hash matches
        verify_res = registry.verify_model_hash("SG-TEST-001")
        assert verify_res["valid"] is True
        assert verify_res["reason"] == "OK"


def test_activation_blocks_corrupted_model():
    """Activation must be rejected if the on-disk file hash does not match registered hash."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        reg_file = Path(tmp_dir) / "registry.json"
        registry = ModelRegistry(registry_file=reg_file)

        ckpt_path = Path(tmp_dir) / "corrupt_model.pt"
        ckpt_path.write_bytes(b"original valid model weights")

        registry.register_model(
            model_id="SG-CORRUPT-001",
            model_name="CorruptModel",
            task="domain_classifier",
            domain="electrical",
            version="1.0.0",
            dataset_version="v1.0",
            training_run_id="RUN-02",
            framework="PyTorch",
            architecture="Net",
            device="cpu",
            checkpoint_path=str(ckpt_path)
        )

        # Deactivate
        registry.deactivate_model("SG-CORRUPT-001")

        # Corrupt file on disk
        ckpt_path.write_bytes(b"tampered malicious model weights")

        # Activation must fail
        success = registry.activate_model("SG-CORRUPT-001")
        assert success is False, "Security failure: Registry activated a corrupted model!"
        assert registry.get_model("SG-CORRUPT-001")["status"] == "INACTIVE"


def test_model_version_comparison():
    """Tests side-by-side comparison of two model versions."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        reg_file = Path(tmp_dir) / "registry.json"
        registry = ModelRegistry(registry_file=reg_file)

        registry.register_model(
            model_id="SG-NER-v1",
            model_name="NER v1",
            task="engineering_ner",
            domain="chemical",
            version="1.0.0",
            dataset_version="v1.0",
            training_run_id="RUN-01",
            framework="PyTorch",
            architecture="NERNet-Small",
            device="cpu",
            metrics={"f1": 0.82}
        )

        registry.register_model(
            model_id="SG-NER-v2",
            model_name="NER v2",
            task="engineering_ner",
            domain="chemical",
            version="2.0.0",
            dataset_version="v2.0",
            training_run_id="RUN-02",
            framework="PyTorch",
            architecture="NERNet-Large",
            device="cpu",
            metrics={"f1": 0.91}
        )

        comp = registry.compare_versions("SG-NER-v1", "SG-NER-v2")
        assert comp["model_1"]["version"] == "1.0.0"
        assert comp["model_2"]["version"] == "2.0.0"
        assert comp["model_1"]["metrics"]["f1"] == 0.82
        assert comp["model_2"]["metrics"]["f1"] == 0.91
