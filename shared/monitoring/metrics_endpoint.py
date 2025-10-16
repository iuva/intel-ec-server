"""
Prometheus Metrics 端点
提供 /metrics 路由用于 Prometheus 抓取指标
"""

from fastapi import APIRouter, Response

from shared.monitoring import get_metrics, get_metrics_content_type

# 创建路由器
router = APIRouter(tags=["监控"])


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    """
    Prometheus 指标端点

    返回 Prometheus 格式的指标数据，供 Prometheus 服务器抓取

    注意：此端点不需要认证，应在认证中间件中排除
    """
    metrics_data = get_metrics()
    return Response(content=metrics_data, media_type=get_metrics_content_type())
