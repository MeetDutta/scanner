"""
ONNX Model Export and Parity Verification for SpecGuard.
Converts trained PyTorch models to standard ONNX format for efficient offline inference.
Strictly verifies numerical parity between PyTorch and ONNX Runtime outputs.
"""

from pathlib import Path
from typing import Tuple, Dict, Any, Optional
import logging
import torch
import numpy as np

logger = logging.getLogger(__name__)


class ExportResult(tuple):
    """
    Subclasses tuple to remain 100% backwards compatible with existing (path, parity, diff) callers
    while also exposing status string via .status attribute.
    """
    def __new__(cls, output_path: str, parity: bool, max_diff: float, status: str = "PASS"):
        return super().__new__(cls, (output_path, parity, max_diff))

    def __init__(self, output_path: str, parity: bool, max_diff: float, status: str = "PASS"):
        self.output_path = output_path
        self.parity = parity
        self.max_diff = max_diff
        self.status = status


class ONNXExporter:
    """Exports PyTorch models to ONNX and validates prediction parity without fabricating results."""

    @staticmethod
    def verify_parity(
        model: torch.nn.Module,
        onnx_file: Path,
        dummy_inputs: Tuple[torch.Tensor, ...],
        tolerance: float = 1e-4
    ) -> Tuple[bool, float, str]:
        """
        Executes identical inputs through PyTorch and ONNX Runtime.
        Calculates maximum absolute difference.
        Returns: (passed: bool, max_diff: float, status_string: 'PASS' | 'FAIL' | 'NOT VERIFIED')
        """
        try:
            import onnxruntime as ort
        except ImportError:
            logger.warning("onnxruntime is not installed. Parity CANNOT be verified.")
            return False, -1.0, "NOT VERIFIED"

        try:
            model = model.to("cpu")
            model.eval()
            cpu_inputs = tuple(inp.to("cpu") for inp in dummy_inputs)

            with torch.no_grad():
                pt_out = model(*cpu_inputs)
                if isinstance(pt_out, (list, tuple)):
                    pt_np = pt_out[0].detach().cpu().numpy()
                else:
                    pt_np = pt_out.detach().cpu().numpy()

            session = ort.InferenceSession(str(onnx_file), providers=["CPUExecutionProvider"])
            ort_inputs = {}
            session_inputs = session.get_inputs()
            for idx, inp in enumerate(session_inputs):
                if idx < len(cpu_inputs):
                    ort_inputs[inp.name] = cpu_inputs[idx].detach().cpu().numpy()

            ort_out = session.run(None, ort_inputs)
            ort_np = ort_out[0]

            max_diff = float(np.max(np.abs(pt_np - ort_np)))
            passed = max_diff <= tolerance
            status = "PASS" if passed else "FAIL"
            logger.info("ONNX Parity Verification for %s: status=%s, max_abs_diff=%.7f (tol=%.1e)",
                        onnx_file.name, status, max_diff, tolerance)
            return passed, max_diff, status
        except Exception as e:
            logger.error("ONNX Runtime parity execution failed: %s", e)
            return False, -1.0, f"FAIL: {str(e)}"

    @classmethod
    def export_classifier(
        cls,
        model: torch.nn.Module,
        output_path: str,
        seq_len: int = 64
    ) -> ExportResult:
        """
        Exports DomainClassifierNet to ONNX format.
        Returns: ExportResult((output_path, parity_success, max_discrepancy), status=status)
        """
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

        model = model.to("cpu")
        model.eval()
        max_idx = getattr(model, "embedding", None)
        vocab_size = max_idx.num_embeddings if max_idx else 500
        dummy_input = torch.randint(1, vocab_size, (1, seq_len), dtype=torch.long, device="cpu")

        torch.onnx.export(
            model,
            dummy_input,
            str(out_file),
            input_names=["input_ids"],
            output_names=["logits"],
            dynamic_axes={"input_ids": {0: "batch_size"}, "logits": {0: "batch_size"}},
            opset_version=17,
            dynamo=False
        )
        logger.info("Exported DomainClassifierNet to ONNX at %s", out_file)

        parity, max_diff, status = cls.verify_parity(model, out_file, (dummy_input,))
        return ExportResult(str(out_file), parity, max_diff, status)

    @classmethod
    def export_ner(
        cls,
        model: torch.nn.Module,
        output_path: str,
        seq_len: int = 64
    ) -> ExportResult:
        """
        Exports EngineeringNERNet to ONNX format.
        Returns: ExportResult((output_path, parity_success, max_discrepancy), status=status)
        """
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

        model = model.to("cpu")
        model.eval()
        max_idx = getattr(model, "embedding", None)
        vocab_size = max_idx.num_embeddings if max_idx else 500
        dummy_ids = torch.randint(1, vocab_size, (1, seq_len), dtype=torch.long, device="cpu")
        dummy_mask = torch.ones((1, seq_len), dtype=torch.float32, device="cpu")

        torch.onnx.export(
            model,
            (dummy_ids, dummy_mask),
            str(out_file),
            input_names=["input_ids", "attention_mask"],
            output_names=["logits"],
            dynamic_axes={
                "input_ids": {0: "batch_size", 1: "seq_len"},
                "attention_mask": {0: "batch_size", 1: "seq_len"},
                "logits": {0: "batch_size", 1: "seq_len"}
            },
            opset_version=17,
            dynamo=False
        )
        logger.info("Exported EngineeringNERNet to ONNX at %s", out_file)

        parity, max_diff, status = cls.verify_parity(model, out_file, (dummy_ids, dummy_mask))
        return ExportResult(str(out_file), parity, max_diff, status)

    @classmethod
    def export_logical(
        cls,
        model: torch.nn.Module,
        output_path: str,
        seq_len: int = 64
    ) -> ExportResult:
        """
        Exports LogicalRelationNet to ONNX format.
        Returns: ExportResult((output_path, parity_success, max_discrepancy), status=status)
        """
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

        model = model.to("cpu")
        model.eval()
        max_idx = getattr(model, "embedding", None)
        vocab_size = max_idx.num_embeddings if max_idx else 500
        dummy_x1 = torch.randint(1, vocab_size, (1, seq_len), dtype=torch.long, device="cpu")
        dummy_x2 = torch.randint(1, vocab_size, (1, seq_len), dtype=torch.long, device="cpu")

        torch.onnx.export(
            model,
            (dummy_x1, dummy_x2),
            str(out_file),
            input_names=["x1", "x2"],
            output_names=["logits"],
            dynamic_axes={
                "x1": {0: "batch_size", 1: "seq_len"},
                "x2": {0: "batch_size", 1: "seq_len"},
                "logits": {0: "batch_size"}
            },
            opset_version=17,
            dynamo=False
        )
        logger.info("Exported LogicalRelationNet to ONNX at %s", out_file)

        parity, max_diff, status = cls.verify_parity(model, out_file, (dummy_x1, dummy_x2))
        return ExportResult(str(out_file), parity, max_diff, status)
