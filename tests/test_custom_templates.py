"""
Unit and Integration Tests for SpecGuard Custom Template Engine,
Sample Ingestion, Profile Learning, Gated Approval, and Version Rollback.
Strictly 100% offline.
"""

import pytest
import shutil
import json
from pathlib import Path
import fitz

from specguard.templates.custom_manager import CustomTemplateManager, CustomTemplateMetadata
from specguard.templates.sample_manager import SampleManager
from specguard.templates.profile_learner import ProfileLearner
from specguard.templates.profile_approver import ProfileApprover
from specguard.core.profiles import ProfileRegistry, PROFILES


@pytest.fixture
def temp_custom_dir(tmp_path):
    custom_dir = tmp_path / "templates" / "custom"
    custom_dir.mkdir(parents=True, exist_ok=True)
    return custom_dir


@pytest.fixture
def custom_mgr(temp_custom_dir):
    return CustomTemplateManager(base_dir=temp_custom_dir)


@pytest.fixture
def sample_mgr(custom_mgr):
    return SampleManager(template_manager=custom_mgr)


@pytest.fixture
def sample_pdf_a(tmp_path):
    pdf_path = tmp_path / "sample_a.pdf"
    doc = fitz.open()
    # Page 1
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text((50, 60), "SPECIFICATION FOR HYDRAULIC ACTUATOR", fontsize=16)
    p1.insert_text((50, 100), "1. Scope", fontsize=13)
    p1.insert_text((50, 120), "This specification establishes requirements for hydraulic actuators.", fontsize=10)
    p1.insert_text((50, 160), "2. Operating Parameters", fontsize=13)
    p1.insert_text((50, 180), "The nominal pressure is 250 bar with maximum flow 50 L/min.", fontsize=10)
    # Page 2
    p2 = doc.new_page(width=595, height=842)
    p2.insert_text((50, 60), "3. Quality Verification", fontsize=13)
    p2.insert_text((50, 80), "Table 1: Test Pressure Ratings", fontsize=9)
    p2.insert_text((50, 120), "Fig. 1: Actuator Schematic Assembly", fontsize=9)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def sample_pdf_b(tmp_path):
    pdf_path = tmp_path / "sample_b.pdf"
    doc = fitz.open()
    # Page 1
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text((50, 60), "SPECIFICATION FOR PNEUMATIC CYLINDER", fontsize=16)
    p1.insert_text((50, 100), "1. Scope", fontsize=13)
    p1.insert_text((50, 120), "This specification defines requirements for pneumatic cylinders.", fontsize=10)
    p1.insert_text((50, 160), "2. Operating Parameters", fontsize=13)
    p1.insert_text((50, 180), "The cylinder stroke length is 300 mm with bore diameter 80 mm.", fontsize=10)
    # Page 2
    p2 = doc.new_page(width=595, height=842)
    p2.insert_text((50, 60), "3. Quality Verification", fontsize=13)
    p2.insert_text((50, 80), "Table 1: Pressure Tolerances", fontsize=9)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def test_custom_template_lifecycle(custom_mgr):
    """Verifies template creation, path traversal protection, and uniqueness."""
    # 1. Successful creation
    meta = custom_mgr.create_template(
        template_id="actuator_spec",
        name="Hydraulic Actuator Specification",
        description="Standard rules for hydraulic actuator validation.",
        category="Mechanical"
    )
    assert meta.template_id == "actuator_spec"
    assert meta.status == "DRAFT"

    # 2. Duplicate prevention
    with pytest.raises(FileExistsError):
        custom_mgr.create_template(
            template_id="actuator_spec",
            name="Duplicate Spec",
            description="Duplicate"
        )

    # 3. Path traversal attack protection
    with pytest.raises(ValueError):
        custom_mgr.create_template(
            template_id="../../etc/passwd",
            name="Malicious Template",
            description="Exploit attempt"
        )

    # 4. Reserved name protection
    with pytest.raises(ValueError):
        custom_mgr.create_template(
            template_id="mechanical",
            name="Override Built-in",
            description="Should fail"
        )


def test_sample_ingestion_and_deduplication(custom_mgr, sample_mgr, sample_pdf_a):
    """Verifies SHA-256 duplicate detection and multi-page sample extraction."""
    custom_mgr.create_template(template_id="valve_spec", name="Valve Specification", description="Test")

    # Ingest first time
    info1 = sample_mgr.ingest_sample("valve_spec", sample_pdf_a, original_filename="actuator.pdf")
    assert info1.page_count == 2
    assert info1.status == "PROCESSED"
    assert len(info1.file_hash) == 64

    # Duplicate ingestion with same content
    with pytest.raises(ValueError, match="Duplicate sample detected"):
        sample_mgr.ingest_sample("valve_spec", sample_pdf_a, original_filename="actuator_copy.pdf")

    # List samples
    samples = sample_mgr.list_samples("valve_spec")
    assert len(samples) == 1
    assert samples[0].sample_id == info1.sample_id


def test_local_profile_learning(custom_mgr, sample_mgr, sample_pdf_a, sample_pdf_b):
    """Verifies statistical profile learning across multiple sample documents."""
    custom_mgr.create_template(template_id="fluid_power_spec", name="Fluid Power Spec", description="Test")
    sample_mgr.ingest_sample("fluid_power_spec", sample_pdf_a)
    sample_mgr.ingest_sample("fluid_power_spec", sample_pdf_b)

    learner = ProfileLearner(custom_mgr, sample_mgr)
    profile = learner.learn_profile("fluid_power_spec")

    assert profile.sample_count == 2
    assert profile.overall_confidence > 0.6
    assert "layout.columns" in profile.properties
    assert "structure.required_sections" in profile.properties

    # Both samples have 'Scope' and 'Operating Parameters'
    req_secs = profile.summary_rules["structure"]["required_sections"]
    assert any("Scope" in s for s in req_secs)
    assert any("Operating Parameters" in s for s in req_secs)

    # Check status changed to VALIDATION
    meta = custom_mgr.get_template("fluid_power_spec")
    assert meta.status == "VALIDATION"


def test_gated_approval_and_dynamic_activation(custom_mgr, sample_mgr, sample_pdf_a):
    """Verifies that unapproved templates cannot be activated, and approved templates register dynamically."""
    custom_mgr.create_template(template_id="pump_spec", name="Pump Spec", description="Test")
    sample_mgr.ingest_sample("pump_spec", sample_pdf_a)

    learner = ProfileLearner(custom_mgr, sample_mgr)
    learner.learn_profile("pump_spec")

    approver = ProfileApprover(custom_mgr)

    # 1. Attempting activation BEFORE approval must fail!
    with pytest.raises(ValueError, match="Profile has not been approved"):
        approver.activate_template("pump_spec")

    # 2. Review summary categorization
    review = approver.get_review_summary("pump_spec")
    assert "learned_properties" in review
    assert "tolerances" in review

    # 3. Explicit approval
    approver.approve_profile("pump_spec", approver_name="Chief Engineer")
    meta = custom_mgr.get_template("pump_spec")
    assert meta.status == "APPROVED"

    # 4. Activation succeeds and registers into ProfileRegistry
    cfg = approver.activate_template("pump_spec")
    assert cfg.profile_id == "pump_spec"
    assert "pump_spec" in PROFILES

    retrieved = ProfileRegistry.get_profile("pump_spec")
    assert retrieved.display_name == "Pump Spec"


def test_version_snapshot_and_rollback(custom_mgr):
    """Verifies that custom template profiles can be snapshotted and rolled back."""
    custom_mgr.create_template(template_id="heat_exchanger", name="HX Spec", description="Test")

    # Modify profile
    prof = custom_mgr.get_profile("heat_exchanger")
    prof["tolerances"]["font_size_pt"] = 0.5
    custom_mgr.save_profile("heat_exchanger", prof)
    tag1 = custom_mgr.create_version_snapshot("heat_exchanger", note="Tighter font tolerance")

    # Change again
    prof["tolerances"]["font_size_pt"] = 2.5
    custom_mgr.save_profile("heat_exchanger", prof)
    assert custom_mgr.get_profile("heat_exchanger")["tolerances"]["font_size_pt"] == 2.5

    # Rollback to tag1
    custom_mgr.rollback_version("heat_exchanger", tag1)
    restored_prof = custom_mgr.get_profile("heat_exchanger")
    assert restored_prof["tolerances"]["font_size_pt"] == 0.5
