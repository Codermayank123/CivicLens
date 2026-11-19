# ==============================================================================
# CivicLens Backend — Dockerfile
# ==============================================================================
# Multi-stage build: install dependencies in builder, copy to slim runtime.
# ==============================================================================

FROM python:3.11-slim AS builder

WORKDIR /build

# Install system dependencies required by the MongoDB/FastAPI service.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .[dev]

# ── Runtime Stage ────────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create non-root user
RUN groupadd -r civiclens && useradd -r -g civiclens civiclens && \
    mkdir -p /app/uploads && chown -R civiclens:civiclens /app
USER civiclens

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
