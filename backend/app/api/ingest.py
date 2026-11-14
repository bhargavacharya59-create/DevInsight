"""
Telemetry ingest API.
Receives logs, errors, metrics and application events pushed by ShopSphere.

Authentication: X-API-Key header validated against INGEST_API_KEY env var.
All ingest calls are fire-and-forget from ShopSphere — DevInsight must
respond quickly (< 200ms). Heavy processing happens in background tasks.
"""
import hmac
import logging
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger("devinsight.ingest")

router = APIRouter(prefix="/api/ingest", tags=["ingest"])

# ── Auth dependency ───────────────────────────────────────────────────────────

def verify_ingest_key(request: Request) -> None:
    """Validate X-API-Key header. Raises 401 if missing or wrong."""
    configured_key = settings.INGEST_API_KEY
    if not configured_key:
        logger.error("Ingest API key is not configured; refusing telemetry ingestion")
        raise HTTPException(status_code=503, detail="Telemetry ingestion is not configured")
    key = request.headers.get("X-API-Key", "")
    if not key or not hmac.compare_digest(key, configured_key):
        logger.warning("Ingest auth failure from %s", request.client.host if request.client else "unknown")
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")


# ── Request schemas ───────────────────────────────────────────────────────────

class IngestErrorEvent(BaseModel):
    """Single error/exception event from ShopSphere."""
    service: str = "shopsphere"
    level: str = "ERROR"
    message: str
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    exception_type: Optional[str] = None
    timestamp: Optional[str] = None
    duration_ms: Optional[float] = None
    extra: Optional[Dict[str, Any]] = None


class IngestLogBatch(BaseModel):
    """Batch of structured log entries."""
    service: str = "shopsphere"
    logs: List[Dict[str, Any]] = Field(..., max_length=500)


class IngestMetricsSnapshot(BaseModel):
    """Point-in-time metric snapshot from ShopSphere."""
    service: str = "shopsphere"
    timestamp: Optional[str] = None
    request_rate: float = 0.0
    error_rate: float = 0.0          # percentage 0-100
    latency_p95_ms: float = 0.0
    cpu_utilization: float = 0.0
    memory_utilization: float = 0.0
    db_query_latency_ms: float = 0.0
    active_requests: float = 0.0
    orders_total: float = 0.0
    payment_failures: float = 0.0
    extra: Optional[Dict[str, Any]] = None


class IngestAppEvent(BaseModel):
    """Generic application lifecycle event."""
    service: str = "shopsphere"
    event_type: str            # e.g. "order_failed", "payment_failed", "simulation_started"
    description: str
    severity: str = "info"     # info | warning | error | critical
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None


# ── In-memory buffers (last 200 items each) ───────────────────────────────────
# In production these would go to a time-series DB or queue.

_error_buffer: List[Dict[str, Any]] = []
_log_buffer: List[Dict[str, Any]] = []
_metrics_buffer: List[Dict[str, Any]] = []
_event_buffer: List[Dict[str, Any]] = []

MAX_BUFFER = 200


def _append(buf: list, item: dict) -> None:
    buf.insert(0, item)
    if len(buf) > MAX_BUFFER:
        buf.pop()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/errors", status_code=202)
async def ingest_error(
    event: IngestErrorEvent,
    background: BackgroundTasks,
    _: None = Depends(verify_ingest_key),
):
    """
    Receive a single error event from ShopSphere.
    Returns 202 Accepted immediately; incident creation runs in background.
    """
    payload = {
        **event.model_dump(),
        "received_at": datetime.now(UTC).isoformat(),
    }
    _append(_error_buffer, payload)
    logger.info(
        "Ingest error received: %s %s → %s",
        event.method or "?",
        event.endpoint or "?",
        event.status_code or "?",
    )
    background.add_task(_process_error_event, payload)
    return {"accepted": True, "event_id": event.request_id}


@router.post("/logs", status_code=202)
async def ingest_logs(
    batch: IngestLogBatch,
    _: None = Depends(verify_ingest_key),
):
    """Receive a batch of structured log lines from ShopSphere."""
    for entry in batch.logs:
        entry["service"] = batch.service
        _append(_log_buffer, entry)

    logger.debug("Ingest log batch: %d lines from %s", len(batch.logs), batch.service)
    return {"accepted": True, "count": len(batch.logs)}


@router.post("/metrics", status_code=202)
async def ingest_metrics(
    snapshot: IngestMetricsSnapshot,
    background: BackgroundTasks,
    _: None = Depends(verify_ingest_key),
):
    """
    Receive a metric snapshot from ShopSphere.
    Runs anomaly detection in background.
    """
    payload = {
        **snapshot.model_dump(),
        "received_at": datetime.now(UTC).isoformat(),
    }
    _append(_metrics_buffer, payload)
    background.add_task(_process_metrics_snapshot, payload)
    return {"accepted": True}


@router.post("/event", status_code=202)
async def ingest_event(
    event: IngestAppEvent,
    _: None = Depends(verify_ingest_key),
):
    """Receive a generic application event (order failed, simulation started, etc.)."""
    payload = {
        **event.model_dump(),
        "received_at": datetime.now(UTC).isoformat(),
    }
    _append(_event_buffer, payload)
    logger.info("Ingest app event: %s / %s", event.service, event.event_type)
    return {"accepted": True}


# ── Read endpoints (for dashboard) ────────────────────────────────────────────

@router.get("/errors/recent")
async def get_recent_errors(limit: int = 50):
    """Return recently ingested ShopSphere errors."""
    return {"errors": _error_buffer[:limit], "total": len(_error_buffer)}


@router.get("/metrics/recent")
async def get_recent_metrics(limit: int = 50):
    """Return recently ingested ShopSphere metric snapshots."""
    return {"snapshots": _metrics_buffer[:limit], "total": len(_metrics_buffer)}


@router.get("/events/recent")
async def get_recent_events(limit: int = 50):
    """Return recently ingested application events."""
    return {"events": _event_buffer[:limit], "total": len(_event_buffer)}


@router.get("/status")
async def ingest_status():
    """Return buffer sizes and ingest health."""
    return {
        "status": "active",
        "buffers": {
            "errors": len(_error_buffer),
            "logs": len(_log_buffer),
            "metrics": len(_metrics_buffer),
            "events": len(_event_buffer),
        },
        "shopsphere_url": settings.SHOPSPHERE_URL,
    }


# ── Background processors ──────────────────────────────────────────────────────

async def _process_error_event(payload: Dict[str, Any]) -> None:
    """
    Background: evaluate a ShopSphere error event.
    If it looks like a production incident, create/update an incident in DevInsight.
    """
    status_code = payload.get("status_code", 0)
    endpoint = payload.get("endpoint", "unknown")
    service = payload.get("service", "shopsphere")

    # Only create incidents for server errors (5xx)
    if not status_code or status_code < 500:
        return

    try:
        from app.db.base import AsyncSessionLocal
        from app.services.incident_service import get_incident_service
        from app.schemas.incident import IncidentCreate
        from app.models.incident import SeverityLevel

        severity = SeverityLevel.CRITICAL if status_code == 500 else SeverityLevel.HIGH
        title = (
            f"HTTP {status_code} on {payload.get('method', 'POST')} {endpoint} "
            f"[{service}]"
        )

        inc_data = IncidentCreate(
            title=title,
            description=(
                f"ShopSphere reported {payload.get('exception_type', 'Exception')}: "
                f"{payload.get('message', 'No message')[:300]}"
            ),
            severity=severity,
            affected_service=service,
            anomaly_score=None,
            is_demo=False,
            fingerprint=f"shopsphere:{endpoint}:{status_code}",
            related_logs=[payload],
        )

        async with AsyncSessionLocal() as db:
            svc = get_incident_service()
            incident, is_new = await svc.create_or_update(db, inc_data)
            await db.commit()
            if is_new:
                logger.info(
                    "Incident created from ShopSphere error: id=%s title=%s",
                    incident.id, title,
                )
            else:
                logger.debug("Merged into existing incident %s", incident.id)

    except Exception as e:
        logger.error("_process_error_event failed: %s", e)


async def _process_metrics_snapshot(payload: Dict[str, Any]) -> None:
    """
    Background: run anomaly detection on a metric snapshot pushed by ShopSphere.
    If anomalous, create an incident.
    """
    try:
        from app.ml.anomaly_detector import get_detector
        detector = get_detector()
        if not detector.is_trained:
            return

        sample = {
            "request_rate": payload.get("request_rate", 0.0),
            "error_rate": payload.get("error_rate", 0.0),
            "latency_ms": payload.get("latency_p95_ms", 0.0),
            "cpu_utilization": payload.get("cpu_utilization", 0.0),
            "memory_utilization": payload.get("memory_utilization", 0.0),
            "db_query_latency": payload.get("db_query_latency_ms", 0.0),
            "service_error_count": payload.get("payment_failures", 0.0),
        }

        result = detector.predict(sample)
        if result.get("is_anomaly"):
            logger.warning(
                "Anomaly detected in ShopSphere metrics: score=%.3f",
                result.get("anomaly_score", 0),
            )
            # Create incident
            from app.db.base import AsyncSessionLocal
            from app.services.incident_service import get_incident_service
            from app.schemas.incident import IncidentCreate
            from app.models.incident import SeverityLevel

            score = result.get("anomaly_score", 0.5)
            severity = (
                SeverityLevel.CRITICAL if score > 0.8
                else SeverityLevel.HIGH if score > 0.6
                else SeverityLevel.MEDIUM
            )

            inc_data = IncidentCreate(
                title=f"Anomaly detected on {payload.get('service', 'shopsphere')} (score={score:.2f})",
                description="Isolation Forest anomaly detection flagged abnormal metric patterns in ShopSphere telemetry.",
                severity=severity,
                affected_service=payload.get("service", "shopsphere"),
                anomaly_score=score,
                is_demo=False,
                fingerprint=f"shopsphere:metrics:anomaly:{payload.get('service')}",
                related_metrics={"snapshot": sample, "anomaly_result": result},
            )
            async with AsyncSessionLocal() as db:
                svc = get_incident_service()
                incident, is_new = await svc.create_or_update(db, inc_data)
                await db.commit()
                if is_new:
                    logger.info("Anomaly incident created: %s", incident.id)

    except Exception as e:
        logger.error("_process_metrics_snapshot failed: %s", e)
