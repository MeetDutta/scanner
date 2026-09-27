"""
Tests for SpecGuard Dashboard Empty State and Production Cleanliness.
Verifies:
1. No fake fallback documents ('Engineering Specification', 'Academic', 'Pages: 5', fake heatmaps).
2. Clean separation of EMPTY vs ANALYZING vs COMPLETED vs FAILED states.
3. Proper handling of empty history across all sidebar routes.
4. Factual 'Local / LAN Mode' indicator.
"""

import re
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from specguard.server.app import create_app
from specguard.storage.database import DatabaseManager


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_clean_backend_state(client):
    """Verify backend returns 0 records and empty structures on clean state."""
    res_recent = client.get("/api/dashboard/recent")
    assert res_recent.status_code == 200
    recent_data = res_recent.json()
    assert isinstance(recent_data["recent_comparisons"], list)

    res_findings = client.get("/api/findings?session_id=nonexistent_session")
    assert res_findings.status_code == 200
    assert res_findings.json()["findings"] == []
    assert res_findings.json()["total_count"] == 0

    res_samples = client.get("/api/analysis/samples")
    assert res_samples.status_code == 200
    assert res_samples.json() == []


def test_dashboard_js_no_fake_fallbacks():
    """Verify dashboard.js has no hardcoded demo fallbacks or fake page counts."""
    dash_js = Path("specguard/web/static/js/views/dashboard.js").read_text(encoding="utf-8")

    # Must NOT have fallback to "Engineering Specification"
    assert '"Engineering Specification"' not in dash_js
    assert "'Engineering Specification'" not in dash_js

    # Must NOT have hardcoded 5 pages fallback
    assert "|| 5" not in dash_js
    assert "length: 5" not in dash_js
    assert "[1, 2, 3, 4, 5]" not in dash_js
    assert "[1,2,3,4,5]" not in dash_js

    # Must have distinct renderEmpty method
    assert "renderEmpty(" in dash_js
    assert "renderAnalyzing(" in dash_js
    assert "renderCompleted(" in dash_js
    assert "renderFailed(" in dash_js

    # Empty state must include "No Analysis Available" and "+ New Analysis"
    assert "No Analysis Available" in dash_js
    assert "+ New Analysis" in dash_js

    # Inspection button must be renamed from Canvas to Document Inspection
    assert "Open Document Inspection" in dash_js
    assert "Open Canvas Inspection" not in dash_js

    # Recent Analyses must be conditional on actual history
    assert "recentComparisons && recentComparisons.length > 0" in dash_js or "hasHistory" in dash_js


def test_state_js_clean_initial_state():
    """Verify state.js does not initialize fake active domain or document."""
    state_js = Path("specguard/web/static/js/state.js").read_text(encoding="utf-8")

    # activeDomain should be null initially, not hardcoded
    assert "activeDomain: null" in state_js
    assert "activeDocument: null" in state_js
    assert "activeSessionId: null" in state_js
    assert "activeFindings: null" in state_js
    assert "totalPages: null" in state_js


def test_sidebar_views_empty_state_handling():
    """Verify all routes requiring an analysis show clean empty state when no document loaded."""
    views_to_check = [
        "specguard/web/static/js/views/findings.js",
        "specguard/web/static/js/views/results.js",
        "specguard/web/static/js/views/document_inspection.js",
        "specguard/web/static/js/views/viewer.js",
        "specguard/web/static/js/views/formatting.js",
        "specguard/web/static/js/views/structural_issues.js",
        "specguard/web/static/js/views/content_issues.js",
        "specguard/web/static/js/views/reports.js"
    ]

    for v_path in views_to_check:
        content = Path(v_path).read_text(encoding="utf-8")
        assert "No Analysis Available" in content, f"{v_path} must handle empty state with 'No Analysis Available'"
        assert "Start New Analysis" in content or "new_analysis" in content, f"{v_path} must provide link to start new analysis"


def test_history_empty_message():
    """Verify history.js displays 'No previous analyses.' when table is empty."""
    history_js = Path("specguard/web/static/js/views/history.js").read_text(encoding="utf-8")
    assert "No previous analyses." in history_js


def test_index_html_status_pill():
    """Verify index.html uses factual 'Local / LAN Mode' instead of unverified claim."""
    index_html = Path("specguard/web/templates/index.html").read_text(encoding="utf-8")
    assert "Local / LAN Mode" in index_html
    assert "100% Offline (LAN Ready)" not in index_html
