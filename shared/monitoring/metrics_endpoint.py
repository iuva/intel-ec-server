"""
Prometheus Metrics Endpoint
Provides /metrics route for Prometheus to scrape metrics
"""

from fastapi import APIRouter, Response

from shared.monitoring import get_metrics, get_metrics_content_type

# Create router
router = APIRouter(tags=["Monitoring"])


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    """
    Prometheus Metrics Endpoint

    Returns metrics data in Prometheus format for Prometheus server to scrape

    Note: This endpoint does not require authentication, should be excluded from authentication middleware
    """
    metrics_data = get_metrics()
    return Response(content=metrics_data, media_type=get_metrics_content_type())
