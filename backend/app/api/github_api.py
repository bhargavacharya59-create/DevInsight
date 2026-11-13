"""GitHub integration API endpoints."""
from fastapi import APIRouter, Query
from app.services import github_service
from app.core.config import settings

router = APIRouter(prefix="/api/github", tags=["github"])


@router.get("/status")
async def github_status():
    if settings.github_configured:
        ok, msg = await github_service.check_connection()
        return {"connected": ok, "message": msg, "is_demo": False,
                "repo": f"{settings.GITHUB_REPO_OWNER}/{settings.GITHUB_REPO_NAME}"}
    return {
        "connected": False,
        "message": "GitHub not configured. Set GITHUB_TOKEN, GITHUB_REPO_OWNER, GITHUB_REPO_NAME in .env",
        "is_demo": True,
    }


@router.get("/commits")
async def get_commits(branch: str = Query("main"), per_page: int = Query(20, le=50)):
    if settings.github_configured:
        commits = await github_service.get_recent_commits(branch, per_page)
        return {"commits": commits, "is_demo": False}
    return {
        "commits": [
            {"sha": "a1b2c3d4", "full_sha": "a1b2c3d4e5f6", "message": "[DEMO] Add order validation middleware",
             "author": "demo-dev", "date": "2024-01-15T10:00:00Z", "url": "#"},
            {"sha": "b2c3d4e5", "full_sha": "b2c3d4e5f6a7", "message": "[DEMO] Fix payment gateway timeout",
             "author": "demo-dev", "date": "2024-01-14T16:30:00Z", "url": "#"},
            {"sha": "c3d4e5f6", "full_sha": "c3d4e5f6a7b8", "message": "[DEMO] Update cart service dependencies",
             "author": "demo-dev", "date": "2024-01-13T09:15:00Z", "url": "#"},
        ],
        "is_demo": True,
    }


@router.get("/commits/{sha}")
async def get_commit_diff(sha: str):
    if settings.github_configured:
        diff = await github_service.get_commit_diff(sha)
        return {"diff": diff, "is_demo": False}
    return {
        "diff": {
            "sha": sha,
            "message": "[DEMO] Fix payment gateway timeout",
            "author": "demo-dev",
            "date": "2024-01-14T16:30:00Z",
            "files": [
                {"filename": "app/services/payment.py", "status": "modified",
                 "additions": 12, "deletions": 3, "patch": "@@ -45,7 +45,7 @@\n-    timeout=5\n+    timeout=30"}
            ],
        },
        "is_demo": True,
    }


@router.get("/pull-requests")
async def get_pull_requests(state: str = Query("open")):
    if settings.github_configured:
        prs = await github_service.get_pull_requests(state)
        return {"pull_requests": prs, "is_demo": False}
    return {"pull_requests": github_service.demo_pull_requests(), "is_demo": True}


@router.get("/workflows")
async def get_workflows(per_page: int = Query(20, le=50)):
    if settings.github_configured:
        runs = await github_service.get_workflow_runs(per_page)
        return {"runs": runs, "is_demo": False}
    return {"runs": github_service.demo_workflow_runs(), "is_demo": True}


@router.get("/workflows/{run_id}/jobs")
async def get_workflow_jobs(run_id: int):
    if settings.github_configured:
        jobs = await github_service.get_workflow_run_jobs(run_id)
        return {"jobs": jobs, "is_demo": False}
    # Demo jobs
    return {
        "jobs": [
            {"id": 1, "name": "test", "status": "completed", "conclusion": "success",
             "started_at": "2024-01-15T10:00:00Z", "completed_at": "2024-01-15T10:03:00Z",
             "steps": [
                 {"name": "Checkout code", "status": "completed", "conclusion": "success", "number": 1},
                 {"name": "Run tests", "status": "completed", "conclusion": "success", "number": 2},
                 {"name": "Build", "status": "completed", "conclusion": "success", "number": 3},
             ]},
        ],
        "is_demo": True,
    }
