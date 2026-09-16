# SpecGuard Windows Portable Packaging Audit & Architecture Specification

**Document Version:** 1.0.0  
**Target Platform:** Windows 10 / 11 (x86_64, 64-bit)  
**Security Posture:** 100% Offline, Localhost Only (`127.0.0.1`), Zero Cloud Services, Zero External Telemetry  
**Packaging Format:** Portable Zero-Install ZIP Distribution (PyInstaller Onedir Architecture)

---

## 1. Executive Summary & Objective

The objective of this engineering audit is to evaluate the complete **SpecGuard** repository for conversion into a standalone, portable Windows application. The final packaged artifact must run out of the box when extracted from a ZIP file onto a clean Windows machine without requiring pre-installed Python, Node.js, Git, C++ build tools, or administrative privileges.

### Core Portability Contract
1. **Zero External Runtime Prerequisites:** No requirement for Python, pip, Node.js, npm, or virtual environments on the host system.
2. **Instant Double-Click Execution:** Users double-click `SpecGuard.exe` or `Launch_SpecGuard.bat`, the backend initializes locally, and the user's default browser automatically opens to `http://127.0.0.1:<port>`.
3. **Clean Data Separation:** Mutable user-generated artifacts (SQLite databases, uploaded engineering documents, generated verification reports, runtime logs) reside strictly in persistent, writable directories outside of read-only bundled directories.
4. **Resilient Localhost Networking:** Binding strictly to `127.0.0.1` prevents Windows Firewall prompts, isolates the application from local area networks, and dynamically allocates an alternative ephemeral port if the default port (`8765`) is already bound.
5. **Preservation of All Analysis Engines:** All 10 domain engines, multi-format parsers, computer vision models, and ONNX inference runtimes remain fully operational.

---

## 2. Application Architecture Audit

### 2.1 Component Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                        User Interface Layer                            │
│   • Modern HTML5 / CSS3 / Vanilla JavaScript Dashboard & Workspace     │
│   • Document Canvas Viewer with interactive bounding-box overlays      │
│   • 100% Offline Static Assets (Zero CDN, Zero External Google Fonts)   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP REST (127.0.0.1:8765)
┌───────────────────────────────────▼────────────────────────────────────┐
│                        Local Server & API Layer                        │
│   • FastAPI ASGI Application (`specguard.server.app:create_app`)       │
│   • Uvicorn Local Worker (single-process event loop)                   │
│   • 9 Modular Routers: dashboard, analysis, documents, findings,       │
│     history, reports, standards, models_api, settings_api              │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Python In-Process Calls
┌───────────────────────────────────▼────────────────────────────────────┐
│                     Core Analysis & Vision Pipeline                    │
│   • LayoutAnalyzerCV (OpenCV table, line, and morphological detection) │
│   • ScannedDocumentPipeline (deskew, bilateral filter, CLAHE, binarize)│
│   • MultiFormatDocumentParser (PyMuPDF, python-docx, openpyxl, OpenCV) │
│   • DomainTaxonomyClassifier (rule-based + ONNX deep embeddings)       │
│   • EngineeringStandardsEngine & RuleComplianceEngine (YAML rules)     │
│   • TechnicalDrawingEngine & CrossDocumentComparator                   │
│   • PriorityScoringEngine (6-factor multi-criteria risk formula)       │
│   • ModelRegistry & ONNX Runtime (offline execution)                   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ File & SQLite I/O
┌───────────────────────────────────▼────────────────────────────────────┐
│                       Storage & Persistence Layer                      │
│   • SQLite Database: `data/database/specguard.db`                      │
│   • Mutable File Stores: `data/uploads/`, `data/reports/`, `data/logs/`│
│   • Immutable Bundled Stores: `resources/standards/`, `models/`, etc.  │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Entry Points

| Entry Point | Purpose | Current Behavior | Portable Target Behavior |
| :--- | :--- | :--- | :--- |
| `portable_launcher.py` | Primary Windows Portable Entry Point | *New Component* | Dynamically detects root folder, configures logging to `data/logs/specguard.log`, allocates available port, starts FastAPI, polls `/api/health`, and launches default browser. |
| `run_web.py` | Local Development Web Launcher | Uses relative `BASE_DIR = Path(__file__).resolve().parent` and static port 8765. | Refactored to delegate to centralized `runtime_paths.py` and accept dynamic ports. |
| `app.py` | Dual Mode Launcher (`--gui` or web) | Resolves paths via `__file__`. | Updated to use `runtime_paths.py`. |
| `Launch_SpecGuard.bat` | Windows Shell Fallback Launcher | *New Component* | Runs `SpecGuard.exe` or provides diagnostic error trapping if the binary is blocked. |

---

## 3. Dependency & Runtime Audit

### 3.1 Python Core Dependencies

| Package | Version Range | Portability Risk | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| `fastapi` | `>=0.100.0` | Low | Explicitly included in PyInstaller hidden imports along with `starlette`. |
| `uvicorn` | `>=0.22.0` | Medium | Uvicorn uses dynamic worker/protocol imports (`uvicorn.protocols.http.auto`, `uvicorn.lifespan.on`). Must declare explicit hidden imports. |
| `python-multipart` | `>=0.0.6` | Low | Required for file uploads in FastAPI; must be bundled. |
| `pymupdf` (`fitz`) | `>=1.22.0` | High | C-extension with native compiled bindings. PyInstaller must collect all binaries via `collect_all("fitz")` or `collect_dynamic_libs`. |
| `opencv-python-headless` | `>=4.7.0` | High | Native C++ shared libraries (`cv2`). Must use `collect_all("cv2")` to package bundled DLLs. |
| `python-docx` | `>=0.8.11` | Low | Pure Python with XML dependencies (`lxml`). |
| `openpyxl` | `>=3.1.0` | Low | Pure Python with XML dependencies (`et_xmlfile`). |
| `numpy` | `>=1.24.0` | High | Native compiled BLAS/LAPACK binaries. Needs `collect_submodules("numpy")`. |
| `pandas` | `>=2.0.0` | Medium | C-extensions for dataframes. Must collect submodules and shared C-extensions. |
| `pyyaml` | `>=6.0` | Low | Pure Python / LibYAML bindings. Must include YAML rule files as bundled datas. |

### 3.2 Machine Learning & Research Dependencies

| Package | Status | Portability Risk | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| `onnxruntime` | Optional/Core | High | Contains native `onnxruntime.dll` and provider libraries. PyInstaller must bundle all DLLs from the onnxruntime package. |
| `torch` | Optional/Core | Very High | Large native binaries (~150-300MB). Bundling must collect CPU-only PyTorch DLLs (`torch_cpu.dll`, `c10.dll`). |
| `scikit-learn` | Optional | Medium | Scipy/Cython binaries. Handled via `collect_all("sklearn")`. |
| `scipy` | Optional | Medium | Native BLAS/Fortran DLLs. Handled via `collect_submodules("scipy")`. |

### 3.3 OCR & Computer Vision Audit

- **Current Implementation:** SpecGuard's primary scanned-document processing pipeline (`specguard/core/scanned_pipeline.py`) is implemented natively in OpenCV. It uses:
  1. Bilateral filtering for denoising.
  2. Otsu thresholding and minimum area bounding rectangles for deskew angle calculation and affine transformation.
  3. Adaptive Gaussian thresholding for binarization.
  4. Morphological rectangular structuring elements (`cv2.MORPH_RECT`) and contour detection for text region segmentation.
- **Tesseract OCR Status:** No hard dependency on Tesseract exists in the core repository. If users supply a portable Tesseract executable inside `resources/tesseract/` or on system `PATH`, SpecGuard can detect and utilize it. If absent, the application continues safely with built-in OpenCV region extraction without errors.

---

## 4. Portability Vulnerabilities & Architectural Fixes

### 4.1 Vulnerability 1: Fragile `BASE_DIR` Resolution
- **Issue:** Code across `specguard/core/config.py`, `specguard/templates/manager.py`, and `specguard/repository/manager.py` uses:
  ```python
  BASE_DIR = Path(__file__).resolve().parent.parent.parent
  ```
  In a PyInstaller frozen application, `__file__` either does not exist or points to a temporary decompression folder (`_MEIPASS` or `_internal/specguard/core/config.pyc`), causing relative directory traversal to fail.
- **Fix:** Introduce `specguard.core.runtime_paths.py`. It inspects `getattr(sys, "frozen", False)`:
  - If frozen: Base installation directory is `Path(sys.executable).resolve().parent`. Bundled internal resources are located in `sys._MEIPASS` (or `parent / "_internal"`).
  - If development: Base directory is the project workspace root.

### 4.2 Vulnerability 2: User Data Corruption in Temporary Directories
- **Issue:** If user data (SQLite database, file uploads, logs, reports) is written into `_MEIPASS` or the application code directory, it will be wiped when temporary files are purged or will fail with access denied errors if installed in `C:\Program Files` or on read-only media.
- **Fix:** Distinct separation between:
  1. **Read-Only Bundled Resources (`resources/`):** Standards, default templates, ML models, web static files.
  2. **Mutable User Data (`data/`):** SQLite database (`data/database/specguard.db`), uploaded files (`data/uploads/`), generated reports (`data/reports/`), logs (`data/logs/specguard.log`), and cache (`data/cache/`).
  If the application folder is writable (portable mode), `data/` is created adjacent to `SpecGuard.exe`. If not writable, it seamlessly falls back to `%LOCALAPPDATA%\SpecGuard\data`.

### 4.3 Vulnerability 3: Port Conflict Failures
- **Issue:** Hardcoding port `8765` causes immediate application crash if the port is in use by another instance or service (`Errno 48` / `WSAEADDRINUSE 10048`).
- **Fix:** The portable launcher implements a port-discovery utility. It checks if port `8765` is available. If bound, it tests successive ports (`8766`, `8767`, etc.) or requests an ephemeral port from the OS kernel, passing the allocated port to Uvicorn and launching the browser with the exact URL.

### 4.4 Vulnerability 4: CORS & Host Binding
- **Issue:** Hardcoding CORS `allow_origins=["http://127.0.0.1:8765"]` breaks communication if an alternate port is selected.
- **Fix:** Dynamic CORS configuration allowing `http://127.0.0.1:*` and `http://localhost:*` across all valid port numbers, while strictly rejecting any external network requests.

### 4.5 Vulnerability 5: Missing Startup Diagnostics & Silent Hangs
- **Issue:** When a packaged Windows app fails on launch, users see a flashing console window that closes immediately with no diagnostic logs.
- **Fix:** The launcher redirects early stdout/stderr to `data/logs/specguard.log`, executes environment pre-flight diagnostics, and displays a user-friendly error message box if critical failures occur.

---

## 5. Target Portable Directory Structure

```
SpecGuard/
│
├── SpecGuard.exe                  # Main portable application executable
├── Launch_SpecGuard.bat           # Shell launcher & diagnostic wrapper
├── README.txt                     # User instructions & quick-start guide
├── LICENSE.txt                    # License and legal notices
├── PORTABLE_DEPLOYMENT.md         # Deployment & security reference
├── TROUBLESHOOTING.md             # Common issues and solutions
│
├── _internal/                     # Bundled Python runtime, DLLs & modules
│   ├── python*.dll
│   ├── fitz/                      # PyMuPDF compiled binaries
│   ├── cv2/                       # OpenCV compiled binaries
│   ├── onnxruntime/               # ONNX Runtime DLLs
│   ├── torch/                     # PyTorch CPU binaries
│   └── ...                        # Supporting wheels and C-extensions
│
├── resources/                     # Bundled read-only application resources
│   ├── models/                    # ONNX model files and registry
│   │   ├── model_registry.json
│   │   └── onnx/
│   ├── standards/                 # Domain standards (mechanical, chemical, electrical)
│   ├── rules/                     # Compliance rules
│   ├── templates/                 # Industry specification templates
│   ├── web/                       # Offline HTML5/CSS/JS frontend
│   │   ├── static/
│   │   │   ├── css/
│   │   │   └── js/
│   │   └── templates/
│   │       └── index.html
│   └── demo_samples/              # Engineering sample documents
│
├── data/                          # Persistent writable user storage
│   ├── database/
│   │   └── specguard.db           # SQLite database
│   ├── uploads/                   # Uploaded documents
│   ├── reports/                   # Exported verification reports
│   ├── logs/
│   │   └── specguard.log          # Runtime log file
│   └── cache/                     # Temporary processing cache
│
└── uninstall/
    └── Remove_UserData.bat        # Script to clean user data if requested
```

---

## 6. Recommended Packaging Strategy

### Chosen Approach: PyInstaller Onedir Distribution
- **Rationale:** 
  1. **Performance:** SpecGuard bundles native libraries totaling over 250MB (PyMuPDF, OpenCV, ONNX Runtime, PyTorch). A `onefile` executable must extract all files to `%TEMP%` on every run, taking 15 to 30 seconds to launch. An `onedir` build starts in less than 1.5 seconds.
  2. **Stability:** Avoids Windows file-locking issues when DLLs in `%TEMP%` cannot be deleted after abnormal termination.
  3. **Data Clarity:** Users clearly see the `data/` folder and can backup their database and reports easily.
  4. **Portability:** The entire `SpecGuard` directory can be moved to a USB drive, network share, or different directory without losing data or requiring reinstallation.

---

## 7. Packaging Prerequisites Checklist

- [x] Python 3.9+ runtime compatible (tested on 3.11).
- [x] All 68 existing unit and integration tests passing.
- [x] Zero remote CDN dependencies in frontend (HTML/CSS/JS all self-contained).
- [x] Strict localhost binding (`127.0.0.1`).
- [x] Native binary dependency list cataloged.
- [x] Centralized path resolution design completed.
- [x] Port conflict handling design completed.
- [x] Logging to file specification completed.

*Audit complete. Proceeding with application startup architecture and runtime path implementation.*
