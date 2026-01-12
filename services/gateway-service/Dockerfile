# ==========================================
# Gateway Service Dockerfile
# Using multi-stage build to optimize image size
# ==========================================

# ==========================================
# Stage 1: Build stage
# ==========================================
FROM python:3.8.10-slim AS builder

# Set working directory
WORKDIR /build

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Copy dependency files (using non-hashed version)
COPY services/gateway-service/requirements-no-hash.txt ./requirements.txt

# Install Python dependencies to temporary directory
RUN pip install --upgrade pip && \
    pip install --prefix=/install -r requirements.txt

# ==========================================
# Stage 2: Runtime stage
# ==========================================
FROM python:3.8.10-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SERVICE_PORT=8000 \
    PATH="/install/bin:${PATH}" \
    PYTHONPATH="/install/lib/python3.8/site-packages:/app:${PYTHONPATH}"

# Install runtime dependencies (curl for health check)
# Note: If apt-get fails, health check will use Python alternative
RUN apt-get update && apt-get install -y --no-install-recommends curl || true && \
    rm -rf /var/lib/apt/lists/* || true

# Copy installed dependencies from build stage
COPY --from=builder /install /install

# Copy shared modules
COPY shared/ /app/shared/

# Copy service code
COPY services/gateway-service/app/ /app/app/

# Create logs directory
RUN mkdir -p /app/logs && \
    chmod 755 /app/logs

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check (using Python instead of curl dependency)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Startup command
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
