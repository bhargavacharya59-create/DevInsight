"""Integrations status and settings API."""
from fastapi import APIRouter
from app.core.config import settings
from app.services import github_service

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


@router.get("")
async def get_integrations():
    """Return connection status for all integrations."""
    integrations = []

    # GitHub
    if settings.github_configured:
        ok, msg = await github_service.check_connection()
        integrations.append({
            "name": "GitHub",
            "category": "source_control",
            "status": "connected" if ok else "error",
            "message": msg,
            "configured": True,
            "config_keys": ["GITHUB_TOKEN", "GITHUB_REPO_OWNER", "GITHUB_REPO_NAME"],
        })
    else:
        integrations.append({
            "name": "GitHub",
            "category": "source_control",
            "status": "not_configured",
            "message": "Set GITHUB_TOKEN, GITHUB_REPO_OWNER, GITHUB_REPO_NAME in .env",
            "configured": False,
            "config_keys": ["GITHUB_TOKEN", "GITHUB_REPO_OWNER", "GITHUB_REPO_NAME"],
        })

    # GitHub Actions
    integrations.append({
        "name": "GitHub Actions",
        "category": "cicd",
        "status": "connected" if settings.github_configured else "not_configured",
        "message": "Shares GitHub token" if settings.github_configured else "Requires GitHub integration",
        "configured": settings.github_configured,
        "config_keys": ["GITHUB_TOKEN"],
    })

    # Gemini AI
    integrations.append({
        "name": "Gemini AI",
        "category": "ai",
        "status": "connected" if settings.gemini_available else "not_configured",
        "message": f"Model: {settings.GEMINI_MODEL}" if settings.gemini_available else "Set GEMINI_API_KEY in .env",
        "configured": settings.gemini_available,
        "config_keys": ["GEMINI_API_KEY", "GEMINI_MODEL"],
    })

    # Prometheus
    if settings.MONITORING_MODE == "live":
        try:
            from app.telemetry.prometheus_client import PrometheusClient
            client = PrometheusClient()
            ok, err = await client.check_connection()
            integrations.append({
                "name": "Prometheus",
                "category": "monitoring",
                "status": "connected" if ok else "error",
                "message": settings.PROMETHEUS_URL if ok else str(err),
                "configured": True,
                "config_keys": ["PROMETHEUS_URL"],
            })
        except Exception:
            pass
    else:
        integrations.append({
            "name": "Prometheus",
            "category": "monitoring",
            "status": "demo",
            "message": "Demo mode — set MONITORING_MODE=live and PROMETHEUS_URL",
            "configured": False,
            "config_keys": ["PROMETHEUS_URL", "MONITORING_MODE"],
        })

    # Loki
    integrations.append({
        "name": "Grafana Loki",
        "category": "logs",
        "status": "demo" if settings.is_demo_mode else "unknown",
        "message": "Demo mode — set LOKI_URL and MONITORING_MODE=live" if settings.is_demo_mode else settings.LOKI_URL,
        "configured": not settings.is_demo_mode,
        "config_keys": ["LOKI_URL"],
    })

    # OpenTelemetry
    integrations.append({
        "name": "OpenTelemetry",
        "category": "tracing",
        "status": "demo" if settings.is_demo_mode else "unknown",
        "message": "Demo mode — configure OTel collector" if settings.is_demo_mode else settings.OTEL_COLLECTOR_URL,
        "configured": not settings.is_demo_mode,
        "config_keys": ["OTEL_COLLECTOR_URL"],
    })

    # ShopSphere
    from app.services.shopsphere_poller import get_poller_status
    poller = get_poller_status()
    integrations.append({
        "name": "ShopSphere",
        "category": "application",
        "status": "connected" if poller["shopsphere_reachable"] else "not_reachable",
        "message": (
            f"Scraping {poller['metrics_url']} — "
            f"{poller['scrape_count']} scrapes, {poller['anomalies_detected']} anomalies"
            if poller["shopsphere_reachable"]
            else poller.get("last_error") or "ShopSphere not running (start on port 8001)"
        ),
        "configured": True,
        "config_keys": ["SHOPSPHERE_URL", "SHOPSPHERE_METRICS_URL", "INGEST_API_KEY"],
        "poller": poller,
    })

    # Grafana
    integrations.append({
        "name": "Grafana",
        "category": "visualization",
        "status": "not_configured",
        "message": "Optional — start with docker compose up",
        "configured": False,
        "config_keys": [],
    })

    return {
        "integrations": integrations,
        "monitoring_mode": settings.MONITORING_MODE,
        "is_demo": settings.is_demo_mode,
    }
