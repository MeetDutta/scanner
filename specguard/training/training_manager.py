"""
Unified Training Coordinator for SpecGuard.
Coordinates hardware profiling, dataset ingestion, validation, model training,
checkpointing, ONNX export with parity check, dynamic registry registration,
and experiment reporting.
Strictly 100% offline.
"""

from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable
import uuid
import logging
import torch

from specguard.training.hardware import HardwareManager, HardwareProfile
from specguard.training.dataset_manager import DatasetManager
from specguard.training.annotation_manager import AnnotationManager
from specguard.training.dataset_validator import DatasetValidator, DatasetHealthReport
from specguard.training.dataset_splitter import DatasetSplitter
from specguard.training.checkpoints import CheckpointManager
from specguard.training.train_domain import DomainClassifierTrainer
from specguard.training.train_ner import EngineeringNERTrainer
from specguard.training.train_logical import LogicalTrainer
from specguard.training.onnx_exporter import ONNXExporter
from specguard.training.experiment_report import ExperimentReportGenerator
from specguard.models.registry import ModelRegistry, ONNX_DIR
from specguard.core.config import MODELS_DIR

logger = logging.getLogger(__name__)


class TrainingManager:
    """Master orchestrator for all SpecGuard offline training operations."""

    def __init__(self):
        self.hardware_manager = HardwareManager()
        self.dataset_manager = DatasetManager()
        self.annotation_manager = AnnotationManager()
        self.dataset_validator = DatasetValidator(self.annotation_manager)
        self.checkpoint_manager = CheckpointManager()
        self.registry = ModelRegistry()

        self.domain_trainer = DomainClassifierTrainer(self.checkpoint_manager)
        self.ner_trainer = EngineeringNERTrainer(self.checkpoint_manager)
        self.logical_trainer = LogicalTrainer(self.checkpoint_manager)

    def get_hardware_profile(self) -> HardwareProfile:
        return self.hardware_manager.get_profile()

    def validate_dataset(self, domain: Optional[str] = None) -> DatasetHealthReport:
        return self.dataset_validator.validate_dataset(domain)

    def run_training_job(
        self,
        task_name: str,
        domain: str,
        epochs: int = 5,
        batch_size: int = 4,
        learning_rate: float = 0.001,
        device_str: str = "auto",
        mode: str = "research",
        progress_callback: Optional[Callable[[int, int, float, float, float, float], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes an end-to-end training job:
        1. Gathers annotations for domain (enforcing research mode integrity)
        2. Splits data without document leakage (70/15/15)
        3. Dispatches training with held-out test evaluation
        4. Saves versioned checkpoint with reproducibility metadata
        5. Exports ONNX and verifies parity without fabrication
        6. Registers artifact automatically into ModelRegistry
        7. Generates comprehensive JSON and HTML experiment reports
        """
        training_run_id = f"RUN-SG-{task_name.upper()[:4]}-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        is_synthetic = False

        annotations = self.annotation_manager.list_annotations(domain)
        if not annotations:
            if mode == "research":
                raise ValueError(
                    f"RESEARCH MODE VIOLATION: Zero annotated engineering documents found for domain '{domain}'. "
                    f"Research mode strictly requires real local annotated data. Synthetic/bootstrap examples are prohibited. "
                    f"Please annotate local documents using the Annotation Manager before running research training."
                )
            logger.warning("No local annotations found for %s. Using DEMO synthetic baseline.", domain)
            annotations = self._get_bootstrap_samples(domain)
            is_synthetic = True

        train_samples, val_samples, test_samples = DatasetSplitter.split_annotations(
            annotations,
            random_seed=42,
            mode=mode
        )

        logger.info(
            "Starting %s training for %s (%s mode, run_id=%s). Partitions: %d Train, %d Val, %d Test",
            task_name, domain, mode.upper(), training_run_id, len(train_samples), len(val_samples), len(test_samples)
        )

        # Execute training with test set passed for unbiased evaluation
        if task_name.lower() in ["domain_classifier", "domain"]:
            res = self.domain_trainer.train(
                train_samples=train_samples,
                val_samples=val_samples,
                test_samples=test_samples,
                epochs=epochs,
                batch_size=batch_size,
                learning_rate=learning_rate,
                device_str=device_str,
                progress_callback=progress_callback
            )
            model_arch = "DomainClassifierNet(LSTM)"
        elif task_name.lower() in ["ner", "engineering_ner"]:
            res = self.ner_trainer.train(
                train_samples=train_samples,
                val_samples=val_samples,
                test_samples=test_samples,
                domain=domain,
                epochs=epochs,
                batch_size=batch_size,
                learning_rate=learning_rate,
                device_str=device_str,
                progress_callback=progress_callback
            )
            model_arch = "EngineeringNERNet(BiLSTM+AttentionMask)"
        elif task_name.lower() in ["logical", "contradiction"]:
            res = self.logical_trainer.train(
                train_samples=train_samples,
                val_samples=val_samples,
                test_samples=test_samples,
                domain=domain,
                epochs=epochs,
                batch_size=batch_size,
                learning_rate=learning_rate,
                device_str=device_str,
                mode=mode,
                progress_callback=progress_callback
            )
            model_arch = "LogicalRelationNet(SiameseBiLSTM)"
        else:
            raise ValueError(f"Unknown training task: {task_name}")

        res["training_run_id"] = training_run_id
        res["mode"] = mode
        res["is_synthetic"] = is_synthetic

        # Export ONNX and run real parity verification
        onnx_path = None
        parity_verified = False
        parity_max_diff = -1.0
        parity_status = "NOT VERIFIED"

        try:
            model_instance = res.get("model")
            if model_instance and isinstance(model_instance, torch.nn.Module):
                onnx_out_file = ONNX_DIR / f"{res['model_id']}.onnx"
                if task_name.lower() in ["domain_classifier", "domain"]:
                    exp_res = ONNXExporter.export_classifier(model_instance, str(onnx_out_file))
                elif task_name.lower() in ["ner", "engineering_ner"]:
                    exp_res = ONNXExporter.export_ner(model_instance, str(onnx_out_file))
                elif task_name.lower() in ["logical", "contradiction"]:
                    exp_res = ONNXExporter.export_logical(model_instance, str(onnx_out_file))
                else:
                    exp_res = None

                if exp_res:
                    onnx_path = exp_res.output_path
                    parity_verified = exp_res.parity
                    parity_max_diff = exp_res.max_diff
                    parity_status = getattr(exp_res, "status", "PASS" if exp_res.parity else "FAIL")
        except Exception as onnx_err:
            logger.warning("ONNX export / parity verification encountered an error: %s", onnx_err)
            parity_status = f"ERROR: {str(onnx_err)}"

        res["onnx_path"] = onnx_path
        res["parity_verified"] = parity_verified
        res["parity_max_diff"] = parity_max_diff
        res["parity_status"] = parity_status

        # Register model artifact in ModelRegistry
        try:
            self.registry.register_model(
                model_id=res["model_id"],
                model_name=f"SpecGuard-{task_name.title()}-{domain.title()}",
                task=task_name.lower(),
                domain=domain.lower(),
                version="1.0.0",
                dataset_version=f"v1.0-{len(train_samples)+len(val_samples)+len(test_samples)}samples",
                training_run_id=training_run_id,
                framework="PyTorch" + (" + ONNX" if onnx_path else ""),
                architecture=model_arch,
                device=device_str,
                checkpoint_path=res.get("checkpoint_path"),
                onnx_path=onnx_path,
                metrics=res.get("metrics", {}),
                parity_verified=parity_verified,
                parity_max_diff=parity_max_diff if parity_max_diff >= 0 else None
            )
        except Exception as reg_err:
            logger.error("Failed registering model in ModelRegistry: %s", reg_err)

        # Generate Experiment Report (JSON and HTML)
        try:
            report_gen = ExperimentReportGenerator()
            hw_prof = self.get_hardware_profile()
            rep_files = report_gen.generate_report(
                training_run_id=training_run_id,
                task=task_name,
                domain=domain,
                mode=mode,
                architecture=model_arch,
                hyperparameters={
                    "epochs": epochs,
                    "batch_size": batch_size,
                    "learning_rate": learning_rate
                },
                hardware_info={
                    "device": device_str,
                    "cpu_cores": hw_prof.cpu_cores,
                    "ram_gb": hw_prof.ram_gb,
                    "gpu_available": hw_prof.gpu_available,
                    "gpu_name": hw_prof.gpu_name
                },
                dataset_meta={
                    "split_counts": {
                        "train": len(train_samples),
                        "validation": len(val_samples),
                        "test": len(test_samples)
                    },
                    "is_synthetic": is_synthetic
                },
                validation_metrics=res.get("validation_metrics", {}),
                test_metrics=res.get("test_metrics", res.get("metrics", {})),
                duration_seconds=0.0
            )
            json_p = rep_files.get("json_path") or rep_files.get("json")
            html_p = rep_files.get("html_path") or rep_files.get("html")
            res["experiment_report_json"] = json_p
            res["experiment_report_html"] = html_p
            logger.info("Generated experiment reports:\n- JSON: %s\n- HTML: %s", json_p, html_p)
        except Exception as rep_err:
            logger.error("Failed generating experiment report: %s", rep_err)

        return res

    def _get_bootstrap_samples(self, domain: str) -> List[Dict[str, Any]]:
        """Provides verified baseline engineering training samples when dataset is initially empty."""
        return [
            {
                "annotation_id": "BOOT_001",
                "document_id": "DOC_MECH_01",
                "family_id": "FAM_MECH_01",
                "domain": "mechanical",
                "text": "The drive shaft bearing tolerance = ±0.05 mm for precision fitting.",
                "entities": [
                    {"label": "COMPONENT", "text": "shaft", "start_char": 10, "end_char": 15},
                    {"label": "TOLERANCE", "text": "±0.05", "start_char": 36, "end_char": 41},
                    {"label": "UNIT", "text": "mm", "start_char": 42, "end_char": 44}
                ],
                "classification_label": "MECHANICAL",
                "logical_label": "CONSISTENT"
            },
            {
                "annotation_id": "BOOT_002",
                "document_id": "DOC_ELEC_01",
                "family_id": "FAM_ELEC_01",
                "domain": "electrical",
                "text": "The motor feeder operates at rated voltage = 415 V and 50 Hz.",
                "entities": [
                    {"label": "COMPONENT", "text": "motor", "start_char": 4, "end_char": 9},
                    {"label": "VOLTAGE", "text": "415", "start_char": 45, "end_char": 48},
                    {"label": "UNIT", "text": "V", "start_char": 49, "end_char": 50},
                    {"label": "FREQUENCY", "text": "50", "start_char": 55, "end_char": 57}
                ],
                "classification_label": "ELECTRICAL",
                "logical_label": "CONSISTENT"
            },
            {
                "annotation_id": "BOOT_003",
                "document_id": "DOC_CHEM_01",
                "family_id": "FAM_CHEM_01",
                "domain": "chemical",
                "text": "The reactor solution required concentration = 10% under continuous reflux.",
                "entities": [
                    {"label": "COMPONENT", "text": "reactor", "start_char": 4, "end_char": 11},
                    {"label": "CONCENTRATION", "text": "10", "start_char": 46, "end_char": 48},
                    {"label": "UNIT", "text": "%", "start_char": 48, "end_char": 49}
                ],
                "classification_label": "CHEMICAL",
                "logical_label": "CONSISTENT"
            }
        ]
