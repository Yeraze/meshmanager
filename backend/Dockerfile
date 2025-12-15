# MeshManager Backend Dockerfile
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy all source files
COPY . .

# Upgrade pip and setuptools to compatible versions
RUN pip install --no-cache-dir "pip>=23.0" "setuptools<69.0.0" "hatchling" "wheel" "cython" "numpy"

# Set GDAL_CONFIG to help fiona find the correct GDAL version
ENV GDAL_CONFIG=/usr/bin/gdal-config

# Install Python dependencies with --no-build-isolation to work around fiona/rasterio build issues
RUN pip install --no-cache-dir --no-build-isolation .

# Production stage
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libgdal36 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 meshmanager && \
    chown -R meshmanager:meshmanager /app

USER meshmanager

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
