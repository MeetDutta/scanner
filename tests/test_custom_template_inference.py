"""
Tests for Custom Template Document Analysis & Drift Detection in the AnalysisPipeline.
Strictly 100% offline.
"""

import pytest
import fitz
from pathlib import Path

from specguard.templates.custom_manager import CustomTemplateManager
from specguard.templates.sample_manager import SampleManager
from specguard.templates.profile_learner import ProfileLearner
from specguard.templates.profile_approver import ProfileApprover
from specguard.core.pipeline import AnalysisPipeline
from specguard.core.models import FindingCategory


@pytest.fixture
def custom_setup(tmp_path):
    custom_dir = tmp_path / "templates" / "custom"
    custom_dir.mkdir(parents=True, exist_ok=True)
    custom_mgr = CustomTemplateManager(base_dir=custom_dir)
    sample_mgr = SampleManager(template_manager=custom_mgr)

    # 1. Create template
    custom_mgr.create_template(
        template_id="turbine_spec",
        name="Steam Turbine Standard",
        description="Specifications for industrial steam turbines"
    )

    # 2. Create sample PDF
    sample_pdf = tmp_path / "sample_turbine.pdf"
    doc = fitz.open()
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text((50, 60), "STEAM TURBINE SPECIFICATION", fontsize=16)
    p1.insert_text((50, 100), "1. Scope", fontsize=13)
    p1.insert_text((50, 120), "General scope of steam turbine supply.", fontsize=10)
    p1.insert_text((50, 160), "2. Rotor Assembly", fontsize=13)
    p1.insert_text((50, 180), "The rotor must withstand 3600 RPM continuously.", fontsize=10)
    doc.save(str(sample_pdf))
    doc.close()

    # 3. Ingest and Learn
    sample_mgr.ingest_sample("turbine_spec", sample_pdf)
    learner = ProfileLearner(custom_mgr, sample_mgr)
    learner.learn_profile("turbine_spec")

    # 4. Approve & Activate
    approver = ProfileApprover(custom_mgr)
    approver.approve_profile("turbine_spec")
    approver.activate_template("turbine_spec")

    return custom_mgr, sample_mgr, approver


def test_custom_template_pipeline_compliance_and_drift(custom_setup, tmp_path):
    """
    Verifies that AnalysisPipeline evaluates documents against the activated custom template
    and detects missing mandatory sections and font size drift.
    """
    custom_mgr, _, _ = custom_setup

    # Create test document that violates the turbine_spec:
    # - Missing '2. Rotor Assembly'
    # - Font size drift: uses 14pt body text instead of 10pt baseline
    bad_pdf = tmp_path / "deviant_turbine.pdf"
    doc = fitz.open()
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text((50, 60), "DEVIANT TURBINE SPECIFICATION", fontsize=16)
    p1.insert_text((50, 100), "1. Scope", fontsize=13)
    p1.insert_text((50, 140), "Only scope is present. The rotor assembly section is completely missing.", fontsize=13)
    doc.save(str(bad_pdf))
    doc.close()

    pipeline = AnalysisPipeline(custom_template_manager=custom_mgr)
    doc_model, findings, session_id = pipeline.run_analysis(
        file_path=str(bad_pdf),
        domain="custom",
        profile="turbine_spec"
    )

    assert doc_model is not None
    assert len(findings) > 0

    # Verify missing section finding
    missing_sec_findings = [
        f for f in findings if "Missing Mandatory Section" in f.explanation or "SEC-MISSING" in f.finding_id
    ]
    assert len(missing_sec_findings) > 0
    assert any("Rotor Assembly" in f.explanation for f in missing_sec_findings)

    # Verify font drift finding
    drift_findings = [f for f in findings if "Typography Drift" in f.explanation or "DRIFT-FONTSIZE" in f.finding_id]
    assert len(drift_findings) > 0
