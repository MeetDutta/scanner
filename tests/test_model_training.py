"""
Tests for SpecGuard PyTorch Deep Learning Training Subsystem:
Domain Classifier, Engineering NER, Siamese Logical Contradiction Model, Checkpointing, and Evaluation.
"""

import pytest
import tempfile
from pathlib import Path
import torch

from specguard.models.domain_classifier import DomainClassifierNet, SimpleTokenizer
from specguard.models.engineering_ner import EngineeringNERNet, NER_LABELS
from specguard.models.logical_classifier import LogicalRelationNet
from specguard.training.train_domain import DomainClassifierTrainer
from specguard.training.train_ner import EngineeringNERTrainer
from specguard.training.train_logical import LogicalTrainer
from specguard.training.checkpoints import CheckpointManager
from specguard.training.evaluation import ModelEvaluator, DetailedEvaluationResult
from specguard.training.onnx_exporter import ONNXExporter


def test_domain_classifier_training_loop():
    """Tests real PyTorch training loop on domain classification samples."""
    train_samples = [
        {"text": "ASME Section VIII Div 1 pressure vessel flange rating 150# carbon steel.", "domain": "mechanical"},
        {"text": "Centrifugal pump impeller diameter 250 mm with mechanical seal.", "domain": "mechanical"},
        {"text": "Piping and instrumentation diagram for catalytic cracking unit reactor.", "domain": "chemical"},
        {"text": "Molar concentration of sodium hydroxide solution at 2.5 mol/L.", "domain": "chemical"},
        {"text": "Three-phase induction motor 460 V 60 Hz 50 HP power factor 0.88.", "domain": "electrical"},
        {"text": "Medium voltage switchgear with 1200 A busbar and 24 VDC control.", "domain": "electrical"},
    ] * 3

    val_samples = [
        {"text": "Shell and tube heat exchanger design pressure 10 bar.", "domain": "mechanical"},
        {"text": "Chemical distillation column reflux ratio 2.5.", "domain": "chemical"},
        {"text": "Step-down transformer 13.8 kV to 480 V delta-wye.", "domain": "electrical"},
    ]

    with tempfile.TemporaryDirectory() as tmp_dir:
        ckpt_mgr = CheckpointManager(base_dir=Path(tmp_dir))
        trainer = DomainClassifierTrainer(checkpoint_manager=ckpt_mgr)

        results = trainer.train(
            train_samples=train_samples,
            val_samples=val_samples,
            epochs=2,
            batch_size=4,
            learning_rate=0.01,
            device_str="cpu"
        )

        assert "history" in results
        assert len(results["history"]) == 2
        assert "train_loss" in results["history"][0]
        # Verify genuine training execution (loss is a real float number > 0)
        assert results["history"][0]["train_loss"] > 0
        assert results["history"][1]["train_loss"] > 0

        # Verify saved checkpoint
        ckpts = ckpt_mgr.list_checkpoints(domain="cross_domain")
        assert len(ckpts) >= 1
        assert "sha256" in ckpts[0]
        assert len(ckpts[0]["sha256"]) == 64


def test_engineering_ner_model_and_training():
    """Tests sequence tagging NER model on tokenized engineering sentences."""
    tokenizer = SimpleTokenizer(max_vocab=200)
    texts = [
        "Vessel V-101 design pressure 15 bar",
        "Motor M-201 voltage 460 V frequency 60 Hz",
        "Pump P-101 flow rate 50 m3/h"
    ]
    tokenizer.fit(texts)

    net = EngineeringNERNet(vocab_size=len(tokenizer.word2idx), num_labels=len(NER_LABELS))
    sample_input = torch.randint(1, len(tokenizer.word2idx), (2, 8))
    logits = net(sample_input)
    assert logits.shape == (2, 8, len(NER_LABELS))

    # Test EngineeringNERTrainer on sample annotated records
    with tempfile.TemporaryDirectory() as tmp_dir:
        ckpt_mgr = CheckpointManager(base_dir=Path(tmp_dir))
        trainer = EngineeringNERTrainer(checkpoint_manager=ckpt_mgr)
        train_records = [
            {
                "text": "Vessel V-101 design pressure 15 bar",
                "entities": [
                    {"label": "COMPONENT", "text": "Vessel V-101", "start_char": 0, "end_char": 12},
                    {"label": "PRESSURE", "text": "15 bar", "start_char": 29, "end_char": 35}
                ]
            },
            {
                "text": "Motor M-1 voltage 400 V",
                "entities": [
                    {"label": "COMPONENT", "text": "Motor M-1", "start_char": 0, "end_char": 9},
                    {"label": "VOLTAGE", "text": "400 V", "start_char": 18, "end_char": 23}
                ]
            }
        ] * 4

        results = trainer.train(
            train_samples=train_records,
            val_samples=train_records,
            domain="mechanical",
            epochs=2,
            batch_size=2,
            device_str="cpu"
        )
        assert "history" in results
        assert len(results["history"]) == 2
        assert results["history"][0]["train_loss"] > 0


def test_logical_relation_siamese_network():
    """Tests Siamese network forward pass and contradiction classification."""
    net = LogicalRelationNet(vocab_size=100, embed_dim=32, hidden_dim=32)
    s1 = torch.randint(1, 50, (2, 10))
    s2 = torch.randint(1, 50, (2, 10))
    out = net(s1, s2)
    assert out.shape == (2, 2)

    with tempfile.TemporaryDirectory() as tmp_dir:
        ckpt_mgr = CheckpointManager(base_dir=Path(tmp_dir))
        trainer = LogicalTrainer(checkpoint_manager=ckpt_mgr)
        samples = [
            {"text": "Maximum vessel pressure is 15 bar.", "statement_b": "Operating pressure is 12 bar.", "logical_label": "CONSISTENT"},
            {"text": "Maximum vessel pressure is 15 bar.", "statement_b": "Design pressure was set to 8 bar.", "logical_label": "CONTRADICTORY"},
            {"text": "Motor voltage rating is 460 V.", "statement_b": "Electrical supply voltage is 460 V.", "logical_label": "CONSISTENT"},
            {"text": "Motor voltage rating is 460 V.", "statement_b": "Electrical supply is 230 V single-phase.", "logical_label": "CONTRADICTORY"},
        ] * 3

        results = trainer.train(
            samples=samples,
            domain="cross_domain",
            epochs=2,
            batch_size=2,
            device_str="cpu"
        )
        assert "history" in results
        assert len(results["history"]) == 2
        assert results["history"][0]["loss"] > 0


def test_evaluation_engine_metrics():
    """Tests full academic evaluation engine (Accuracy, F1, Critical Recall, Confusion Matrix)."""
    y_true = [0, 1, 1, 0, 1, 0, 1, 1, 0, 0]
    y_pred = [0, 1, 1, 0, 0, 0, 1, 1, 0, 1]
    class_names = ["Critical Contradiction", "Consistent"]

    metrics = ModelEvaluator.evaluate_classification(
        y_true=y_true,
        y_pred=y_pred,
        class_names=class_names
    )

    assert isinstance(metrics, DetailedEvaluationResult)
    assert 0.0 <= metrics.accuracy <= 1.0
    assert 0.0 <= metrics.critical_recall <= 1.0
    assert metrics.critical_recall + metrics.false_negative_rate == pytest.approx(1.0)
    assert len(metrics.confusion_matrix) == 2


def test_onnx_export():
    """Tests exporting PyTorch model to standard ONNX artifact."""
    net = DomainClassifierNet(vocab_size=50, embed_dim=16, hidden_dim=16, num_classes=3)

    with tempfile.TemporaryDirectory() as tmp_dir:
        out_file = str(Path(tmp_dir) / "domain_classifier.onnx")
        out_path, parity, diff = ONNXExporter.export_classifier(
            model=net,
            output_path=out_file,
            seq_len=16
        )
        assert Path(out_path).exists()
        assert Path(out_path).stat().st_size > 0
        assert parity is True
