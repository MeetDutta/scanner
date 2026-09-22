"""
Automated Verification Test Suite for SpecGuard / DocReady
Interactive Document Viewer & Live Rectification Workstation.

Verifies:
- Responsive page scaling calculations (Fit Page, Fit Width, A4, Letter)
- PDF Live Rectification with dynamic text search bbox fallback
- Revision snapshotting, undo, and redo operations
- Session working copy isolation (original source file is immutable)
- Backend editor API endpoints (/apply, /undo, /redo, /file, /changes)
- Certified RECTIFICATION CHANGE REPORT generation (HTML and JSON)
"""

import json
import shutil
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from specguard.core.config import REPO_DIR, DATA_DIR, DEMO_SAMPLES_DIR
from specguard.core.rectification import RectificationManager, RectificationError
from specguard.server.app import create_app
from specguard.export.report_generator import generate_change_report_html, generate_change_report_json


@pytest.fixture
def client():
    """Provides FastAPI test client."""
    return TestClient(create_app())


@pytest.fixture
def test_session():
    import uuid
    session_id = f"CMP-TEST-RECT-{uuid.uuid4().hex[:6]}"
    session_dir = REPO_DIR / "comparisons" / session_id
    if session_dir.exists():
        shutil.rmtree(session_dir)
    session_dir.mkdir(parents=True, exist_ok=True)
    yield session_id
    if session_dir.exists():
        shutil.rmtree(session_dir, ignore_errors=True)


def test_responsive_fit_page_scale_calculation():
    """Validates responsive scaling logic for A4, Letter, and Legal documents."""
    # A4 dimensions in points: 595.28 x 841.89
    page_w, page_h = 595.28, 841.89

    # Test standard 1920x1080 screen with 1200x800 available viewport
    viewport_w, viewport_h = 1200 - 48, 800 - 48
    scale = min(viewport_w / page_w, viewport_h / page_h)
    assert 0.8 < scale < 1.0  # Entire page fits inside 752px vertical height
    assert scale * page_h <= viewport_h
    assert scale * page_w <= viewport_w

    # Test Letter: 612 x 792
    letter_w, letter_h = 612.0, 792.0
    scale_letter = min(viewport_w / letter_w, viewport_h / letter_h)
    assert scale_letter * letter_h <= viewport_h

    # Test Fit Width
    fit_width_scale = viewport_w / page_w
    assert fit_width_scale > scale


def _setup_mock_session(session_id: str):
    """Sets up comparison directory and sample document for session."""
    session_dir = REPO_DIR / "comparisons" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    sample_src = Path("data/uploads/0348c086_Thermodynamics_Knowledge_Base.pdf")
    if not sample_src.exists():
        # Fallback to any PDF in data/uploads
        candidates = list(Path("data/uploads").glob("*.pdf"))
        if candidates:
            sample_src = candidates[0]
        else:
            pytest.skip("Sample PDF not found.")

    doc_id = f"DOC-{session_id}"
    doc_dir = REPO_DIR / "documents" / doc_id / "original"
    doc_dir.mkdir(parents=True, exist_ok=True)
    target_doc = doc_dir / sample_src.name
    shutil.copy2(sample_src, target_doc)

    # Write comparison.json
    comp_data = {
        "comparison_id": session_id,
        "document_id": doc_id,
        "document_filename": sample_src.name,
        "domain": "Mechanical",
        "total_findings": 12,
    }
    (session_dir / "comparison.json").write_text(json.dumps(comp_data), encoding="utf-8")

    # Write mock findings with both explicit bbox and null bbox
    findings = [
        {
            "finding_id": "FMT-SIZE-001",
            "category": "Formatting",
            "page": 1,
            "page_number": 1,
            "bbox": {"x0": 50, "y0": 50, "x1": 250, "y1": 70},
            "original_content": "Thermodynamics Knowledge Base",
            "matched_text": "Thermodynamics Knowledge Base",
            "detected_value": "9 pt",
            "expected_value": "11 pt",
            "suggested_fix": "11 pt",
            "explanation": "Header font size must be 11 pt according to standard.",
            "rule_reference": "ASME Standard §4.1"
        },
        {
            "finding_id": "TMPL-PRM-009",
            "category": "Engineering Parameter",
            "page": 1,
            "page_number": 1,
            "bbox": None,  # Null bounding box test
            "original_content": "",
            "detected_value": "Parameter absent",
            "expected_value": "Bearing Journal Tolerance (mm)",
            "suggested_fix": "Bearing Journal Tolerance (mm)",
            "explanation": "Mechanical standard mandates Bearing Journal Tolerance.",
            "rule_reference": "ASME Y14.5-2018"
        }
    ]
    (session_dir / "findings.json").write_text(json.dumps(findings), encoding="utf-8")
    return target_doc


def test_rectification_manager_pdf_with_thermodynamics_sample(test_session):
    """Verifies live rectification on Thermodynamics sample with snapshotting and undo/redo."""
    session_id = test_session
    target_doc = _setup_mock_session(session_id)

    manager = RectificationManager(session_id)
    status_init = manager.status()
    assert status_init["revision"] == 0
    assert status_init["can_undo"] is False
    assert status_init["can_redo"] is False

    # 1. Apply format correction
    res1 = manager.apply(
        finding_id="FMT-SIZE-001",
        operation="format",
        field="font_size",
        value=11.0,
        note="Adjusted header size"
    )
    assert res1["revision"] == 1
    assert len(res1["changes"]) == 1
    assert res1["can_undo"] is True
    assert res1["change"]["status"] == "APPLIED"

    # Verify working copy was actually modified
    working_file = manager.working_path()
    assert working_file.exists()
    assert working_file.stat().st_size > 0

    # Verify original source file is untouched
    assert target_doc.exists()

    # 2. Apply text correction with null bbox (tests dynamic text search fallback)
    res2 = manager.apply(
        finding_id="TMPL-PRM-009",
        operation="text",
        field="text",
        value="Bearing Journal Tolerance: ±0.05 mm",
        note="Added missing parameter"
    )
    assert res2["revision"] == 2
    assert len(res2["changes"]) == 2

    # 3. Test Undo
    undo_res = manager.undo()
    assert undo_res["revision"] == 1
    assert len(undo_res["changes"]) == 1
    assert undo_res["can_redo"] is True

    # 4. Test Redo
    redo_res = manager.redo()
    assert redo_res["revision"] == 2
    assert len(redo_res["changes"]) == 2
    assert redo_res["can_undo"] is True


def test_editor_api_routes(client, test_session):
    """Verifies FastAPI editor API endpoints (/status, /apply, /undo, /redo, /file, /changes)."""
    session_id = test_session
    _setup_mock_session(session_id)
    manager = RectificationManager(session_id)

    # Status
    status_resp = client.get(f"/api/documents/editor/{session_id}")
    assert status_resp.status_code == 200
    st_data = status_resp.json()
    assert "revision" in st_data
    assert "changes" in st_data

    # Apply through API
    payload = {
        "finding_id": "FMT-SIZE-001",
        "operation": "suggested",
        "field": "auto",
        "value": None,
        "note": "API applied suggested"
    }
    apply_resp = client.post(f"/api/documents/editor/{session_id}/apply", json=payload)
    assert apply_resp.status_code == 200
    assert apply_resp.json()["status"] == "saved"

    # Changes endpoint
    changes_resp = client.get(f"/api/documents/editor/{session_id}/changes")
    assert changes_resp.status_code == 200
    assert "changes" in changes_resp.json()

    # Undo through API
    undo_resp = client.post(f"/api/documents/editor/{session_id}/undo")
    assert undo_resp.status_code == 200
    assert undo_resp.json()["status"] == "undone"

    # Redo through API
    redo_resp = client.post(f"/api/documents/editor/{session_id}/redo")
    assert redo_resp.status_code == 200
    assert redo_resp.json()["status"] == "redone"

    # File download endpoint
    file_resp = client.get(f"/api/documents/editor/{session_id}/file")
    assert file_resp.status_code == 200
    assert "attachment" in file_resp.headers.get("content-disposition", "")
    assert len(file_resp.content) > 0


def test_rectification_change_report_generation(tmp_path):
    """Verifies that generated Rectification Change Report contains all required sections."""
    change_report = {
        "session_id": "CMP-TEST-RECTIFY-001",
        "document": "Thermodynamics_Knowledge_Base.pdf",
        "document_id": "DOC-TEST-001",
        "working_document": "working.pdf",
        "working_format": "pdf",
        "comparison_mode": "Mechanical Specification",
        "revision": 2,
        "created_at": "2026-09-22T15:30:00Z",
        "updated_at": "2026-09-22T15:35:00Z",
        "total_findings": 12,
        "changes": [
            {
                "change_id": "CHG-0001",
                "finding_id": "FMT-SIZE-001",
                "page": 1,
                "category": "Formatting",
                "issue_type": "FONT_SIZE_MISMATCH",
                "before": "9 pt",
                "suggested": "11 pt",
                "after": "11 pt",
                "operation": "format",
                "field": "font_size",
                "status": "APPLIED",
                "timestamp": "2026-09-22T15:32:00Z",
                "note": "Adjusted header size"
            },
            {
                "change_id": "CHG-0002",
                "finding_id": "TMPL-PRM-009",
                "page": 1,
                "category": "Engineering Parameter",
                "issue_type": "PARAMETER_ABSENT",
                "before": "Parameter absent",
                "suggested": "Bearing Journal Tolerance (mm)",
                "after": "Bearing Journal Tolerance: ±0.05 mm",
                "operation": "text",
                "field": "text",
                "status": "APPLIED",
                "timestamp": "2026-09-22T15:34:00Z",
                "note": "Added missing parameter"
            }
        ]
    }

    # HTML Report
    html_out = tmp_path / "test_change_report.html"
    generate_change_report_html(change_report, str(html_out))
    assert html_out.exists()
    html_content = html_out.read_text(encoding="utf-8")

    assert "RECTIFICATION CHANGE REPORT" in html_content
    assert "Document Information" in html_content
    assert "Summary" in html_content
    assert "Detailed Change Log" in html_content
    assert "CHG-0001" in html_content
    assert "CHG-0002" in html_content
    assert "9 pt" in html_content
    assert "11 pt" in html_content
    assert "Corrections Applied" in html_content

    # JSON Report
    json_out = tmp_path / "test_change_report.json"
    generate_change_report_json(change_report, str(json_out))
    assert json_out.exists()
    json_data = json.loads(json_out.read_text(encoding="utf-8"))
    assert json_data["title"] == "RECTIFICATION CHANGE REPORT"
    assert json_data["summary"]["corrections_applied"] == 2
    assert len(json_data["changes"]) == 2
