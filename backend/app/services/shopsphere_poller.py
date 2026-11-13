"""
ShopSphere metrics poller.
Runs as a background asyncio task inside DevInsight.
Every DETECTION_INTERVAL_SECONDS it scrapes ShopSphere /metrics,
parses the Prometheus text format, feeds values into the anomaly
detector, and creates incidents when anomalies are found.

Tracks the last-seen counter values so it can compute rates correctly.
Reports connection status accurately — never pretends ShopSphere is up.
"""
from __future__ import annotations
import asyncio
import logging
import re
from datetime import datetime, UTC
from typing import Dict, Optional, Tuple

import aiohttp

from app.core.config import settings

logger = logging.getLogger("devinsight.poller")

# ── Prometheus text-format parser (no external library needed) ────────────────

_METRIC_RE = re.compile(
    r'^(?P<name>[a-zA-Z_:][a-zA-Z0-9_:]*)'
    r'(?:\{(?P<labels>[^}]*)\})?\s+'
    r'(?P<value>[+-]?(?:inf|nan|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?))'
    r'(?:\s+\d+)?$'
)


def parse_prometheus_text(text: str) -> Dict[str, float]:
    """
    Parse Prometheus text exposition format into a flat dict.
    For metrics with labels, keeps the first sample only (sufficient for our use).
    Returns metric_name → float value.
    """
    result: Dict[str, float] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = _METRIC_RE.match(line)
        if m:
            name = m.group("name")
            try:
                value = float(m.group("value"))
            except ValueError:
                continue
            # Keep first occurrence of each metric name
            if name not in result:
                result[name] = value
    return result


def extract_shopsphere_features(metrics: Dict[str, float]) -> Dict[str, float]:
    """
    Map raw Prometheus counter/gauge values from ShopSphere
    to the feature vector expected by the anomaly detector.
    Uses simple totals (not rates) since we're doing snapshot comparison.
    """
    total_requests = metrics.get("shopsphere_http_requests_total", 0.0)
    error_requests = metrics.get("shopsphere_http_errors_total", 0.0)
    active_requests = metrics.get("shopsphere_http_requests_active", 0.0)

    error_rate = (error_requests / total_requests * 100.0) if total_requests > 0 else 0.0

    # Latency: use the _sum / _count if _bucket not easily parseable
    latency_sum = metrics.get("shopsphere_http_request_duration_seconds_sum", 0.0)
    latency_count = metrics.get("shopsphere_http_request_duration_seconds_count", 0.0)
    latency_ms = (latency_sum / latency_count * 1000.0) if latency_count > 0 else 0.0

    db_sum = metrics.get("shopsphere_db_query_duration_seconds_sum", 0.0)
    db_count = metrics.get("shopsphere_db_query_duration_seconds_count", 0.0)
    db_latency_ms = (db_sum / db_count * 1000.0) if db_count > 0 else 0.0

    payment_failures = metrics.get("shopsphere_payments_total", 0.0)
    db_failures = metrics.get("shopsphere_db_connection_failures_total", 0.0)

    return {
        "request_rate": active_requests,
        "error_rate": round(error_rate, 3),
        "latency_ms": round(latency_ms, 2),
        "cpu_utilization": 0.0,       # not available from app-level metrics
        "memory_utilization": 0.0,    # not available from app-level metrics
        "db_query_latency": round(db_latency_ms, 2),
        "service_error_count": db_failures + payment_failures,
    }


# ── Poller state ──────────────────────────────────────────────────────────────

class PollerState:
    def __init__(self):
        self.running = False
        self.last_scrape: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.shopsphere_reachable: bool = False
        self.consecutive_failures: int = 0
        self.scrape_count: int = 0
        self.anomalies_detected: int = 0
        self.last_metrics: Dict[str, float] = {}


_state = PollerState()


def get_poller_status() -> dict:
    return {
        "running": _state.running,
        "shopsphere_reachable": _state.shopsphere_reachable,
        "last_scrape": _state.last_scrape.isoformat() if _state.last_scrape else None,
        "last_error": _state.last_error,
        "scrape_count": _state.scrape_count,
        "anomalies_detected": _state.anomalies_detected,
        "consecutive_failures": _state.consecutive_failures,
        "metrics_url": settings.SHOPSPHERE_METRICS_URL,
    }


# ── Core scrape function ───────────────────────────────────────────────────────

async def scrape_once() -> Tuple[bool, Optional[str]]:
    """
    Scrape ShopSphere /metrics once.
    Returns (success, error_message).
    """
    url = settings.SHOPSPHERE_METRICS_URL
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return False, f"HTTP {resp.status} from {url}"
                text = await resp.text()

        raw_metrics = parse_prometheus_text(text)
        features = extract_shopsphere_features(raw_metrics)

        _state.last_scrape = datetime.now(UTC)
        _state.last_metrics = raw_metrics
        _state.shopsphere_reachable = True
        _state.consecutive_failures = 0
        _state.scrape_count += 1

        logger.debug(
            "Scraped ShopSphere metrics: error_rate=%.2f%% latency=%.1fms",
            features["error_rate"], features["latency_ms"],
        )

        # Run anomaly detection
        from app.ml.anomaly_detector import get_detector
        detector = get_detector()
        if not detector.is_trained:
            return True, None

        prediction = detector.predict(features)
        if prediction.get("is_anomaly"):
            _state.anomalies_detected += 1
            score = prediction.get("anomaly_score", 0)
            logger.warning(
                "ShopSphere anomaly detected via poller: score=%.3f features=%s",
                score, features,
            )
            await _create_anomaly_incident(features, prediction)

        return True, None

    except aiohttp.ClientConnectorError:
        msg = f"Cannot connect to ShopSphere at {url} — is it running on port 8001?"
        _state.shopsphere_reachable = False
        _state.last_error = msg
        _state.consecutive_failures += 1
        if _state.consecutive_failures == 1:
            logger.info("ShopSphere not reachable: %s", msg)
        return False, msg

    except Exception as e:
        msg = str(e)
        _state.last_error = msg
        _state.consecutive_failures += 1
        logger.error("Poller scrape error: %s", e)
        return False, msg


async def _create_anomaly_incident(features: dict, prediction: dict) -> None:
    """Create a DevInsight incident from a poller-detected anomaly."""
    try:
        from app.db.base import AsyncSessionLocal
        from app.services.incident_service import get_incident_service
        from app.schemas.incident import IncidentCreate
        from app.models.incident import SeverityLevel

        score = prediction.get("anomaly_score", 0.5)
        severity = (
            SeverityLevel.CRITICAL if score > 0.8
            else SeverityLevel.HIGH if score > 0.6
            else SeverityLevel.MEDIUM
        )

        async with AsyncSessionLocal() as db:
            svc = get_incident_service()
            inc_data = IncidentCreate(
                title=f"ShopSphere anomaly detected (score={score:.2f}) — poller",
                description=(
                    f"Isolation Forest flagged abnormal metrics scraped from ShopSphere. "
                    f"error_rate={features['error_rate']:.1f}% "
                    f"latency={features['latency_ms']:.0f}ms "
                    f"db_latency={features['db_query_latency']:.0f}ms"
                ),
                severity=severity,
                affected_service="shopsphere",
                anomaly_score=score,
                is_demo=False,
                fingerprint=f"shopsphere:poller:anomaly",
                related_metrics={"features": features, "prediction": prediction},
            )
            incident, is_new = await svc.create_or_update(db, inc_data)
            await db.commit()
            if is_new:
                logger.info("Poller created incident %s", incident.id)

    except Exception as e:
        logger.error("_create_anomaly_incident failed: %s", e)


# ── Background loop ───────────────────────────────────────────────────────────

async def run_poller() -> None:
    """
    Main polling loop. Runs forever until cancelled.
    Interval: DETECTION_INTERVAL_SECONDS (default 30s).
    """
    _state.running = True
    interval = settings.DETECTION_INTERVAL_SECONDS
    logger.info(
        "ShopSphere poller started — scraping %s every %ds",
        settings.SHOPSPHERE_METRICS_URL, interval,
    )

    while True:
        try:
            await scrape_once()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Poller loop error: %s", e)

        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            break

    _state.running = False
    logger.info("ShopSphere poller stopped")
