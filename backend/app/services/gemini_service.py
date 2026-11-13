"""
Gemini AI integration for incident explanation and recommendations.
Uses google-genai SDK (the newer unified SDK).
Falls back gracefully when API is unavailable.
"""
from typing import Dict, Any, Optional, List
import logging
import json

from app.core.config import settings

logger = logging.getLogger("devinsight.gemini")


EXPLANATION_PROMPT_TEMPLATE = """You are an expert SRE (Site Reliability Engineer) analyzing a production incident.
You have been provided with structured telemetry evidence collected by the DevInsight AI system.
Your role is to explain the incident clearly and provide actionable recommendations.

IMPORTANT RULES:
- Only use the evidence provided below. Do not invent metrics, logs, or traces.
- Clearly distinguish between what the evidence shows and what is probable but unconfirmed.
- Do not claim you can execute commands or modify infrastructure.
- Be specific and technical, but also understandable to an on-call engineer.

=== INCIDENT INFORMATION ===
Title: {title}
Severity: {severity}
Affected Service: {affected_service}
Detection Time: {detected_at}
Status: {status}
Anomaly Score: {anomaly_score}

=== ANOMALY DETECTION RESULTS ===
{anomaly_details}

=== ROOT CAUSE ANALYSIS (Deterministic) ===
Top Root Cause Candidate: {top_candidate}
Confidence: {confidence}

Supporting Evidence:
{evidence_summary}

=== METRIC SIGNALS ===
{metric_signals}

=== LOG PATTERNS ===
{log_patterns}

=== TRACE SIGNALS ===
{trace_signals}

=== DEPLOYMENT CORRELATION ===
{deployment_info}

Please provide a JSON response with exactly these keys:
{{
  "incident_explanation": "2-3 sentence plain-language explanation of what happened",
  "probable_root_cause": "What likely caused this based on the evidence",
  "why_it_happened": "The underlying technical reason",
  "user_impact": "How this affected end users of the ShopSphere platform",
  "investigation_steps": ["step 1", "step 2", "step 3"],
  "remediation_steps": ["step 1", "step 2", "step 3"],
  "prevention": ["action 1", "action 2"],
  "confidence_limitations": "What the evidence cannot confirm"
}}
"""


class GeminiService:
    """Wraps the Google Gemini API (google-genai SDK) with graceful degradation."""

    def __init__(self) -> None:
        self._client = None
        self._available = False
        self._init()

    def _init(self) -> None:
        if not settings.GEMINI_API_KEY:
            logger.info("GEMINI_API_KEY not set — AI explanations will use fallback mode")
            return
        try:
            from google import genai
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
            self._available = True
            logger.info("Gemini client initialized with model %s", settings.GEMINI_MODEL)
        except ImportError:
            logger.warning("google-genai not installed — AI explanations unavailable")
        except Exception as e:
            logger.warning("Failed to initialize Gemini client: %s", e)

    @property
    def available(self) -> bool:
        return self._available

    def _get_model(self) -> str:
        """Return model name with models/ prefix if needed."""
        m = settings.GEMINI_MODEL
        if not m.startswith("models/"):
            m = f"models/{m}"
        return m

    def explain_incident(
        self,
        incident: Dict[str, Any],
        rca_result: Dict[str, Any],
        anomaly_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate AI explanation for an incident.
        Returns structured explanation dict, or fallback if unavailable.
        """
        if not self._available or self._client is None:
            return self._fallback_explanation(incident, rca_result)

        try:
            prompt = self._build_prompt(incident, rca_result, anomaly_result)
            response = self._client.models.generate_content(
                model=self._get_model(),
                contents=prompt,
            )
            text = response.text.strip()
            result = self._parse_response(text)
            result["ai_available"] = True
            result["model"] = settings.GEMINI_MODEL
            return result

        except Exception as e:
            logger.error("Gemini API call failed: %s", e)
            fallback = self._fallback_explanation(incident, rca_result)
            fallback["ai_error"] = str(e)
            return fallback

    def answer_question(
        self,
        question: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Answer a specific question about an incident with context."""
        if not self._available or self._client is None:
            return {
                "answer": (
                    "AI assistant is not available. Configure GEMINI_API_KEY to enable "
                    "AI-powered responses. You can still view the deterministic RCA results "
                    "in the incident detail page."
                ),
                "ai_available": False,
                "sources": [],
            }

        try:
            ctx_summary = json.dumps(context, indent=2, default=str)[:3000]
            prompt = f"""You are an SRE AI assistant helping investigate a production incident on the ShopSphere platform.
Answer ONLY based on the incident context provided. Do not invent data or claim to execute commands.

INCIDENT CONTEXT:
{ctx_summary}

QUESTION: {question}

Provide a specific, helpful answer. If the context doesn't contain enough information to answer
confidently, say so clearly. Include which pieces of evidence support your answer."""

            from google import genai
            response = self._client.models.generate_content(
                model=self._get_model(),
                contents=prompt,
            )
            return {
                "answer": response.text.strip(),
                "ai_available": True,
                "model": settings.GEMINI_MODEL,
                "sources": ["incident_data", "rca_results"],
            }
        except Exception as e:
            logger.error("Gemini question answer failed: %s", e)
            return {
                "answer": f"AI assistant encountered an error: {e}. Please check the RCA results directly.",
                "ai_available": False,
                "error": str(e),
            }

    def _build_prompt(
        self,
        incident: Dict[str, Any],
        rca: Dict[str, Any],
        anomaly: Optional[Dict[str, Any]],
    ) -> str:
        candidates = rca.get("candidates", [])
        top = candidates[0] if candidates else {}
        evidence = top.get("evidence", [])[:5]

        metric_signals = "\n".join(
            f"- {s.get('description', '')}"
            for s in (rca.get("evidence_metrics") or [])[:5]
        ) or "No metric signals available."

        log_patterns = "\n".join(
            f"- {p.get('description', '')} (count: {p.get('count', 'N/A')})"
            for p in (rca.get("evidence_logs") or [])[:5]
        ) or "No log patterns available."

        trace_signals = "\n".join(
            f"- {t.get('description', '')}"
            for t in (rca.get("evidence_traces") or [])[:5]
        ) or "No trace signals available."

        dep_corr = rca.get("deployment_correlation", {})
        if dep_corr.get("correlated"):
            deps = dep_corr.get("deployments", [])
            dep_info = "\n".join(
                f"- {d.get('service')} {d.get('version', '')} deployed "
                f"{d.get('minutes_before_incident', '?')} minutes before incident"
                for d in deps
            )
        else:
            dep_info = "No recent deployments correlated with this incident."

        anomaly_details = "Isolation Forest anomaly detection flagged this event."
        if anomaly:
            score = anomaly.get("anomaly_score", 0)
            features = anomaly.get("features", {})
            anomaly_details = (
                f"Anomaly score: {score:.3f}\n"
                f"Feature values: {json.dumps(features, default=str)}"
            )

        evidence_summary = "\n".join(
            f"- [{e.get('kind', '?').upper()}] {e.get('description', '')}"
            for e in evidence
        ) or "No structured evidence available."

        return EXPLANATION_PROMPT_TEMPLATE.format(
            title=incident.get("title", "Unknown Incident"),
            severity=incident.get("severity", "unknown"),
            affected_service=incident.get("affected_service", "unknown"),
            detected_at=incident.get("detected_at", "unknown"),
            status=incident.get("status", "unknown"),
            anomaly_score=incident.get("anomaly_score", "N/A"),
            anomaly_details=anomaly_details,
            top_candidate=top.get("title", "Undetermined"),
            confidence=f"{top.get('confidence', 0):.1%}",
            evidence_summary=evidence_summary,
            metric_signals=metric_signals,
            log_patterns=log_patterns,
            trace_signals=trace_signals,
            deployment_info=dep_info,
        )

    def _parse_response(self, text: str) -> Dict[str, Any]:
        """Extract JSON from Gemini response."""
        try:
            if text.startswith("{"):
                return json.loads(text)
        except json.JSONDecodeError:
            pass

        import re
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find any JSON object in the text
        match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        return {
            "incident_explanation": text,
            "probable_root_cause": "See full explanation above.",
            "why_it_happened": "",
            "user_impact": "",
            "investigation_steps": [],
            "remediation_steps": [],
            "prevention": [],
            "confidence_limitations": "Response was not in expected JSON format.",
        }

    def _fallback_explanation(
        self, incident: Dict[str, Any], rca: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deterministic fallback when Gemini is unavailable."""
        candidates = rca.get("candidates", [])
        top = candidates[0] if candidates else {}
        svc = incident.get("affected_service", "the affected service")
        severity = incident.get("severity", "unknown")

        investigation_steps = []
        if top.get("recommended_investigation"):
            investigation_steps = [
                line.strip()
                for line in top["recommended_investigation"].split("\n")
                if line.strip() and line.strip()[0].isdigit()
            ]

        return {
            "ai_available": False,
            "incident_explanation": (
                f"A {severity}-severity incident was detected on {svc}. "
                f"The anomaly detection system identified unusual patterns requiring investigation. "
                f"Root cause analysis has been completed using available telemetry."
            ),
            "probable_root_cause": top.get("title", rca.get("root_cause_summary", "Undetermined")),
            "why_it_happened": top.get(
                "reasoning",
                "Insufficient data to determine the underlying cause with confidence."
            ),
            "user_impact": (
                f"Users of the ShopSphere platform may have experienced degraded performance "
                f"or errors on {svc}."
            ),
            "investigation_steps": investigation_steps or [
                "Review application logs for the incident time window",
                "Check metric dashboards for the affected service",
                "Examine recent deployment history",
                "Review database performance metrics",
            ],
            "remediation_steps": [
                "Identify and revert the root cause change if deployment-related",
                "Scale affected services if resource saturation is confirmed",
                "Restart affected service pods if application error is confirmed",
                "Engage database team if database performance issue is confirmed",
            ],
            "prevention": [
                "Improve monitoring coverage and alerting thresholds",
                "Add automated regression tests for the affected code path",
                "Review deployment rollout strategy",
                "Conduct a post-incident review",
            ],
            "confidence_limitations": (
                "AI explanation is unavailable (GEMINI_API_KEY not configured). "
                "The above is a deterministic fallback based on RCA evidence. "
                "Configure GEMINI_API_KEY for AI-powered explanations."
            ),
        }


# ── Singleton ─────────────────────────────────────────────────────────────────
_gemini_service: Optional[GeminiService] = None


def get_gemini_service() -> GeminiService:
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService()
    return _gemini_service
