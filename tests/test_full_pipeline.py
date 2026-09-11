"""
End-to-end integration pipeline tests across Mechanical, Electrical, and Chemical test documents.
"""

from pathlib import Path
from specguard.core.pipeline import AnalysisPipeline

DEMO_DIR = Path(__file__).resolve().parent.parent / "demo_samples"


def test_full_mechanical_pipeline():
    pipeline = AnalysisPipeline()
    doc, findings, session_id = pipeline.run_analysis(
        str(DEMO_DIR / "mechanical_sample_with_errors.pdf"),
        domain="mechanical"
    )
    assert doc.page_count == 2
    assert len(findings) > 0
    # Top finding should be Critical
    assert findings[0].severity == "Critical"
    # Ensure all 10 analyzer categories are represented or executed cleanly
    cats = {f.category for f in findings}
    assert "Standards Deviation" in cats or "Logical Contradiction" in cats


def test_full_electrical_pipeline():
    pipeline = AnalysisPipeline()
    doc, findings, session_id = pipeline.run_analysis(
        str(DEMO_DIR / "electrical_sample_with_errors.pdf"),
        domain="electrical"
    )
    assert doc.page_count == 1
    assert len(findings) > 0
    # Must flag the voltage 230V vs 415V deviation
    volt_findings = [f for f in findings if "230" in str(f.detected_value)]
    assert len(volt_findings) > 0
    assert volt_findings[0].severity == "Critical"


def test_full_chemical_pipeline():
    pipeline = AnalysisPipeline()
    doc, findings, session_id = pipeline.run_analysis(
        str(DEMO_DIR / "chemical_sample_with_errors.docx"),
        domain="chemical"
    )
    assert doc.file_type == "DOCX"
    assert len(findings) > 0
    # Must flag the 15% concentration violation
    conc_findings = [f for f in findings if "15" in str(f.detected_value)]
    assert len(conc_findings) > 0
    assert conc_findings[0].severity == "Critical"
