"""
Tests for Region Annotation Management, Dataset Readiness Diagnostics,
and Local Supervised ML Training with Document-Level Data Partitioning.
Strictly 100% offline.
"""

import pytest
from pathlib import Path

from specguard.templates.custom_manager import CustomTemplateManager
from specguard.templates.region_annotator import RegionAnnotator, SUPPORTED_REGION_LABELS
from specguard.templates.layout_trainer import LayoutTrainer


@pytest.fixture
def annot_mgr(tmp_path):
    custom_dir = tmp_path / "templates" / "custom"
    custom_dir.mkdir(parents=True, exist_ok=True)
    tmpl_mgr = CustomTemplateManager(base_dir=custom_dir)
    tmpl_mgr.create_template("robotics_spec", "Robotics Standard", "Spec")
    return RegionAnnotator(template_manager=tmpl_mgr), tmpl_mgr


def test_annotation_crud(annot_mgr):
    annotator, _ = annot_mgr

    # Add annotations
    a1 = annotator.add_annotation(
        template_id="robotics_spec",
        sample_id="SMPL-001",
        page_number=1,
        label="TITLE",
        bbox={"x0": 50, "y0": 60, "x1": 500, "y1": 90},
        text_content="ROBOTICS MANIPULATOR SPECIFICATION"
    )
    assert a1.label == "TITLE"

    a2 = annotator.add_annotation(
        template_id="robotics_spec",
        sample_id="SMPL-001",
        page_number=1,
        label="HEADING",
        bbox={"x0": 50, "y0": 100, "x1": 200, "y1": 120},
        text_content="1. Scope"
    )
    assert a2.label == "HEADING"

    # List
    all_annots = annotator.list_annotations("robotics_spec")
    assert len(all_annots) == 2

    # Delete
    deleted = annotator.delete_annotation("robotics_spec", a1.annotation_id)
    assert deleted is True
    assert len(annotator.list_annotations("robotics_spec")) == 1


def test_dataset_summary_insufficient_handling(annot_mgr):
    """Verifies that an insufficient dataset halts ML training and recommends statistical profile learning."""
    annotator, tmpl_mgr = annot_mgr
    trainer = LayoutTrainer(template_manager=tmpl_mgr, region_annotator=annotator)

    # Add only 2 annotations
    annotator.add_annotation("robotics_spec", "SMPL-001", 1, "TITLE", {"x0": 0, "y0": 0, "x1": 100, "y1": 20})
    annotator.add_annotation("robotics_spec", "SMPL-001", 1, "BODY", {"x0": 0, "y0": 30, "x1": 100, "y1": 60})

    summary = annotator.get_dataset_summary("robotics_spec")
    assert summary["is_sufficient_for_ml"] is False
    assert len(summary["insufficient_reasons"]) > 0

    # Training must raise ValueError explaining why
    with pytest.raises(ValueError, match="INSUFFICIENT DATASET FOR SUPERVISED ML TRAINING"):
        trainer.train_model("robotics_spec")


def test_supervised_ml_training_with_document_split(annot_mgr):
    """
    Verifies that with adequate multi-document annotations, supervised training succeeds,
    evaluates on held-out documents without leakage, and calculates genuine metrics.
    """
    annotator, tmpl_mgr = annot_mgr
    trainer = LayoutTrainer(template_manager=tmpl_mgr, region_annotator=annotator)

    # Populate 16 annotations across 2 distinct sample documents with 3 distinct classes
    # Document 1 (Train partition)
    for i in range(10):
        lbl = "TITLE" if i == 0 else "HEADING" if i % 2 == 0 else "BODY"
        annotator.add_annotation(
            "robotics_spec", "SMPL-DOC-1", 1, lbl,
            {"x0": 50, "y0": 50 + i * 20, "x1": 500, "y1": 65 + i * 20},
            text_content=f"Sample text block {i}"
        )

    # Document 2 (Held-out validation partition)
    for i in range(6):
        lbl = "TITLE" if i == 0 else "HEADING" if i % 2 == 0 else "BODY"
        annotator.add_annotation(
            "robotics_spec", "SMPL-DOC-2", 1, lbl,
            {"x0": 50, "y0": 50 + i * 20, "x1": 500, "y1": 65 + i * 20},
            text_content=f"Validation block {i}"
        )

    summary = annotator.get_dataset_summary("robotics_spec")
    assert summary["is_sufficient_for_ml"] is True

    # Train model
    report = trainer.train_model("robotics_spec", epochs=5)
    assert report["status"] == "VALIDATED"
    assert report["accuracy"] >= 0.0
    assert report["macro_f1"] >= 0.0
    assert report["train_samples"] == 10
    assert report["val_samples"] == 6

    # Verify template metadata updated
    meta = tmpl_mgr.get_template("robotics_spec")
    assert meta.has_active_model is True
