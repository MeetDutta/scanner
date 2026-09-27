# SpecGuard — Offline Runtime Manifest

This manifest documents all local software components, packages, runtime engines, and data resources required to run SpecGuard in a 100% offline, isolated LAN or air-gapped intranet environment.

---

## 1. Environment & Runtime Specifications

| Attribute | Specification | Offline Verification |
| :--- | :--- | :--- |
| **Operating System** | Linux (Ubuntu 20.04+, Debian 11+, RHEL 8+), macOS (11+), Windows Server | Verified |
| **Python Runtime** | Python 3.9, 3.10, or 3.11 | Pre-installed local interpreter |
| **Network Interface** | Local Loopback (`127.0.0.1`) and/or LAN Adapter (e.g. `192.168.1.0/24`) | No external WAN or Internet gateway required |
| **DNS Dependency** | None (direct IP address or local `/etc/hosts` / mDNS) | Zero external DNS queries |
| **Internet Access** | **Strictly 0%** (Blocked / Disconnected) | Verified with simulated socket blocking |

---

## 2. Python Packages (Installed Locally in Virtualenv)

| Package | Purpose | Local Dependency Details |
| :--- | :--- | :--- |
| `fastapi` | High-performance ASGI Web Framework | Local ASGI routing & validation |
| `uvicorn` | Production ASGI Web Server | Local TCP socket listener (`0.0.0.0`) |
| `pymupdf` (`fitz`) | Native C/C++ Document Parsing & Rendering | Compiles to native binary; zero external services |
| `opencv-python-headless` | Morphological Document Vision & Layout | Native C++ computer vision algorithms |
| `python-docx` | DOCX Document AST Extraction | Pure local XML parsing |
| `openpyxl` | Spreadsheet Structure & Data Parsing | Pure local XML parsing |
| `numpy` | Numerical Matrix Operations & Coordinates | Native C arrays |
| `pandas` | Tabular Data Processing & Summary | Native C data structures |
| `pyyaml` | Engineering Standards & Template Deserialization | Pure local YAML parser |
| `pydantic` | Data Validation & Serialization | Pure local schema verification |

*No cloud SDKs (boto3, google-cloud-*, azure-*, openai, anthropic) are required or installed.*

---

## 3. Frontend Web Assets (Static & Self-Contained)

All client-side code is bundled under [`specguard/web/static/`](file:///Users/meet/Desktop/scanner/specguard/web/static):

| Asset Category | Location | External CDN? | Notes |
| :--- | :--- | :--- | :--- |
| **HTML Shell** | `specguard/web/templates/index.html` | **None** | Served directly by FastAPI |
| **CSS Stylesheets** | `static/css/base.css`<br>`static/css/layout.css`<br>`static/css/components.css`<br>`static/css/views.css`<br>`static/css/findings.css` | **None** | Modern CSS variables; no Tailwind CDN or Bootstrap CDN |
| **Typography & Fonts** | System font stack in `base.css` | **None** | `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif` |
| **Icons & Emblems** | Native Unicode & SVG symbols | **None** | Zero FontAwesome / Material Icons CDN calls |
| **Client Logic** | `static/js/api.js`<br>`static/js/state.js`<br>`static/js/router.js`<br>`static/js/app.js` | **None** | Native Vanilla JavaScript (ES2022) |
| **Document Viewer** | `static/js/components/document_viewer.js` | **None** | Custom high-DPI canvas & SVG overlay engine |

---

## 4. Local Analysis Engines & Rules

All detection algorithms operate purely on deterministic local logic:

| Engine | Source Directory | Detection Mechanism |
| :--- | :--- | :--- |
| **Grammar & Spelling** | `specguard/analyzers/grammar_analyzer.py` | Local algorithmic spell-checker & token analysis |
| **Formatting & Typography** | `specguard/analyzers/formatting_analyzer.py` | Font size, font family, margins, heading hierarchies |
| **Document Structure** | `specguard/analyzers/structure_analyzer.py` | Heading levels, section continuity, numbering gaps |
| **Table of Contents** | `specguard/analyzers/toc_analyzer.py` | Page drift, title alignment, missing entries |
| **Figure Inspection** | `specguard/analyzers/figure_analyzer.py` | Sequence numbering, caption formatting, aspect ratio |
| **Table Inspection** | `specguard/analyzers/table_analyzer.py` | Header row detection, missing units, column continuity |
| **Cross-References** | `specguard/analyzers/cross_reference_analyzer.py` | Unresolved mentions, target verification |
| **Equations** | `specguard/analyzers/equation_analyzer.py` | Formula numbering, missing symbol definitions |

---

## 5. Storage & Databases

* **Database**: Local SQLite 3 database located at `data/specguard.db`. Configured with `PRAGMA journal_mode = WAL;` and `busy_timeout = 30000;` for concurrent multi-user transactions.
* **Upload Storage**: `data/uploads/` with UUID-prefixed file isolation and directory traversal containment checks.
* **Reports Storage**: `data/reports/` for local PDF/HTML/JSON report downloads.
* **Archive Repository**: `data/repository/` for document and finding archiving.
