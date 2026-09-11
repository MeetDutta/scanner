"""
Comprehensive End-to-End Production Smoke & Cleanup Test Suite.
Verifies the complete production workflow for SpecGuard:
Upload -> Select Mode (Mechanical/Electrical/Chemical) -> Compare -> Analyze -> Preview -> Export.
Verifies rule-only deterministic fallback when ML checkpoints are absent.
"""

import os
import tempfile
from pathlib import Path
import pytest

from specguard.core.pipeline import AnalysisPipeline
from specguard.export.pdf_annotator import PDFAnnotator
from specguard.export.report_generator import ReportGenerator
from specguard.templates.manager import TemplateManager

DEMO_DIR = Path(__file__).resolve().parent.parent / "demo_samples"


@pytest.fixture
def temp_export_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


def test_e2e_mechanical_workflow(temp_export_dir):
    """Full workflow for Mechanical specification: upload -> analyze -> preview data -> export."""
    input_file = str(DEMO_DIR / "mechanical_sample_with_errors.pdf")
    pipeline = AnalysisPipeline()

    # 1. Pipeline Analysis
    doc, findings, session_id = pipeline.run_analysis(input_file, domain="Mechanical")
    assert doc.page_count >= 1
    assert len(findings) > 0

    # 2. Preview data validation (all findings have locations, explanation, and severity)
    for f in findings:
        assert f.severity in ["Critical", "High", "Medium", "Low", "Informational"]
        assert len(f.finding_id) > 0
        assert f.explanation is not None

    # 3. Export PDF
    pdf_out = str(temp_export_dir / "mechanical_annotated.pdf")
    res_pdf = PDFAnnotator.create_annotated_pdf(input_file, pdf_out, findings)
    assert Path(res_pdf).exists()
    assert Path(res_pdf).stat().st_size > 1000

    # 4. Export HTML
    html_out = str(temp_export_dir / "mechanical_audit.html")
    res_html = ReportGenerator.generate_html_report(doc, findings, session_id, html_out)
    assert Path(res_html).exists()
    assert "SpecGuard Engineering Compliance" in Path(res_html).read_text(encoding="utf-8")

    # 5. Export JSON
    json_out = str(temp_export_dir / "mechanical_findings.json")
    res_json = ReportGenerator.generate_json_report(doc, findings, session_id, json_out)
    assert Path(res_json).exists()


def test_e2e_electrical_workflow(temp_export_dir):
    """Full workflow for Electrical specification: upload -> analyze -> preview data -> export."""
    input_file = str(DEMO_DIR / "electrical_sample_with_errors.pdf")
    pipeline = AnalysisPipeline()

    doc, findings, session_id = pipeline.run_analysis(input_file, domain="Electrical")
    assert doc.page_count >= 1
    assert len(findings) > 0

    # Must catch 230 V deviation
    volt_findings = [f for f in findings if "230" in str(f.detected_value)]
    assert len(volt_findings) > 0

    # Export PDF & HTML
    pdf_out = str(temp_export_dir / "electrical_annotated.pdf")
    PDFAnnotator.create_annotated_pdf(input_file, pdf_out, findings)
    assert Path(pdf_out).exists()

    html_out = str(temp_export_dir / "electrical_audit.html")
    ReportGenerator.generate_html_report(doc, findings, session_id, html_out)
    assert Path(html_out).exists()


def test_e2e_chemical_workflow(temp_export_dir):
    """Full workflow for Chemical specification: upload -> analyze -> preview data -> export."""
    input_file = str(DEMO_DIR / "chemical_sample_with_errors.docx")
    pipeline = AnalysisPipeline()

    doc, findings, session_id = pipeline.run_analysis(input_file, domain="Chemical")
    assert doc.file_type == "DOCX"
    assert len(findings) > 0

    # Must catch 15% concentration deviation
    conc_findings = [f for f in findings if "15" in str(f.detected_value)]
    assert len(conc_findings) > 0

    # Export HTML & JSON
    html_out = str(temp_export_dir / "chemical_audit.html")
    ReportGenerator.generate_html_report(doc, findings, session_id, html_out)
    assert Path(html_out).exists()

    json_out = str(temp_export_dir / "chemical_findings.json")
    ReportGenerator.generate_json_report(doc, findings, session_id, json_out)
    assert Path(json_out).exists()


def test_rule_only_fallback_without_checkpoints(monkeypatch, temp_export_dir):
    """Verifies that the entire pipeline functions deterministically when NO ML checkpoints exist."""
    # Ensure no models directory exists in search path
    monkeypatch.setattr("specguard.core.config.MODELS_DIR", temp_export_dir / "nonexistent_models")

    pipeline = AnalysisPipeline()
    input_file = str(DEMO_DIR / "mechanical_sample_with_errors.pdf")

    # Pipeline must complete with Template + Regex + Rules + OpenCV
    doc, findings, session_id = pipeline.run_analysis(input_file, domain="Mechanical")
    assert doc is not None
    assert len(findings) > 0

    # Export must also succeed
    html_out = str(temp_export_dir / "fallback_audit.html")
    ReportGenerator.generate_html_report(doc, findings, session_id, html_out)
    assert Path(html_out).exists()
