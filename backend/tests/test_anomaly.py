"""Tests for anomaly detection."""
import pytest
from app.ml.anomaly_detector import AnomalyDetector, build_demo_training_data


def make_anomalous_sample():
    return {
        "request_rate": 400.0,
        "error_rate": 85.0,   # Very high
        "latency_ms": 8000.0, # Very high
        "cpu_utilization": 97.0,
        "memory_utilization": 95.0,
        "db_query_latency": 4000.0,
        "service_error_count": 200.0,
    }


def make_normal_sample():
    return {
        "request_rate": 400.0,
        "error_rate": 1.0,
        "latency_ms": 180.0,
        "cpu_utilization": 35.0,
        "memory_utilization": 50.0,
        "db_query_latency": 12.0,
        "service_error_count": 5.0,
    }


def test_train_requires_minimum_samples():
    detector = AnomalyDetector()
    result = detector.train([make_normal_sample()] * 5)
    assert result["success"] is False
    assert "Insufficient" in result["reason"]


def test_train_succeeds_with_enough_samples():
    samples = build_demo_training_data(200)
    detector = AnomalyDetector()
    result = detector.train(samples)
    assert result["success"] is True
    assert result["trained"] is True
    assert detector.is_trained


def test_predict_returns_score():
    samples = build_demo_training_data(200)
    detector = AnomalyDetector()
    detector.train(samples)

    result = detector.predict(make_normal_sample())
    assert "anomaly_score" in result
    assert "is_anomaly" in result
    assert 0.0 <= result["anomaly_score"] <= 1.0


def test_anomaly_score_higher_for_anomalous():
    samples = build_demo_training_data(300)
    detector = AnomalyDetector()
    detector.train(samples)

    normal = detector.predict(make_normal_sample())
    anomalous = detector.predict(make_anomalous_sample())

    # Anomalous sample should have a higher anomaly score
    assert anomalous["anomaly_score"] > normal["anomaly_score"], (
        f"Expected anomalous score ({anomalous['anomaly_score']}) > "
        f"normal score ({normal['anomaly_score']})"
    )


def test_predict_without_training():
    detector = AnomalyDetector()
    result = detector.predict(make_normal_sample())
    assert "error" in result
    assert result["is_anomaly"] is False


def test_feature_contributions():
    samples = build_demo_training_data(200)
    detector = AnomalyDetector()
    detector.train(samples)

    contrib = detector.feature_contributions(make_anomalous_sample())
    assert isinstance(contrib, dict)
    # Should have contributions for all features
    assert len(contrib) > 0


def test_batch_predict():
    samples = build_demo_training_data(200)
    detector = AnomalyDetector()
    detector.train(samples)

    results = detector.predict_batch([make_normal_sample(), make_anomalous_sample()])
    assert len(results) == 2
