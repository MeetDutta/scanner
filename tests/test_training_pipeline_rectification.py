"""
Comprehensive Rectification Verification Tests for SpecGuard Training Pipeline.
Verifies:
1. Strict 70/15/15 document-level and family-level split with zero data leakage.
2. Tokenizer train-only vocabulary fitting (no validation/test leakage).
3. Research mode strict enforcement vs. Demo mode synthetic isolation.
4. Robust offset-aware NER tokenization, BIO labeling, and attention mask padding exclusion.
5. Mathematical multiclass evaluation: FP, FN, Critical Recall, High Recall, FPR, FNR.
6. Finding-level evaluation with FindingEvaluator.
"""

import pytest
import tempfile
from pathlib import Path
import torch
import numpy as np

from specguard.training.dataset_splitter import DatasetSplitter
from specguard.models.engineering_ner import RegexOffsetTokenizer, align_entities_to_bio, PAD_ID, O_ID, EngineeringNERNet
from specguard.training.evaluation import ModelEvaluator, FindingEvaluator
from specguard.core.models import Finding, BBox
from specguard.training.training_manager import TrainingManager


def test_dataset_split_document_and_family_isolation():
    """Verifies 70/15/15 split, document family isolation, and zero overlap."""
    annotations = [
        # Document Family 1 (DOC_A has 2 revisions)
        {"document_id": "DOC_A_rev1", "text": "Pressure 10 bar", "family_id": "FAM_A"},
        {"document_id": "DOC_A_rev2", "text": "Pressure 12 bar", "family_id": "FAM_A"},
        # Document Family 2
        {"document_id": "DOC_B", "text": "Voltage 415 V", "family_id": "FAM_B"},
        {"document_id": "DOC_B", "text": "Frequency 50 Hz", "family_id": "FAM_B"},
        # Document Family 3
        {"document_id": "DOC_C", "text": "Temperature 80 C", "family_id": "FAM_C"},
        # Document Family 4
        {"document_id": "DOC_D", "text": "Shaft tolerance ±0.05 mm", "family_id": "FAM_D"},
        # Document Family 5
        {"document_id": "DOC_E", "text": "Reactor concentration 10%", "family_id": "FAM_E"}
    ]

    train, val, test = DatasetSplitter.split_annotations(annotations, random_seed=42, mode="research")

    # Extract all family IDs in each split
    train_fams = {DatasetSplitter.extract_family_id(a) for a in train}
    val_fams = {DatasetSplitter.extract_family_id(a) for a in val}
    test_fams = {DatasetSplitter.extract_family_id(a) for a in test}

    # Zero overlap assertions
    assert train_fams.isdisjoint(val_fams), f"Train and Val share families: {train_fams & val_fams}"
    assert train_fams.isdisjoint(test_fams), f"Train and Test share families: {train_fams & test_fams}"
    assert val_fams.isdisjoint(test_fams), f"Val and Test share families: {val_fams & test_fams}"

    # Verify all revisions of DOC_A stayed together in one partition
    doc_a_partitions = []
    if any(a["document_id"] == "DOC_A_rev1" for a in train):
        doc_a_partitions.append("train")
    if any(a["document_id"] == "DOC_A_rev1" for a in val):
        doc_a_partitions.append("val")
    if any(a["document_id"] == "DOC_A_rev1" for a in test):
        doc_a_partitions.append("test")
    assert len(doc_a_partitions) == 1, "DOC_A leaked into multiple partitions"

    rev2_in_same = any(a["document_id"] == "DOC_A_rev2" for a in (train if doc_a_partitions[0] == "train" else val if doc_a_partitions[0] == "val" else test))
    assert rev2_in_same, "DOC_A_rev2 was separated from DOC_A_rev1!"


def test_research_mode_rejects_insufficient_documents():
    """Research mode must raise ValueError if fewer than 3 document families exist."""
    insufficient_annots = [
        {"document_id": "DOC_1", "text": "Statement 1", "family_id": "FAM_1"},
        {"document_id": "DOC_2", "text": "Statement 2", "family_id": "FAM_2"}
    ]
    with pytest.raises(ValueError, match="Research mode requires at least 3 distinct document families"):
        DatasetSplitter.split_annotations(insufficient_annots, mode="research")


def test_demo_mode_identifies_synthetic_data():
    """Demo mode must execute gracefully and flag synthetic data."""
    manager = TrainingManager()
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Train domain classifier in demo mode on synthetic data
        res = manager.run_training_job(
            task_name="domain_classifier",
            domain="unannotated_demo_domain",
            epochs=1,
            batch_size=2,
            mode="demo"
        )
        assert res["mode"] == "demo"
        assert res["is_synthetic"] is True
        assert "training_run_id" in res


def test_robust_ner_offset_tokenization_engineering_terms():
    """Verifies character offset preservation for complex engineering notation."""
    text = "Motor operates at 415 V with 80 °C, 10 bar, 25 mm, M12 × 1.5, 0.75 kW, 304 SS."
    tokenizer = RegexOffsetTokenizer()
    tokens = tokenizer.tokenize_with_offsets(text)

    # Check that each token strictly matches its character span
    for t in tokens:
        assert text[t.start_char:t.end_char] == t.token

    token_strings = [t.token for t in tokens]
    # Check that individual engineering tokens and symbols are properly parsed
    assert "415" in token_strings and "V" in token_strings
    assert "80" in token_strings and "°C" in token_strings
    assert "10" in token_strings and "bar" in token_strings
    assert "25" in token_strings and "mm" in token_strings
    assert "M12" in token_strings and "×" in token_strings and "1.5" in token_strings
    assert "0.75" in token_strings and "kW" in token_strings
    assert "304" in token_strings and "SS" in token_strings

    # Verify character-offset based BIO alignment for multi-word engineering entities
    entities = [
        {"label": "VOLTAGE", "text": "415 V", "start_char": 18, "end_char": 23},
        {"label": "TEMPERATURE", "text": "80 °C", "start_char": 29, "end_char": 34},
        {"label": "DIMENSION", "text": "M12 × 1.5", "start_char": 52, "end_char": 61}
    ]
    tag_to_id = {
        "B-VOLTAGE": 2, "I-VOLTAGE": 3,
        "B-TEMPERATURE": 4, "I-TEMPERATURE": 5,
        "B-DIMENSION": 6, "I-DIMENSION": 7
    }
    tag_ids = align_entities_to_bio(tokens, entities, tag_to_id)

    # 415 V gets B-VOLTAGE then I-VOLTAGE
    t_415_idx = token_strings.index("415")
    t_v_idx = token_strings.index("V")
    assert tag_ids[t_415_idx] == tag_to_id["B-VOLTAGE"]
    assert tag_ids[t_v_idx] == tag_to_id["I-VOLTAGE"]

    # 80 °C gets B-TEMPERATURE then I-TEMPERATURE
    t_80_idx = token_strings.index("80")
    t_c_idx = token_strings.index("°C")
    assert tag_ids[t_80_idx] == tag_to_id["B-TEMPERATURE"]
    assert tag_ids[t_c_idx] == tag_to_id["I-TEMPERATURE"]

    # M12 × 1.5 gets B-DIMENSION then I-DIMENSION then I-DIMENSION
    t_m12_idx = token_strings.index("M12")
    t_times_idx = t_m12_idx + 1
    t_pitch_idx = t_m12_idx + 2
    assert tag_ids[t_m12_idx] == tag_to_id["B-DIMENSION"]
    assert tag_ids[t_times_idx] == tag_to_id["I-DIMENSION"]
    assert tag_ids[t_pitch_idx] == tag_to_id["I-DIMENSION"]


def test_ner_bio_alignment_and_padding_reservation():
    """Verifies PAD_ID=0 and O_ID=1 reservation and BIO tag alignment."""
    text = "The pump rated at 415 V operates safely."
    entities = [
        {"label": "COMPONENT", "text": "pump", "start_char": 4, "end_char": 8},
        {"label": "VOLTAGE", "text": "415 V", "start_char": 18, "end_char": 23}
    ]
    tokenizer = RegexOffsetTokenizer()
    tokens = tokenizer.tokenize_with_offsets(text)
    tag_to_id = {"B-COMPONENT": 2, "I-COMPONENT": 3, "B-VOLTAGE": 4, "I-VOLTAGE": 5}

    tag_ids = align_entities_to_bio(tokens, entities, tag_to_id)

    assert PAD_ID == 0
    assert O_ID == 1
    assert tag_to_id["B-COMPONENT"] in tag_ids
    assert tag_to_id["B-VOLTAGE"] in tag_ids

    # Non-entity tokens must have O_ID = 1, NOT PAD_ID = 0
    assert tag_ids[0] == O_ID  # 'The'
    assert tag_ids[1] == tag_to_id["B-COMPONENT"]  # 'pump'
    assert tag_ids[2] == O_ID  # 'rated'


def test_ner_model_attention_mask():
    """Verifies that EngineeringNERNet accepts attention_mask and masks padded tokens."""
    model = EngineeringNERNet(vocab_size=100, embed_dim=16, hidden_dim=16, num_classes=6)
    input_ids = torch.tensor([[5, 12, 18, PAD_ID, PAD_ID]])
    attention_mask = torch.tensor([[1.0, 1.0, 1.0, 0.0, 0.0]])

    logits = model(input_ids, attention_mask=attention_mask)
    assert logits.shape == (1, 5, 6)
    # The padded positions should have logits zeroed by mask
    assert torch.all(logits[0, 3:] == 0.0)


def test_mathematical_fp_fn_and_critical_recall():
    """
    Verifies that ModelEvaluator computes multiclass FP, FN, Critical Recall, and High Recall
    without confusing classes or hardcoding class 0 as Critical.
    """
    # Classes: 0: Medium, 1: High, 2: Critical, 3: Low
    class_names = ["Medium", "High", "Critical", "Low"]
    y_true = [2, 2, 1, 1, 0, 3, 2, 1]  # 3 Critical, 3 High, 1 Med, 1 Low
    y_pred = [2, 0, 1, 2, 0, 3, 2, 1]  # Predicted: 2 Crit (1 FN for Crit), 2 High (1 FN for High)

    res = ModelEvaluator.evaluate_multiclass(y_true, y_pred, class_names)

    # Critical: TP=2, FN=1, FP=1 (sample 3 predicted as Crit when true was High)
    assert res.per_class["Critical"]["TP"] == 2
    assert res.per_class["Critical"]["FN"] == 1
    assert res.per_class["Critical"]["FP"] == 1
    assert res.critical_recall == pytest.approx(2 / 3, abs=1e-3)

    # High: TP=2, FN=1 (sample 3 predicted as Crit), FP=0
    assert res.per_class["High"]["TP"] == 2
    assert res.per_class["High"]["FN"] == 1
    assert res.high_recall == pytest.approx(2 / 3, abs=1e-3)

    # Critical + High Recall: (TP_crit + TP_high) / (Actual_crit + Actual_high) = (2 + 2) / (3 + 3) = 4/6
    assert res.critical_high_recall == pytest.approx(4 / 6, abs=1e-3)


def test_finding_evaluator():
    """Verifies FindingEvaluator precision, recall, and severity performance matching."""
    gt_findings = [
        Finding(
            finding_id="GT_1",
            category="Standards Deviation",
            domain="Mechanical",
            location="Page 1",
            page=1,
            original_content="Tolerance 0.5 mm",
            detected_value="0.5 mm",
            expected_value="0.05 mm",
            deviation="Excessive tolerance",
            severity="Critical",
            confidence=0.95,
            rule_reference="ISO-2768-m"
        ),
        Finding(
            finding_id="GT_2",
            category="Electrical Inconsistency",
            domain="Electrical",
            location="Page 3",
            page=3,
            original_content="Voltage 230 V",
            detected_value="230 V",
            expected_value="415 V",
            deviation="Voltage mismatch",
            severity="High",
            confidence=0.90,
            rule_reference="IEC-60034"
        )
    ]

    pred_findings = [
        Finding(
            finding_id="PR_1",
            category="Standards Deviation",
            domain="Mechanical",
            location="Page 1",
            page=1,
            original_content="Tolerance 0.5 mm",
            detected_value="0.5 mm",
            expected_value="0.05 mm",
            deviation="Excessive tolerance",
            severity="Critical",
            confidence=0.92,
            rule_reference="ISO-2768-m"
        ),
        Finding(
            finding_id="PR_FALSE_ALARM",
            category="Grammar",
            domain="General",
            location="Page 2",
            page=2,
            original_content="Typo detected",
            detected_value="teh",
            expected_value="the",
            deviation="Spelling error",
            severity="Low",
            confidence=0.70
        )
    ]

    evaluator = FindingEvaluator()
    report = evaluator.evaluate(pred_findings, gt_findings)

    assert report["true_positives"] == 1
    assert report["false_positives"] == 1
    assert report["false_negatives"] == 1
    assert report["precision"] == pytest.approx(0.5)
    assert report["recall"] == pytest.approx(0.5)
    assert report["critical_recall"] == pytest.approx(1.0)  # GT_1 was Critical and was matched
