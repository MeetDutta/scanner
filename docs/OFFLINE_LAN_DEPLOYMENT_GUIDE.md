# SpecGuard — 100% Offline & LAN Deployment Guide

This guide describes how to deploy and operate the SpecGuard inspection platform on a dedicated server inside an isolated Local Area Network (LAN), air-gapped intranet, or corporate private network with **zero Internet access**.

---

## 1. Network Architecture Overview

```text
       AIR-GAPPED / ISOLATED LOCAL AREA NETWORK (NO INTERNET GATEWAY)
┌────────────────────────────────────────────────────────────────────────┐
│                                                                        │
│   ┌────────────────────────┐                                           │
│   │ SpecGuard Host Server  │ (IP: 192.168.1.100)                       │
│   │ • Uvicorn / FastAPI    │                                           │
│   │ • Port: 8765           │                                           │
│   │ • Local SQLite (WAL)   │                                           │
│   │ • Local PyMuPDF Engine │                                           │
│   └───────────┬────────────┘                                           │
│               │                                                        │
│               ├──────────────────────────┬─────────────────────────┐   │
│               │                          │                         │   │
│   ┌───────────▼────────────┐ ┌───────────▼───────────┐ ┌───────────▼───┴───┐
│   │ LAN Workstation 1      │ │ LAN Workstation 2     │ │ LAN Workstation 3 │
│   │ IP: 192.168.1.101      │ │ IP: 192.168.1.102     │ │ IP: 192.168.1.103 │
│   │ Chrome / Edge / Firefox│ │ Chrome / Edge / Safari│ │ Chrome / Firefox  │
│   │ (Zero client install)  │ │ (Zero client install) │ │ (Zero install)    │
│   └────────────────────────┘ └───────────────────────┘ └───────────────────┘
└────────────────────────────────────────────────────────────────────────┘
```

* **Server**: Runs the Python web server, document parser, rules engine, and SQLite database.
* **Clients**: Connect purely via web browser using standard HTTP to the server's private LAN IP.
* **No external requests**: Zero calls to Google, OpenAI, CDNs, npm, or cloud infrastructure.

---

## 2. Server Installation & Preparation

### A. System Prerequisites
* Linux (Ubuntu 20.04+, Debian 11+, RHEL 8+), macOS, or Windows Server.
* Python 3.9+ with virtual environment tools.
* Local network adapter connected to the LAN switch/router with a static IP (e.g. `192.168.1.100`).

### B. Setup Environment
```bash
# 1. Clone or extract the repository onto the server
cd /opt/specguard   # or /Users/<username>/scanner

# 2. Create local Python virtual environment
python3 -m venv .venv

# 3. Activate and install dependencies offline from pre-downloaded wheels:
source .venv/bin/activate
pip install -r requirements.txt --no-index --find-links=/path/to/local/wheels
# (Or standard pip install if preparing on an online staging machine before isolation)
```

### C. Firewall Configuration
Ensure the host firewall permits inbound TCP traffic on port `8765` from the local subnet:

* **Linux (UFW)**:
  ```bash
  sudo ufw allow from 192.168.1.0/24 to any port 8765 proto tcp
  sudo ufw reload
  ```
* **Linux (firewalld)**:
  ```bash
  sudo firewall-cmd --zone=internal --add-port=8765/tcp --permanent
  sudo firewall-cmd --reload
  ```
* **Windows Defender Firewall**:
  ```powershell
  New-NetFirewallRule -DisplayName "SpecGuard Intranet" -Direction Inbound -LocalPort 8765 -Protocol TCP -Action Allow -RemoteAddress 192.168.1.0/24
  ```

---

## 3. Starting the Server for LAN Access

By default, running `python app.py` binds to `0.0.0.0`, enabling access across all network adapters:

```bash
# Activate virtual environment
source .venv/bin/activate

# Launch server binding to all LAN interfaces on port 8765:
python app.py --host 0.0.0.0 --port 8765
```

### Expected Startup Output
```text
2026-09-27 13:20:00 [INFO] SpecGuard: Starting SpecGuard 100% Offline LAN Web Server
2026-09-27 13:20:00 [INFO] SpecGuard: Listening on: http://0.0.0.0:8765 (Localhost: http://127.0.0.1:8765)
2026-09-27 13:20:00 [INFO] SpecGuard: LAN Access available at http://<YOUR-SERVER-LAN-IP>:8765 for intranet clients.
2026-09-27 13:20:00 [INFO] DocReady.Server: Verifying local offline environment...
2026-09-27 13:20:00 [INFO] SpecGuard: Environment verified: 100% Offline Mode Active.
```

---

## 4. Client Connection (Workstations)

Any user on the same LAN can access the platform without installing any software:

1. Open any modern browser (Google Chrome, Microsoft Edge, Mozilla Firefox, Apple Safari).
2. Enter the server's private IP and port:
   ```text
   http://192.168.1.100:8765
   ```
3. The SpecGuard application shell loads immediately from the server's local static assets.

---

## 5. System Health & Diagnostic Endpoints

Administrators can verify subsystem status via local API:

* **Top-Level Health Check**:
  ```bash
  curl http://192.168.1.100:8765/health
  # Response: {"status":"ok","service":"specguard","environment":"local","offline":true,"lan_ready":true}
  ```
* **Detailed Subsystem Report**:
  ```bash
  curl http://192.168.1.100:8765/api/health
  # Response:
  # {
  #   "status": "online",
  #   "mode": "offline",
  #   "components": {
  #     "application": "OK",
  #     "database": "OK",
  #     "storage": "OK",
  #     "rules": "OK",
  #     "document_engine": "OK",
  #     "pdf_renderer": "OK"
  #   },
  #   "network": {
  #     "offline": true,
  #     "lan_ready": true,
  #     "external_calls": "None"
  #   }
  # }
  ```

---

## 6. Multi-User Concurrency & Session Isolation

* **Isolated Uploads**: Each upload receives an 8-character cryptographic UUID prefix preventing filename collisions.
* **Concurrent SQLite Access**: Configured with Write-Ahead Logging (`WAL`) and `busy_timeout = 30000`, allowing multiple LAN clients to upload, inspect, and export documents simultaneously without database locks.
* **Memory & Process Separation**: Document rendering occurs per request in isolated memory buffers without cross-contamination.
