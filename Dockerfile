# syntax=docker/dockerfile:1

# ==============================================================================
# Stage 1: Build & Dependency Wheel Compilation
# ==============================================================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies for C extensions (e.g. murmurhash)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install wheel dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ==============================================================================
# Stage 2: Hardened Runtime Container
# ==============================================================================
FROM python:3.11-slim AS runtime

LABEL maintainer="AetherSDLC Engineering <engineering@aethersdlc.internal>"
LABEL description="AetherSDLC Agentic Engineering System & URL Shortener Service"

# Set secure, deterministic Python environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000 \
    HOST=0.0.0.0

# Copy pre-built virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create dedicated non-root user and group
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/sh -m appuser

# Set up working directory with correct permissions
WORKDIR /app

# Create persistent state directories
RUN mkdir -p /app/logs /app/artifacts && \
    chown -R appuser:appgroup /app

# Copy application source code with non-root ownership
COPY --chown=appuser:appgroup main.py .
COPY --chown=appuser:appgroup src/ ./src/

# Switch to non-root execution
USER appuser:appgroup

# Expose default listening port
EXPOSE 8000

# Container liveness health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; res = urllib.request.urlopen('http://127.0.0.1:8000/api/pipeline/status'); exit(0 if res.status == 200 else 1)"

# Default entrypoint
CMD ["python", "main.py"]
