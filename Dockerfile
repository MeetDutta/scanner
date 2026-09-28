# ==============================================================================
# SpecGuard — Production Multi-Stage Offline Dockerfile
# 100% Offline Architecture — Zero Remote API Calls — Zero Runtime Downloads
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Builder
# Compiles wheels and installs Python dependencies in an isolated virtualenv
# ------------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS builder

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install minimal build tools for native Python wheel compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment for clean layer extraction
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build

# Copy dependency manifest
COPY requirements-docker.txt /build/

# Install dependencies using CPU-optimized PyTorch wheel index
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements-docker.txt --extra-index-url https://download.pytorch.org/whl/cpu

# ------------------------------------------------------------------------------
# Stage 2: Runtime
# Minimal, secure, non-root production runtime image
# ------------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS runtime

# Metadata labels (OCI specification compliant)
LABEL org.opencontainers.image.title="SpecGuard" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.description="SpecGuard 100% Offline Engineering Document Quality & Compliance Inspection Platform" \
      org.opencontainers.image.created="2026-09-28T00:00:00Z" \
      org.opencontainers.image.source="https://github.com/MeetDutta/scanner" \
      org.opencontainers.image.licenses="Proprietary"

# Configure environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    SPECGUARD_ENV=production \
    SPECGUARD_HOST=0.0.0.0 \
    SPECGUARD_PORT=8765 \
    SPECGUARD_APP_DIR=/app \
    SPECGUARD_DATA_DIR=/app/data \
    TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

# Install runtime system packages (Tesseract OCR, English data, OpenCV GLib, and curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-built virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create dedicated unprivileged service user and group
RUN groupadd -g 1001 specguard && \
    useradd -u 1001 -g specguard -m -s /bin/bash specguard

WORKDIR /app

# Copy application source code and bundled offline intelligence assets
COPY specguard /app/specguard
COPY models /app/models
COPY rules /app/rules
COPY standards /app/standards
COPY templates /app/templates
COPY app.py /app/app.py
COPY benchmark.py /app/benchmark.py
COPY MODEL_INVENTORY.json /app/MODEL_INVENTORY.json
COPY pyproject.toml /app/pyproject.toml

# Set up static directory symlink for path flexibility
RUN ln -s /app/specguard/web/static /app/static

# Initialize mutable persistent data directory structure
RUN mkdir -p /app/data/uploads \
             /app/data/reports \
             /app/data/logs \
             /app/data/database \
             /app/data/repository \
             /app/data/tmp && \
    chown -R specguard:specguard /app && \
    chmod -R 755 /app && \
    chmod -R 775 /app/data

# Switch to unprivileged runtime user
USER specguard

# Expose default application port
EXPOSE 8765

# Self-contained container healthcheck targeting /health endpoint
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=4)" || exit 1

# Start SpecGuard ASGI web application server
CMD ["python", "-m", "uvicorn", "specguard.server.app:app", "--host", "0.0.0.0", "--port", "8765", "--workers", "1"]
