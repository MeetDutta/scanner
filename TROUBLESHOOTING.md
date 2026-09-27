# SpecGuard Web Platform Troubleshooting & Diagnostics Guide

This guide addresses common issues encountered when deploying and running **SpecGuard**.

---

## 1. Quick Diagnostic Checklist

If SpecGuard does not launch or behave as expected:

1. **Check the Log File:**
   Open:
   ```
   data/logs/docready.log (or data/logs/specguard.log)
   ```
   This file records detailed technical exceptions, environment checks, and startup events.

2. **Run Diagnostics via CLI:**
   ```bash
   python -c "from specguard.core.startup import verify_environment; r = verify_environment(); print('Ready:', r.is_ready, r.errors)"
   ```

3. **Verify Python Environment:**
   Ensure Python 3.9+ is active and dependencies are installed:
   ```bash
   pip install -r requirements-render.txt
   ```

---

## 2. Common Issues & Solutions

### Issue 1: Port Conflict (Port 8765 in Use)
- **Symptom:** Another local development server or background application is already using port `8765`.
- **Resolution:**
  Launch the server on a custom port:
  ```bash
  python app.py --port 9050
  ```

### Issue 2: Document Inspection Image Rendering
- **Symptom:** Page previews do not display in the browser.
- **Cause:** Missing or corrupt PyMuPDF dependency.
- **Resolution:**
  Ensure `pymupdf` is installed:
  ```bash
  pip install pymupdf>=1.22.0
  ```

### Issue 3: DOCX Fallback Pagination Notice
- **Symptom:** Analysis of a `.docx` file shows a notice regarding layout estimation.
- **Explanation:** DOCX format is a flow-document format without fixed physical pages. SpecGuard uses an advanced XML run-and-paragraph geometry estimator. For exact visual fidelity, install LibreOffice (`soffice`) on the host system.

### Issue 4: Database Locked or Read-Only Error
- **Symptom:** `sqlite3.OperationalError: attempt to write a readonly database`.
- **Cause:** Missing write permissions on `data/` or `data/database/`.
- **Resolution:**
  Ensure the process user has write permissions to the repository directory:
  ```bash
  chmod -R 755 data
  ```

---

## 3. Web Service Health Checks

Test the live API health:
```bash
curl -f http://127.0.0.1:8765/health
curl -f http://127.0.0.1:8765/api/health
```
Both return `200 OK` with JSON status when the server is healthy.
