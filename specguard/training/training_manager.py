"""
Unified Training Coordinator for SpecGuard.
Coordinates hardware profiling, dataset ingestion, validation, model training,
checkpointing, evaluation, and experiment tracking.
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
import logging

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

logger = logging.getLogger(__name__)


class TrainingManager:
    """Master orchestrator for all SpecGuard offline training operations."""

    def __init__(self):
        self.hardware_manager = HardwareManager()
        self.dataset_manager = DatasetManager()
        self.annotation_manager = AnnotationManager()
        self.dataset_validator = DatasetValidator(self.annotation_manager)
        self.checkpoint_manager = CheckpointManager()

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
        progress_callback: Optional[Callable[[int, int, float, float, float, float], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes an end-to-end training job:
        1. Gathers annotations for domain
        2. Splits data without document leakage (70/15/15)
        3. Dispatches training to the specialized PyTorch trainer
        4. Saves versioned checkpoint and logs experiment
        """
        annotations = self.annotation_manager.list_annotations(domain)
        if not annotations:
            # Generate minimal bootstrap training samples if user hasn't annotated yet
            annotations = self._get_bootstrap_samples(domain)

        train_samples, val_samples, test_samples = DatasetSplitter.split_annotations(annotations)

        if task_name.lower() in ["domain_classifier", "domain"]:
            res = self.domain_trainer.train(
                train_samples=train_samples,
                val_samples=val_samples,
                epochs=epochs,
                batch_size=batch_size,
                learning_rate=learning_rate,
                device_str=device_str,
                progress_callback=progress_callback
            )
        elif task_name.lower() in ["ner", "engineering_ner"]:
            res = self.ner_trainer.train(
                train_samples=train_samples,
                val_samples=val_samples,
                domain=domain,
                epochs=epochs,
                batch_size=batch_size,
                learning_rate=learning_rate,
                device_str=device_str,
                progress_callback=progress_callback
            )
        elif task_name.lower() in ["logical", "contradiction"]:
            res = self.logical_trainer.train(
                samples=train_samples + val_samples,
                domain=domain,
                epochs=epochs,
                batch_size=batch_size,
                learning_rate=learning_rate,
                device_str=device_str,
                progress_callback=progress_callback
            )
        else:
            raise ValueError(f"Unknown training task: {task_name}")

        return res

    def _get_bootstrap_samples(self, domain: str) -> List[Dict[str, Any]]:
        """Provides verified baseline engineering training samples when dataset is initially empty."""
        return [
            {
                "annotation_id": "BOOT_001",
                "document_id": "DOC_MECH_01",
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
