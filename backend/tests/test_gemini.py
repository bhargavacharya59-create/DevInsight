"""Tests for Gemini service (graceful degradation)."""
import pytest
from app.services.gemini_service import GeminiService


def make_incident():
    return {
        "id": "test-001",
        "title": "Test: Payment Service Failure",
        "severity": "critical",
        "status": "investigating",
        "affected_service": "payment-service",
        "detected_at": "2024-01-01T10:00:00",
        "anomaly_score": 0.87,
    }


def make_rca():
    return {
        "root_cause_summary": "Payment gateway rate limiting",
        "confidence": 0.79,
        "candidates": [
            {
                "rank": 1,
                "title": "Payment gateway 503",
                "confidence": 0.79,
                "evidence": [
                    {"kind": "log", "description": "503 errors in payment logs", "weight": 0.4, "source": "loki"}
                ],
                "reasoning": "Log evidence shows gateway returning 503.",
                "recommended_investigation": "1. Check payment gateway status page.",
            }
        ],
        "evidence_metrics": [],
        "evidence_logs": [],
        "evidence_traces": [],
        "deployment_correlation": {"correlated": False, "deployments": []},
    }


def test_fallback_when_no_api_key():
    """App must not crash when GEMINI_API_KEY is not set."""
    svc = GeminiService.__new__(GeminiService)
    svc._client = None
    svc._available = False

    result = svc._fallback_explanation(make_incident(), make_rca())
    assert "incident_explanation" in result
    assert result["ai_available"] is False
    assert "probable_root_cause" in result
    assert len(result["investigation_steps"]) > 0


def test_explain_incident_without_key():
    """explain_incident must return valid dict even without API key."""
    svc = GeminiService.__new__(GeminiService)
    svc._client = None
    svc._available = False

    result = svc.explain_incident(make_incident(), make_rca())
    assert "incident_explanation" in result
    assert "remediation_steps" in result
    assert result["ai_available"] is False


def test_answer_question_without_key():
    """answer_question must return valid response without API key."""
    svc = GeminiService.__new__(GeminiService)
    svc._client = None
    svc._available = False

    result = svc.answer_question("Why did this happen?", {})
    assert "answer" in result
    assert result["ai_available"] is False
