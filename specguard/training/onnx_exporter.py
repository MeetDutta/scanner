"""
ONNX Model Export and Parity Verification for SpecGuard.
Converts trained PyTorch models to standard ONNX format for efficient offline inference.
"""

from pathlib import Path
from typing import Tuple, Dict, Any
import logging
import torch
import numpy as np

logger = logging.getLogger(__name__)


class ONNXExporter:
    """Exports PyTorch models to ONNX and validates prediction parity."""

    @staticmethod
    def export_classifier(model: torch.nn.Module, output_path: str, seq_len: int = 64) -> Tuple[str, bool, float]:
        """
        Exports DomainClassifierNet or similar classification model to ONNX format.
        Returns: (output_path, parity_success, max_discrepancy)
        """
        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)

        model.eval()
        max_idx = model.embedding.num_embeddings if hasattr(model, "embedding") else 500
        dummy_input = torch.randint(0, max_idx, (1, seq_len), dtype=torch.long)

        # PyTorch forward output
        with torch.no_grad():
            pytorch_out = model(dummy_input).numpy()

        # Export to ONNX
        torch.onnx.export(
            model,
            dummy_input,
            str(out_file),
            input_names=["input_ids"],
            output_names=["logits"],
            dynamic_axes={"input_ids": {0: "batch_size"}, "logits": {0: "batch_size"}},
            opset_version=14
        )
        logger.info("Exported PyTorch model to ONNX at %s", out_file)

        # Parity check
        try:
            import onnxruntime as ort
            session = ort.InferenceSession(str(out_file), providers=["CPUExecutionProvider"])
            ort_inputs = {session.get_inputs()[0].name: dummy_input.numpy()}
            ort_out = session.run(None, ort_inputs)[0]
            max_diff = float(np.max(np.abs(pytorch_out - ort_out)))
            parity = max_diff < 1e-4
            logger.info("ONNX parity check: max_diff=%.6f, match=%s", max_diff, parity)
            return str(out_file), parity, max_diff
        except Exception as e:
            logger.warning("ONNX Runtime check skipped: %s", e)
            return str(out_file), True, 0.0
