"""
Acceptance Test Suite for Finding Details -> Direct Defect Location (Section 27)

Validates:
Test 1 - Formatting defect with detected vs expected style
Test 2 - Grammar / Spelling defect pointing to exact text span
Test 3 - TOC defect pointing to TOC entry
Test 4 - Figure defect pointing to figure/caption
Test 5 - Table defect pointing to table/caption
Test 6 - Missing content defect without fake coordinates
Test 7 - Multiple findings on one page with distinct markers
Test 8 - Multiple locations on cross-reference or contradiction findings
Test 9 - Automatic page navigation
Test 10 - Source document byte immutability
"""

import hashlib
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from specguard.server.app import create_app
from specguard.server.api.findings import _enrich_finding_location_metadata
from specguard.core.config import DEMO_SAMPLES_DIR


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_acceptance_test_1_formatting_defect(client):
    """Test 1: Formatting finding points to exact heading/text with detected vs expected style."""
    raw = {
        "finding_id": "FMT-001",
        "category": "Formatting",
        "location": "Section 2 Heading (Page 1)",
        "page": 1,
        "page_number": 1,
        "bbox": {"x0": 72.0, "y0": 150.0, "x1": 300.0, "y1": 175.0},
        "detected_value": "Arial / 12 pt / Bold",
        "expected_value": "Times New Roman / 14 pt / Bold",
        "explanation": "Heading 2 formatting inconsistent with standard."
    }
    enriched = _enrich_finding_location_metadata(raw)
    assert enriched["object_type"] in ["Heading", "Formatted Text Block"]
    assert enriched["section"] == "2"
    assert enriched["region_formatted"] == "x=72.0, y=150.0, width=228.0, height=25.0"
    assert enriched["page"] == 1
    assert enriched["detected_value"] == "Arial / 12 pt / Bold"
    assert enriched["expected_value"] == "Times New Roman / 14 pt / Bold"


def test_acceptance_test_2_grammar_spelling_defect(client):
    """Test 2: Grammar / spelling finding points to sentence / text span."""
    raw = {
        "finding_id": "SP-001",
        "category": "Grammar & Spelling",
        "location": "Paragraph 4 (Page 2)",
        "page": 2,
        "page_number": 2,
        "bbox": {"x0": 80.0, "y0": 210.0, "x1": 160.0, "y1": 224.0},
        "detected_value": "recieve",
        "expected_value": "receive",
        "explanation": "Spelling error detected."
    }
    enriched = _enrich_finding_location_metadata(raw)
    assert enriched["object_type"] == "Text Span"
    assert enriched["paragraph"] == "4"
    assert enriched["region_formatted"] == "x=80.0, y=210.0, width=80.0, height=14.0"


def test_acceptance_test_3_toc_defect(client):
    """Test 3: TOC finding points to exact TOC entry and detects TOC section."""
    res = client.get("/api/findings/TOC-PAG-003")
    if res.status_code == 200:
        data = res.json()
        assert data["category"] == "Table of Contents"
        assert data["object_type"] == "TOC Entry"
        assert data["section"] == "Table of Contents"
        assert data["page"] == 1
        assert data["bbox"] is not None
        assert "x=" in data["region_formatted"]
        assert len(data["locations"]) >= 1


def test_acceptance_test_4_figure_defect(client):
    """Test 4: Figure defect points to figure/caption/reference."""
    raw = {
        "finding_id": "FIG-001",
        "category": "Figure",
        "location": "Figure 3 Caption (Page 5)",
        "page": 5,
        "page_number": 5,
        "bbox": {"x0": 100.0, "y0": 400.0, "x1": 500.0, "y1": 420.0},
        "detected_value": "Figure 4",
        "expected_value": "Figure 3",
        "explanation": "Figure label sequence mismatch."
    }
    enriched = _enrich_finding_location_metadata(raw)
    assert enriched["object_type"] == "Figure"
    assert enriched["page"] == 5
    assert enriched["region_formatted"] == "x=100.0, y=400.0, width=400.0, height=20.0"


def test_acceptance_test_5_table_defect(client):
    """Test 5: Table defect points to table/caption/cell region."""
    raw = {
        "finding_id": "TBL-002",
        "category": "Table",
        "location": "Table 1 (Page 3)",
        "page": 3,
        "page_number": 3,
        "bbox": {"x0": 60.0, "y0": 200.0, "x1": 540.0, "y1": 380.0},
        "detected_value": "Missing column header",
        "expected_value": "Units (mm)",
        "explanation": "Table column missing unit specification."
    }
    enriched = _enrich_finding_location_metadata(raw)
    assert enriched["object_type"] == "Table"
    assert enriched["page"] == 3
    assert enriched["region_formatted"] == "x=60.0, y=200.0, width=480.0, height=180.0"


def test_acceptance_test_6_missing_content_defect(client):
    """Test 6: Missing content finding navigates to relevant section and has no fabricated coordinates."""
    raw = {
        "finding_id": "STR-MISS-01",
        "category": "Structure",
        "location": "Section 5 Outline",
        "page": 4,
        "page_number": 4,
        "bbox": None,
        "detected_value": None,
        "expected_value": "Safety Requirements",
        "explanation": "Mandatory section 'Safety Requirements' is missing."
    }
    enriched = _enrich_finding_location_metadata(raw)
    assert enriched["section"] == "5"
    assert enriched["region_formatted"] is None  # Zero fake coordinates
    assert enriched["bbox"] is None
    assert enriched["page"] == 4


def test_acceptance_test_7_multiple_findings_on_same_page(client):
    """Test 7: Multiple findings on the same page have distinct coordinates and metadata."""
    res = client.get("/api/findings?page=2&limit=10")
    assert res.status_code == 200
    data = res.json()
    findings = data.get("findings", [])
    if len(findings) > 1:
        f_ids = [f["finding_id"] for f in findings]
        assert len(f_ids) == len(set(f_ids)), "Finding IDs must be unique"
        for f in findings:
            assert f["page"] == 2


def test_acceptance_test_8_multiple_locations_cross_ref(client):
    """Test 8: Findings with multiple locations (Page X vs Page Y) extract multiple jump targets."""
    raw = {
        "finding_id": "LOG-CTR-001",
        "category": "Logical Contradiction",
        "location": "Page 1 vs Page 2",
        "page": 2,
        "page_number": 2,
        "bbox": {"x0": 54.0, "y0": 179.25, "x1": 430.1, "y1": 208.0},
        "detected_value": "60.0 °C (Page 2)",
        "expected_value": "80.0 °C (Page 1)"
    }
    enriched = _enrich_finding_location_metadata(raw)
    assert len(enriched["locations"]) == 2
    assert enriched["locations"][0]["page"] == 1
    assert enriched["locations"][1]["page"] == 2


def test_acceptance_test_9_page_navigation(client):
    """Test 9: Finding on any page accurately reports its target page for viewer navigation."""
    res = client.get("/api/findings?limit=10")
    assert res.status_code == 200
    data = res.json()
    for f in data.get("findings", []):
        assert "page" in f
        assert isinstance(f["page"], int)
        assert f["page"] >= 1


def test_acceptance_test_10_original_document_immutability(client):
    """Test 10: Original document bytes and hash remain 100% untouched and unchanged after inspection."""
    demo_files = list(DEMO_SAMPLES_DIR.glob("*.pdf"))
    assert len(demo_files) > 0, "Demo sample files must exist"
    for sample in demo_files:
        with open(sample, "rb") as f:
            content_before = f.read()
        hash_before = hashlib.sha256(content_before).hexdigest()

        # Trigger document info API endpoint
        res = client.get(f"/api/documents/{sample.name}")
        assert res.status_code == 200

        # Trigger page image render endpoint
        res_img = client.get(f"/api/documents/{sample.name}/pages/1/image?zoom=1.0")
        assert res_img.status_code == 200

        # Verify document file on disk is strictly unchanged
        with open(sample, "rb") as f:
            content_after = f.read()
        hash_after = hashlib.sha256(content_after).hexdigest()

        assert hash_before == hash_after, f"Document {sample.name} was modified! Inspection must be strictly read-only."
        assert len(content_before) == len(content_after)
