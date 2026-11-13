"""Quick import and unit test for new integration modules."""
from app.main import app
from app.api.ingest import router as ingest_router
from app.services.shopsphere_poller import (
    run_poller, scrape_once,
    parse_prometheus_text, extract_shopsphere_features, get_poller_status
)
print("All DevInsight integration imports: OK")

sample = "\n".join([
    "shopsphere_http_requests_total 1200",
    "shopsphere_http_errors_total 45",
    "shopsphere_http_request_duration_seconds_sum 142.5",
    "shopsphere_http_request_duration_seconds_count 1200",
    "shopsphere_db_query_duration_seconds_sum 18.3",
    "shopsphere_db_query_duration_seconds_count 850",
    "shopsphere_http_requests_active 12",
    "shopsphere_payments_total 3",
    "shopsphere_db_connection_failures_total 0",
])
metrics = parse_prometheus_text(sample)
features = extract_shopsphere_features(metrics)
print("Parsed metrics:", len(metrics), "entries")
print("Features:", features)
print("Error rate:", features["error_rate"], "%  (expect ~3.75)")
assert len(metrics) == 9, "Expected 9 metrics, got " + str(len(metrics))
assert 3.0 <= features["error_rate"] <= 5.0, "Unexpected error_rate: " + str(features["error_rate"])
assert features["latency_ms"] > 0
assert features["db_query_latency"] > 0
print("Prometheus parser assertions: PASSED")
status = get_poller_status()
print("Poller status:", status)
print("All DevInsight integration checks PASSED")
