"""
Seeds the database with demo incidents and services on first startup.
Only runs if no incidents exist (idempotent).
"""
from datetime import datetime, UTC, timedelta
from typing import Optional
import uuid
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.incident import (
    Incident, IncidentEvent, AnomalyEvent, RCAResult, RootCauseCandidate, Recommendation,
    SeverityLevel, IncidentStatus, RCAStatus,
)
from app.models.service import Service, ServiceStatus, DeploymentEvent

logger = logging.getLogger("devinsight.seeder")


async def seed_demo_data(db: AsyncSession) -> None:
    """Seed demo incidents and services if DB is empty."""
    # Check if already seeded
    count_result = await db.execute(select(func.count(Incident.id)))
    if count_result.scalar_one() > 0:
        logger.info("Demo data already seeded, skipping")
        return

    logger.info("Seeding demo data...")
    now = datetime.now(UTC)

    # ── Services ──────────────────────────────────────────────────────────────
    services = [
        Service(id=str(uuid.uuid4()), name="shopsphere-frontend", display_name="ShopSphere Frontend",
                status=ServiceStatus.HEALTHY, error_rate=0.5, latency_ms=85.0, request_rate=450.0,
                dependencies=[]),
        Service(id=str(uuid.uuid4()), name="shopsphere-api", display_name="ShopSphere API",
                status=ServiceStatus.DEGRADED, error_rate=8.2, latency_ms=1240.0, request_rate=380.0,
                dependencies=["shopsphere-frontend"]),
        Service(id=str(uuid.uuid4()), name="order-service", display_name="Order Service",
                status=ServiceStatus.DEGRADED, error_rate=3.1, latency_ms=890.0, request_rate=120.0,
                dependencies=["shopsphere-api"]),
        Service(id=str(uuid.uuid4()), name="payment-service", display_name="Payment Service",
                status=ServiceStatus.UNHEALTHY, error_rate=18.5, latency_ms=2400.0, request_rate=85.0,
                dependencies=["shopsphere-api"]),
        Service(id=str(uuid.uuid4()), name="database", display_name="Database",
                status=ServiceStatus.DEGRADED, error_rate=0.8, latency_ms=340.0, request_rate=520.0,
                dependencies=["order-service", "payment-service"]),
    ]
    for svc in services:
        db.add(svc)

    # ── Demo Incidents ────────────────────────────────────────────────────────
    incidents_data = [
        {
            "id": str(uuid.uuid4()),
            "title": "[DEMO] Payment Service Failure — Elevated Error Rate",
            "description": "Payment service error rate surged to 18.5%, causing checkout failures across ShopSphere.",
            "severity": SeverityLevel.CRITICAL,
            "status": IncidentStatus.INVESTIGATING,
            "affected_service": "payment-service",
            "detected_at": now - timedelta(hours=2),
            "started_at": now - timedelta(hours=2, minutes=5),
            "anomaly_score": 0.87,
            "rca_status": RCAStatus.COMPLETED,
            "probable_root_cause": "Payment gateway returning 503 — likely downstream rate limiting",
            "confidence_score": 0.79,
            "fingerprint": "demo:payment_failures:seed",
            "is_demo": True,
        },
        {
            "id": str(uuid.uuid4()),
            "title": "[DEMO] Database Latency Spike — Cascading Impact",
            "description": "Database query latency increased 800% causing order processing delays and payment failures.",
            "severity": SeverityLevel.HIGH,
            "status": IncidentStatus.OPEN,
            "affected_service": "database",
            "detected_at": now - timedelta(hours=1),
            "started_at": now - timedelta(hours=1, minutes=10),
            "anomaly_score": 0.82,
            "rca_status": RCAStatus.COMPLETED,
            "probable_root_cause": "Database query latency spike due to missing index on orders.user_id",
            "confidence_score": 0.87,
            "fingerprint": "demo:database_latency_spike:seed",
            "is_demo": True,
        },
        {
            "id": str(uuid.uuid4()),
            "title": "[DEMO] HTTP 500 Error Spike — ShopSphere API",
            "description": "HTTP 500 error rate increased 15x above baseline following recent API deployment.",
            "severity": SeverityLevel.CRITICAL,
            "status": IncidentStatus.RESOLVED,
            "affected_service": "shopsphere-api",
            "detected_at": now - timedelta(days=1, hours=3),
            "started_at": now - timedelta(days=1, hours=3, minutes=2),
            "resolved_at": now - timedelta(days=1, hours=1),
            "anomaly_score": 0.91,
            "rca_status": RCAStatus.COMPLETED,
            "probable_root_cause": "Unhandled NullPointerException in checkout endpoint introduced in v2.3.0",
            "confidence_score": 0.94,
            "fingerprint": "demo:http_500_spike:seed",
            "is_demo": True,
        },
        {
            "id": str(uuid.uuid4()),
            "title": "[DEMO] CPU Spike — ShopSphere API Host",
            "description": "CPU utilization reached 91% causing request queuing and P95 latency increase.",
            "severity": SeverityLevel.HIGH,
            "status": IncidentStatus.RESOLVED,
            "affected_service": "shopsphere-api",
            "detected_at": now - timedelta(days=2, hours=5),
            "started_at": now - timedelta(days=2, hours=5, minutes=8),
            "resolved_at": now - timedelta(days=2, hours=3),
            "anomaly_score": 0.75,
            "rca_status": RCAStatus.COMPLETED,
            "probable_root_cause": "Runaway background job consuming excessive CPU cycles",
            "confidence_score": 0.74,
            "fingerprint": "demo:cpu_spike:seed",
            "is_demo": True,
        },
        {
            "id": str(uuid.uuid4()),
            "title": "[DEMO] Memory Leak — Order Service",
            "description": "Order service memory climbing steadily over 6 hours, consistent with a memory leak.",
            "severity": SeverityLevel.MEDIUM,
            "status": IncidentStatus.RESOLVED,
            "affected_service": "order-service",
            "detected_at": now - timedelta(days=3),
            "started_at": now - timedelta(days=3, hours=1),
            "resolved_at": now - timedelta(days=2, hours=20),
            "anomaly_score": 0.68,
            "rca_status": RCAStatus.COMPLETED,
            "probable_root_cause": "Memory leak in order processing pipeline — unclosed DB cursors",
            "confidence_score": 0.81,
            "fingerprint": "demo:memory_spike:seed",
            "is_demo": True,
        },
    ]

    incident_objs = []
    for inc_data in incidents_data:
        inc = Incident(**inc_data)
        db.add(inc)
        incident_objs.append(inc)

        # Add events
        db.add(IncidentEvent(
            id=str(uuid.uuid4()),
            incident_id=inc.id,
            event_type="incident_created",
            description=f"Anomaly detected by Isolation Forest (score={inc.anomaly_score:.3f})",
            created_at=inc.detected_at,
        ))
        if inc.status in (IncidentStatus.INVESTIGATING, IncidentStatus.RESOLVED):
            db.add(IncidentEvent(
                id=str(uuid.uuid4()),
                incident_id=inc.id,
                event_type="incident_acknowledged",
                description="Incident acknowledged and moved to Investigating",
                created_at=inc.detected_at + timedelta(minutes=5),
            ))
        if inc.status == IncidentStatus.RESOLVED:
            db.add(IncidentEvent(
                id=str(uuid.uuid4()),
                incident_id=inc.id,
                event_type="rca_completed",
                description=f"RCA completed (confidence={inc.confidence_score:.0%})",
                created_at=inc.detected_at + timedelta(minutes=30),
            ))
            db.add(IncidentEvent(
                id=str(uuid.uuid4()),
                incident_id=inc.id,
                event_type="incident_resolved",
                description="Incident resolved after root cause remediation",
                created_at=inc.resolved_at,
            ))

        # Add RCA result
        rca = RCAResult(
            id=str(uuid.uuid4()),
            incident_id=inc.id,
            root_cause_summary=inc.probable_root_cause,
            confidence=inc.confidence_score or 0.0,
            candidates=[
                {
                    "rank": 1,
                    "title": inc.probable_root_cause,
                    "confidence": inc.confidence_score or 0.0,
                    "description": f"Primary root cause identified with {inc.confidence_score or 0:.0%} confidence.",
                    "evidence": [
                        {"kind": "metric", "description": "Elevated error rate and latency observed", "weight": 0.3, "source": "prometheus"},
                        {"kind": "log", "description": "Error patterns detected in service logs", "weight": 0.25, "source": "loki"},
                    ],
                }
            ],
            ai_explanation=f"Analysis of {inc.affected_service} telemetry indicates {inc.probable_root_cause}.",
            ai_available=False,
        )
        db.add(rca)

        # Recommendations
        recs = [
            Recommendation(id=str(uuid.uuid4()), incident_id=inc.id, category="immediate",
                           action="Review application logs for the incident time window", priority=1),
            Recommendation(id=str(uuid.uuid4()), incident_id=inc.id, category="immediate",
                           action="Check metric dashboards for the affected service", priority=2),
            Recommendation(id=str(uuid.uuid4()), incident_id=inc.id, category="long_term",
                           action="Add automated regression tests for the affected code path", priority=3),
        ]
        for rec in recs:
            db.add(rec)

    # ── Deployment events ─────────────────────────────────────────────────────
    db.add(DeploymentEvent(
        id=str(uuid.uuid4()),
        service="shopsphere-api",
        version="v2.3.0",
        deployed_at=now - timedelta(days=1, hours=3, minutes=10),
        deployed_by="ci-pipeline",
        description="Feature: new checkout endpoint with promo code support",
        is_demo=True,
    ))
    db.add(DeploymentEvent(
        id=str(uuid.uuid4()),
        service="payment-service",
        version="v1.8.2",
        deployed_at=now - timedelta(hours=3),
        deployed_by="ci-pipeline",
        description="Patch: update payment gateway SDK to v3.1.0",
        is_demo=True,
    ))

    await db.commit()
    logger.info("Demo data seeded successfully: %d incidents", len(incidents_data))


