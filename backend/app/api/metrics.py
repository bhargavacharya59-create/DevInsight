"""Metrics explorer API."""
from typing import Optional
from fastapi import APIRouter, Query
from app.services import demo_telemetry
from app.core.config import settings

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

AVAILABLE_METRICS = [
    "request_rate", "error_rate", "latency_ms",
    "cpu_utilization", "memory_utilization",
    "db_query_latency", "db_connections",
]


@router.get("")
async def get_metrics(
    service: Optional[str] = Query(None),
    metric: Optional[str] = Query(None),
    duration_minutes: int = Query(60, ge=5, le=1440),
    resolution_seconds: int = Query(60, ge=15, le=3600),
):
    """Return metric timeseries for the explorer."""
    services = [service] if service else [s["name"] for s in demo_telemetry.SERVICES]
    metrics = [metric] if metric else ["request_rate", "error_rate", "latency_ms", "cpu_utilization", "memory_utilization"]

    result = {}
    for svc in services:
        result[svc] = {}
        for m in metrics:
            if m not in AVAILABLE_METRICS:
                continue
            series = demo_telemetry.generate_metric_timeseries(svc, m, duration_minutes, resolution_seconds)
            result[svc][m] = {
                "name": m,
                "unit": series.unit,
                "current_value": series.current_value,
                "data_points": [
                    {"timestamp": p.timestamp.isoformat() + "Z", "value": p.value}
                    for p in series.data_points
                ],
                "anomaly_markers": [
                    ts.isoformat() + "Z" for ts in (series.anomaly_markers or [])
                ],
            }

    return {
        "metrics": result,
        "available_metrics": AVAILABLE_METRICS,
        "services": [s["name"] for s in demo_telemetry.SERVICES],
        "is_demo": settings.is_demo_mode,
        "active_scenario": demo_telemetry.get_active_scenario(),
    }


@router.get("/current")
async def get_current_metrics():
    """Return current-snapshot metrics for all services."""
    return {
        "services": demo_telemetry.generate_current_service_metrics(),
        "overview": demo_telemetry.generate_overview_metrics(),
        "is_demo": settings.is_demo_mode,
    }
