"""Deployment history and version comparison API."""
from datetime import datetime, UTC, timedelta
from typing import Optional
from fastapi import APIRouter, Query
from app.services import github_service
from app.core.config import settings

router = APIRouter(prefix="/api/deployments", tags=["deployments"])


@router.get("")
async def get_deployments(limit: int = Query(20, le=50)):
    """Return deployment history from GitHub Actions workflow runs."""
    if settings.github_configured:
        runs = await github_service.get_workflow_runs(limit)
        # Treat completed workflow runs as deployments
        deployments = [
            {
                "id": r["id"],
                "version": r["commit_sha"],
                "branch": r["branch"],
                "deployed_at": r["updated_at"],
                "status": r["conclusion"] or r["status"],
                "workflow": r["name"],
                "run_number": r["run_number"],
                "url": r["url"],
                "is_demo": False,
            }
            for r in runs
            if r["status"] == "completed"
        ]
        return {"deployments": deployments, "is_demo": False}

    # Demo data
    now = datetime.now(UTC)
    return {
        "deployments": [
            {
                "id": "dep-001",
                "version": "v2.4.1",
                "branch": "main",
                "deployed_at": (now - timedelta(hours=2)).isoformat(),
                "status": "success",
                "workflow": "CI — Deploy to Production",
                "run_number": 42,
                "url": "#",
                "is_demo": True,
                "metrics_comparison": {
                    "error_rate_before": 1.2,
                    "error_rate_after": 8.5,
                    "latency_before": 185,
                    "latency_after": 1240,
                    "verdict": "degraded",
                },
            },
            {
                "id": "dep-002",
                "version": "v2.4.0",
                "branch": "main",
                "deployed_at": (now - timedelta(days=1)).isoformat(),
                "status": "success",
                "workflow": "CI — Deploy to Production",
                "run_number": 41,
                "url": "#",
                "is_demo": True,
                "metrics_comparison": {
                    "error_rate_before": 1.1,
                    "error_rate_after": 1.2,
                    "latency_before": 180,
                    "latency_after": 185,
                    "verdict": "stable",
                },
            },
            {
                "id": "dep-003",
                "version": "v2.3.9",
                "branch": "main",
                "deployed_at": (now - timedelta(days=3)).isoformat(),
                "status": "success",
                "workflow": "CI — Deploy to Production",
                "run_number": 40,
                "url": "#",
                "is_demo": True,
                "metrics_comparison": {
                    "error_rate_before": 1.5,
                    "error_rate_after": 1.1,
                    "latency_before": 220,
                    "latency_after": 180,
                    "verdict": "improved",
                },
            },
        ],
        "is_demo": True,
    }


@router.get("/{deployment_id}/compare")
async def compare_deployment(deployment_id: str):
    """Compare metrics before and after a specific deployment."""
    # In live mode: query Prometheus with time ranges around deployment
    # For now: demo comparison data
    return {
        "deployment_id": deployment_id,
        "is_demo": True,
        "before": {
            "error_rate": 1.2,
            "latency_p95": 185,
            "request_rate": 420,
            "cpu_utilization": 32,
            "memory_utilization": 48,
        },
        "after": {
            "error_rate": 8.5,
            "latency_p95": 1240,
            "request_rate": 390,
            "cpu_utilization": 71,
            "memory_utilization": 65,
        },
        "verdict": "degraded",
        "rollback_recommended": True,
        "incidents_in_window": 2,
        "note": "[DEMO] Comparison uses synthetic telemetry data.",
    }
