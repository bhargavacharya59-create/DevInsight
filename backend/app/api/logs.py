"""Logs explorer API."""
from typing import Optional
from fastapi import APIRouter, Query
from app.services import demo_telemetry
from app.core.config import settings

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("")
async def get_logs(
    service: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    minutes_back: int = Query(60, ge=1, le=1440),
):
    """Return log entries from demo or live Loki."""
    if settings.is_demo_mode:
        logs = demo_telemetry.generate_logs(
            service=service,
            severity=severity,
            limit=limit,
            minutes_back=minutes_back,
        )
        if search:
            logs = [l for l in logs if search.lower() in l["message"].lower()]
        return {
            "logs": logs,
            "total": len(logs),
            "is_demo": True,
            "source": "demo_synthetic",
        }
    else:
        # Live mode: attempt Loki query
        from app.telemetry.loki_client import LokiClient
        client = LokiClient()
        connected, error = await client.check_connection()
        if not connected:
            return {
                "logs": [],
                "total": 0,
                "is_demo": False,
                "source": "loki",
                "connection_error": error,
                "message": "Loki is not connected. Check LOKI_URL in configuration.",
            }
        logs = await client.get_service_logs(
            service=service or "shopsphere",
            severity=severity,
            minutes_back=minutes_back,
            limit=limit,
        ) or []
        return {
            "logs": logs,
            "total": len(logs),
            "is_demo": False,
            "source": "loki",
        }
