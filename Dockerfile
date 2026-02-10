# MeshManager - Unified Docker Image
# Multi-stage build combining frontend and backend into a single container

# =============================================================================
# Stage 1: Build Frontend
# =============================================================================
FROM node:22-alpine AS frontend-builder

WORKDIR /app

# Install dependencies
COPY frontend/package*.json ./
RUN npm ci

# Copy source and build
COPY frontend/ ./
RUN npm run build

# =============================================================================
# Stage 2: Build Backend Dependencies
# =============================================================================
FROM python:3.12-slim AS backend-builder

WORKDIR /app

# Install build dependencies (libgdal-dev needed for fiona on ARM64)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy backend source
COPY backend/ ./

# Install Python dependencies
RUN pip install --no-cache-dir .

# =============================================================================
# Stage 3: Production Image
# =============================================================================
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    gdal-bin \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from backend builder
COPY --from=backend-builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Copy backend application code
COPY backend/ ./

# Copy frontend build output to static directory
COPY --from=frontend-builder /app/dist ./static

# Create non-root user
RUN chmod +x entrypoint.sh && \
    useradd -m -u 1000 meshmanager && \
    chown -R meshmanager:meshmanager /app

USER meshmanager

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

# Run migrations then start the application
ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
