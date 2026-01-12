# ==========================================
# Auth Service Dockerfile
# Using multi-stage build to optimize image size
# ==========================================

# ==========================================
# Stage 1: Build stage
# ==========================================
FROM python:3.8.19-slim-bullseye AS builder

# Set working directory
WORKDIR /build

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files (using non-hashed version)
COPY services/auth-service/requirements-no-hash.txt ./requirements.txt

# Install Python dependencies to temporary directory
RUN pip install --upgrade pip && \
    pip install --prefix=/install -r requirements.txt

# ==========================================
# Stage 2: Runtime stage
# ==========================================
FROM python:3.8.19-slim-bullseye

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SERVICE_PORT=8001 \
    PATH="/install/bin:${PATH}" \
    PYTHONPATH="/install/lib/python3.8/site-packages:/app:${PYTHONPATH}"

# No need to install curl, health check uses Python urllib

# Copy installed dependencies from build stage
COPY --from=builder /install /install

# Copy shared modules
COPY shared/ /app/shared/

# Copy service code
COPY services/auth-service/app/ /app/app/

# Create logs directory
RUN mkdir -p /app/logs && \
    chmod 755 /app/logs

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8001

# Health check (using Python urllib to avoid curl dependency)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')" || exit 1

# Startup command
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
