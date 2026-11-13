"""
Demo telemetry generator.
Produces clearly-labeled synthetic telemetry for demo mode.
Never presented as real production data.
"""
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Any
import random
import math
import uuid

from app.schemas.service import MetricDataPoint, MetricSeries, LogEntry, TraceSpan

# ── Scenario definitions ─────────────────────────────────────────────────────

DEMO_SCENARIOS = [
    {
        "id": "normal_operation",
        "name": "Normal System Operation",
        "description": "Baseline healthy operation across all ShopSphere services with typical traffic patterns.",
        "category": "baseline",
        "duration_seconds": 60,
        "config": {
            "error_rate_multiplier": 1.0,
            "latency_multiplier": 1.0,
            "cpu_multiplier": 1.0,
            "memory_multiplier": 1.0,
        },
    },
    {
        "id": "database_latency_spike",
        "name": "Database Latency Spike",
        "description": "Simulates a sudden increase in database query latency causing cascading slowdowns across Order and Payment services.",
        "category": "database",
        "duration_seconds": 120,
        "config": {
            "db_latency_multiplier": 8.0,
            "latency_multiplier": 3.0,
            "error_rate_multiplier": 2.5,
            "cpu_multiplier": 1.3,
            "affected_services": ["order-service", "payment-service", "database"],
        },
    },
    {
        "id": "http_500_spike",
        "name": "HTTP 500 Error Spike",
        "description": "Simulates a surge in HTTP 500 errors across the ShopSphere API, likely due to an unhandled exception.",
        "category": "api",
        "duration_seconds": 90,
        "config": {
            "error_rate_multiplier": 15.0,
            "latency_multiplier": 1.4,
            "affected_services": ["shopsphere-api"],
        },
    },
    {
        "id": "payment_failures",
        "name": "Payment Service Failures",
        "description": "Simulates intermittent payment processing failures, causing elevated error rates in the Payment Service.",
        "category": "payment",
        "duration_seconds": 150,
        "config": {
            "error_rate_multiplier": 1.0,
            "payment_error_multiplier": 12.0,
            "latency_multiplier": 2.0,
            "affected_services": ["payment-service"],
        },
    },
    {
        "id": "cpu_spike",
        "name": "CPU Spike",
        "description": "Simulates a CPU utilization spike on the ShopSphere API host, possibly due to a compute-intensive operation or runaway process.",
        "category": "infrastructure",
        "duration_seconds": 120,
        "config": {
            "cpu_multiplier": 4.5,
            "latency_multiplier": 2.2,
            "error_rate_multiplier": 1.8,
            "affected_services": ["shopsphere-api", "shopsphere-frontend"],
        },
    },
    {
        "id": "memory_spike",
        "name": "Memory Spike / Memory Leak",
        "description": "Simulates steadily increasing memory utilization, consistent with a memory leak in the Order Service.",
        "category": "infrastructure",
        "duration_seconds": 180,
        "config": {
            "memory_multiplier": 3.8,
            "latency_multiplier": 1.6,
            "error_rate_multiplier": 2.0,
            "affected_services": ["order-service"],
        },
    },
    {
        "id": "bad_deployment",
        "name": "Bad Deployment",
        "description": "Simulates a faulty deployment to the ShopSphere API that introduces regressions in error rate and latency immediately after release.",
        "category": "deployment",
        "duration_seconds": 120,
        "config": {
            "error_rate_multiplier": 8.0,
            "latency_multiplier": 3.5,
            "cpu_multiplier": 2.0,
            "deployment_event": True,
            "affected_services": ["shopsphere-api"],
        },
    },
    {
        "id": "db_connection_failures",
        "name": "Database Connection Failures",
        "description": "Simulates exhausted database connection pool causing connection timeout errors across multiple services.",
        "category": "database",
        "duration_seconds": 120,
        "config": {
            "db_connection_failures": True,
            "error_rate_multiplier": 6.0,
            "db_latency_multiplier": 5.0,
            "latency_multiplier": 2.8,
            "affected_services": ["database", "order-service", "payment-service"],
        },
    },
]

# ── Service definitions ───────────────────────────────────────────────────────

SERVICES = [
    {
        "name": "shopsphere-frontend",
        "display_name": "ShopSphere Frontend",
        "base_request_rate": 450.0,
        "base_error_rate": 0.5,
        "base_latency_ms": 85.0,
        "base_cpu": 22.0,
        "base_memory": 38.0,
        "dependencies": [],
    },
    {
        "name": "shopsphere-api",
        "display_name": "ShopSphere API",
        "base_request_rate": 380.0,
        "base_error_rate": 0.8,
        "base_latency_ms": 145.0,
        "base_cpu": 35.0,
        "base_memory": 52.0,
        "dependencies": ["shopsphere-frontend"],
    },
    {
        "name": "order-service",
        "display_name": "Order Service",
        "base_request_rate": 120.0,
        "base_error_rate": 0.6,
        "base_latency_ms": 210.0,
        "base_cpu": 28.0,
        "base_memory": 45.0,
        "dependencies": ["shopsphere-api"],
    },
    {
        "name": "payment-service",
        "display_name": "Payment Service",
        "base_request_rate": 85.0,
        "base_error_rate": 0.4,
        "base_latency_ms": 320.0,
        "base_cpu": 20.0,
        "base_memory": 40.0,
        "dependencies": ["shopsphere-api"],
    },
    {
        "name": "database",
        "display_name": "Database",
        "base_request_rate": 520.0,
        "base_error_rate": 0.2,
        "base_latency_ms": 12.0,
        "base_cpu": 45.0,
        "base_memory": 68.0,
        "dependencies": ["order-service", "payment-service"],
    },
]

# ── Telemetry generation ──────────────────────────────────────────────────────

_active_scenario: Optional[str] = None
_scenario_start: Optional[datetime] = None


def set_active_scenario(scenario_id: Optional[str], start_time: Optional[datetime] = None) -> None:
    global _active_scenario, _scenario_start
    _active_scenario = scenario_id
    _scenario_start = start_time or datetime.now(UTC)


def get_active_scenario() -> Optional[str]:
    return _active_scenario


def _get_scenario_config() -> Dict[str, Any]:
    if not _active_scenario:
        return DEMO_SCENARIOS[0]["config"]
    for s in DEMO_SCENARIOS:
        if s["id"] == _active_scenario:
            return s["config"]
    return DEMO_SCENARIOS[0]["config"]


def _jitter(value: float, pct: float = 0.05) -> float:
    """Add ±pct% random jitter to a value."""
    return value * (1.0 + random.uniform(-pct, pct))


def _wave(t_minutes: float, period: float = 60.0, amplitude: float = 0.1) -> float:
    """Sinusoidal component to simulate traffic waves."""
    return 1.0 + amplitude * math.sin(2 * math.pi * t_minutes / period)


def generate_metric_timeseries(
    service_name: str,
    metric: str,
    duration_minutes: int = 60,
    resolution_seconds: int = 60,
) -> MetricSeries:
    """Generate a realistic synthetic time series for a given metric."""
    svc = next((s for s in SERVICES if s["name"] == service_name), SERVICES[1])
    cfg = _get_scenario_config()
    now = datetime.now(UTC)
    affected = cfg.get("affected_services", [])
    is_affected = service_name in affected or not affected

    points: List[MetricDataPoint] = []
    n_points = (duration_minutes * 60) // resolution_seconds

    base_map = {
        "request_rate": svc["base_request_rate"],
        "error_rate": svc["base_error_rate"],
        "latency_ms": svc["base_latency_ms"],
        "cpu_utilization": svc["base_cpu"],
        "memory_utilization": svc["base_memory"],
        "db_query_latency": 12.0,
        "db_connections": 45.0,
    }
    base = base_map.get(metric, 1.0)

    multiplier_map = {
        "request_rate": cfg.get("request_rate_multiplier", 1.0),
        "error_rate": cfg.get("error_rate_multiplier", 1.0) if is_affected else 1.0,
        "latency_ms": cfg.get("latency_multiplier", 1.0) if is_affected else 1.0,
        "cpu_utilization": cfg.get("cpu_multiplier", 1.0) if is_affected else 1.0,
        "memory_utilization": cfg.get("memory_multiplier", 1.0) if is_affected else 1.0,
        "db_query_latency": cfg.get("db_latency_multiplier", 1.0) if is_affected else 1.0,
        "db_connections": 1.0,
    }
    target_multiplier = multiplier_map.get(metric, 1.0)

    anomaly_start = int(n_points * 0.6) if _active_scenario and _active_scenario != "normal_operation" else n_points
    anomaly_markers = []

    for i in range(n_points):
        ts = now - timedelta(seconds=(n_points - i) * resolution_seconds)
        t_minutes = i * resolution_seconds / 60.0

        # Traffic wave
        wave_factor = _wave(t_minutes, period=120.0, amplitude=0.08)

        # Anomaly ramp-up
        if i >= anomaly_start:
            progress = (i - anomaly_start) / max(1, n_points - anomaly_start)
            # Sigmoid ramp
            ramp = 1.0 / (1.0 + math.exp(-8 * (progress - 0.3)))
            effective_multiplier = 1.0 + (target_multiplier - 1.0) * ramp
            if progress > 0.2 and metric == "anomaly_score":
                anomaly_markers.append(ts)
        else:
            effective_multiplier = 1.0

        value = _jitter(base * wave_factor * effective_multiplier, pct=0.04)
        value = max(0.0, value)

        # Cap percentages
        if metric in ("error_rate", "cpu_utilization", "memory_utilization"):
            value = min(value, 99.9)

        points.append(MetricDataPoint(timestamp=ts, value=round(value, 3)))

    unit_map = {
        "request_rate": "req/s",
        "error_rate": "%",
        "latency_ms": "ms",
        "cpu_utilization": "%",
        "memory_utilization": "%",
        "db_query_latency": "ms",
        "db_connections": "connections",
    }

    return MetricSeries(
        name=metric,
        service=service_name,
        unit=unit_map.get(metric, ""),
        data_points=points,
        current_value=points[-1].value if points else None,
        anomaly_markers=anomaly_markers or None,
    )


def generate_current_service_metrics() -> List[Dict[str, Any]]:
    """Return current-state metrics for all services."""
    cfg = _get_scenario_config()
    affected = cfg.get("affected_services", [])
    results = []
    for svc in SERVICES:
        is_affected = svc["name"] in affected or not affected

        err_mult = cfg.get("error_rate_multiplier", 1.0) if is_affected else 1.0
        lat_mult = cfg.get("latency_multiplier", 1.0) if is_affected else 1.0
        cpu_mult = cfg.get("cpu_multiplier", 1.0) if is_affected else 1.0
        mem_mult = cfg.get("memory_multiplier", 1.0) if is_affected else 1.0

        error_rate = min(_jitter(svc["base_error_rate"] * err_mult, 0.1), 99.9)
        latency_ms = _jitter(svc["base_latency_ms"] * lat_mult, 0.08)
        cpu = min(_jitter(svc["base_cpu"] * cpu_mult, 0.06), 99.9)
        memory = min(_jitter(svc["base_memory"] * mem_mult, 0.05), 99.9)
        req_rate = _jitter(svc["base_request_rate"], 0.05)

        # Determine health from metrics
        if error_rate > 5.0 or latency_ms > 2000 or cpu > 85:
            status = "unhealthy"
        elif error_rate > 2.0 or latency_ms > 800 or cpu > 70:
            status = "degraded"
        else:
            status = "healthy"

        results.append({
            "name": svc["name"],
            "display_name": svc["display_name"],
            "status": status,
            "error_rate": round(error_rate, 2),
            "latency_ms": round(latency_ms, 1),
            "request_rate": round(req_rate, 1),
            "cpu_utilization": round(cpu, 1),
            "memory_utilization": round(memory, 1),
            "dependencies": svc["dependencies"],
            "is_demo": True,
        })
    return results


def generate_logs(
    service: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 50,
    minutes_back: int = 60,
) -> List[Dict[str, Any]]:
    """Generate synthetic log entries for demo mode."""
    cfg = _get_scenario_config()
    affected = cfg.get("affected_services", [])
    now = datetime.now(UTC)
    logs = []

    log_templates = {
        "normal": [
            ("INFO", "Request processed successfully in {ms}ms"),
            ("INFO", "Cache hit for key user:{uid}"),
            ("DEBUG", "DB query executed in {db_ms}ms"),
            ("INFO", "Order #{order_id} status updated to processing"),
            ("INFO", "Payment {payment_id} authorized"),
        ],
        "error": [
            ("ERROR", "Database connection timeout after {ms}ms"),
            ("ERROR", "Unhandled exception in OrderController: NullPointerException"),
            ("ERROR", "Payment gateway returned 503: Service Unavailable"),
            ("ERROR", "Failed to acquire DB connection from pool (pool exhausted)"),
            ("WARN", "Slow query detected: {query} took {db_ms}ms"),
            ("ERROR", "HTTP 500 Internal Server Error at /api/v1/checkout"),
            ("CRITICAL", "Circuit breaker OPEN for payment-service after 5 consecutive failures"),
            ("ERROR", "Memory allocation failed: heap space exhausted"),
            ("WARN", "CPU throttling detected: current utilization {cpu}%"),
            ("ERROR", "Trace ID {trace_id}: request timeout after 30s"),
        ],
    }

    services_to_use = [service] if service else [s["name"] for s in SERVICES]
    error_multiplier = cfg.get("error_rate_multiplier", 1.0)

    for i in range(limit):
        ts = now - timedelta(seconds=random.randint(0, minutes_back * 60))
        svc = random.choice(services_to_use)
        is_affected = svc in affected or not affected

        # Weighted error probability
        err_prob = min(0.05 * (error_multiplier if is_affected else 1.0), 0.8)
        use_error = random.random() < err_prob

        template_pool = log_templates["error"] if use_error else log_templates["normal"]
        lvl, msg_template = random.choice(template_pool)

        if severity and lvl.upper() != severity.upper():
            lvl_map = {"ERROR": log_templates["error"], "WARN": log_templates["error"], "INFO": log_templates["normal"]}
            template_pool = lvl_map.get(severity.upper(), log_templates["normal"])
            lvl, msg_template = random.choice(template_pool)

        msg = msg_template.format(
            ms=random.randint(50, 5000),
            db_ms=random.randint(10, 8000),
            uid=random.randint(1000, 9999),
            order_id=random.randint(100000, 999999),
            payment_id=f"PAY-{uuid.uuid4().hex[:8].upper()}",
            query="SELECT * FROM orders WHERE user_id = ?",
            trace_id=uuid.uuid4().hex[:16],
            cpu=random.randint(85, 99),
        )

        logs.append({
            "timestamp": ts.isoformat() + "Z",
            "level": lvl,
            "message": msg,
            "service": svc,
            "trace_id": uuid.uuid4().hex[:16],
            "span_id": uuid.uuid4().hex[:8],
            "request_id": f"req-{uuid.uuid4().hex[:12]}",
            "is_demo": True,
        })

    return sorted(logs, key=lambda x: x["timestamp"], reverse=True)


def generate_traces(service: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """Generate synthetic distributed traces for demo mode."""
    cfg = _get_scenario_config()
    affected = cfg.get("affected_services", [])
    now = datetime.now(UTC)
    traces = []

    operations = {
        "shopsphere-api": ["GET /api/v1/products", "POST /api/v1/orders", "GET /api/v1/cart", "POST /api/v1/checkout"],
        "order-service": ["createOrder", "validateOrder", "updateOrderStatus", "getOrderHistory"],
        "payment-service": ["processPayment", "authorizeCard", "capturePayment", "refundPayment"],
        "database": ["SELECT users", "INSERT orders", "UPDATE inventory", "SELECT products"],
        "shopsphere-frontend": ["renderProductPage", "fetchCartItems", "submitCheckout"],
    }

    for i in range(limit):
        trace_id = uuid.uuid4().hex
        svc = service or random.choice([s["name"] for s in SERVICES])
        is_affected = svc in affected or not affected
        lat_mult = cfg.get("latency_multiplier", 1.0) if is_affected else 1.0

        svc_ops = operations.get(svc, ["processRequest"])
        op = random.choice(svc_ops)

        base_duration = random.uniform(50, 400)
        duration = base_duration * lat_mult
        has_error = random.random() < (0.02 * cfg.get("error_rate_multiplier", 1.0) if is_affected else 0.02)

        start = now - timedelta(seconds=random.randint(0, 3600))

        span = {
            "trace_id": trace_id,
            "span_id": uuid.uuid4().hex[:16],
            "parent_span_id": None,
            "service": svc,
            "operation": op,
            "start_time": start.isoformat() + "Z",
            "duration_ms": round(duration, 2),
            "status": "error" if has_error else "ok",
            "error_message": "Connection timeout" if has_error else None,
            "is_demo": True,
        }

        # Add child spans
        children = []
        if svc == "shopsphere-api":
            child_svc = random.choice(["order-service", "payment-service", "database"])
            child_op = random.choice(operations.get(child_svc, ["query"]))
            child_duration = duration * random.uniform(0.4, 0.8)
            children.append({
                "trace_id": trace_id,
                "span_id": uuid.uuid4().hex[:16],
                "parent_span_id": span["span_id"],
                "service": child_svc,
                "operation": child_op,
                "start_time": (start + timedelta(milliseconds=10)).isoformat() + "Z",
                "duration_ms": round(child_duration, 2),
                "status": "error" if has_error and random.random() < 0.6 else "ok",
                "error_message": "Downstream dependency failed" if has_error else None,
                "is_demo": True,
            })

        traces.append({"root_span": span, "child_spans": children})

    return traces


def generate_overview_metrics() -> Dict[str, Any]:
    """High-level metrics for the overview dashboard."""
    cfg = _get_scenario_config()
    err_mult = cfg.get("error_rate_multiplier", 1.0)
    lat_mult = cfg.get("latency_multiplier", 1.0)
    cpu_mult = cfg.get("cpu_multiplier", 1.0)
    mem_mult = cfg.get("memory_multiplier", 1.0)

    req_rate = _jitter(850.0, 0.05)
    error_rate = min(_jitter(1.2 * err_mult, 0.08), 99.9)
    latency = _jitter(185.0 * lat_mult, 0.06)
    cpu = min(_jitter(34.0 * cpu_mult, 0.07), 99.9)
    memory = min(_jitter(52.0 * mem_mult, 0.05), 99.9)

    return {
        "request_rate": round(req_rate, 1),
        "error_rate": round(error_rate, 2),
        "latency_p50": round(latency * 0.7, 1),
        "latency_p95": round(latency * 1.4, 1),
        "latency_p99": round(latency * 2.1, 1),
        "cpu_utilization": round(cpu, 1),
        "memory_utilization": round(memory, 1),
        "is_demo": True,
    }


def get_demo_incident_template(scenario_id: str) -> Optional[Dict[str, Any]]:
    """Return a pre-built incident template for a given demo scenario."""
    templates = {
        "database_latency_spike": {
            "title": "[DEMO] Database Latency Spike — Cascading Impact on Order and Payment Services",
            "description": "Database query latency increased by 800% causing cascading slowdowns across dependent services.",
            "severity": "high",
            "affected_service": "database",
            "probable_root_cause": "Database query latency spike due to missing index on orders.user_id",
            "confidence_score": 0.87,
        },
        "http_500_spike": {
            "title": "[DEMO] HTTP 500 Error Surge — ShopSphere API",
            "description": "HTTP 500 error rate increased 15x above baseline in the ShopSphere API.",
            "severity": "critical",
            "affected_service": "shopsphere-api",
            "probable_root_cause": "Unhandled NullPointerException in checkout controller after recent code change",
            "confidence_score": 0.82,
        },
        "payment_failures": {
            "title": "[DEMO] Payment Processing Failures — Elevated Error Rate",
            "description": "Payment service error rate elevated 12x above normal; transactions failing at checkout.",
            "severity": "critical",
            "affected_service": "payment-service",
            "probable_root_cause": "Payment gateway returning 503 — likely downstream rate limiting or outage",
            "confidence_score": 0.79,
        },
        "cpu_spike": {
            "title": "[DEMO] CPU Utilization Spike — ShopSphere API Host",
            "description": "CPU utilization spiked to ~90% on the ShopSphere API host, causing request queuing and latency increase.",
            "severity": "high",
            "affected_service": "shopsphere-api",
            "probable_root_cause": "Runaway background job consuming excessive CPU cycles",
            "confidence_score": 0.74,
        },
        "memory_spike": {
            "title": "[DEMO] Memory Leak Detected — Order Service",
            "description": "Order service memory utilization climbing steadily, consistent with a memory leak pattern.",
            "severity": "high",
            "affected_service": "order-service",
            "probable_root_cause": "Memory leak in order processing pipeline — unclosed DB cursors",
            "confidence_score": 0.81,
        },
        "bad_deployment": {
            "title": "[DEMO] Post-Deployment Regression — ShopSphere API v2.4.1",
            "description": "Error rate and latency spiked immediately after deployment of ShopSphere API v2.4.1.",
            "severity": "critical",
            "affected_service": "shopsphere-api",
            "probable_root_cause": "Deployment of v2.4.1 introduced regression in checkout endpoint",
            "confidence_score": 0.94,
        },
        "db_connection_failures": {
            "title": "[DEMO] Database Connection Pool Exhausted",
            "description": "Database connection pool exhausted, causing connection timeout errors across Order and Payment services.",
            "severity": "critical",
            "affected_service": "database",
            "probable_root_cause": "Connection pool exhaustion due to long-running transactions not releasing connections",
            "confidence_score": 0.89,
        },
    }
    return templates.get(scenario_id)


