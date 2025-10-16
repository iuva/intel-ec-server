# ==========================================
# Gateway Service Dockerfile
# 使用多阶段构建优化镜像大小
# ==========================================

# ==========================================
# 阶段 1: 构建阶段
# ==========================================
FROM python:3.8.10-slim AS builder

# 设置工作目录
WORKDIR /build

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 复制依赖文件（使用无哈希版本）
COPY services/gateway-service/requirements-no-hash.txt ./requirements.txt

# 安装 Python 依赖到临时目录
RUN pip install --upgrade pip && \
    pip install --prefix=/install -r requirements.txt

# ==========================================
# 阶段 2: 运行阶段
# ==========================================
FROM python:3.8.10-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SERVICE_PORT=8000 \
    PATH="/install/bin:${PATH}" \
    PYTHONPATH="/install/lib/python3.8/site-packages:/app:${PYTHONPATH}"

# 安装运行时依赖（curl 用于健康检查）
# 注意：如果 apt-get 失败，健康检查将使用 Python 替代方案
RUN apt-get update && apt-get install -y --no-install-recommends curl || true && \
    rm -rf /var/lib/apt/lists/* || true

# 从构建阶段复制已安装的依赖
COPY --from=builder /install /install

# 复制共享模块
COPY shared/ /app/shared/

# 复制服务代码
COPY services/gateway-service/app/ /app/app/

# 创建日志目录
RUN mkdir -p /app/logs && \
    chmod 755 /app/logs

# 创建非root用户
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 8000

# 健康检查（使用 Python 而不依赖 curl）
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# 启动命令
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
