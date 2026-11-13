"""Tests for the RCA engine."""
import pytest
from datetime import datetime, UTC, timedelta
from app.services.rca_engine import RCAEngine


def make_incident(service="shopsphere-api"):
    return {
        "id": "test-incident-001",
        "title": "Test incident",
        "affected_service": service,
        "detected_at": datetime.now(UTC).isoformat(),
        "severity": "high",
        "status": "open",
    }


def make_db_metrics():
    return [
        {
            "name": "db_query_latency",
            "service": "database",
            "current_value": 850.0,
            "baseline_value": 12.0,
        },
        {
            "name": "latency_ms",
            "service": "order-service",
            "current_value": 2400.0,
            "baseline_value": 210.0,
        },
    ]


def make_error_logs():
    return [
        {
            "level": "ERROR",
            "message": "Database connection timeout after 5000ms",
            "service": "order-service",
        },
        {
            "level": "ERROR",
            "message": "Pool exhausted: cannot acquire connection from database pool",
            "service": "payment-service",
        },
    ] * 8  # Repeat to simulate volume


def make_deployment():
    dep_time = datetime.now(UTC) - timedelta(minutes=8)
    return [{
        "service": "shopsphere-api",
        "version": "v2.4.0",
        "deployed_at": dep_time.isoformat(),
        "deployed_by": "ci",
    }]


def test_investigate_returns_structure():
    engine = RCAEngine()
    result = engine.investigate(make_incident())
    assert "root_cause_summary" in result
    assert "confidence" in result
    assert "candidates" in result
    assert "investigation_timestamp" in result


def test_investigate_with_db_signals():
    engine = RCAEngine()
    result = engine.investigate(
        make_incident("database"),
        metrics=make_db_metrics(),
        logs=make_error_logs(),
    )
    # Should find database-related root cause
    assert result["confidence"] > 0
    # At least one candidate should mention database
    titles = [c["title"].lower() for c in result["candidates"]]
    assert any("database" in t for t in titles), f"Expected database candidate in: {titles}"


def test_deployment_correlation():
    engine = RCAEngine()
    result = engine.investigate(
        make_incident(),
        deployments=make_deployment(),
    )
    assert result["deployment_correlation"]["correlated"] is True
    # Should have a deployment candidate
    titles = [c["title"].lower() for c in result["candidates"]]
    assert any("deployment" in t for t in titles), f"Expected deployment candidate in: {titles}"


def test_insufficient_evidence():
    engine = RCAEngine()
    result = engine.investigate(make_incident(), metrics=[], logs=[], traces=[])
    # Should handle gracefully
    assert isinstance(result["root_cause_summary"], str)
    assert result["confidence"] >= 0


def test_candidates_are_ranked():
    engine = RCAEngine()
    result = engine.investigate(
        make_incident(),
        metrics=make_db_metrics(),
        logs=make_error_logs(),
        deployments=make_deployment(),
    )
    candidates = result["candidates"]
    if len(candidates) > 1:
        for i in range(len(candidates) - 1):
            assert candidates[i]["confidence"] >= candidates[i + 1]["confidence"], \
                f"Candidates not sorted: {candidates[i]['confidence']} < {candidates[i+1]['confidence']}"


def test_candidates_have_evidence():
    engine = RCAEngine()
    result = engine.investigate(
        make_incident(),
        metrics=make_db_metrics(),
        logs=make_error_logs(),
    )
    for candidate in result["candidates"]:
        assert "evidence" in candidate
        assert "confidence" in candidate
        assert 0.0 <= candidate["confidence"] <= 1.0


