"""
Tests for SpecGuard Export Engines (Annotated PDF, HTML & JSON Reports).
"""

from pathlib import Path
from specguard.core.document_parser import DocumentParser
from specguard.core.pipeline import AnalysisPipeline
from specguard.export.pdf_annotator import PDFAnnotator
from specguard.export.report_generator import ReportGenerator

DEMO_DIR = Path(__file__).resolve().parent.parent / "demo_samples"


def test_pdf_annotation(tmp_path):
    pdf_in = DEMO_DIR / "mechanical_sample_with_errors.pdf"
    pdf_out = tmp_path / "annotated_mech.pdf"

    pipeline = AnalysisPipeline()
    doc, findings, session_id = pipeline.run_analysis(str(pdf_in), domain="mechanical")

    result_path = PDFAnnotator.create_annotated_pdf(str(pdf_in), str(pdf_out), findings)
    assert Path(result_path).exists()
    assert Path(result_path).stat().st_size > 1000


def test_html_and_json_reports(tmp_path):
    pdf_in = DEMO_DIR / "mechanical_sample_with_errors.pdf"
    html_out = tmp_path / "compliance_report.html"
    json_out = tmp_path / "findings.json"

    pipeline = AnalysisPipeline()
    doc, findings, session_id = pipeline.run_analysis(str(pdf_in), domain="mechanical")

    ReportGenerator.generate_html_report(doc, findings, session_id, str(html_out))
    assert html_out.exists()
    content = html_out.read_text()
    assert ("DocReady" in content or "SpecGuard" in content)
    assert "Critical" in content

    ReportGenerator.generate_json_report(doc, findings, session_id, str(json_out))
    assert json_out.exists()
    assert "total_findings" in json_out.read_text()
