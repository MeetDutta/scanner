================================================================================
SPECGUARD — PRODUCTION OFFLINE DOCKER DEPLOYMENT GUIDE
================================================================================

SpecGuard is a 100% self-contained web platform for engineering document quality,
compliance inspection, tolerance evaluation, and verification.

This package contains the prebuilt offline container image and configuration.
No internet connection, Python, pip, Node.js, or external APIs are required on the
target machine.

--------------------------------------------------------------------------------
1. BUILD MACHINE INSTRUCTIONS (Reference)
--------------------------------------------------------------------------------

BUILD IMAGE:
  docker build -t specguard:1.0.0 .

EXPORT IMAGE:
  docker save -o specguard-offline.tar specguard:1.0.0

GENERATE CHECKSUM:
  shasum -a 256 specguard-offline.tar > SHA256SUMS.txt

--------------------------------------------------------------------------------
2. TRANSFER INSTRUCTIONS
--------------------------------------------------------------------------------

TRANSFER:
  Copy the entire `SpecGuard-Docker-Offline` folder or `specguard-offline.tar`
  via physical media (USB drive, optical disc, secure air-gap transfer) to the
  offline host machine.

--------------------------------------------------------------------------------
3. OFFLINE MACHINE DEPLOYMENT
--------------------------------------------------------------------------------

STEP 1 — LOAD IMAGE:
  docker load -i specguard-offline.tar

STEP 2 — VERIFY LOADED IMAGE:
  docker images

  Expected Output:
  REPOSITORY   TAG       IMAGE ID       SIZE
  specguard    1.0.0     ...            ~525MB

STEP 3 — START SERVICE:
  docker compose up -d

  IMPORTANT:
  Do NOT run `docker pull` on the offline machine.
  Docker Compose will use the locally loaded `specguard:1.0.0` image.

STEP 4 — CHECK CONTAINER STATUS:
  docker ps

  Expected Status: Up (healthy)

STEP 5 — VIEW RUNTIME LOGS:
  docker logs -f specguard

STEP 6 — OPEN IN BROWSER:
  Localhost:
    http://localhost:8765

  LAN / Intranet Clients:
    http://<HOST-IP>:8765

STEP 7 — STOP SERVICE:
  docker compose down

--------------------------------------------------------------------------------
4. HEALTH AND READINESS ENDPOINTS
--------------------------------------------------------------------------------

Liveness Probe:
  curl http://localhost:8765/health
  Response: {"status": "ok", "service": "specguard", "offline": true, "lan_ready": true}

Readiness Probe:
  curl http://localhost:8765/health/ready
  Response: {"status": "ready", "service": "specguard", "models": "OK", "rules": "OK", "standards": "OK", "templates": "OK", "storage": "OK", "offline": true}

--------------------------------------------------------------------------------
5. PERSISTENT STORAGE
--------------------------------------------------------------------------------

All user uploads, reports, databases, and inspection history are stored in:
  ./data/ (mounted to /app/data inside the container)

Directory structure:
  ./data/database/   -> SQLite database (specguard.db)
  ./data/uploads/    -> Uploaded engineering documents
  ./data/reports/    -> Generated formal inspection PDF reports
  ./data/logs/       -> Runtime application logs
  ./data/repository/ -> Cross-document comparison repository

Data persists automatically across `docker compose down` and `docker compose up -d`.
================================================================================
