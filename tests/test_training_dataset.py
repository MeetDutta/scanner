"""
Tests for SpecGuard Training Dataset Subsystems:
Hardware Detection, Dataset Manager, Annotation Schema, Dataset Validator, and Leakage-Free Splitting.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from specguard.training.hardware import HardwareManager, HardwareProfile
from specguard.training.dataset_manager import DatasetManager
from specguard.training.annotation_manager import AnnotationManager, DocumentAnnotation, EntityAnnotation
from specguard.training.dataset_validator import DatasetValidator, DatasetHealthReport
from specguard.training.dataset_splitter import DatasetSplitter


def test_hardware_profiling():
    profile = HardwareManager.get_profile()
    assert isinstance(profile, HardwareProfile)
    assert profile.device in ["cpu", "mps", "cuda"]
    assert profile.cpu_cores > 0
    assert profile.ram_gb > 0
    assert profile.recommended_batch_size in [4, 8, 16]
    assert len(profile.recommendations) > 0


def test_dataset_manager_structure_and_manifest():
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_dir = Path(tmp_dir)
        dm = DatasetManager(base_dir=base_dir)

        # Ingest a sample text document into mechanical domain
        sample_file = base_dir / "sample_vessel.txt"
        sample_file.write_text("Vessel V-101 design pressure is 15.0 bar at 250 C.", encoding="utf-8")

        imported = dm.import_document(str(sample_file), domain="mechanical")
        assert imported["domain"] == "mechanical"
        assert imported["filename"] == "sample_vessel.txt"

        processed = dm.list_processed_documents(domain="mechanical")
        assert len(processed) == 1
        assert processed[0]["filename"] == "sample_vessel.txt"


def test_annotation_manager_schema_and_export():
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_dir = Path(tmp_dir)
        am = AnnotationManager(base_dir=base_dir)

        record = DocumentAnnotation(
            annotation_id="ANN-TEST-001",
            document_id="DOC-TEST-001",
            domain="mechanical",
            page=1,
            text="Centrifugal pump P-201 operates at 460 V and 60 Hz with 15 bar discharge.",
            entities=[
                EntityAnnotation(label="COMPONENT", text="Centrifugal pump P-201", start_char=0, end_char=22),
                EntityAnnotation(label="VOLTAGE", text="460 V", start_char=35, end_char=40),
                EntityAnnotation(label="FREQUENCY", text="60 Hz", start_char=45, end_char=50),
                EntityAnnotation(label="PRESSURE", text="15 bar", start_char=56, end_char=62),
            ]
        )

        saved = am.save_annotation(record)
        assert Path(saved).exists()

        loaded = am.list_annotations(domain="mechanical")
        assert len(loaded) == 1
        assert loaded[0]["document_id"] == "DOC-TEST-001"
        assert len(loaded[0]["entities"]) == 4
        assert loaded[0]["entities"][0]["label"] == "COMPONENT"


def test_dataset_validator_clean_and_anomalies():
    with tempfile.TemporaryDirectory() as tmp_dir:
        base_dir = Path(tmp_dir)
        am = AnnotationManager(base_dir=base_dir)

        # 1. Clean annotations
        ann1 = DocumentAnnotation(
            annotation_id="ANN-1",
            document_id="DOC-1",
            domain="mechanical",
            page=1,
            text="Pump P-101 flow rate is 50 m3/h at 10 bar.",
            entities=[EntityAnnotation(label="COMPONENT", text="Pump P-101", start_char=0, end_char=10)]
        )
        ann2 = DocumentAnnotation(
            annotation_id="ANN-2",
            document_id="DOC-2",
            domain="chemical",
            page=1,
            text="Reactor R-101 operating temperature is 350 C.",
            entities=[EntityAnnotation(label="COMPONENT", text="Reactor R-101", start_char=0, end_char=13)]
        )
        am.save_annotation(ann1)
        am.save_annotation(ann2)

        validator = DatasetValidator(annotation_manager=am)
        report = validator.validate_dataset()
        assert isinstance(report, DatasetHealthReport)
        assert report.total_annotations == 2
        assert report.status == "HEALTHY"

        # 2. Overlapping span anomaly
        ann_overlap = DocumentAnnotation(
            annotation_id="ANN-3",
            document_id="DOC-3",
            domain="electrical",
            page=1,
            text="Motor M-1 operates at 400 V.",
            entities=[
                EntityAnnotation(label="COMPONENT", text="Motor M-1", start_char=0, end_char=9),
                EntityAnnotation(label="PARAMETER", text="M-1 opera", start_char=6, end_char=15)
            ]
        )
        am.save_annotation(ann_overlap)
        report2 = validator.validate_dataset()
        assert report2.overlapping_entities >= 1


def test_leakage_free_dataset_splitter():
    annotations = []
    # Create multi-page documents where doc_0 has 3 pages, doc_1 has 3 pages, etc.
    for doc_idx in range(10):
        doc_id = f"SPEC-DOC-{doc_idx:03d}"
        for page_idx in range(3):
            annotations.append({
                "annotation_id": f"ANN-{doc_idx}-{page_idx}",
                "document_id": doc_id,
                "text": f"Document {doc_id} Page {page_idx + 1} equipment specifications.",
                "domain": "mechanical" if doc_idx % 2 == 0 else "electrical",
                "entities": [{"label": "COMPONENT", "text": "Document", "start_char": 0, "end_char": 8}]
            })

    train_set, val_set, test_set = DatasetSplitter.split_annotations(
        annotations, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15, random_seed=42
    )

    assert len(train_set) > 0
    assert len(val_set) > 0
    assert len(test_set) > 0
    assert len(train_set) + len(val_set) + len(test_set) == len(annotations)

    # CRITICAL LEAKAGE CHECK: verify NO document_id exists across partitions
    train_docs = {a["document_id"] for a in train_set}
    val_docs = {a["document_id"] for a in val_set}
    test_docs = {a["document_id"] for a in test_set}

    assert len(train_docs.intersection(val_docs)) == 0, "Data leakage between Train and Val!"
    assert len(train_docs.intersection(test_docs)) == 0, "Data leakage between Train and Test!"
    assert len(val_docs.intersection(test_docs)) == 0, "Data leakage between Val and Test!"
