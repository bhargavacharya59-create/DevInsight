"""Demo scenario management API."""
from datetime import datetime, UTC
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.db.base import get_db
from app.models.incident import Incident, SeverityLevel, IncidentStatus, RCAStatus
from app.models.service import DemoScenario
from app.services import demo_telemetry
from app.services.incident_service import get_incident_service
from app.schemas.incident import IncidentCreate

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.get("/scenarios")
async def list_scenarios():
    """List all available demo scenarios."""
    return {
        "scenarios": demo_telemetry.DEMO_SCENARIOS,
        "active_scenario": demo_telemetry.get_active_scenario(),
    }


@router.post("/scenarios/{scenario_id}/start")
async def start_scenario(scenario_id: str, db: AsyncSession = Depends(get_db)):
    """
    Start a demo scenario.
    Sets active telemetry profile and optionally creates a demo incident.
    """
    scenario = next((s for s in demo_telemetry.DEMO_SCENARIOS if s["id"] == scenario_id), None)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")

    # Activate the scenario telemetry
    demo_telemetry.set_active_scenario(scenario_id, datetime.now(UTC))

    # Create a demo incident for this scenario (if not normal operation)
    incident_created = None
    if scenario_id != "normal_operation":
        template = demo_telemetry.get_demo_incident_template(scenario_id)
        if template:
            svc = get_incident_service()
            data = IncidentCreate(
                title=template["title"],
                description=template["description"],
                severity=template.get("severity", "medium"),
                affected_service=template.get("affected_service"),
                anomaly_score=0.78,
                is_demo=True,
                fingerprint=f"demo:{scenario_id}:{datetime.now(UTC).strftime('%Y%m%d%H')}",
            )
            incident, is_new = await svc.create_or_update(db, data, dedup_window_minutes=120)
            incident_created = {
                "id": incident.id,
                "title": incident.title,
                "is_new": is_new,
            }

    return {
        "success": True,
        "scenario": scenario,
        "active_scenario": scenario_id,
        "incident_created": incident_created,
        "message": f"Scenario '{scenario['name']}' started. Telemetry is now simulating this scenario.",
    }


@router.post("/scenarios/{scenario_id}/stop")
async def stop_scenario(scenario_id: str):
    """Stop the active scenario and return to normal operation."""
    demo_telemetry.set_active_scenario("normal_operation")
    return {
        "success": True,
        "message": f"Scenario '{scenario_id}' stopped. Returning to normal operation baseline.",
        "active_scenario": "normal_operation",
    }


@router.post("/reset")
async def reset_demo(db: AsyncSession = Depends(get_db)):
    """Reset demo to normal operation. Does not delete incidents."""
    demo_telemetry.set_active_scenario(None)
    return {
        "success": True,
        "message": "Demo reset to normal operation. Demo incidents are preserved in the database.",
        "active_scenario": None,
    }


@router.get("/status")
async def demo_status():
    """Return current demo status."""
    return {
        "active_scenario": demo_telemetry.get_active_scenario(),
        "scenarios": [
            {"id": s["id"], "name": s["name"], "category": s["category"]}
            for s in demo_telemetry.DEMO_SCENARIOS
        ],
    }


