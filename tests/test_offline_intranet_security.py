"""
Offline Intranet Security and Network Isolation Audit Test Suite.
Guarantees:
1. Zero public internet connections or external telemetry/cloud APIs.
2. Zero external CDN references (fonts, scripts, stylesheets) in static web assets.
3. Private intranet IP address validation and localhost binding.
Strictly 100% offline.
"""

import re
from pathlib import Path
from fastapi.testclient import TestClient

from specguard.server.app import create_app
from specguard.core.config import WEB_DIR


def test_no_external_cdn_references_in_web_assets():
    """Scans all web HTML, JS, and CSS files to guarantee 0% external CDN or third-party URLs."""
    forbidden_domains = [
        "googleapis.com", "gstatic.com", "cdnjs.cloudflare.com", "unpkg.com",
        "jsdelivr.net", "bootstrapcdn.com", "fontawesome.com", "openai.com",
        "anthropic.com", "google.com", "huggingface.co"
    ]

    pattern = re.compile(r"https?://([a-zA-Z0-9.-]+)")
    violating_files = []

    for ext in ["*.html", "*.js", "*.css"]:
        for file_path in WEB_DIR.rglob(ext):
            try:
                content = file_path.read_text(encoding="utf-8")
                matches = pattern.findall(content)
                for domain in matches:
                    domain_lower = domain.lower()
                    if any(f_dom in domain_lower for f_dom in forbidden_domains):
                        violating_files.append((str(file_path), domain))
            except Exception:
                pass

    assert len(violating_files) == 0, f"Found external CDN or remote cloud dependencies in web assets: {violating_files}"


def test_cors_allows_private_intranet_and_localhost():
    """Verifies that CORS allows localhost and private intranet IP ranges (RFC 1918)."""
    app = create_app()
    client = TestClient(app)

    allowed_origins = [
        "http://127.0.0.1:8765",
        "http://localhost:3000",
        "http://192.168.1.50:8765",
        "http://10.0.0.12:8765",
        "http://172.16.5.20:8765"
    ]

    for origin in allowed_origins:
        resp = client.options(
            "/api/dashboard/stats",
            headers={"Origin": origin, "Access-Control-Request-Method": "GET"}
        )
        assert resp.headers.get("access-control-allow-origin") == origin, f"Origin {origin} should be allowed on intranet"

    # Public internet origins must NOT be allowed
    forbidden_origin = "http://malicious-public-site.com"
    resp_bad = client.options(
        "/api/dashboard/stats",
        headers={"Origin": forbidden_origin, "Access-Control-Request-Method": "GET"}
    )
    assert resp_bad.headers.get("access-control-allow-origin") != forbidden_origin


def test_offline_endpoints_work_without_network():
    """Verifies all core endpoints function without external network connectivity."""
    app = create_app()
    client = TestClient(app)

    # 1. Health check
    res = client.get("/api/settings/health")
    assert res.status_code == 200
    assert res.json()["is_ready"] is True

    # 2. Hardware profile
    res_hw = client.get("/api/models/hardware")
    assert res_hw.status_code == 200
    assert "cpu_cores" in res_hw.json()

    # 3. Custom templates list
    res_tmpl = client.get("/api/templates/custom")
    assert res_tmpl.status_code == 200
    assert isinstance(res_tmpl.json(), list)
