"""Services and telemetry sources API."""
from fastapi import APIRouter
from app.services import demo_telemetry
from app.core.config import settings

router = APIRouter(prefix="/api/services", tags=["services"])


@router.get("")
async def get_services():
    """Return current health status for all monitored services."""
    services = demo_telemetry.generate_current_service_metrics()
    return {
        "services": services,
        "is_demo": settings.is_demo_mode,
        "monitoring_mode": settings.MONITORING_MODE,
    }


@router.get("/map")
async def get_service_map():
    """Return service dependency map."""
    services = demo_telemetry.generate_current_service_metrics()
    # Build nodes and edges
    nodes = []
    edges = []
    for svc in services:
        nodes.append({
            "id": svc["name"],
            "label": svc["display_name"],
            "status": svc["status"],
            "error_rate": svc["error_rate"],
            "latency_ms": svc["latency_ms"],
            "request_rate": svc["request_rate"],
        })
        for dep in svc.get("dependencies", []):
            edges.append({
                "source": svc["name"],
                "target": dep,
                "label": f"{svc['request_rate']:.0f} req/s",
            })

    return {
        "nodes": nodes,
        "edges": edges,
        "is_demo": settings.is_demo_mode,
    }


@router.get("/telemetry-sources")
async def get_telemetry_sources():
    """Return connection status of all telemetry data sources."""
    if settings.is_demo_mode:
        return {
            "sources": [
                {"name": "prometheus", "status": "demo", "message": "Demo mode — synthetic metrics"},
                {"name": "loki", "status": "demo", "message": "Demo mode — synthetic logs"},
                {"name": "opentelemetry", "status": "demo", "message": "Demo mode — synthetic traces"},
            ],
            "is_demo": True,
        }

    sources = []
    # Check Prometheus
    from app.telemetry.prometheus_client import PrometheusClient
    prom = PrometheusClient()
    prom_ok, prom_err = await prom.check_connection()
    sources.append({
        "name": "prometheus",
        "url": settings.PROMETHEUS_URL,
        "status": "connected" if prom_ok else "disconnected",
        "error": prom_err,
    })

    # Check Loki
    from app.telemetry.loki_client import LokiClient
    loki = LokiClient()
    loki_ok, loki_err = await loki.check_connection()
    sources.append({
        "name": "loki",
        "url": settings.LOKI_URL,
        "status": "connected" if loki_ok else "disconnected",
        "error": loki_err,
    })

    # Check OTel
    from app.telemetry.otel_client import OTelClient
    otel = OTelClient()
    otel_ok, otel_err = await otel.check_connection()
    sources.append({
        "name": "opentelemetry",
        "url": settings.OTEL_COLLECTOR_URL,
        "status": "connected" if otel_ok else "disconnected",
        "error": otel_err,
    })

    return {"sources": sources, "is_demo": False}
