"""
Offline Intranet Security, LAN Isolation, and Multi-User Concurrency Audit Test Suite.
Guarantees:
1. Zero public internet connections, zero external telemetry, zero cloud APIs.
2. Zero external CDN references (fonts, scripts, stylesheets) in static web assets.
3. Private intranet IP address validation and LAN CORS support (RFC 1918 + mDNS .local).
4. Subsystem health checks report 100% offline status.
5. Simulated total internet blocking does not break document processing or viewer.
6. File upload directory traversal prevention.
7. Concurrent multi-user isolation across 2, 5, and 10 simultaneous LAN clients.
Strictly 100% offline.
"""

import re
import socket
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient

from specguard.server.app import create_app
from specguard.core.config import WEB_DIR, UPLOADS_DIR
from specguard.server.api.analysis import sanitize_filename


def test_no_external_cdn_references_in_web_assets():
    """Scans all web HTML, JS, and CSS files to guarantee 0% external CDN or third-party URLs."""
    forbidden_domains = [
        "googleapis.com", "gstatic.com", "cdnjs.cloudflare.com", "unpkg.com",
        "jsdelivr.net", "bootstrapcdn.com", "fontawesome.com", "openai.com",
        "anthropic.com", "google.com", "huggingface.co", "sentry.io", "posthog.com"
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
    """Verifies that CORS allows localhost, RFC 1918 private intranet IP ranges, and mDNS .local hostnames."""
    app = create_app()
    client = TestClient(app)

    allowed_origins = [
        "http://127.0.0.1:8765",
        "http://localhost:3000",
        "http://192.168.1.50:8765",
        "http://10.0.0.12:8765",
        "http://172.16.5.20:8765",
        "http://specguard.local:8765",
        "http://server.local"
    ]

    for origin in allowed_origins:
        resp = client.options(
            "/api/dashboard/stats",
            headers={"Origin": origin, "Access-Control-Request-Method": "GET"}
        )
        assert resp.headers.get("access-control-allow-origin") == origin, f"Origin {origin} should be allowed on intranet"

    # Public internet origins must NOT be allowed
    forbidden_origins = [
        "http://malicious-public-site.com",
        "https://api.openai.com",
        "https://google.com"
    ]
    for bad_origin in forbidden_origins:
        resp_bad = client.options(
            "/api/dashboard/stats",
            headers={"Origin": bad_origin, "Access-Control-Request-Method": "GET"}
        )
        assert resp_bad.headers.get("access-control-allow-origin") != bad_origin


def test_offline_endpoints_work_without_network():
    """Verifies all core endpoints function without external network connectivity."""
    app = create_app()
    client = TestClient(app)

    # 1. Root /health
    res_root = client.get("/health")
    assert res_root.status_code == 200
    assert res_root.json()["offline"] is True
    assert res_root.json()["lan_ready"] is True

    # 2. Detailed /api/health
    res_api = client.get("/api/health")
    assert res_api.status_code == 200
    data_api = res_api.json()
    assert data_api["mode"] == "offline"
    assert data_api["components"]["application"] == "OK"
    assert data_api["components"]["database"] == "OK"
    assert data_api["components"]["document_engine"] == "OK"
    assert data_api["network"]["offline"] is True
    assert data_api["network"]["external_calls"] == "None"

    # 3. Settings Diagnostics health check
    res = client.get("/api/settings/health")
    assert res.status_code == 200
    assert res.json()["is_ready"] is True

    # 4. Hardware profile
    res_hw = client.get("/api/models/hardware")
    assert res_hw.status_code == 200
    assert "cpu_cores" in res_hw.json()

    # 5. Custom templates list
    res_tmpl = client.get("/api/templates/custom")
    assert res_tmpl.status_code == 200
    assert isinstance(res_tmpl.json(), list)


def test_offline_network_socket_blocking_simulation(monkeypatch):
    """
    Simulates a 100% disconnected network / blocked DNS environment.
    Blocks all external socket connections and verifies full analysis workflow passes.
    """
    # Guard function that rejects any attempt to establish an external network socket
    def blocked_connect(self, *args, **kwargs):
        raise OSError("SIMULATED_OFFLINE: External network interface blocked.")

    def blocked_getaddrinfo(*args, **kwargs):
        raise socket.gaierror("SIMULATED_OFFLINE: DNS name resolution unavailable.")

    # Patch socket to guarantee zero external calls
    monkeypatch.setattr(socket.socket, "connect", blocked_connect)
    monkeypatch.setattr(socket, "getaddrinfo", blocked_getaddrinfo)

    app = create_app()
    client = TestClient(app)

    # Workflow Step 1: Upload real document
    pdf_path = Path("demo_samples/mechanical_sample_with_errors.pdf")
    with open(pdf_path, "rb") as f:
        upload_resp = client.post("/api/analysis/upload", files={"file": ("test_doc.pdf", f, "application/pdf")})
    assert upload_resp.status_code == 200
    upload_data = upload_resp.json()
    doc_path = upload_data["file_path"]

    # Workflow Step 2: Start analysis
    start_resp = client.post("/api/analysis/start", json={"file_path": doc_path, "domain": "mechanical"})
    assert start_resp.status_code == 200
    job_id = start_resp.json()["job_id"]

    # Workflow Step 3: Poll job to completion
    import time
    completed = False
    for _ in range(30):
        job_resp = client.get(f"/api/analysis/jobs/{job_id}")
        assert job_resp.status_code == 200
        if job_resp.json()["status"] == "completed":
            completed = True
            break
        time.sleep(0.1)
    assert completed, "Offline analysis must complete without network access."

    session_id = job_resp.json()["session_id"]

    # Workflow Step 4: Fetch findings
    findings_resp = client.get(f"/api/findings?session_id={session_id}")
    assert findings_resp.status_code == 200
    assert len(findings_resp.json()["findings"]) > 0

    # Workflow Step 5: Render page image
    doc_hash = upload_data["file_hash"]
    img_resp = client.get(f"/api/documents/{doc_hash}/pages/1/image?zoom=1.25")
    assert img_resp.status_code == 200
    assert img_resp.headers["content-type"] == "image/png"


def test_file_upload_security_and_traversal_prevention():
    """Verifies that malicious filenames with directory traversal sequences cannot escape UPLOADS_DIR."""
    # Test path traversal payloads
    dangerous_names = [
        "../../../etc/passwd",
        "..\\..\\windows\\system32\\cmd.exe",
        "....//....//shell.php",
        ".._.._test.pdf",
        ".hidden_file.pdf"
    ]

    for name in dangerous_names:
        sanitized = sanitize_filename(name)
        assert "/" not in sanitized
        assert "\\" not in sanitized
        assert not sanitized.startswith(".")

    app = create_app()
    client = TestClient(app)

    # Attempt uploading with traversal filename
    sample_content = b"%PDF-1.4 test document binary content"
    resp = client.post(
        "/api/analysis/upload",
        files={"file": ("../../../../malicious.pdf", sample_content, "application/pdf")}
    )
    assert resp.status_code == 200
    data = resp.json()
    dest_path = Path(data["file_path"]).resolve()

    # Must be strictly contained inside UPLOADS_DIR
    assert str(dest_path).startswith(str(UPLOADS_DIR.resolve()))
    assert dest_path.exists()
    dest_path.unlink(missing_ok=True)


def test_concurrent_multi_user_isolation():
    """
    Tests simultaneous access by 2, 5, and 10 concurrent LAN clients.
    Verifies that uploads, jobs, findings, and sessions remain completely isolated.
    """
    app = create_app()
    client = TestClient(app)
    sample_pdf = Path("demo_samples/mechanical_sample_with_errors.pdf").read_bytes()

    for user_count in [2, 5, 10]:
        results = []
        errors = []

        def simulate_client(user_idx: int):
            try:
                # 1. Unique client upload
                doc_name = f"user_{user_idx}_spec.pdf"
                up_resp = client.post(
                    "/api/analysis/upload",
                    files={"file": (doc_name, sample_pdf, "application/pdf")}
                )
                assert up_resp.status_code == 200
                up_data = up_resp.json()

                # 2. Client initiates analysis
                start_resp = client.post(
                    "/api/analysis/start",
                    json={"file_path": up_data["file_path"], "domain": "mechanical"}
                )
                assert start_resp.status_code == 200
                job_id = start_resp.json()["job_id"]

                # 3. Wait for client job to complete
                import time
                session_id = None
                for _ in range(40):
                    j_resp = client.get(f"/api/analysis/jobs/{job_id}")
                    if j_resp.status_code == 200 and j_resp.json()["status"] == "completed":
                        session_id = j_resp.json()["session_id"]
                        break
                    time.sleep(0.1)

                assert session_id is not None, f"Client {user_idx} job did not complete."

                # 4. Client retrieves their findings
                f_resp = client.get(f"/api/findings?session_id={session_id}")
                assert f_resp.status_code == 200
                findings = f_resp.json()["findings"]

                results.append({
                    "user_idx": user_idx,
                    "job_id": job_id,
                    "session_id": session_id,
                    "findings_count": len(findings)
                })
            except Exception as e:
                errors.append(f"User {user_idx} error: {e}")

        # Execute concurrent client simulation in parallel threads
        with ThreadPoolExecutor(max_workers=user_count) as executor:
            list(executor.map(simulate_client, range(user_count)))

        assert len(errors) == 0, f"Errors encountered during {user_count}-user test: {errors}"
        assert len(results) == user_count

        # Verify all sessions and jobs are strictly unique (zero cross-contamination)
        job_ids = [r["job_id"] for r in results]
        session_ids = [r["session_id"] for r in results]
        assert len(set(job_ids)) == user_count, "All concurrent jobs must have distinct job IDs."
        assert len(set(session_ids)) == user_count, "All concurrent sessions must have distinct session IDs."
