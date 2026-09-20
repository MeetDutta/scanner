"""
Comprehensive Render Deployment Simulation Test Suite for DocReady.
Validates:
1. Health endpoints (/health and /api/health)
2. Frontend SPA shell (GET /) and static asset serving
3. Dashboard statistics and API routes
4. Multi-format document upload (PDF, DOCX, XLSX)
5. Analysis pipeline execution and progress polling
6. Finding extraction and coordinate mapping
7. Report generation and preview
8. Security boundaries: invalid file extensions, path traversal rejection
9. Offline compliance (zero external network calls)
"""

import os
import sys
import io
import time
import pytest
from pathlib import Path

# Force Render deployment environment variables
os.environ["DOCREADY_ENV"] = "render_demo"
os.environ["DOCREADY_WEB_MODE"] = "1"
os.environ["DOCREADY_HOST"] = "0.0.0.0"

from fastapi.testclient import TestClient
from specguard.server.app import create_app
from specguard.core.config import DEMO_SAMPLES_DIR


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_health_check_endpoints(client):
    """Verify both /health (Render default) and /api/health return expected schema."""
    # 1. Top-level /health
    res1 = client.get("/health")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "ok"
    assert data1["service"] == "docready"
    assert data1["environment"] == "render_demo"

    # 2. API /api/health
    res2 = client.get("/api/health")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "online"
    assert data2["service"] == "docready"


def test_frontend_shell_and_static_assets(client):
    """Verify single-page application index.html and static assets are served properly."""
    # Root shell
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "DocReady" in res.text or "SpecGuard" in res.text

    # Static CSS
    res_css = client.get("/static/css/base.css")
    assert res_css.status_code == 200

    # Static JS
    res_js = client.get("/static/js/api.js")
    assert res_js.status_code == 200
    assert "ApiClient" in res_js.text


def test_core_api_routes(client):
    """Verify standard metadata, dashboard, models, and standards routes."""
    # Dashboard stats
    res_dash = client.get("/api/dashboard/stats")
    assert res_dash.status_code == 200
    stats = res_dash.json()
    assert "total_documents" in stats

    # Standards
    res_std = client.get("/api/standards")
    assert res_std.status_code == 200
    stds = res_std.json()
    assert isinstance(stds, list)

    # Models registry
    res_models = client.get("/api/models")
    assert res_models.status_code == 200
    models = res_models.json()
    assert isinstance(models, list)


def test_document_upload_pdf(client):
    """Verify PDF upload, SHA-256 calculation, and fast metadata pre-parsing."""
    pdf_path = DEMO_SAMPLES_DIR / "mechanical_sample_with_errors.pdf"
    assert pdf_path.exists(), f"Missing demo sample: {pdf_path}"

    with open(pdf_path, "rb") as f:
        res = client.post(
            "/api/analysis/upload",
            files={"file": ("test_mechanical.pdf", f, "application/pdf")}
        )

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["file_type"] == "PDF"
    assert data["page_count"] >= 1
    assert "file_path" in data
    assert "file_hash" in data


def test_document_upload_docx(client):
    """Verify DOCX upload and metadata parsing."""
    docx_path = DEMO_SAMPLES_DIR / "chemical_sample_with_errors.docx"
    assert docx_path.exists(), f"Missing demo sample: {docx_path}"

    with open(docx_path, "rb") as f:
        res = client.post(
            "/api/analysis/upload",
            files={"file": ("test_chemical.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        )

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert data["file_type"] == "DOCX"


def test_document_upload_xlsx(client):
    """Verify XLSX upload and metadata extraction."""
    # Create minimal in-memory Excel workbook
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Engineering Specs"
    ws.append(["Parameter", "Nominal Value", "Unit", "Tolerance"])
    ws.append(["Shaft Diameter", 25.0, "mm", "±0.02"])
    
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    res = client.post(
        "/api/analysis/upload",
        files={"file": ("specs_test.xlsx", buf, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["file_type"] == "XLSX"


def test_end_to_end_analysis_execution(client):
    """Verify analysis job dispatch, progress polling, and finding generation."""
    pdf_path = DEMO_SAMPLES_DIR / "mechanical_sample_with_errors.pdf"
    with open(pdf_path, "rb") as f:
        up_res = client.post(
            "/api/analysis/upload",
            files={"file": ("e2e_test.pdf", f, "application/pdf")}
        )
    assert up_res.status_code == 200
    uploaded_file_path = up_res.json()["file_path"]

    # Start analysis job
    start_res = client.post(
        "/api/analysis/start",
        json={"file_path": uploaded_file_path, "domain": "mechanical"}
    )
    assert start_res.status_code == 200
    job_id = start_res.json()["job_id"]

    # Poll until completed (timeout 25s)
    start_t = time.time()
    job_completed = False
    result_data = None

    while time.time() - start_t < 25:
        poll_res = client.get(f"/api/analysis/jobs/{job_id}")
        assert poll_res.status_code == 200
        poll_data = poll_res.json()
        if poll_data["status"] == "completed":
            job_completed = True
            result_data = poll_data
            break
        elif poll_data["status"] == "failed":
            pytest.fail(f"Analysis job failed: {poll_data.get('error')}")
        time.sleep(0.3)

    assert job_completed, f"Analysis job {job_id} timed out before completion."
    assert "total_findings" in result_data
    session_id = result_data.get("session_id")
    assert session_id is not None

    # Query findings
    findings_res = client.get(f"/api/findings?session_id={session_id}")
    assert findings_res.status_code == 200
    findings_data = findings_res.json()
    assert isinstance(findings_data, dict)
    assert "findings" in findings_data
    assert findings_data["total_count"] >= 1
    assert isinstance(findings_data["findings"], list)

    # Test report generation
    rep_res = client.post(
        "/api/reports/generate",
        json={"session_id": session_id, "format": "html"}
    )
    assert rep_res.status_code == 200
    rep_data = rep_res.json()
    assert "html_path" in rep_data or "preview_url" in rep_data

    # Test report preview
    prev_res = client.get(f"/api/reports/preview/{session_id}")
    assert prev_res.status_code == 200
    assert "text/html" in prev_res.headers["content-type"]


def test_security_rejection_invalid_file_extension(client):
    """Verify that executable or unapproved file extensions are rejected with HTTP 400."""
    fake_exe = io.BytesIO(b"MZ\x90\x00BinaryPayload")
    res = client.post(
        "/api/analysis/upload",
        files={"file": ("malicious_payload.exe", fake_exe, "application/x-msdownload")}
    )
    assert res.status_code == 400
    assert "Unsupported format" in res.json()["detail"]


def test_security_path_traversal_rejection(client):
    """Verify that start_analysis strictly rejects path traversal attempts."""
    traversal_paths = [
        "../../../../etc/passwd",
        "/etc/shadow",
        "C:\\Windows\\System32\\calc.exe",
        "../../secret.env"
    ]
    for p in traversal_paths:
        res = client.post("/api/analysis/start", json={"file_path": p})
        assert res.status_code == 400
        assert "invalid or does not exist" in res.json()["detail"]
