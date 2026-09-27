"""
Tests for Custom Template Document Analysis & Drift Detection in the AnalysisPipeline.
Strictly 100% offline.
"""

import pytest
import fitz
from pathlib import Path

from specguard.templates.custom_manager import CustomTemplateManager
from specguard.core.pipeline import AnalysisPipeline
from specguard.core.models import FindingCategory


@pytest.fixture
def custom_setup(tmp_path):
    custom_dir = tmp_path / "templates" / "custom"
    custom_dir.mkdir(parents=True, exist_ok=True)
    custom_mgr = CustomTemplateManager(base_dir=custom_dir)

    # 1. Create template
    custom_mgr.create_template(
        template_id="turbine_spec",
        name="Steam Turbine Standard",
        description="Specifications for industrial steam turbines"
    )

    # 2. Save configured profile
    custom_mgr.save_profile("turbine_spec", {
        "template_id": "turbine_spec",
        "display_name": "Steam Turbine Standard",
        "category": "Mechanical",
        "status": "APPROVED",
        "is_approved": True,
        "summary_rules": {
            "structure": {
                "required_sections": ["1. Scope", "2. Rotor Assembly"]
            },
            "typography": {
                "body_font_size": 10.0
            }
        },
        "learned_properties": {
            "typography": {
                "body_font_size": 10.0
            }
        },
        "tolerances": {
            "font_size_pt": 1.0,
            "margin_mm": 5.0
        }
    })

    # 3. Activate template into ProfileRegistry
    custom_mgr.activate_template("turbine_spec")

    return custom_mgr


def test_custom_template_pipeline_compliance_and_drift(custom_setup, tmp_path):
    """
    Verifies that AnalysisPipeline evaluates documents against the activated custom template
    and detects missing mandatory sections and font size drift.
    """
    custom_mgr = custom_setup

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
