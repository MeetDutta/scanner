# DocReady — Render Deployment & Production Readiness Audit

**Document Version:** 1.0.0  
**Audit Date:** September 20, 2026  
**Auditor:** Senior Backend, DevOps & QA Systems Architecture Team  
**Scope:** Evaluation of the existing DocReady (formerly SpecGuard) codebase for deployment on Render for mentor demonstration and evaluation.

---

## 1. Actual Project Structure

The DocReady repository is a 100% offline-capable, modular document formatting and engineering specification intelligence system. The actual repository tree is structured as follows:

```
scanner/
├── app.py                         # Application CLI & PySide6 Desktop launcher entry point
├── portable_launcher.py           # Production portable launcher (port allocation, pre-flight checks, uvicorn)
├── run_web.py                     # Minimal web launcher delegating to portable_launcher
├── pyproject.toml                 # Packaging metadata, scripts, and runtime dependencies
├── requirements-build.txt         # PyInstaller freeze build requirements
├── Dockerfile                     # [To be generated] Container definition for cloud/Render deployment
├── render.yaml                    # [To be generated] Infrastructure-as-code deployment blueprint
├── .env.example                   # [To be generated] Documented environment variables template
├── specguard/                     # Core application package (DocReady backend & engine)
│   ├── core/                      # Document ingestion, layout geometry, coordinate mapping, runtime config
│   │   ├── config.py              # Central runtime configuration & directory initialization
│   │   ├── document_parser.py     # Multi-format parser dispatch (PyMuPDF, python-docx, openpyxl, OpenCV)
│   │   ├── location_mapper.py     # Sub-pixel coordinate mapping and word/line bounding box calculation
│   │   ├── models.py              # Data models (DocumentModel, PageModel, Finding, BBox, etc.)
│   │   ├── pipeline.py            # End-to-end analysis orchestrator & repository storage
│   │   ├── reading_order.py       # Column-aware topological reading order engine
│   │   ├── runtime_paths.py       # Frozen/dev path resolution, writable user data directory resolution
│   │   ├── scanned_pipeline.py    # OpenCV image preprocessing, deskew, noise filter & CLAHE
│   │   └── startup.py             # Pre-flight hardware and dependency diagnostic checks
│   ├── analyzers/                 # 16 domain and formatting analyzers
│   │   ├── base.py                # BaseAnalyzer abstract interface
│   │   ├── cross_references.py    # Figure, table, and section cross-reference linking & resolution
│   │   ├── custom_template_analyzer.py # User-defined JSON template rule verification
│   │   ├── engineering.py         # Engineering parameters, units, tolerances, ranges
│   │   ├── equations.py           # Equation syntax, numbering, and cross-reference verification
│   │   ├── figures.py             # Image resolution, aspect ratio, caption placement
│   │   ├── formatting.py          # Font consistency, margins, spacing, hierarchy
│   │   ├── grammar.py             # Technical spell-check, passive voice, repetition
│   │   ├── ieee.py                # IEEE two-column conference paper layout compliance
│   │   ├── logical.py             # Cross-statement engineering contradiction detector
│   │   ├── semantic.py            # Domain-specific terminology and context checks
│   │   ├── severity.py            # Multi-criteria severity and priority scoring engine
│   │   ├── standards.py           # Regulatory engineering standards verification (ASME, ISO, etc.)
│   │   ├── structure.py           # Section hierarchy, numbering, and orphan headings
│   │   ├── tables.py              # Table grid, headers, units, caption orientation
│   │   ├── template_analyzer.py   # Baseline layout template verification
│   │   └── toc.py                 # Table of Contents page drift and title matching
│   ├── server/                    # FastAPI web server and API layer
│   │   ├── app.py                 # FastAPI application factory (create_app), lifespan, CORS, static routes
│   │   └── api/                   # REST API routers
│   │       ├── analysis.py        # File upload, analysis job dispatch, progress polling, cancellation
│   │       ├── dashboard.py       # Overview statistics, recent documents, system health
│   │       ├── documents.py       # Document metadata, page image rendering, raw file download
│   │       ├── findings.py        # Finding query, filtering, sorting, and detail views
│   │       ├── history.py         # Revision history, document comparison diffs
│   │       ├── models_api.py      # ML model registry, ONNX parity status, hardware profile
│   │       ├── reports.py         # Executive HTML & JSON report generation and preview
│   │       ├── settings_api.py    # System preferences, weights, backup snapshot creation
│   │       ├── standards.py       # Regulatory standard rules and custom rule definitions
│   │       └── templates_api.py   # Template learning, extraction, and management
│   ├── web/                       # Bundled offline Web Dashboard UI
│   │   ├── static/
│   │   │   ├── css/               # Modern responsive design styles
│   │   │   └── js/                # Vanilla ES6 SPA architecture
│   │   │       ├── api.js         # REST client (uses relative baseUrl: '/api')
│   │   │       ├── app.js         # Main application controller & event bus
│   │   │       ├── router.js      # Hash-based SPA client-side routing
│   │   │       ├── state.js       # Reactive store for active document, session, and filters
│   │   │       ├── components/    # Reusable UI widgets (nav, modal, viewer, charts)
│   │   │       └── views/         # Page views (dashboard, upload, viewer, templates, settings)
│   │   └── templates/
│   │       └── index.html         # Single-page application root shell
│   ├── storage/                   # Persistent SQLite persistence
│   │   ├── database.py            # SQLite connection lifecycle & automatic schema migrations
│   │   ├── repositories.py        # CRUD repositories for documents, sessions, findings
│   │   └── backup.py              # SQLite online snapshot backup mechanism
│   ├── repository/                # Revision and cross-document comparison repository
│   │   ├── comparator.py          # Visual and textual document comparison engine
│   │   ├── manager.py             # Repository index manager
│   │   ├── models.py              # Comparison models
│   │   └── search.py              # Local SQLite full-text search engine
│   ├── models/                    # Machine learning models, checkpoints, ONNX graphs, and registry
│   │   ├── model_registry.json    # Cryptographic registry of all active and standby models
│   │   ├── registry.py            # Dynamic model lifecycle and ONNX parity validator
│   │   ├── domain_classifier.py   # LSTM domain classification model
│   │   ├── engineering_ner.py     # BiLSTM engineering parameter extraction model
│   │   └── logical_classifier.py  # Siamese BiLSTM contradiction detection model
│   ├── standards/                 # Regulatory rules (ASME B1.1, ISO 2768, IEEE, OSHA, DIN)
│   └── templates/                 # Built-in document layout templates
├── tests/                         # Test suite (31 modules, 100% offline)
└── demo_samples/                  # Sample engineering test documents (PDF, DOCX, etc.)
```

---

## 2. Actual Application Entry Point

The application provides three distinct entry points depending on target environment:

1. **Web Server Factory (Primary Render Entry Point):**
   - **File:** `specguard/server/app.py`
   - **Factory Function:** `create_app() -> FastAPI`
   - **Module Instance:** `specguard.server.app:app`
   - **Description:** Initializes FastAPI with API routers, static file mounting (`/static`), single-page application shell (`/`), pre-flight lifespan verification, and CORS configuration.
   - **Uvicorn Invocation:**
     ```bash
     uvicorn specguard.server.app:create_app --factory --host 0.0.0.0 --port $PORT
     ```

2. **Portable CLI Launcher:**
   - **File:** `portable_launcher.py`
   - **Function:** `main()`
   - **Description:** Designed for desktop Windows/macOS/Linux. Performs dynamic port allocation (default 8765+), background health polling, and automatically launches the local web browser.

3. **Desktop GUI Application:**
   - **File:** `app.py`
   - **Flags:** `python app.py --gui` (launches PySide6 desktop interface) or fallback to `portable_launcher.main()`.

---

## 3. Required Dependencies

The dependencies can be categorized into web runtime, document processing, computer vision, machine learning, and desktop-only components:

### A. Web Runtime Dependencies (Essential for Render)
- `fastapi>=0.100.0` — Web REST API framework
- `uvicorn>=0.22.0` — ASGI web server
- `python-multipart>=0.0.6` — Multipart form handling for document uploads

### B. Document Processing & Parsing (Essential for Render)
- `pymupdf>=1.22.0` — High-performance PDF parser, word coordinate extractor, and page renderer (bundles MuPDF C library; zero external system dependencies)
- `python-docx>=0.8.11` — Pure Python Microsoft Word parser (zero LibreOffice dependency)
- `openpyxl>=3.1.0` — Pure Python Excel spreadsheet parser
- `numpy>=1.24.0` — Coordinate geometry, matrix operations, bounding box calculations
- `pandas>=2.0.0` — Tabular data extraction, table structure processing
- `pyyaml>=6.0` — Regulatory standards and custom template rule configuration

### C. Computer Vision & Layout Analysis (Essential for Render)
- `opencv-python-headless>=4.7.0` — Critical: Headless build of OpenCV. Provides image denoising, deskewing, Otsu binarization, adaptive thresholding, and morphological table detection **without requiring X11, libGL, or display servers**.

### D. Machine Learning & Inference (Optional / Supported on Render)
- `torch>=2.0.0` — PyTorch deep learning backend (optional; rule-based engine operates if missing)
- `onnx>=1.14.0` — ONNX serialization
- `onnxruntime>=1.15.0` — Lightweight, CPU-optimized offline inference engine
- `scikit-learn>=1.2.0`, `scipy>=1.10.0`, `psutil>=5.9.0` — Research evaluation & metric reporting

### E. Desktop GUI Dependencies (PROHIBITED on Render)
- `PySide6>=6.5.0` — Qt6 GUI framework (~180MB). **Must not be installed or imported in Render web deployment**.

---

## 4. Required Environment Variables

| Variable | Default Value | Purpose |
| :--- | :--- | :--- |
| `PORT` | `8765` (local) / `$PORT` (Render) | Server bind port provided dynamically by Render |
| `DOCREADY_HOST` | `127.0.0.1` (local) / `0.0.0.0` (Render) | Network interface binding |
| `DOCREADY_ENV` | `local` | Environment mode (`local`, `portable`, `render_demo`) |
| `DOCREADY_WEB_MODE` | `0` | If `1`, suppresses PySide6 GUI requirements in startup checks |
| `DOCREADY_DATA_DIR` | Auto-detected | Custom writable storage path for SQLite DB, uploads, and reports |
| `DOCREADY_CORS_ORIGINS` | `*` | Allowed CORS origins (e.g. `https://docready.onrender.com`) |

---

## 5. Deployment Blockers Identified

1. **PySide6 Required in Pre-Flight Diagnostics (`specguard/core/startup.py`):**
   - **Issue:** Line 24 of `startup.py` includes `("PySide6", "PySide6 GUI Framework")` in `REQUIRED_PACKAGES`. If PySide6 is not installed on Render, `verify_environment()` marks the environment as unready and logs an error.
   - **Impact:** While `specguard/server/app.py` continues running with a warning, any launcher checking `report.is_ready` would abort.
   - **Severity:** High.

2. **Hardcoded CORS Regex in `specguard/server/app.py`:**
   - **Issue:** Lines 63-69 currently restrict CORS exclusively to `localhost`, `127.0.0.1`, and private intranet subnets (`10.*`, `172.*`, `192.168.*`).
   - **Impact:** Requests from external origins or client scripts on Render would be blocked by CORS unless same-origin requests are used.
   - **Severity:** Medium.

3. **Absence of Top-Level `/health` Endpoint:**
   - **Issue:** Only `/api/health` currently exists in `specguard/server/app.py`. Render's default health check probe often queries `/health`.
   - **Impact:** Render service health check may fail if configured to query `/health`.
   - **Severity:** Medium.

4. **Ephemeral Filesystem on Render:**
   - **Issue:** On Render free/starter tiers, container restarts reset the local disk. SQLite database files, uploaded PDFs, and generated reports will not persist across container redeploys.
   - **Impact:** Document history will be reset upon service sleep or redeploy.
   - **Severity:** Architectural limitation (acceptable for testing/demonstration, must be documented).

5. **`pyproject.toml` Bundles Desktop Dependencies:**
   - **Issue:** Running `pip install .` on Render attempts to compile/install `PySide6>=6.5.0`, causing excessive build times, memory exhaustion, or failure due to missing X11/GL system libraries.
   - **Severity:** High blocker for native builds.

---

## 6. Recommended Fixes

1. **Environment-Aware Pre-Flight Checks:**
   - Update `specguard/core/startup.py` so that when `DOCREADY_WEB_MODE=1` or `DOCREADY_ENV=render_demo`, `PySide6` is treated as optional, ensuring `is_ready=True`.
2. **Dual Health Check Endpoints:**
   - Add `@app.get("/health")` alongside `@app.get("/api/health")` in `specguard/server/app.py`, returning service status and active environment mode.
3. **Dynamic CORS Configuration:**
   - Update `specguard/server/app.py` to accept `DOCREADY_CORS_ORIGINS` from environment variables, supporting `.onrender.com` while preserving strict localhost enforcement in local mode.
4. **Dedicated Render Dependency Manifest (`requirements-render.txt`):**
   - Create a clean `requirements-render.txt` with exact web/analysis requirements (`pymupdf`, `opencv-python-headless`, `python-docx`, `openpyxl`, `fastapi`, `uvicorn`, etc.) without `PySide6`.
5. **Configurable Data Directory (`specguard/core/runtime_paths.py`):**
   - Enhance `get_data_dir()` to honor `DOCREADY_DATA_DIR` if set in the environment, enabling persistence via Render Persistent Disks if attached.
6. **Dual Deployment Support (Docker & Native Python):**
   - Provide a lean `Dockerfile` (with Tesseract OCR installed) and a `render.yaml` supporting both native Python and Docker configurations.

---

## 7. Features Expected to Work on Render

- **Web Dashboard UI:** Complete single-page dashboard with real-time stats, system status, and rule counters.
- **Document Upload & Ingestion:** Drag-and-drop file upload for PDF, DOCX, XLSX, TXT, and images up to 50MB.
- **Multi-Format Parsing:** PyMuPDF, python-docx, and openpyxl parsing with complete coordinate mapping.
- **Visual Page Rendering:** Rendering PDF pages to PNG data with sub-pixel word, line, and block coordinates.
- **Interactive Finding Overlays:** Color-coded bounding box highlights on document pages (Critical, High, Medium, Low).
- **All 16 Rule Analyzers:**
  - Structure & Section Hierarchy
  - Cross-Reference Integrity & Dangling Reference Detection
  - Table and Figure Formatting & Caption Orientation
  - Table of Contents Page Drift Detection
  - Engineering Unit Normalization & Parameter Validation
  - Technical Grammar, Repeated Word, and Spell Checking
  - Regulatory Standards Checks (ASME, ISO, IEEE, OSHA)
  - Custom User-Defined Template Verification
  - Severity and Priority Scoring Engine
- **Report Generation:** Full executive report generation in both interactive HTML and structured JSON formats.
- **Document Comparison:** Side-by-side visual and textual diffing of document revisions.
- **100% Offline Integrity:** Zero external API calls, zero telemetry, zero remote model downloads.

---

## 8. Features That May Not Work on Render

- **PySide6 Desktop GUI:** Disabled by design in cloud environments.
- **Hardware GPU Acceleration (MPS/CUDA):** Render starter/free tiers run on CPU instances; all PyTorch/ONNX inferences will run on multi-core CPU.
- **Long-term File Persistence (Free Tier):** Uploaded files and generated reports are stored on the ephemeral container disk and will be cleared when the free service spins down after inactivity.
- **System Tesseract OCR (Native Python Mode):** If deployed via native Python without Docker, Tesseract binary is absent; the system automatically falls back to the built-in OpenCV morphological document vision engine.

---

## 9. Security Risks & Mitigation

| Risk | Threat Vector | Mitigation in DocReady |
| :--- | :--- | :--- |
| **Unauthenticated Cloud Access** | Public Render URL allows anyone to access the demo | Intended for testing/mentor review only. No confidential files should be uploaded. CORS restricted. |
| **Arbitrary File Upload** | Malicious executable upload (`.exe`, `.sh`, `.php`) | Strict whitelist validation (`.pdf`, `.docx`, `.xlsx`, `.txt`, `.png`, `.jpg`). |
| **Path Traversal Attacks** | Manipulation of `filename` parameter (`../../etc/passwd`) | `Path(filename).name` sanitization; files stored with randomized SHA-256 prefixes. |
| **Denial of Service via Huge Files** | Server memory exhaustion via 500MB+ files | File size limit enforced in backend (50MB threshold). |
| **Information Disclosure** | Stack traces or internal server paths in error responses | Clean error handling in `ApiClient` returning structured error details without host paths. |

---

## 10. Testing Strategy

1. **Static Analysis & Dependency Verification:**
   - Validate that `requirements-render.txt` installs cleanly in a clean virtual environment without `PySide6`.
   - Verify Python syntax across all modified modules.
2. **Local Render Simulation:**
   - Launch server using: `DOCREADY_ENV=render_demo DOCREADY_WEB_MODE=1 PORT=10000 HOST=0.0.0.0 uvicorn specguard.server.app:create_app --factory --port 10000`.
   - Verify `/health` and `/api/health` respond with HTTP 200 and expected payload.
   - Verify static assets (`/static/js/app.js`, `/static/css/`) and index shell (`/`) load correctly.
3. **End-to-End Pipeline Execution:**
   - Test PDF analysis on sample engineering documents.
   - Test DOCX analysis on structured technical manuals.
   - Test XLSX analysis on engineering calculation sheets.
   - Test report preview and HTML download.
4. **Security & Boundary Tests:**
   - Test invalid extension rejection.
   - Test path traversal attempts.
5. **Offline Verification:**
   - Ensure zero outgoing connections to cloud AI (OpenAI, Gemini, Hugging Face).
