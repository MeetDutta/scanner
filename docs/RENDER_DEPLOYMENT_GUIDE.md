# DocReady — Render Deployment & Demonstration Guide

**Environment:** Render Cloud Web Service (Testing & Demonstration Only)  
**Target Platform:** Python 3.11 / Debian Linux (Headless)  
**Offline Integrity:** 100% Preserved (Zero external AI APIs, Zero telemetry, Zero cloud CDN dependencies)  
**Version:** 1.0.0  

---

## 1. Executive Summary

This guide provides step-by-step instructions for deploying the **DocReady** document intelligence and formatting readiness verification platform to **Render** for testing and mentor demonstration.

DocReady is originally architected as an offline-first desktop/intranet system. The Render deployment is configured as an isolated, environment-aware testing profile (`render_demo`) that:
- Binds to `0.0.0.0` using Render's dynamic `$PORT`.
- Suppresses desktop GUI dependencies (`PySide6`) while keeping all 16 core analysis engines active.
- Serves the modern single-page dashboard directly over HTTP.
- Exposes a dedicated health-check endpoint (`/health`).
- Strictly avoids introducing any external cloud AI services, tracking, or remote model downloads.

---

## 2. Deployment Architecture

DocReady supports two deployment modes on Render:

| Feature | Option A: Native Python Web Service (Recommended) | Option B: Docker Container |
| :--- | :--- | :--- |
| **Best For** | Fastest build time (~1.5 min), zero container overhead | Native Tesseract OCR binary bundled |
| **Build Command** | `pip install --upgrade pip && pip install -r requirements-render.txt` | Automatically builds from `Dockerfile` |
| **Start Command** | `uvicorn specguard.server.app:create_app --factory --host 0.0.0.0 --port $PORT --workers 1` | Defined in Dockerfile `CMD` |
| **System Packages** | Uses pre-built Linux wheels (`opencv-python-headless`, `pymupdf`) | Bundles `tesseract-ocr` & `tesseract-ocr-eng` |
| **OCR Fallback** | OpenCV Morphological Vision Engine (Built-in) | Hybrid OpenCV + Tesseract OCR |
| **Free Tier Ready** | Yes | Yes |

---

## 3. Option A: Native Python Deployment (Step-by-Step)

### Step 1: Connect Repository to Render
1. Log in to your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** → **Web Service**.
3. Connect your GitHub / GitLab repository containing the `scanner` codebase.
4. Select the target branch (e.g. `web-interface-migration` or `main`).

### Step 2: Configure Service Settings

| Setting | Value |
| :--- | :--- |
| **Name** | `docready-demo` (or desired name) |
| **Region** | Oregon (US West) or closest region |
| **Branch** | Your target branch |
| **Root Directory** | Leave empty (or `.` if required) |
| **Runtime** | **Python** |
| **Build Command** | `pip install --upgrade pip && pip install -r requirements-render.txt` |
| **Start Command** | `uvicorn specguard.server.app:create_app --factory --host 0.0.0.0 --port $PORT --workers 1` |
| **Instance Type** | Free (or Starter for persistent RAM) |

### Step 3: Configure Environment Variables
Under the **Environment Variables** tab, add:

| Key | Value | Description |
| :--- | :--- | :--- |
| `PYTHON_VERSION` | `3.11.10` | Enforces compatible Python 3.11 runtime |
| `DOCREADY_ENV` | `render_demo` | Activates Render testing profile |
| `DOCREADY_WEB_MODE` | `1` | Bypasses desktop PySide6 pre-flight checks |
| `DOCREADY_HOST` | `0.0.0.0` | Binds to all network interfaces |
| `LOG_LEVEL` | `INFO` | Standard application logging |

### Step 4: Configure Health Check
Under **Advanced Settings**:
- **Health Check Path**: `/health`

Click **Create Web Service**. Render will install dependencies and start DocReady.

---

## 4. Option B: Docker Container Deployment

If you require the system Tesseract OCR binary:
1. In Render, select **Runtime: Docker**.
2. **Dockerfile Path**: `./Dockerfile`.
3. Set the identical Environment Variables as above (`DOCREADY_ENV=render_demo`, `DOCREADY_WEB_MODE=1`).
4. Set **Health Check Path**: `/health`.
5. Click **Create Web Service**.

---

## 5. Blueprint Deployment (`render.yaml`)

You can also deploy with one click using Render's Infrastructure-as-Code feature:
1. In Render Dashboard, click **New +** → **Blueprint**.
2. Point to the repository. Render will automatically detect `render.yaml` and configure all build commands, environment variables, and health-check endpoints.
3. Click **Apply**.

---

## 6. Storage & Ephemeral Filesystem Notice

> [!WARNING]
> **Ephemeral Storage Notice**: Render's free and starter tiers utilize ephemeral container filesystems. Any documents uploaded, analysis records created, or reports generated will be stored temporarily in memory/disk and cleared whenever the service spins down due to inactivity or redeploys.
>
> **For Demonstrations**: This is standard and expected behavior for stateless testing environments.

### Optional: Persistent Disk Setup (Paid Plans)
If permanent retention of uploads and reports is required:
1. In Render Web Service settings, navigate to **Disks**.
2. Add a persistent disk:
   - **Name**: `docready-data`
   - **Mount Path**: `/var/data/docready`
   - **Size**: 10 GB
3. Add Environment Variable:
   - `DOCREADY_DATA_DIR` = `/var/data/docready`

---

## 7. Verification & Post-Deployment Testing

Once Render displays **Service Live**, verify the deployment:

### 1. Health Probe
Open `https://<your-service-name>.onrender.com/health` in your browser:
```json
{
  "status": "ok",
  "service": "docready",
  "environment": "render_demo"
}
```

### 2. Frontend Dashboard
Navigate to `https://<your-service-name>.onrender.com/`:
- Confirm the DocReady Dashboard loads with CSS formatting and sidebar navigation.
- Verify that active standards and system readiness counters render.

### 3. Document Analysis Test
1. Click **Upload Document** (or navigate to `#analysis`).
2. Upload a sample PDF or DOCX file (such as `demo_samples/mechanical_sample_with_errors.pdf`).
3. Select an engineering domain (`mechanical`, `electrical`, `chemical`).
4. Click **Start Verification Analysis**.
5. Observe real-time stage progress updates and verify that findings and visual bounding box overlays display properly.
6. Click **Generate Executive Report** to preview and download the HTML report.

---

## 8. Rollback & Maintenance Instructions

### Rollback on Render
1. In the Render Dashboard, open your web service.
2. Go to the **Events** tab.
3. Locate the previous successful deploy and click **Rollback to this deploy**.

### Local Desktop Execution Unaffected
The original offline desktop workflow remains completely untouched:
```bash
# To run local offline web dashboard:
python portable_launcher.py

# To run local PySide6 desktop GUI:
python app.py --gui
```
