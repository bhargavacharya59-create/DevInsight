"""
GitHub webhook receiver.
Accepts push, pull_request, workflow_run events.
"""
import json
import logging
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from app.services.github_service import verify_webhook_signature
from app.core.config import settings

router = APIRouter(prefix="/api/webhook", tags=["webhook"])
logger = logging.getLogger("devinsight.webhook")

# In-memory event log (last 50 events)
_webhook_events: list = []


@router.post("/github")
async def github_webhook(request: Request, background: BackgroundTasks):
    """Receive GitHub webhook events."""
    body = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")
    event_type = request.headers.get("X-GitHub-Event", "unknown")

    # Verify signature if secret is set (always verify in production)
    if settings.GITHUB_WEBHOOK_SECRET and not verify_webhook_signature(body, sig):
        logger.warning("Webhook signature mismatch — rejecting event")
        raise HTTPException(401, "Invalid webhook signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON payload")

    event = {
        "type": event_type,
        "action": payload.get("action"),
        "ref": payload.get("ref"),
        "sender": payload.get("sender", {}).get("login"),
        "repository": payload.get("repository", {}).get("full_name"),
        "payload_summary": _summarise(event_type, payload),
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    }

    _webhook_events.insert(0, event)
    if len(_webhook_events) > 50:
        _webhook_events.pop()

    # Background processing
    background.add_task(_process_event, event_type, payload)

    logger.info("Webhook received: %s / %s", event_type, payload.get("action"))
    return {"received": True}


@router.get("/events")
async def list_events(limit: int = 20):
    return {"events": _webhook_events[:limit]}


def _summarise(event_type: str, payload: dict) -> str:
    if event_type == "push":
        commits = payload.get("commits", [])
        branch = payload.get("ref", "").replace("refs/heads/", "")
        return f"Push to {branch} — {len(commits)} commit(s)"
    if event_type == "pull_request":
        pr = payload.get("pull_request", {})
        return f"PR #{pr.get('number')} {payload.get('action')} — {pr.get('title', '')[:60]}"
    if event_type == "workflow_run":
        run = payload.get("workflow_run", {})
        return f"Workflow '{run.get('name')}' {run.get('status')} on {run.get('head_branch')}"
    return event_type


async def _process_event(event_type: str, payload: dict):
    """Background: classify and act on GitHub events."""
    try:
        if event_type == "push":
            ref = payload.get("ref", "")
            # Skip DevInsight's own remediation branches
            if "devinsight/" in ref:
                logger.info("Skipping DevInsight auto-branch push: %s", ref)
                return
            # Could trigger analysis here
            logger.info("Developer push detected: %s", ref)

        elif event_type == "workflow_run":
            run = payload.get("workflow_run", {})
            status = run.get("status")
            conclusion = run.get("conclusion")
            branch = run.get("head_branch", "")
            if "devinsight/" in branch:
                logger.info(
                    "DevInsight remediation CI result: branch=%s status=%s conclusion=%s",
                    branch, status, conclusion,
                )
    except Exception as e:
        logger.error("_process_event error: %s", e)
