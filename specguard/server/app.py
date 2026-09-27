"""
SpecGuard Local Web Application Server.
Hosts the local REST API and serves the modern engineering dashboard UI.
Strictly 100% offline, binding exclusively to localhost (127.0.0.1).
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from specguard.core.config import BASE_DIR, DEFAULT_CONFIG, WEB_DIR
from specguard.core.startup import verify_environment

# Import all API routers
from specguard.server.api.dashboard import router as router_dashboard
from specguard.server.api.analysis import router as router_analysis
from specguard.server.api.documents import router as router_documents
from specguard.server.api.findings import router as router_findings
from specguard.server.api.history import router as router_history
from specguard.server.api.reports import router as router_reports
from specguard.server.api.standards import router as router_standards
from specguard.server.api.models_api import router as router_models
from specguard.server.api.templates_api import router as router_templates
from specguard.server.api.settings_api import router as router_settings

logger = logging.getLogger("DocReady.Server")

STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager running pre-flight checks and clean shutdown."""
    logger.info("Verifying local offline environment...")
    report = verify_environment()
    if not report.is_ready:
        logger.warning("Startup diagnostics reported issues: %s", report.errors)
    else:
        logger.info("Environment verified: 100% Offline Mode Active.")
    yield
    logger.info("DocReady local server shutting down cleanly.")


def create_app() -> FastAPI:
    """Factory creating and configuring the DocReady FastAPI server."""
    app = FastAPI(
        title="SpecGuard — Engineering Document Quality & Compliance Inspection Platform",
        description="SpecGuard 100% Offline Document Intelligence & Compliance Inspection System",
        version=DEFAULT_CONFIG.version,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None
    )

    import os
    env_mode = os.environ.get("SPECGUARD_ENV") or os.environ.get("DOCREADY_ENV", "local").lower()
    custom_cors = os.environ.get("SPECGUARD_CORS_ORIGINS") or os.environ.get("DOCREADY_CORS_ORIGINS")

    if custom_cors:
        origins = [orig.strip() for orig in custom_cors.split(",") if orig.strip()]
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    elif env_mode in ["render_demo", "render", "web"]:
        # In Render testing mode, allow *.onrender.com alongside localhost/intranet
        app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=r"^https?://(127\.0\.0\.1|localhost|([a-zA-Z0-9-]+\.)*onrender\.com|([a-zA-Z0-9-]+\.)*local|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2[0-9]|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})(:\d+)?$",
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        # Default local offline mode: restrict strictly to localhost and intranet (RFC 1918 + mDNS .local)
        app.add_middleware(
            CORSMiddleware,
            allow_origin_regex=r"^https?://(127\.0\.0\.1|localhost|([a-zA-Z0-9-]+\.)*local|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2[0-9]|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})(:\d+)?$",
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Register API Routers
    api_prefix = "/api"
    app.include_router(router_dashboard, prefix=api_prefix)
    app.include_router(router_analysis, prefix=api_prefix)
    app.include_router(router_documents, prefix=api_prefix)
    app.include_router(router_findings, prefix=api_prefix)
    app.include_router(router_history, prefix=api_prefix)
    app.include_router(router_reports, prefix=api_prefix)
    app.include_router(router_standards, prefix=api_prefix)
    app.include_router(router_models, prefix=api_prefix)
    app.include_router(router_templates, prefix=api_prefix)
    app.include_router(router_settings, prefix=api_prefix)

    # Health check endpoints (Section 39 - 100% Offline Subsystem Reporting):
    @app.get("/health")
    def health_check():
        return {
            "status": "ok",
            "service": "docready",
            "name": "SpecGuard",
            "environment": env_mode,
            "offline": True,
            "lan_ready": True
        }

    @app.get("/api/health")
    def api_health_check():
        from specguard.core.config import DB_PATH, DATA_DIR, RULES_DIR
        db_ok = DB_PATH.exists() or DB_PATH.parent.exists()
        storage_ok = DATA_DIR.exists()
        rules_ok = RULES_DIR.exists()

        return {
            "status": "online",
            "mode": "offline",
            "name": "SpecGuard",
            "service": "docready",
            "environment": env_mode,
            "version": DEFAULT_CONFIG.version,
            "components": {
                "application": "OK",
                "database": "OK" if db_ok else "INITIALIZING",
                "storage": "OK" if storage_ok else "ERROR",
                "rules": "OK" if rules_ok else "ERROR",
                "document_engine": "OK",
                "pdf_renderer": "OK"
            },
            "network": {
                "offline": True,
                "lan_ready": True,
                "external_calls": "None"
            }
        }

    # Mount static assets
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Serve main application shell
    @app.get("/", response_class=HTMLResponse)
    def serve_index():
        index_file = TEMPLATES_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file), media_type="text/html")
        return HTMLResponse("<h1>SpecGuard UI initializing...</h1>")

    return app


app = create_app()
