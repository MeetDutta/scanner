# ==============================================================================
# DocReady — Production Container for Render Deployment & Mentor Demo
# 100% Offline Architecture — Zero Cloud AI Dependencies — Zero Remote Downloads
# ==============================================================================

FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DOCREADY_ENV=render_demo \
    DOCREADY_WEB_MODE=1 \
    DOCREADY_HOST=0.0.0.0 \
    PORT=10000

# Install optional system OCR & networking healthcheck utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first for optimal Docker layer caching
COPY requirements-render.txt /app/
RUN pip install --no-cache-dir -U pip setuptools wheel && \
    pip install --no-cache-dir -r requirements-render.txt

# Copy application source code, standards, templates, models, and web UI
COPY . /app/

# Ensure runtime directories exist and are writable
RUN mkdir -p /app/data/uploads /app/data/reports /app/data/logs /app/data/database /app/data/repository && \
    chmod -R 777 /app/data

# Non-root service user for container security
RUN useradd -u 1001 -m docready && \
    chown -R docready:docready /app
USER docready

# Expose Render default port
EXPOSE 10000

# Container health probe targeting the verified /health endpoint
HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:${PORT:-10000}/health || exit 1

# Start FastAPI application using the verified factory pattern
CMD ["sh", "-c", "uvicorn specguard.server.app:create_app --factory --host 0.0.0.0 --port ${PORT:-10000} --workers 1"]
