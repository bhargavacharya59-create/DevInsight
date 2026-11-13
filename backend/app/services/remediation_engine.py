"""
Autonomous remediation engine.
Workflow:
  1. Collect incident evidence
  2. Retrieve relevant source files from GitHub
  3. Use Gemini to generate a targeted patch
  4. Create a remediation branch
  5. Commit the patch
  6. Open a pull request
  7. Trigger CI/CD
  8. Poll for results and report back
"""
from __future__ import annotations
import logging
import re
import uuid
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.services import github_service

logger = logging.getLogger("devinsight.remediation")

MAX_RETRIES = 3  # prevent infinite loops


# ── Patch generation via Gemini ───────────────────────────────────────────────

def _build_fix_prompt(
    incident: Dict[str, Any],
    rca: Dict[str, Any],
    source_files: Dict[str, str],
) -> str:
    files_section = "\n\n".join(
        f"=== FILE: {path} ===\n```python\n{content}\n```"
        for path, content in source_files.items()
    )
    candidates = rca.get("candidates", [])
    top = candidates[0] if candidates else {}

    return f"""You are a senior software engineer fixing a production bug in the ShopSphere e-commerce application.

INCIDENT SUMMARY
Title:            {incident.get('title', 'Unknown')}
Severity:         {incident.get('severity', 'unknown')}
Affected service: {incident.get('affected_service', 'unknown')}
Root cause:       {top.get('title', rca.get('root_cause_summary', 'unknown'))}
Confidence:       {top.get('confidence', 0):.0%}

ROOT CAUSE REASONING
{top.get('reasoning', 'No reasoning available.')}

RELEVANT SOURCE FILES
{files_section or "No source files retrieved."}

YOUR TASK
1. Identify the precise lines causing the bug.
2. Generate a minimal, safe code patch.
3. Explain every change.
4. List any risks.
5. Suggest a test to verify the fix.

Respond in this EXACT JSON format (no markdown fences):
{{
  "affected_files": ["path/to/file.py"],
  "patch_description": "One sentence summary of the fix",
  "changes": [
    {{
      "file": "path/to/file.py",
      "original_snippet": "exact lines to replace",
      "fixed_snippet": "replacement lines",
      "explanation": "why this change fixes the bug"
    }}
  ],
  "risk_assessment": "low/medium/high — reason",
  "suggested_test": "code or description of a test that verifies the fix",
  "confidence": 0.85
}}
"""


async def generate_patch(
    incident: Dict[str, Any],
    rca: Dict[str, Any],
    source_files: Dict[str, str],
) -> Optional[Dict[str, Any]]:
    """Call Gemini to generate a code patch. Returns structured patch dict or None."""
    if not settings.gemini_available:
        logger.warning("Gemini API key not set — cannot generate patch")
        return None

    try:
        from google import genai
        import json

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        prompt = _build_fix_prompt(incident, rca, source_files)
        model_name = settings.GEMINI_MODEL
        if not model_name.startswith("models/"):
            model_name = f"models/{model_name}"
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        text = response.text.strip()

        # Strip markdown fences if present
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        patch = json.loads(text)
        patch["generated_at"] = datetime.now(UTC).isoformat()
        return patch

    except Exception as e:
        logger.error("generate_patch error: %s", e)
        return None


# ── Full remediation workflow ─────────────────────────────────────────────────

class RemediationResult:
    def __init__(self):
        self.branch: Optional[str] = None
        self.pr_number: Optional[int] = None
        self.pr_url: Optional[str] = None
        self.patch: Optional[Dict] = None
        self.workflow_run_id: Optional[int] = None
        self.status: str = "pending"   # pending|branch_created|pr_open|ci_running|ci_passed|ci_failed|error
        self.error: Optional[str] = None
        self.steps: List[Dict] = []
        self.retry_count: int = 0

    def add_step(self, name: str, status: str, detail: str = ""):
        self.steps.append({
            "name": name,
            "status": status,
            "detail": detail,
            "timestamp": datetime.now(UTC).isoformat(),
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "branch": self.branch,
            "pr_number": self.pr_number,
            "pr_url": self.pr_url,
            "patch": self.patch,
            "workflow_run_id": self.workflow_run_id,
            "status": self.status,
            "error": self.error,
            "steps": self.steps,
            "retry_count": self.retry_count,
        }


async def run_remediation(
    incident: Dict[str, Any],
    rca: Dict[str, Any],
    source_files: Optional[Dict[str, str]] = None,
    retry_count: int = 0,
) -> RemediationResult:
    result = RemediationResult()
    result.retry_count = retry_count

    if retry_count >= MAX_RETRIES:
        result.status = "error"
        result.error = f"Maximum retries ({MAX_RETRIES}) reached. Manual intervention required."
        result.add_step("Retry limit", "failed", result.error)
        return result

    # ── Step 1: Retrieve source files ─────────────────────────────────────────
    if not source_files:
        source_files = {}
        candidates = rca.get("candidates", [])
        top_candidate = candidates[0] if candidates else {}
        affected_files = top_candidate.get("evidence", [])
        # Try to get ShopSphere backend files — using the actual directory structure
        common_files = [
            "backend/app/services/order_service.py",
            "backend/app/api/routes/orders.py",
            "backend/app/main.py",
        ]
        for f in common_files:
            content = await github_service.get_file_content(f)
            if content:
                source_files[f] = content

    result.add_step(
        "Source retrieval",
        "completed",
        f"Retrieved {len(source_files)} file(s): {', '.join(source_files.keys()) or 'none'}",
    )

    # ── Step 2: Generate patch ─────────────────────────────────────────────────
    patch = await generate_patch(incident, rca, source_files)
    if not patch:
        result.status = "error"
        result.error = "Could not generate a patch. Gemini API key may be missing or service unavailable."
        result.add_step("Patch generation", "failed", result.error)
        return result

    result.patch = patch
    result.add_step(
        "Patch generation",
        "completed",
        f"Generated patch for {len(patch.get('changes', []))} file(s). Risk: {patch.get('risk_assessment', 'unknown')}",
    )

    # ── Step 3: Create branch ─────────────────────────────────────────────────
    incident_id_short = str(incident.get("id", uuid.uuid4()))[:8]
    branch_name = f"devinsight/fix-{incident_id_short}-attempt-{retry_count + 1}"
    result.branch = branch_name

    ok, msg = await github_service.create_branch(branch_name)
    if not ok:
        result.status = "error"
        result.error = f"Branch creation failed: {msg}"
        result.add_step("Branch creation", "failed", result.error)
        return result

    result.add_step("Branch creation", "completed", f"Branch: {branch_name}")

    # ── Step 4: Commit changes ────────────────────────────────────────────────
    for change in patch.get("changes", []):
        file_path = change.get("file", "")
        if not file_path:
            continue

        # Get current file and apply patch
        content = source_files.get(file_path) or await github_service.get_file_content(file_path, branch_name)
        if content and change.get("original_snippet") and change.get("fixed_snippet"):
            new_content = content.replace(
                change["original_snippet"],
                change["fixed_snippet"],
                1,
            )
        else:
            new_content = content or ""

        commit_msg = f"fix: {patch.get('patch_description', 'Auto-remediation')}\n\nGenerated by DevInsight AI\nIncident: {incident.get('id')}"
        ok, msg = await github_service.commit_file(branch_name, file_path, new_content, commit_msg)
        result.add_step(
            f"Commit {file_path}",
            "completed" if ok else "failed",
            msg,
        )

    # ── Step 5: Create PR ─────────────────────────────────────────────────────
    pr_title = f"[DevInsight Auto-Fix] {patch.get('patch_description', incident.get('title', 'Bug fix'))}"
    pr_body = _build_pr_body(incident, rca, patch)
    pr = await github_service.create_pull_request(
        title=pr_title,
        head=branch_name,
        body=pr_body,
    )
    if pr:
        result.pr_number = pr["number"]
        result.pr_url = pr["url"]
        result.status = "pr_open"
        result.add_step("Pull request", "completed", f"PR #{pr['number']}: {pr['url']}")
    else:
        result.status = "pr_open"  # Branch exists, PR may already be open
        result.add_step("Pull request", "skipped", "Could not create PR — may already exist or GitHub not configured")

    return result


def _build_pr_body(
    incident: Dict[str, Any],
    rca: Dict[str, Any],
    patch: Dict[str, Any],
) -> str:
    candidates = rca.get("candidates", [])
    top = candidates[0] if candidates else {}
    changes = patch.get("changes", [])
    changes_text = "\n".join(
        f"- **{c.get('file')}**: {c.get('explanation', '')}"
        for c in changes
    )
    return f"""## 🤖 DevInsight AI — Automated Remediation

> This pull request was automatically generated by DevInsight AI in response to a detected production incident.
> **Do not merge without reviewing the changes and ensuring CI/CD passes.**

---

### Incident
- **ID:** {incident.get('id', 'N/A')}
- **Title:** {incident.get('title', 'N/A')}
- **Severity:** {incident.get('severity', 'N/A')}
- **Service:** {incident.get('affected_service', 'N/A')}

### Root Cause Analysis
- **Root cause:** {top.get('title', rca.get('root_cause_summary', 'N/A'))}
- **Confidence:** {top.get('confidence', 0):.0%}
- **Reasoning:** {top.get('reasoning', 'N/A')}

### Changes Made
{changes_text or 'See diff for details.'}

### Risk Assessment
{patch.get('risk_assessment', 'Unknown')}

### Suggested Test
```
{patch.get('suggested_test', 'No test suggestion available.')}
```

---
*Generated by [DevInsight AI](http://localhost:5173) — Incident #{incident.get('id', '')}*
"""
