"""Tests for the demo telemetry generator."""
import pytest
from app.services import demo_telemetry


def test_generate_metric_timeseries_normal():
    demo_telemetry.set_active_scenario(None)
    series = demo_telemetry.generate_metric_timeseries("shopsphere-api", "error_rate", 60, 60)
    assert series.name == "error_rate"
    assert series.service == "shopsphere-api"
    assert len(series.data_points) > 0
    # All values should be non-negative
    for pt in series.data_points:
        assert pt.value >= 0.0


def test_generate_metric_timeseries_anomaly_scenario():
    demo_telemetry.set_active_scenario("http_500_spike")
    series = demo_telemetry.generate_metric_timeseries("shopsphere-api", "error_rate", 60, 60)
    # Last 40% of points should be higher than first 40% (anomaly ramp)
    n = len(series.data_points)
    early_avg = sum(p.value for p in series.data_points[:int(n * 0.4)]) / int(n * 0.4)
    late_avg = sum(p.value for p in series.data_points[int(n * 0.6):]) / (n - int(n * 0.6))
    assert late_avg >= early_avg, f"Expected late avg ({late_avg}) >= early avg ({early_avg}) in http_500_spike"
    demo_telemetry.set_active_scenario(None)


def test_generate_logs():
    logs = demo_telemetry.generate_logs(limit=20)
    assert len(logs) == 20
    for log in logs:
        assert "timestamp" in log
        assert "level" in log
        assert "message" in log
        assert "service" in log
        assert log["is_demo"] is True


def test_generate_current_service_metrics():
    metrics = demo_telemetry.generate_current_service_metrics()
    assert len(metrics) > 0
    for svc in metrics:
        assert "name" in svc
        assert "status" in svc
        assert "error_rate" in svc
        assert "latency_ms" in svc


def test_generate_traces():
    traces = demo_telemetry.generate_traces(limit=10)
    assert len(traces) == 10
    for t in traces:
        assert "root_span" in t
        span = t["root_span"]
        assert "trace_id" in span
        assert "service" in span
        assert "duration_ms" in span


def test_demo_scenarios_defined():
    assert len(demo_telemetry.DEMO_SCENARIOS) >= 7
    for s in demo_telemetry.DEMO_SCENARIOS:
        assert "id" in s
        assert "name" in s
        assert "description" in s


def test_all_scenario_ids_have_templates():
    for s in demo_telemetry.DEMO_SCENARIOS:
        if s["id"] != "normal_operation":
            template = demo_telemetry.get_demo_incident_template(s["id"])
            assert template is not None, f"No template for scenario {s['id']}"
