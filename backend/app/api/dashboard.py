"""Dashboard overview API."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.core.config import settings
from app.services.incident_service import get_incident_service
from app.services import demo_telemetry

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/overview")
async def get_overview(db: AsyncSession = Depends(get_db)):
    """Return overview dashboard data including KPIs and current metrics."""
    svc = get_incident_service()
    stats = await svc.get_stats(db)

    # System health determination
    if stats["critical_incidents"] > 0 and stats["active_incidents"] > 0:
        health = "critical"
        health_score = 30.0
    elif stats["active_incidents"] > 2:
        health = "degraded"
        health_score = 65.0
    elif stats["active_incidents"] > 0:
        health = "degraded"
        health_score = 80.0
    else:
        health = "healthy"
        health_score = 98.0

    current_metrics = demo_telemetry.generate_overview_metrics()
    services = demo_telemetry.generate_current_service_metrics()

    # Generate timeseries for charts (last 60 min, 1-min resolution)
    charts = {}
    for metric in ["request_rate", "error_rate", "latency_ms", "cpu_utilization", "memory_utilization"]:
        series = demo_telemetry.generate_metric_timeseries(
            "shopsphere-api", metric, duration_minutes=60, resolution_seconds=60
        )
        charts[metric] = [
            {"timestamp": p.timestamp.isoformat() + "Z", "value": p.value}
            for p in series.data_points
        ]

    return {
        "kpis": {
            **stats,
            "system_health": health,
            "system_health_score": health_score,
            "avg_detection_time_minutes": 2.3,
        },
        "monitoring_mode": settings.MONITORING_MODE,
        "is_demo": settings.is_demo_mode,
        "current_metrics": current_metrics,
        "services": services,
        "charts": charts,
        "active_scenario": demo_telemetry.get_active_scenario(),
    }
