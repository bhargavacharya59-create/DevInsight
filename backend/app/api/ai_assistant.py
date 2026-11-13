"""AI Assistant API — incident investigation chatbot."""
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.models.incident import Incident
from app.services.gemini_service import get_gemini_service

router = APIRouter(prefix="/api/ai", tags=["ai"])


class ExplainRequest(BaseModel):
    incident_id: str


class QuestionRequest(BaseModel):
    question: str
    incident_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


@router.post("/explain")
async def explain_incident(req: ExplainRequest, db: AsyncSession = Depends(get_db)):
    """Generate AI explanation for an incident using Gemini."""
    stmt = (
        select(Incident)
        .where(Incident.id == req.incident_id)
        .options(selectinload(Incident.rca_results))
    )
    result = await db.execute(stmt)
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    rca_data = {}
    if incident.rca_results:
        latest = incident.rca_results[-1]
        rca_data = {
            "root_cause_summary": latest.root_cause_summary,
            "confidence": latest.confidence,
            "candidates": latest.candidates or [],
            "evidence_metrics": latest.evidence_metrics or [],
            "evidence_logs": latest.evidence_logs or [],
            "evidence_traces": latest.evidence_traces or [],
            "deployment_correlation": latest.deployment_correlation or {},
        }

    gemini = get_gemini_service()
    explanation = gemini.explain_incident(
        incident={
            "id": incident.id,
            "title": incident.title,
            "severity": str(incident.severity),
            "status": str(incident.status),
            "affected_service": incident.affected_service,
            "detected_at": incident.detected_at.isoformat(),
            "anomaly_score": incident.anomaly_score,
        },
        rca_result=rca_data,
    )
    return explanation


@router.post("/ask")
async def ask_question(req: QuestionRequest, db: AsyncSession = Depends(get_db)):
    """Answer a specific question about an incident or system state."""
    context: Dict[str, Any] = req.context or {}

    if req.incident_id:
        stmt = (
            select(Incident)
            .where(Incident.id == req.incident_id)
            .options(selectinload(Incident.rca_results), selectinload(Incident.recommendations))
        )
        result = await db.execute(stmt)
        incident = result.scalar_one_or_none()
        if incident:
            context["incident"] = {
                "id": incident.id,
                "title": incident.title,
                "severity": str(incident.severity),
                "status": str(incident.status),
                "affected_service": incident.affected_service,
                "detected_at": incident.detected_at.isoformat(),
                "probable_root_cause": incident.probable_root_cause,
                "confidence_score": incident.confidence_score,
                "ai_explanation": incident.ai_explanation,
            }
            if incident.rca_results:
                latest = incident.rca_results[-1]
                context["rca"] = {
                    "root_cause_summary": latest.root_cause_summary,
                    "confidence": latest.confidence,
                    "candidates": latest.candidates or [],
                }
            context["recommendations"] = [
                {"category": r.category, "action": r.action}
                for r in incident.recommendations
            ]

    gemini = get_gemini_service()
    answer = gemini.answer_question(req.question, context)
    return answer
