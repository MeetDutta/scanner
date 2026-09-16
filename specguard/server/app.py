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
from specguard.server.api.settings_api import router as router_settings

logger = logging.getLogger("SpecGuard.Server")

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
    logger.info("SpecGuard local server shutting down cleanly.")


def create_app() -> FastAPI:
    """Factory creating and configuring the SpecGuard FastAPI server."""
    app = FastAPI(
        title="SpecGuard Engineering Document Quality Framework",
        description="100% Offline Deep Learning & Computer Vision Engineering Quality System",
        version=DEFAULT_CONFIG.version,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None
    )

    # Restrict CORS strictly to localhost on any allocated port
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://(127\.0\.0\.1|localhost)(:\d+)?$",
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
    app.include_router(router_settings, prefix=api_prefix)

    # Health check
    @app.get("/api/health")
    def health_check():
        return {
            "status": "online",
            "mode": "offline",
            "name": "SpecGuard",
            "version": DEFAULT_CONFIG.version
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
