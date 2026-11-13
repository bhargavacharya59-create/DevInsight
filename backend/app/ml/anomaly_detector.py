"""
Isolation Forest anomaly detection pipeline.
Uses Scikit-learn's IsolationForest — NOT random scores.
"""
from datetime import datetime, UTC
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
import os
import logging

from app.core.config import settings

logger = logging.getLogger("devinsight.ml")

# Feature columns in the expected order
FEATURE_COLUMNS = [
    "request_rate",
    "error_rate",
    "latency_ms",
    "cpu_utilization",
    "memory_utilization",
    "db_query_latency",
    "service_error_count",
]

MODEL_PATH = os.path.join(os.path.dirname(__file__), "isolation_forest.joblib")
SCALER_PATH = os.path.join(os.path.dirname(__file__), "scaler.joblib")


class AnomalyDetector:
    """
    Isolation Forest-based anomaly detector.

    Training: fit on a window of normal-looking telemetry samples.
    Prediction: returns (anomaly_score, is_anomaly) for a single sample.
    """

    def __init__(self) -> None:
        self.model: Optional[IsolationForest] = None
        self.scaler: Optional[StandardScaler] = None
        self._trained: bool = False
        self._training_sample_count: int = 0

    # ── Training ──────────────────────────────────────────────────────────────

    def train(self, samples: List[Dict[str, float]]) -> Dict[str, Any]:
        """
        Train or retrain the model on the provided samples.
        Samples must contain at least the FEATURE_COLUMNS keys.
        Returns a training report.
        """
        if len(samples) < 20:
            return {
                "success": False,
                "reason": f"Insufficient training data: {len(samples)} samples provided, minimum 20 required.",
                "trained": False,
            }

        df = pd.DataFrame(samples)

        # Fill missing feature columns with 0
        for col in FEATURE_COLUMNS:
            if col not in df.columns:
                df[col] = 0.0

        X = df[FEATURE_COLUMNS].fillna(0.0).values.astype(np.float64)

        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        self.model = IsolationForest(
            n_estimators=200,
            contamination=settings.ANOMALY_CONTAMINATION,
            random_state=42,
            n_jobs=-1,
        )
        self.model.fit(X_scaled)

        self._trained = True
        self._training_sample_count = len(samples)

        # Persist
        try:
            joblib.dump(self.model, MODEL_PATH)
            joblib.dump(self.scaler, SCALER_PATH)
        except Exception as e:
            logger.warning("Could not persist model: %s", e)

        logger.info("IsolationForest trained on %d samples", len(samples))
        return {
            "success": True,
            "trained": True,
            "sample_count": len(samples),
            "features": FEATURE_COLUMNS,
            "contamination": settings.ANOMALY_CONTAMINATION,
        }

    def load(self) -> bool:
        """Load a previously persisted model."""
        if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
            try:
                self.model = joblib.load(MODEL_PATH)
                self.scaler = joblib.load(SCALER_PATH)
                self._trained = True
                logger.info("Loaded existing IsolationForest model from disk")
                return True
            except Exception as e:
                logger.warning("Could not load model: %s", e)
        return False

    # ── Prediction ────────────────────────────────────────────────────────────

    def predict(self, sample: Dict[str, float]) -> Dict[str, Any]:
        """
        Predict anomaly score for a single telemetry sample.
        Returns a dict with: anomaly_score, is_anomaly, features, timestamp, confidence.
        """
        if not self._trained or self.model is None:
            return {
                "anomaly_score": 0.0,
                "is_anomaly": False,
                "error": "Model not trained. Provide more telemetry data.",
                "timestamp": datetime.now(UTC).isoformat(),
            }

        # Build feature vector
        row = [sample.get(col, 0.0) for col in FEATURE_COLUMNS]
        X = np.array([row], dtype=np.float64)
        X_scaled = self.scaler.transform(X)

        # IsolationForest score_samples returns negative average path length.
        # More negative = more anomalous.
        raw_score = float(self.model.score_samples(X_scaled)[0])
        prediction = int(self.model.predict(X_scaled)[0])  # 1=normal, -1=anomaly

        # Normalize to a [0,1] range where 1 = most anomalous
        # Typical range is roughly [-0.6, 0.0] for contamination=0.1
        normalized = max(0.0, min(1.0, (-raw_score - 0.0) / 0.6))

        is_anomaly = prediction == -1 or raw_score < settings.ANOMALY_THRESHOLD

        return {
            "anomaly_score": round(normalized, 4),
            "raw_score": round(raw_score, 4),
            "is_anomaly": is_anomaly,
            "features": {col: sample.get(col, 0.0) for col in FEATURE_COLUMNS},
            "timestamp": datetime.now(UTC).isoformat(),
            "model_trained": True,
        }

    def predict_batch(self, samples: List[Dict[str, float]]) -> List[Dict[str, Any]]:
        """Predict for a list of samples."""
        return [self.predict(s) for s in samples]

    # ── Feature contribution ──────────────────────────────────────────────────

    def feature_contributions(self, sample: Dict[str, float]) -> Dict[str, float]:
        """
        Approximate per-feature anomaly contribution by ablation.
        Each feature is zeroed out and the score difference is measured.
        """
        if not self._trained or self.model is None:
            return {}

        baseline = self.predict(sample)["anomaly_score"]
        contributions = {}
        for col in FEATURE_COLUMNS:
            zeroed = dict(sample)
            zeroed[col] = 0.0
            ablated = self.predict(zeroed)["anomaly_score"]
            contributions[col] = round(baseline - ablated, 4)

        return contributions

    @property
    def is_trained(self) -> bool:
        return self._trained


# ── Singleton ─────────────────────────────────────────────────────────────────

_detector_instance: Optional[AnomalyDetector] = None


def get_detector() -> AnomalyDetector:
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = AnomalyDetector()
        # Try to load from disk
        _detector_instance.load()
    return _detector_instance


def build_demo_training_data(n_samples: int = 500) -> List[Dict[str, float]]:
    """
    Generate synthetic normal-operation samples for initial model training in demo mode.
    These are NOT anomalies — they represent healthy baseline behavior.
    """
    import random
    import math

    rng = random.Random(42)
    samples = []
    for i in range(n_samples):
        t = i / n_samples * 2 * math.pi
        samples.append({
            "request_rate": rng.gauss(400.0, 40.0) + 30 * math.sin(t),
            "error_rate": max(0.0, rng.gauss(1.0, 0.3)),
            "latency_ms": max(10.0, rng.gauss(180.0, 25.0)),
            "cpu_utilization": max(5.0, min(60.0, rng.gauss(35.0, 8.0))),
            "memory_utilization": max(20.0, min(70.0, rng.gauss(50.0, 8.0))),
            "db_query_latency": max(2.0, rng.gauss(12.0, 3.0)),
            "service_error_count": max(0.0, rng.gauss(5.0, 2.0)),
        })
    return samples


