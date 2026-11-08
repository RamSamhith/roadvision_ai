# Multi-stage production Dockerfile for RoadVision
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies including FFmpeg and OpenCV runtime libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency specifications and install CPU-compatible wheels by default
COPY backend/requirements.txt /app/backend/
RUN pip install --upgrade pip setuptools wheel && \
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install -r /app/backend/requirements.txt

# Copy backend code, models, and configuration
COPY backend /app/backend
COPY models /app/models

# Expose backend API port
EXPOSE 8000

ENV PYTHONPATH=/app/backend \
    ROADVISION_DATA_DIR=/app/data \
    ROADVISION_DEVICE=cpu

# Create runtime directories
RUN mkdir -p /app/data/db /app/data/outputs /app/data/uploads_tmp /app/data/logs

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

