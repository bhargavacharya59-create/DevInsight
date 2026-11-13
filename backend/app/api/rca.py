"""Root Cause Analysis API."""
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.models.incident import Incident
from app.services.rca_engine import get_rca_engine
from app.services.gemini_service import get_gemini_service
from app.services.incident_service import get_incident_service
from app.services import demo_telemetry
from app.core.config import settings

router = APIRouter(prefix="/api/rca", tags=["rca"])


class InvestigateRequest(BaseModel):
    incident_id: str
    include_demo_evidence: bool = True


@router.post("/investigate")
async def investigate_incident(req: InvestigateRequest, db: AsyncSession = Depends(get_db)):
    """
    Run a full RCA investigation for an incident.
    Collects evidence, runs RCA engine, calls Gemini, persists results.
    """
    # Load incident
    stmt = (
        select(Incident)
        .where(Incident.id == req.incident_id)
        .options(selectinload(Incident.rca_results))
    )
    result = await db.execute(stmt)
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Gather evidence
    service = incident.affected_service or "shopsphere-api"
    is_demo = incident.is_demo or req.include_demo_evidence or settings.is_demo_mode

    if is_demo:
        logs = demo_telemetry.generate_logs(service=service, limit=50)
        traces = demo_telemetry.generate_traces(service=service, limit=20)

        # Build metric signals with baseline comparison
        metrics_evidence = []
        for metric_name in ["error_rate", "latency_ms", "cpu_utilization", "memory_utilization", "db_query_latency"]:
            series = demo_telemetry.generate_metric_timeseries(service, metric_name, 60, 60)
            if series.data_points:
                # Split into before/during incident (last 40% is "during")
                n = len(series.data_points)
                baseline_pts = series.data_points[:int(n * 0.6)]
                incident_pts = series.data_points[int(n * 0.6):]
                baseline_val = sum(p.value for p in baseline_pts) / len(baseline_pts) if baseline_pts else 0
                current_val = sum(p.value for p in incident_pts) / len(incident_pts) if incident_pts else 0
                metrics_evidence.append({
                    "name": metric_name,
                    "service": service,
                    "current_value": current_val,
                    "baseline_value": baseline_val,
                })

        # Demo deployments for bad_deployment scenario
        deployments = []
        if demo_telemetry.get_active_scenario() == "bad_deployment":
            from datetime import datetime, UTC, timedelta
            deployments = [{
                "service": service,
                "version": "v2.4.1",
                "deployed_at": (datetime.now(UTC) - timedelta(minutes=8)).isoformat() + "Z",
                "deployed_by": "ci-system",
            }]
    else:
        metrics_evidence = []
        logs = []
        traces = []
        deployments = []

    # Run RCA engine
    rca_engine = get_rca_engine()
    rca_result = rca_engine.investigate(
        incident={"id": incident.id, "title": incident.title,
                  "affected_service": service, "detected_at": incident.detected_at.isoformat(),
                  "severity": str(incident.severity), "status": str(incident.status)},
        metrics=metrics_evidence,
        logs=logs,
        traces=traces,
        deployments=deployments,
    )

    # Run Gemini explanation
    gemini = get_gemini_service()
    ai_result = gemini.explain_incident(
        incident={"id": incident.id, "title": incident.title,
                  "severity": str(incident.severity), "status": str(incident.status),
                  "affected_service": service, "detected_at": incident.detected_at.isoformat(),
                  "anomaly_score": incident.anomaly_score},
        rca_result=rca_result,
    )

    # Persist results
    incident_svc = get_incident_service()
    rca_db = await incident_svc.save_rca(db, incident, rca_result, ai_result)

    return {
        "incident_id": incident.id,
        "rca_id": rca_db.id,
        "root_cause_summary": rca_result["root_cause_summary"],
        "confidence": rca_result["confidence"],
        "candidates": rca_result["candidates"],
        "evidence_metrics": rca_result["evidence_metrics"],
        "evidence_logs": rca_result["evidence_logs"],
        "evidence_traces": rca_result["evidence_traces"],
        "deployment_correlation": rca_result["deployment_correlation"],
        "ai_explanation": ai_result.get("incident_explanation"),
        "ai_probable_root_cause": ai_result.get("probable_root_cause"),
        "ai_investigation_steps": ai_result.get("investigation_steps", []),
        "ai_remediation_steps": ai_result.get("remediation_steps", []),
        "ai_prevention": ai_result.get("prevention", []),
        "ai_available": ai_result.get("ai_available", False),
        "ai_user_impact": ai_result.get("user_impact"),
        "ai_why": ai_result.get("why_it_happened"),
        "ai_confidence_limitations": ai_result.get("confidence_limitations"),
    }


