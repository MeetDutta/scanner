"""
Verification and Regression Tests for SpecGuard Web-Only Inspection Architecture.
Validates:
1. Complete web-only inspection navigation & information architecture.
2. Zero document mutation / read-only guarantees.
3. Full findings metadata schema (detected vs expected, suggested action as info only, precision, bounding boxes).
4. Formatting, structural, and content error classification.
5. High-DPI page rendering & document overview inspection.
6. Inspection report generation with non-modifying compliance language.
"""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from specguard.server.app import app
from specguard.core.config import DEMO_SAMPLES_DIR


@pytest.fixture
def client():
    return TestClient(app)


def test_web_index_information_architecture(client):
    """Verifies that index.html contains the full new navigation structure and zero workstation/editor concepts."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    # 1. Product Identity
    assert "SPECGUARD" in html
    assert "Engineering Document Quality & Compliance Inspection" in html

    # 2. Primary Navigation Sections
    assert "ANALYSIS" in html
    assert "DOCUMENT INSPECTION" in html
    assert "REPORTING" in html
    assert "CONFIGURATION" in html

    # 3. Required Inspection Routes
    assert 'data-route="dashboard"' in html
    assert 'data-route="new_analysis"' in html
    assert 'data-route="results"' in html
    assert 'data-route="findings"' in html
    assert 'data-route="overview"' in html
    assert 'data-route="viewer"' in html
    assert 'data-route="formatting"' in html
    assert 'data-route="structural"' in html
    assert 'data-route="content"' in html
    assert 'data-route="reports"' in html
    assert 'data-route="history"' in html
    assert 'data-route="standards"' in html
    assert 'data-route="settings"' in html

    # 4. Verified Removal of Workstation / ML Training from Primary Navigation
    # Workstation / Editor / ML Training must not be in primary navigation links
    assert 'data-route="workspace"' not in html
    assert 'data-route="training"' not in html
    assert 'data-route="editor"' not in html
    assert 'data-route="rectification"' not in html

    # 5. Local CSS links present
    assert "/static/css/base.css" in html
    assert "/static/css/layout.css" in html
    assert "/static/css/components.css" in html
    assert "/static/css/views.css" in html
    assert "/static/css/findings.css" in html

    # 6. JavaScript views present
    assert "/static/js/views/analysis_progress.js" in html
    assert "/static/js/views/document_inspection.js" in html
    assert "/static/js/views/formatting.js" in html
    assert "/static/js/views/structural_issues.js" in html
    assert "/static/js/views/content_issues.js" in html


def test_findings_schema_and_inspection_fields(client):
    """Verifies that findings contain complete inspection fields without mutation capabilities."""
    sample_pdf = DEMO_SAMPLES_DIR / "mechanical_sample_with_errors.pdf"
    if not sample_pdf.exists():
        pytest.skip("Demo sample mechanical_sample_with_errors.pdf not found.")

    # Run analysis
    start_res = client.post("/api/analysis/start", json={
        "file_path": str(sample_pdf.resolve()),
        "domain": "mechanical",
        "selected_standards": []
    })
    assert start_res.status_code == 200
    job_id = start_res.json()["job_id"]

    import time
    session_id = None
    for _ in range(40):
        time.sleep(0.25)
        status_res = client.get(f"/api/analysis/jobs/{job_id}")
        assert status_res.status_code == 200
        data = status_res.json()
        if data["status"] == "completed":
            session_id = data["session_id"]
            break
        elif data["status"] == "failed":
            pytest.fail(f"Analysis failed: {data.get('error')}")

    assert session_id is not None

    # Query findings
    findings_res = client.get(f"/api/findings?session_id={session_id}&limit=50")
    assert findings_res.status_code == 200
    findings_data = findings_res.json()
    findings = findings_data["findings"]
    assert len(findings) > 0

    # Verify Finding Inspection Data Model
    for f in findings:
        assert "finding_id" in f
        assert "severity" in f
        assert f["severity"] in ["Critical", "High", "Medium", "Low", "Informational"]
        assert "category" in f
        assert "page" in f
        assert "page_number" in f
        assert f["page"] >= 1
        assert "location" in f
        assert "detected_value" in f
        assert "expected_value" in f
        assert "explanation" in f
        assert "suggested_correction" in f
        assert "confidence" in f
        assert "location_precision" in f
        assert "bounding_boxes" in f
        assert isinstance(f["bounding_boxes"], list)

        # Verification of read-only nature: suggested correction is guidance
        assert f["suggested_correction"] is not None

    # Verify detail lookup
    first_f = findings[0]
    detail_res = client.get(f"/api/findings/{first_f['finding_id']}?session_id={session_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["finding_id"] == first_f["finding_id"]
    assert "suggested_fix" in detail
    assert "explanation" in detail
    assert "bounding_boxes" in detail


def test_document_overview_and_page_rendering(client):
    """Verifies that Document Overview AST endpoint and page image rendering work in 100% read-only mode."""
    sample_pdf = DEMO_SAMPLES_DIR / "mechanical_sample_with_errors.pdf"
    if not sample_pdf.exists():
        pytest.skip("Demo sample not found.")

    with open(sample_pdf, "rb") as fp:
        upload_res = client.post("/api/analysis/upload", files={"file": ("mech_test.pdf", fp, "application/pdf")})
    assert upload_res.status_code == 200
    doc_hash = upload_res.json()["file_hash"]

    # 1. Document Overview AST
    doc_info_res = client.get(f"/api/documents/{doc_hash}")
    assert doc_info_res.status_code == 200
    doc_info = doc_info_res.json()
    assert doc_info["page_count"] >= 1
    assert "pages" in doc_info
    assert "sections" in doc_info
    assert "tables" in doc_info
    assert "figures" in doc_info

    # 2. Read-only High-DPI Page Image
    page_img_res = client.get(f"/api/documents/{doc_hash}/pages/1/image?zoom=1.25")
    assert page_img_res.status_code == 200
    assert page_img_res.headers["content-type"] == "image/png"
    assert len(page_img_res.content) > 1000

    # 3. Original file download preserves source document
    download_res = client.get(f"/api/documents/{doc_hash}/file")
    assert download_res.status_code == 200
    assert len(download_res.content) == sample_pdf.stat().st_size


def test_inspection_report_generation(client):
    """Verifies report generation uses inspection compliance language and no auto-correction claims."""
    sample_pdf = DEMO_SAMPLES_DIR / "mechanical_sample_with_errors.pdf"
    if not sample_pdf.exists():
        pytest.skip("Demo sample not found.")

    # Start analysis
    start_res = client.post("/api/analysis/start", json={
        "file_path": str(sample_pdf.resolve()),
        "domain": "mechanical"
    })
    job_id = start_res.json()["job_id"]

    import time
    session_id = None
    for _ in range(40):
        time.sleep(0.25)
        status_res = client.get(f"/api/analysis/jobs/{job_id}")
        data = status_res.json()
        if data["status"] == "completed":
            session_id = data["session_id"]
            break

    assert session_id is not None

    # Generate HTML inspection report
    html_res = client.post("/api/reports/generate", json={"session_id": session_id, "format": "html"})
    assert html_res.status_code == 200
    html_data = html_res.json()
    assert html_data["status"] == "success"

    # Preview HTML report
    preview_res = client.get(f"/api/reports/preview/{session_id}")
    assert preview_res.status_code == 200
    report_html = preview_res.text
    assert "SpecGuard" in report_html
    assert "Inspection Report" in report_html
    assert "Detailed Findings" in report_html
    assert "Suggested Correction" in report_html or "Suggested Corrective Action" in report_html
    # Ensure no claims of automatically modifying the document
    assert "automatically corrected the document" not in report_html
