# ── RecoveryBench Dockerfile ─────────────────────────────────────────
# Multi-stage build for production deployment.
#
# Build:  docker build -t recoverybench .
# Run:    docker run -p 8000:8000 recoverybench
# ─────────────────────────────────────────────────────────────────────

FROM python:3.10-slim AS base

# System dependencies
# ffmpeg is required for Whisper ASR audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir \
        fastapi>=0.100.0 \
        uvicorn[standard]>=0.22.0 \
        python-multipart>=0.0.6

# Copy project files
COPY . .

# Create necessary directories
RUN mkdir -p traces/logs traces/reports tmp

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run the API server
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
