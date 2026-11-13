"""Code fix and remediation API."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.models.incident import Incident, RCAResult
from app.services.remediation_engine import run_remediation
from app.core.config import settings

router = APIRouter(prefix="/api/remediation", tags=["remediation"])


class RemediationRequest(BaseModel):
    incident_id: str
    source_files: Optional[dict] = None  # optional pre-loaded files
    retry_count: int = 0


@router.post("/start")
async def start_remediation(req: RemediationRequest, db: AsyncSession = Depends(get_db)):
    """Start autonomous remediation for an incident."""
    # Load incident + latest RCA
    stmt = (
        select(Incident)
        .where(Incident.id == req.incident_id)
        .options(selectinload(Incident.rca_results))
    )
    result = await db.execute(stmt)
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(404, "Incident not found")

    rca_data: dict = {}
    if incident.rca_results:
        latest = incident.rca_results[-1]
        rca_data = {
            "root_cause_summary": latest.root_cause_summary,
            "confidence": latest.confidence,
            "candidates": latest.candidates or [],
            "evidence_metrics": latest.evidence_metrics or [],
        }

    incident_dict = {
        "id": str(incident.id),
        "title": incident.title,
        "severity": str(incident.severity),
        "affected_service": incident.affected_service,
    }

    remediation = await run_remediation(
        incident=incident_dict,
        rca=rca_data,
        source_files=req.source_files,
        retry_count=req.retry_count,
    )

    return remediation.to_dict()


@router.get("/demo")
async def demo_remediation():
    """Return a demo remediation result for display without GitHub."""
    return {
        "branch": "devinsight/fix-abc12345-attempt-1",
        "pr_number": 12,
        "pr_url": "https://github.com/demo/shopsphere/pull/12",
        "status": "pr_open",
        "error": None,
        "is_demo": True,
        "patch": {
            "affected_files": ["app/routes/orders.py"],
            "patch_description": "Fix missing null check on user address before order insertion",
            "changes": [
                {
                    "file": "app/routes/orders.py",
                    "original_snippet": "    address = user.saved_address\n    order = Order(address=address)",
                    "fixed_snippet": "    address = user.saved_address\n    if not address:\n        raise HTTPException(400, 'No saved address found')\n    order = Order(address=address)",
                    "explanation": "Added null guard before using saved_address. When address was None, the ORM threw an IntegrityError which surfaced as HTTP 500.",
                }
            ],
            "risk_assessment": "low — purely additive validation, no logic change",
            "suggested_test": "def test_order_without_address(client):\n    resp = client.post('/api/orders', json={...})\n    assert resp.status_code == 400",
            "confidence": 0.88,
        },
        "steps": [
            {"name": "Source retrieval", "status": "completed", "detail": "Retrieved app/routes/orders.py"},
            {"name": "Patch generation", "status": "completed", "detail": "Gemini generated patch for 1 file. Risk: low"},
            {"name": "Branch creation", "status": "completed", "detail": "Branch: devinsight/fix-abc12345-attempt-1"},
            {"name": "Commit app/routes/orders.py", "status": "completed", "detail": "File committed"},
            {"name": "Pull request", "status": "completed", "detail": "PR #12: https://github.com/demo/shopsphere/pull/12"},
        ],
        "retry_count": 0,
    }
