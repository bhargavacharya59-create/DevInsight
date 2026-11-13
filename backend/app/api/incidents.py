"""Incident management API."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, or_, and_, func

from app.db.base import get_db
from app.models.incident import Incident, IncidentEvent, RCAResult
from app.schemas.incident import (
    IncidentCreate, IncidentUpdate, IncidentResponse, IncidentListResponse
)
from app.services.incident_service import get_incident_service

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


async def _load_full_incident(db: AsyncSession, incident_id: str) -> Optional[Incident]:
    """Load incident with all relations."""
    stmt = (
        select(Incident)
        .where(Incident.id == incident_id)
        .options(
            selectinload(Incident.events),
            selectinload(Incident.rca_results).selectinload(RCAResult.root_cause_candidates),
            selectinload(Incident.recommendations),
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


@router.get("", response_model=IncidentListResponse)
async def list_incidents(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    service: Optional[str] = Query(None),
    is_demo: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    svc = get_incident_service()
    total, incidents = await svc.list_incidents(
        db, status=status, severity=severity, service=service,
        is_demo=is_demo, search=search, page=page, page_size=page_size
    )
    return IncidentListResponse(
        total=total,
        incidents=[IncidentResponse.model_validate(i) for i in incidents],
        page=page,
        page_size=page_size,
    )


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(incident_id: str, db: AsyncSession = Depends(get_db)):
    incident = await _load_full_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return IncidentResponse.model_validate(incident)


@router.post("", response_model=IncidentResponse, status_code=201)
async def create_incident(data: IncidentCreate, db: AsyncSession = Depends(get_db)):
    svc = get_incident_service()
    incident, _ = await svc.create_or_update(db, data)
    full = await _load_full_incident(db, incident.id)
    return IncidentResponse.model_validate(full)


@router.patch("/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: str,
    update: IncidentUpdate,
    db: AsyncSession = Depends(get_db),
):
    svc = get_incident_service()
    incident = await svc.get(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    await svc.update(db, incident, update)
    full = await _load_full_incident(db, incident_id)
    return IncidentResponse.model_validate(full)


@router.post("/{incident_id}/acknowledge", response_model=IncidentResponse)
async def acknowledge_incident(incident_id: str, db: AsyncSession = Depends(get_db)):
    svc = get_incident_service()
    incident = await svc.get(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    await svc.acknowledge(db, incident)
    full = await _load_full_incident(db, incident_id)
    return IncidentResponse.model_validate(full)


@router.post("/{incident_id}/resolve", response_model=IncidentResponse)
async def resolve_incident(incident_id: str, db: AsyncSession = Depends(get_db)):
    svc = get_incident_service()
    incident = await svc.get(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    await svc.resolve(db, incident)
    full = await _load_full_incident(db, incident_id)
    return IncidentResponse.model_validate(full)


@router.get("/{incident_id}/rca")
async def get_incident_rca(incident_id: str, db: AsyncSession = Depends(get_db)):
    """Get RCA results for an incident."""
    incident = await _load_full_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    if not incident.rca_results:
        return {
            "incident_id": incident_id,
            "rca_status": incident.rca_status,
            "message": "RCA has not been run yet. POST to /api/rca/investigate to trigger.",
        }

    rca = incident.rca_results[-1]  # Most recent
    return {
        "incident_id": incident_id,
        "rca_id": rca.id,
        "root_cause_summary": rca.root_cause_summary,
        "confidence": rca.confidence,
        "candidates": rca.candidates,
        "evidence_metrics": rca.evidence_metrics,
        "evidence_logs": rca.evidence_logs,
        "evidence_traces": rca.evidence_traces,
        "deployment_correlation": rca.deployment_correlation,
        "ai_explanation": rca.ai_explanation,
        "ai_available": rca.ai_available,
        "created_at": rca.created_at.isoformat() + "Z",
        "recommendations": [
            {"category": r.category, "action": r.action, "priority": r.priority}
            for r in incident.recommendations
        ],
    }
