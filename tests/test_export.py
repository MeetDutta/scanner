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

    # Verify annotations are physically present in the PDF document
    import pymupdf
    annotated_doc = pymupdf.open(result_path)
    total_annots = 0
    for page in annotated_doc:
        a = page.first_annot
        while a:
            total_annots += 1
            a = a.next
    annotated_doc.close()
    assert total_annots > 0, "Annotated PDF must contain visual annotations!"


def test_pdf_annotation_with_missing_bboxes(tmp_path):
    """Verify that findings without bounding boxes still get highlighted or callout annotated."""
    import pymupdf
    from specguard.core.models import Finding

    pdf_in = DEMO_DIR / "mechanical_sample_with_errors.pdf"
    pdf_out = tmp_path / "annotated_fallback.pdf"

    # Create findings with None bboxes
    findings = [
        Finding(
            finding_id="TEST-001",
            category="Dimension",
            domain="mechanical",
            location="Page 1",
            page=1,
            bbox=None,
            original_content="",
            detected_value="Operating Temperature",
            expected_value="Operating Temperature: -20°C to +80°C",
            deviation="Parameter absent",
            severity="High",
            confidence=0.9,
            explanation="Operating temperature absent",
            suggested_correction="Add temperature parameter"
        ),
        Finding(
            finding_id="TEST-002",
            category="Structural",
            domain="mechanical",
            location="Page 2",
            page=2,
            bbox=None,
            original_content="",
            detected_value="Section absent",
            expected_value="Section 3.2",
            deviation="Section 3.2 missing",
            severity="Critical",
            confidence=0.95,
            explanation="Section absent",
            suggested_correction="Insert Section 3.2"
        )
    ]

    result_path = PDFAnnotator.create_annotated_pdf(str(pdf_in), str(pdf_out), findings)
    assert Path(result_path).exists()

    annotated_doc = pymupdf.open(result_path)
    total_annots = 0
    for page in annotated_doc:
        a = page.first_annot
        while a:
            total_annots += 1
            a = a.next
    annotated_doc.close()
    assert total_annots >= 2, "Findings with missing bboxes must still produce visual annotations!"


def test_annotated_editor_api_endpoint():
    """Verify the /documents/editor/{session_id}/annotated endpoint generates and serves highlighted PDF."""
    from fastapi.testclient import TestClient
    from specguard.server.app import app
    import pymupdf

    client = TestClient(app)
    # Using comparison CMP-2026-000024
    resp = client.get("/api/documents/editor/CMP-2026-000024/annotated")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers.get("content-disposition", "")

    doc = pymupdf.open(stream=resp.content, filetype="pdf")
    total_annots = 0
    for page in doc:
        a = page.first_annot
        while a:
            total_annots += 1
            a = a.next
    doc.close()
    assert total_annots > 0, "Downloaded document from editor must contain embedded error annotations!"


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

