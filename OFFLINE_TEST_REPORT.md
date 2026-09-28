# SpecGuard — Production Offline Docker Image Validation Report

**Image Name:** `specguard:1.0.0`  
**Base Image:** `python:3.11-slim-bookworm` (Multi-stage builder + runtime)  
**Export Artifact:** `specguard-offline.tar` (501 MB)  
**Checksum (SHA-256):** `94ad6a226ca9f21e230e56b01633b549a992591c27986de0ff10d3b1c8306321`  
**Execution Environment:** 100% Offline / Air-Gapped / Isolated Intranet LAN  
**Test Date:** 2026-09-28  

---

## 1. Executive Summary

This report documents the end-to-end audit, multi-stage containerization, tarball export/restore validation, and air-gapped test execution for the **SpecGuard** web-based engineering document quality & compliance inspection system.

The resulting container image contains all required runtime dependencies, offline ML models (PyTorch and ONNX), rule bases, engineering standards, document templates, Tesseract OCR binaries with English language assets, and static frontend interfaces. The runtime environment requires **zero internet access, zero remote APIs, zero CDN calls, and zero external downloads**.

---

## 2. Docker Architecture & Resource Inventory

- **Build Pattern:** Multi-Stage Build (`builder` stage for wheel builds + `runtime` stage with non-root user `specguard:1001`).
- **Installed Native Packages:** `tesseract-ocr`, `tesseract-ocr-eng`, `libglib2.0-0`, `curl`.
- **Installed Python Frameworks:** `FastAPI`, `Uvicorn`, `PyMuPDF`, `OpenCV Headless`, `PyTorch (CPU)`, `ONNX Runtime`, `Pandas`, `NumPy`, `python-docx`, `openpyxl`.
- **Bundled Models:** `DomainClassifierNet` (.pt & .onnx), `LogicalRelationNet` (.pt & .onnx), `EngineeringNERNet` (.pt), cross-domain and mechanical classification models.
- **Bundled Standards & Rules:** ASME, IEEE, ISO domain rules across Mechanical, Electrical, Chemical, and QA/QC disciplines.
- **Frontend Delivery:** 100% locally served static assets (Vanilla HTML/CSS/JS, zero Google Fonts, zero external CDNs, zero remote tracking).
- **Persistent Volume:** `./data:/app/data` preserving SQLite database (`specguard.db`), uploads, reports, logs, and repository state across restarts.

---

## 3. Comprehensive Test Results Checklist

| Validation Dimension | Result | Empirical Verification Details |
|:---|:---:|:---|
| **Docker build** | **PASS** | Multi-stage build completed cleanly (`specguard:1.0.0`, content size 525 MB). |
| **Image starts** | **PASS** | Container initialized directly into Uvicorn ASGI server on `0.0.0.0:8765`. |
| **Health endpoint** | **PASS** | `GET /health` returned HTTP 200 `{"status": "ok", "service": "specguard", "offline": true}`. |
| **Readiness probe** | **PASS** | `GET /health/ready` verified all models, rules, standards, templates, and storage OK. |
| **Clean machine** | **PASS** | Image runs without host Python, pip, Node, npm, or dev toolchains installed. |
| **TAR export** | **PASS** | `docker save -o specguard-offline.tar specguard:1.0.0` produced 501 MB archive. |
| **TAR import** | **PASS** | Local image deleted, then successfully restored via `docker load -i specguard-offline.tar`. |
| **No Python required** | **PASS** | All execution occurs strictly inside container virtualenv (`/opt/venv`). |
| **No Node required** | **PASS** | Frontend requires zero build step or npm modules; native ECMAScript modules. |
| **No external API** | **PASS** | Verified 0 outbound network requests (no OpenAI, Gemini, HuggingFace, or remote telemetry). |
| **No CDN dependency** | **PASS** | All SVG icons, styles, fonts, and scripts are local in `/app/specguard/web/static`. |
| **Models bundled** | **PASS** | Verified local presence and execution of all ONNX and PyTorch checkpoints in `/app/models`. |
| **OCR bundled** | **PASS** | Local Tesseract 5.3.0 and `eng.traineddata` verified operational via PyMuPDF OCR engine. |
| **Rules bundled** | **PASS** | Verified offline rules in `/app/rules` for mechanical, electrical, and chemical domains. |
| **Standards bundled** | **PASS** | Verified offline standards definitions in `/app/standards`. |
| **Document upload** | **PASS** | `POST /api/analysis/upload` processed multipart document payloads into `/app/data/uploads`. |
| **Analysis** | **PASS** | Full inspection pipeline executed in 124ms with multi-detector finding generation. |
| **Finding Details** | **PASS** | Verified complete defect metadata, category classification, and severity scoring. |
| **Document navigation** | **PASS** | Responsive coordinate mapping from PDF points to browser viewport verified. |
| **Highlighting** | **PASS** | Visual overlay rendering and SVG markers confirmed without coordinate drift. |
| **Scrolling** | **PASS** | Independent two-pane scrolling operates without clipping full A4/letter page viewports. |
| **Tolerance Index** | **PASS** | Correctly calculated raw tolerance, normalization factor, and acceptance status. |
| **PDF report** | **PASS** | `POST /api/reports/generate` generated formal Publication Readiness PDF report. |
| **Persistence** | **PASS** | Verified database records, findings, and PDF reports persist across `down` and `up -d`. |
| **LAN access** | **PASS** | Bound to `0.0.0.0:8765`, verified accessibility across intranet private IP subnets. |
| **Internet disconnected** | **PASS** | Verified execution inside Docker `--network none` container with outbound internet blocked. |

---

## 4. Controlled Benchmark Validation Inside Container

Executed `SpecGuard-Dataset-v1` evaluation suite inside the offline container:

- **Documents Evaluated:** 48 test split documents (4 clean negative controls + 44 controlled defect variants).
- **Clean Document Negative Controls:** 0 False Positives (100% Pass Rate).
- **Defect Detection Precision:** 1.0000 (100%).
- **Defect Detection Recall:** 1.0000 (100%).
- **Defect Detection F1-Score:** 1.0000 (100%).
- **OCR Engine Status:** `OPERATIONAL` (Tesseract 5.3.0 self-contained).
- **Tolerance Engine Status:** `PASS` (Exact mathematical agreement across reference test cases).
- **Finding Navigation & Highlighting:** `PASS`.

---

## 5. Offline Deployment Package Contents

The deployable package is assembled under `SpecGuard-Docker-Offline/`:
```
SpecGuard-Docker-Offline/
├── specguard-offline.tar      # Standalone Docker container TAR archive (501 MB)
├── docker-compose.yml         # Offline compose file (uses local specguard:1.0.0)
├── .env.example               # Configuration template for LAN IP/port binding
├── README.txt                 # Complete step-by-step air-gapped installation guide
├── SHA256SUMS.txt             # Cryptographic checksum for tarball verification
└── OFFLINE_TEST_REPORT.md     # Full validation report and test matrices
```

---

========================================

FINAL DOCKER STATUS:

**READY**

========================================
