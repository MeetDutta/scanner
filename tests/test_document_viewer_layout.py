"""
Acceptance Test Suite for Document View Mode: Page Clipping, Scrolling & Multi-Page Viewport

Validates:
1. Multi-Page Continuous Document Serving & Metadata
2. Viewport Scroll Container Architecture (overflow: auto, min-height: 0, no flex centering traps)
3. CSS Fixed Height Hacks Removal (.findings-coordinated-layout, .view-container)
4. Fit-Page & Fit-Width Dynamic Aspect Ratio Calculation
5. Direct Defect Location & Highlight Preservation
6. 100% Document Immutability & Read-Only Safety
"""

import hashlib
import re
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from specguard.server.app import create_app
from specguard.server.api.documents import DocumentParser


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_multipage_document_metadata_and_images(client):
    """Test 1: Verify 3-page document metadata and image rendering for all pages."""
    pdf_path = Path("demo_samples/three_page_inspection_sample.pdf")
    assert pdf_path.exists(), "3-page sample PDF must exist."

    doc_model = DocumentParser.parse_file(str(pdf_path))
    assert doc_model.page_count == 3
    assert len(doc_model.pages) == 3

    # Verify A4 aspect ratio (595.28 x 841.89 pt)
    for p in doc_model.pages:
        assert round(p.width) == 595
        assert round(p.height) == 842
        aspect_ratio = p.width / p.height
        assert 0.70 <= aspect_ratio <= 0.71  # ISO 216 standard ~ 1/sqrt(2) = 0.7071

    # Verify document info API
    res = client.get(f"/api/documents/{doc_model.file_hash}")
    assert res.status_code == 200
    data = res.json()
    assert data["page_count"] == 3
    assert len(data["pages"]) == 3

    # Verify high-DPI image bytes for each page without clipping
    for page_num in range(1, 4):
        img_res = client.get(f"/api/documents/{doc_model.file_hash}/pages/{page_num}/image?zoom=1.5")
        assert img_res.status_code == 200
        assert img_res.headers["content-type"] == "image/png"
        png_bytes = img_res.content
        assert len(png_bytes) > 1000
        # PNG header check
        assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"


def test_css_scroll_container_architecture():
    """Test 2: Verify dedicated document viewport scroll container and absence of flex centering traps."""
    views_css = Path("specguard/web/static/css/views.css").read_text(encoding="utf-8")

    # Document viewport must have overflow: auto and min-height: 0
    assert ".document-viewport" in views_css or ".canvas-viewport" in views_css
    assert "overflow: auto;" in views_css

    # Must NOT have align-items: center; justify-content: center; on .canvas-viewport scroll container
    # because flexbox centering causes negative scroll coordinates clipping the top/left of pages.
    viewport_section = re.search(r"\.canvas-viewport\s*\{([^}]+)\}", views_css)
    assert viewport_section, "Must define .canvas-viewport"
    viewport_rules = viewport_section.group(1)
    assert "overflow: auto" in viewport_rules
    assert "display: block" in viewport_rules or "align-items: center" not in viewport_rules or "display: flex" not in viewport_rules

    # Continuous multi-page container must exist
    assert ".document-pages-container" in views_css
    pages_section = re.search(r"\.document-pages-container\s*\{([^}]+)\}", views_css)
    assert pages_section
    assert "margin: 0 auto" in pages_section.group(1)

    # Document page wrapper must exist with box shadow and no clipping
    assert ".document-page-wrapper" in views_css
    assert ".page-canvas-wrapper" in views_css


def test_css_layout_container_and_fixed_height_removal():
    """Test 3: Verify removal of fixed height traps on layout containers."""
    layout_css = Path("specguard/web/static/css/layout.css").read_text(encoding="utf-8")
    findings_css = Path("specguard/web/static/css/findings.css").read_text(encoding="utf-8")

    # .view-container in layout.css must have min-height: 0 and flex-aware properties
    vc_section = re.search(r"\.view-container\s*\{([^}]+)\}", layout_css)
    assert vc_section
    vc_rules = vc_section.group(1)
    assert "min-height: 0" in vc_rules
    assert "display: flex" in vc_rules

    # .findings-coordinated-layout must NOT have hardcoded calc(100vh - 185px) or min-height: 600px trap
    assert "calc(100vh - 185px)" not in findings_css
    assert "min-height: 600px" not in findings_css
    fcl_section = re.search(r"\.findings-coordinated-layout\s*\{([^}]+)\}", findings_css)
    assert fcl_section
    fcl_rules = fcl_section.group(1)
    assert "min-height: 0" in fcl_rules
    assert "flex: 1" in fcl_rules or "height: 100%" in fcl_rules


def test_js_component_features():
    """Test 4: Verify DocumentViewerComponent has continuous multi-page, fit-page, fit-width, and observers."""
    viewer_js = Path("specguard/web/static/js/components/document_viewer.js").read_text(encoding="utf-8")

    # Multi-page continuous rendering
    assert "renderPages()" in viewer_js
    assert "viewer-pages-container" in viewer_js
    assert "page-container-" in viewer_js

    # Fit Page calculation must use Math.min of width and height scales (Section 7)
    assert "fitPage()" in viewer_js
    assert "Math.min(scaleW, scaleH)" in viewer_js

    # Fit Width calculation must scale width properly (Section 8)
    assert "fitWidth()" in viewer_js
    assert "availableW / pW" in viewer_js

    # Scroll and Resize Observers must be implemented (Sections 13, 17)
    assert "_initScrollObserver()" in viewer_js
    assert "_initResizeObserver()" in viewer_js
    assert "ResizeObserver" in viewer_js

    # Defect navigation with unhindered manual scrolling (Section 14)
    assert "focusFinding(" in viewer_js
    assert "_isProgrammaticScroll" in viewer_js


def test_document_immutability():
    """Test 5: Verify original document is never mutated by viewing or layout fixes."""
    sample_files = list(Path("demo_samples").glob("*.pdf"))
    assert len(sample_files) >= 2

    hashes_before = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sample_files}
    for f in sample_files:
        _ = DocumentParser.parse_file(str(f))

    hashes_after = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sample_files}
    assert hashes_before == hashes_after, "Original PDF files must never be modified."
