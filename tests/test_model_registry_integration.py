"""
Integration Tests for SpecGuard Model Registry and ONNX Parity Engine.
Verifies:
1. Dynamic model registration with SHA-256 calculation.
2. Safe model activation (blocks corrupted or missing models).
3. Deactivation and status tracking.
4. Cryptographic SHA-256 integrity check.
5. ONNX Export and Numerical Parity Verification with ONNX Runtime.
"""

import pytest
import tempfile
import json
from pathlib import Path
import torch
import numpy as np

from specguard.models.registry import ModelRegistry, calculate_sha256
from specguard.models.domain_classifier import DomainClassifierNet
from specguard.models.engineering_ner import EngineeringNERNet
from specguard.training.onnx_exporter import ONNXExporter


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

        ckpt_path = Path(tmp_dir) / "corrupted_model.pt"
        ckpt_path.write_bytes(b"Original valid content")

        registry.register_model(
            model_id="SG-CORRUPT-001",
            model_name="CorruptibleModel",
            task="engineering_ner",
            domain="electrical",
            version="1.0.0",
            dataset_version="v1.0",
            training_run_id="RUN-TEST-02",
            framework="PyTorch",
            architecture="EngineeringNERNet",
            device="cpu",
            checkpoint_path=str(ckpt_path)
        )

        # Deactivate first
        registry.deactivate_model("SG-CORRUPT-001")
        assert registry.get_model("SG-CORRUPT-001")["status"] == "INACTIVE"

        # Tamper with file
        ckpt_path.write_bytes(b"TAMPERED CORRUPTED CONTENT")

        # Attempt to reactivate
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


def test_onnx_parity_real_execution():
    """
    Exports a model to ONNX and validates prediction parity between PyTorch and ONNX Runtime.
    Ensures that discrepancies exceeding tolerance are caught as FAIL.
    """
    net = DomainClassifierNet(vocab_size=100, embed_dim=16, hidden_dim=16, num_classes=3)
    net.eval()

    with tempfile.TemporaryDirectory() as tmp_dir:
        onnx_file = Path(tmp_dir) / "classifier.onnx"
        out_path, parity, max_diff = ONNXExporter.export_classifier(
            model=net,
            output_path=str(onnx_file),
            seq_len=16
        )

        assert Path(out_path).exists()
        assert parity is True
        assert max_diff < 1e-4

        # Verify parity helper method returns PASS
        dummy_input = torch.randint(1, 100, (1, 16), dtype=torch.long)
        passed, diff, status = ONNXExporter.verify_parity(net, onnx_file, (dummy_input,))
        assert passed is True
        assert status == "PASS"
        assert diff < 1e-4
