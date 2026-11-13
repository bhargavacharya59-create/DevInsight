"""
GitHub integration service.
Handles: commits, PRs, Actions workflow runs, branch creation,
file commits, PR creation, and webhook event processing.
"""
from __future__ import annotations
import hashlib
import hmac
import logging
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

from app.core.config import settings

logger = logging.getLogger("devinsight.github")

GITHUB_API = "https://api.github.com"


def _headers() -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _repo_base() -> str:
    return f"{GITHUB_API}/repos/{settings.GITHUB_REPO_OWNER}/{settings.GITHUB_REPO_NAME}"


# ── Connectivity ──────────────────────────────────────────────────────────────

async def check_connection() -> Tuple[bool, str]:
    """Verify GitHub token and repo access."""
    if not settings.github_configured:
        return False, "GitHub not configured (GITHUB_TOKEN / GITHUB_REPO_OWNER / GITHUB_REPO_NAME missing)"
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as s:
            async with s.get(f"{_repo_base()}", headers=_headers()) as r:
                if r.status == 200:
                    data = await r.json()
                    return True, f"Connected to {data.get('full_name', 'repo')}"
                text = await r.text()
                return False, f"GitHub API returned {r.status}: {text[:200]}"
    except Exception as e:
        return False, str(e)


# ── Commits ───────────────────────────────────────────────────────────────────

async def get_recent_commits(branch: str = "main", per_page: int = 20) -> List[Dict]:
    if not settings.github_configured:
        return []
    url = f"{_repo_base()}/commits"
    params = {"sha": branch, "per_page": per_page}
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            async with s.get(url, headers=_headers(), params=params) as r:
                if r.status == 200:
                    raw = await r.json()
                    return [
                        {
                            "sha": c["sha"][:8],
                            "full_sha": c["sha"],
                            "message": c["commit"]["message"].split("\n")[0],
                            "author": c["commit"]["author"]["name"],
                            "date": c["commit"]["author"]["date"],
                            "url": c["html_url"],
                        }
                        for c in raw
                    ]
    except Exception as e:
        logger.error("get_recent_commits error: %s", e)
    return []


async def get_commit_diff(sha: str) -> Optional[Dict]:
    """Get the diff/files changed for a specific commit."""
    if not settings.github_configured:
        return None
    url = f"{_repo_base()}/commits/{sha}"
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            async with s.get(url, headers=_headers()) as r:
                if r.status == 200:
                    data = await r.json()
                    files = [
                        {
                            "filename": f["filename"],
                            "status": f["status"],
                            "additions": f["additions"],
                            "deletions": f["deletions"],
                            "patch": f.get("patch", ""),
                        }
                        for f in data.get("files", [])
                    ]
                    return {
                        "sha": sha,
                        "message": data["commit"]["message"],
                        "author": data["commit"]["author"]["name"],
                        "date": data["commit"]["author"]["date"],
                        "files": files,
                    }
    except Exception as e:
        logger.error("get_commit_diff error: %s", e)
    return None


# ── File content ──────────────────────────────────────────────────────────────

async def get_file_content(path: str, ref: str = "main") -> Optional[str]:
    """Fetch raw file content from the repo."""
    if not settings.github_configured:
        return None
    import base64
    url = f"{_repo_base()}/contents/{path}"
    params = {"ref": ref}
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            async with s.get(url, headers=_headers(), params=params) as r:
                if r.status == 200:
                    data = await r.json()
                    content = data.get("content", "")
                    return base64.b64decode(content).decode("utf-8", errors="replace")
    except Exception as e:
        logger.error("get_file_content error: %s", e)
    return None


# ── Branch operations ─────────────────────────────────────────────────────────

async def create_branch(branch_name: str, from_branch: str = "main") -> Tuple[bool, str]:
    """Create a new branch from an existing branch."""
    if not settings.github_configured:
        return False, "GitHub not configured"
    # Get ref SHA
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            async with s.get(f"{_repo_base()}/git/ref/heads/{from_branch}", headers=_headers()) as r:
                if r.status != 200:
                    return False, f"Could not find branch {from_branch}"
                ref_data = await r.json()
                sha = ref_data["object"]["sha"]

            # Create new branch
            payload = {"ref": f"refs/heads/{branch_name}", "sha": sha}
            async with s.post(f"{_repo_base()}/git/refs", headers=_headers(), json=payload) as r:
                if r.status in (200, 201):
                    return True, f"Branch {branch_name} created"
                text = await r.text()
                return False, f"Failed to create branch: {text[:200]}"
    except Exception as e:
        return False, str(e)


async def commit_file(
    branch: str,
    file_path: str,
    content: str,
    message: str,
) -> Tuple[bool, str]:
    """Create or update a file on a branch."""
    if not settings.github_configured:
        return False, "GitHub not configured"
    import base64
    encoded = base64.b64encode(content.encode()).decode()
    url = f"{_repo_base()}/contents/{file_path}"

    # Check if file exists (to get SHA for update)
    existing_sha = None
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            async with s.get(url, headers=_headers(), params={"ref": branch}) as r:
                if r.status == 200:
                    existing_sha = (await r.json()).get("sha")

            payload: Dict[str, Any] = {
                "message": message,
                "content": encoded,
                "branch": branch,
            }
            if existing_sha:
                payload["sha"] = existing_sha

            async with s.put(url, headers=_headers(), json=payload) as r:
                if r.status in (200, 201):
                    return True, "File committed"
                text = await r.text()
                return False, f"Commit failed: {text[:200]}"
    except Exception as e:
        return False, str(e)


# ── Pull Requests ─────────────────────────────────────────────────────────────

async def create_pull_request(
    title: str,
    head: str,
    base: str = "main",
    body: str = "",
) -> Optional[Dict]:
    """Open a pull request."""
    if not settings.github_configured:
        return None
    payload = {"title": title, "head": head, "base": base, "body": body}
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            async with s.post(f"{_repo_base()}/pulls", headers=_headers(), json=payload) as r:
                if r.status in (200, 201):
                    data = await r.json()
                    return {
                        "number": data["number"],
                        "url": data["html_url"],
                        "title": data["title"],
                        "state": data["state"],
                        "head": data["head"]["ref"],
                        "base": data["base"]["ref"],
                    }
                logger.error("create_pr failed: %s", await r.text())
    except Exception as e:
        logger.error("create_pull_request error: %s", e)
    return None


async def get_pull_requests(state: str = "open", per_page: int = 20) -> List[Dict]:
    if not settings.github_configured:
        return []
    url = f"{_repo_base()}/pulls"
    params = {"state": state, "per_page": per_page, "sort": "updated", "direction": "desc"}
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            async with s.get(url, headers=_headers(), params=params) as r:
                if r.status == 200:
                    raw = await r.json()
                    return [
                        {
                            "number": pr["number"],
                            "title": pr["title"],
                            "state": pr["state"],
                            "author": pr["user"]["login"],
                            "head": pr["head"]["ref"],
                            "base": pr["base"]["ref"],
                            "created_at": pr["created_at"],
                            "updated_at": pr["updated_at"],
                            "url": pr["html_url"],
                            "draft": pr.get("draft", False),
                            "mergeable": pr.get("mergeable"),
                        }
                        for pr in raw
                    ]
    except Exception as e:
        logger.error("get_pull_requests error: %s", e)
    return []


# ── GitHub Actions ────────────────────────────────────────────────────────────

async def get_workflow_runs(per_page: int = 20) -> List[Dict]:
    if not settings.github_configured:
        return []
    url = f"{_repo_base()}/actions/runs"
    params = {"per_page": per_page}
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            async with s.get(url, headers=_headers(), params=params) as r:
                if r.status == 200:
                    data = await r.json()
                    return [
                        {
                            "id": run["id"],
                            "name": run["name"],
                            "workflow": run.get("path", ""),
                            "branch": run["head_branch"],
                            "commit_sha": run["head_sha"][:8],
                            "status": run["status"],        # queued, in_progress, completed
                            "conclusion": run["conclusion"], # success, failure, cancelled, None
                            "created_at": run["created_at"],
                            "updated_at": run["updated_at"],
                            "url": run["html_url"],
                            "run_number": run["run_number"],
                            "event": run["event"],          # push, pull_request, workflow_dispatch
                        }
                        for run in data.get("workflow_runs", [])
                    ]
    except Exception as e:
        logger.error("get_workflow_runs error: %s", e)
    return []


async def get_workflow_run_jobs(run_id: int) -> List[Dict]:
    if not settings.github_configured:
        return []
    url = f"{_repo_base()}/actions/runs/{run_id}/jobs"
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            async with s.get(url, headers=_headers()) as r:
                if r.status == 200:
                    data = await r.json()
                    return [
                        {
                            "id": job["id"],
                            "name": job["name"],
                            "status": job["status"],
                            "conclusion": job["conclusion"],
                            "started_at": job.get("started_at"),
                            "completed_at": job.get("completed_at"),
                            "steps": [
                                {
                                    "name": s["name"],
                                    "status": s["status"],
                                    "conclusion": s["conclusion"],
                                    "number": s["number"],
                                }
                                for s in job.get("steps", [])
                            ],
                        }
                        for job in data.get("jobs", [])
                    ]
    except Exception as e:
        logger.error("get_workflow_run_jobs error: %s", e)
    return []


async def trigger_workflow(workflow_id: str, ref: str = "main", inputs: Optional[Dict] = None) -> Tuple[bool, str]:
    """Trigger a workflow_dispatch event."""
    if not settings.github_configured:
        return False, "GitHub not configured"
    url = f"{_repo_base()}/actions/workflows/{workflow_id}/dispatches"
    payload: Dict[str, Any] = {"ref": ref}
    if inputs:
        payload["inputs"] = inputs
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            async with s.post(url, headers=_headers(), json=payload) as r:
                if r.status == 204:
                    return True, "Workflow triggered"
                return False, f"Failed: HTTP {r.status}"
    except Exception as e:
        return False, str(e)


# ── Webhook verification ──────────────────────────────────────────────────────

def verify_webhook_signature(payload_bytes: bytes, signature_header: str) -> bool:
    """Verify GitHub webhook HMAC-SHA256 signature."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode(),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature_header)


# ── Demo stubs (when GitHub not configured) ───────────────────────────────────

def demo_workflow_runs() -> List[Dict]:
    now = datetime.now(UTC).isoformat()
    return [
        {
            "id": 9001,
            "name": "CI — Test & Build",
            "workflow": ".github/workflows/ci.yml",
            "branch": "main",
            "commit_sha": "a1b2c3d4",
            "status": "completed",
            "conclusion": "success",
            "created_at": now,
            "updated_at": now,
            "url": "#",
            "run_number": 42,
            "event": "push",
            "is_demo": True,
        },
        {
            "id": 9002,
            "name": "CI — Test & Build",
            "workflow": ".github/workflows/ci.yml",
            "branch": "devinsight/fix-order-500-error",
            "commit_sha": "deadbeef",
            "status": "completed",
            "conclusion": "failure",
            "created_at": now,
            "updated_at": now,
            "url": "#",
            "run_number": 41,
            "event": "pull_request",
            "is_demo": True,
        },
    ]


def demo_pull_requests() -> List[Dict]:
    now = datetime.now(UTC).isoformat()
    return [
        {
            "number": 12,
            "title": "[DevInsight Auto-Fix] Fix HTTP 500 on POST /api/orders",
            "state": "open",
            "author": "devinsight-bot",
            "head": "devinsight/fix-order-500-error",
            "base": "main",
            "created_at": now,
            "updated_at": now,
            "url": "#",
            "draft": False,
            "mergeable": True,
            "is_demo": True,
        }
    ]
