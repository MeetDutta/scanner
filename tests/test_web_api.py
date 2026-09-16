"""
Comprehensive Integration Tests for SpecGuard Local Web API.
Verifies all REST API endpoints, document rendering, stage progress, and offline integrity.
"""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from specguard.server.app import app
from specguard.core.config import DEMO_SAMPLES_DIR


@pytest.fixture
def client():
    """Provides FastAPI test client."""
    return TestClient(app)


def test_health_endpoint(client):
    """Verifies health check and 100% offline status."""
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "online"
    assert data["mode"] == "offline"
    assert data["name"] == "SpecGuard"


def test_dashboard_endpoints(client):
    """Verifies operational statistics and recent verifications from SQLite."""
    res = client.get("/api/dashboard/stats")
    assert res.status_code == 200
    stats = res.json()
    assert stats["offline_mode"] is True
    assert "total_analyses" in stats
    assert "severity_distribution" in stats
    assert "domain_distribution" in stats

    res_recent = client.get("/api/dashboard/recent?limit=5")
    assert res_recent.status_code == 200
    recent = res_recent.json()
    assert "recent_comparisons" in recent
    assert "recent_documents" in recent


def test_standards_and_templates_endpoints(client):
    """Verifies domain templates and installed standards."""
    res = client.get("/api/standards")
    assert res.status_code == 200
    templates = res.json()
    assert len(templates) == 3
    domains = [t["domain_key"] for t in templates]
    assert "mechanical" in domains
    assert "electrical" in domains
    assert "chemical" in domains

    # Verify Mechanical template detail
    res_mech = client.get("/api/standards/mechanical")
    assert res_mech.status_code == 200
    mech_data = res_mech.json()
    assert "sections" in mech_data
    assert "parameters" in mech_data
    assert "rules" in mech_data
    assert len(mech_data["sections"]) > 0


def test_models_and_hardware_endpoints(client):
    """Verifies local model registry and hardware detection."""
    res_hw = client.get("/api/models/hardware")
    assert res_hw.status_code == 200
    hw = res_hw.json()
    assert "device" in hw
    assert "cpu_cores" in hw
    assert "ram_gb" in hw

    res_models = client.get("/api/models")
    assert res_models.status_code == 200
    models = res_models.json()
    assert isinstance(models, list)

    res_dataset = client.get("/api/models/dataset-health")
    assert res_dataset.status_code == 200
    health = res_dataset.json()
    assert "total_annotations" in health


def test_settings_endpoints(client):
    """Verifies pre-flight diagnostics and storage telemetry."""
    res_health = client.get("/api/settings/health")
    assert res_health.status_code == 200
    report = res_health.json()
    assert "python_version" in report
    assert "packages" in report

    res_storage = client.get("/api/settings/storage")
    assert res_storage.status_code == 200
    storage = res_storage.json()
    assert "database" in storage
    assert "repository" in storage
    assert storage["offline_verified"] is True

    res_audit = client.get("/api/settings/audit?limit=5")
    assert res_audit.status_code == 200
    audit = res_audit.json()
    assert "logs" in audit


def test_history_and_findings_endpoints(client):
    """Verifies comparison history and findings queries."""
    res_hist = client.get("/api/history?limit=5")
    assert res_hist.status_code == 200
    hist = res_hist.json()
    assert "comparisons" in hist

    if hist["comparisons"]:
        sample_cmp = hist["comparisons"][0]
        cmp_id = sample_cmp["comparison_id"]

        # Detail query
        res_detail = client.get(f"/api/history/{cmp_id}")
        assert res_detail.status_code == 200
        detail = res_detail.json()
        assert detail["comparison_id"] == cmp_id

        # Findings query
        res_findings = client.get(f"/api/findings?comparison_id={cmp_id}")
        assert res_findings.status_code == 200
        f_data = res_findings.json()
        assert "findings" in f_data


def test_document_page_image_rendering(client):
    """Verifies high-DPI PyMuPDF page rendering endpoint for browser viewer."""
    sample_pdf = DEMO_SAMPLES_DIR / "mechanical_sample_with_errors.pdf"
    if not sample_pdf.exists():
        pytest.skip("Demo sample not found.")

    # Upload document to get hash
    with open(sample_pdf, "rb") as f:
        upload_res = client.post("/api/analysis/upload", files={"file": ("test.pdf", f, "application/pdf")})
    assert upload_res.status_code == 200
    doc_data = upload_res.json()
    doc_hash = doc_data["file_hash"]

    # Render page 1 image
    img_res = client.get(f"/api/documents/{doc_hash}/pages/1/image?zoom=1.0")
    assert img_res.status_code == 200
    assert img_res.headers["content-type"] == "image/png"
    assert len(img_res.content) > 1000  # valid PNG bytes


def test_full_analysis_workflow_via_api(client):
    """Verifies complete end-to-end analysis triggering, status checking, and report generation."""
    sample_pdf = DEMO_SAMPLES_DIR / "mechanical_sample_with_errors.pdf"
    if not sample_pdf.exists():
        pytest.skip("Demo sample not found.")

    # 1. Trigger analysis
    start_res = client.post("/api/analysis/start", json={
        "file_path": str(sample_pdf.resolve()),
        "domain": "mechanical",
        "selected_standards": []
    })
    assert start_res.status_code == 200
    job_id = start_res.json()["job_id"]

    # 2. Wait for completion
    import time
    completed = False
    session_id = None
    for _ in range(30):
        time.sleep(0.3)
        job_res = client.get(f"/api/analysis/jobs/{job_id}")
        assert job_res.status_code == 200
        job_data = job_res.json()
        if job_data["status"] == "completed":
            completed = True
            session_id = job_data["session_id"]
            break
        elif job_data["status"] == "failed":
            pytest.fail(f"Analysis failed: {job_data.get('error')}")

    assert completed is True
    assert session_id is not None

    # 3. Generate HTML & JSON reports
    rep_html = client.post("/api/reports/generate", json={"session_id": session_id, "format": "html"})
    assert rep_html.status_code == 200
    assert rep_html.json()["format"] == "html"

    rep_json = client.post("/api/reports/generate", json={"session_id": session_id, "format": "json"})
    assert rep_json.status_code == 200
    assert rep_json.json()["format"] == "json"
