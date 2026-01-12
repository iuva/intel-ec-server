# ==========================================
# Host Service Dockerfile
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
COPY services/host-service/requirements-no-hash.txt ./requirements.txt

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
    SERVICE_PORT=8003 \
    PATH="/install/bin:${PATH}" \
    PYTHONPATH="/install/lib/python3.8/site-packages:/app:${PYTHONPATH}"

# No need to install curl, health check uses Python urllib

# Copy installed dependencies from build stage
COPY --from=builder /install /install

# Copy shared modules
COPY shared/ /app/shared/

# Copy service code
COPY services/host-service/app/ /app/app/

# Create non-root user (before creating directories)
RUN useradd -m -u 1000 appuser

# Create logs directory and file upload directory
# Note:
# 1. Directories must exist to perform volume mounting
# 2. Volume mounting will overwrite directory contents, but the directory itself will be preserved
# 3. After volume mounting, directory ownership may change, the application will automatically check and fix at startup
RUN mkdir -p /app/logs /app/uploads && \
    chown -R appuser:appuser /app && \
    chmod 755 /app/logs && \
    chmod 755 /app/uploads

# Switch to non-root user
USER appuser

# Note: When Docker volume mounts to /app/uploads:
# - Files in the volume will overwrite directory contents in the image
# - Directory permissions are determined by the volume's permissions
# - When the application starts (FileManageService.__init__) will automatically check and fix permissions

# Expose port
EXPOSE 8003

# Health check (using Python urllib to avoid curl dependency)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8003/health')" || exit 1

# Startup command
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
