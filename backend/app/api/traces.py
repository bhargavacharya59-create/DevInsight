"""Traces API."""
from typing import Optional
from fastapi import APIRouter, Query
from app.services import demo_telemetry
from app.core.config import settings

router = APIRouter(prefix="/api/traces", tags=["traces"])


@router.get("")
async def get_traces(
    service: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    """Return distributed traces."""
    if settings.is_demo_mode:
        traces = demo_telemetry.generate_traces(service=service, limit=limit)
        return {
            "traces": traces,
            "total": len(traces),
            "is_demo": True,
            "source": "demo_synthetic",
        }
    else:
        from app.telemetry.otel_client import OTelClient
        client = OTelClient()
        connected, error = await client.check_connection()
        if not connected:
            return {
                "traces": [],
                "total": 0,
                "is_demo": False,
                "source": "otel",
                "connection_error": error,
                "message": "OpenTelemetry backend is not connected. Check OTEL_COLLECTOR_URL.",
            }
        traces = await client.search_traces(service=service, limit=limit) or []
        return {
            "traces": traces,
            "total": len(traces),
            "is_demo": False,
            "source": "otel",
        }
