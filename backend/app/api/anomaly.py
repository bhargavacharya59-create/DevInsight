"""Anomaly detection API."""
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.ml.anomaly_detector import get_detector, build_demo_training_data
from app.core.config import settings

router = APIRouter(prefix="/api/anomaly", tags=["anomaly"])


class DetectRequest(BaseModel):
    service: str = "shopsphere-api"
    request_rate: float = 0.0
    error_rate: float = 0.0
    latency_ms: float = 0.0
    cpu_utilization: float = 0.0
    memory_utilization: float = 0.0
    db_query_latency: float = 0.0
    service_error_count: float = 0.0


@router.post("/detect")
async def detect_anomaly(req: DetectRequest):
    """Run anomaly detection on a telemetry sample."""
    detector = get_detector()
    if not detector.is_trained:
        # Auto-train on demo data if not already trained
        samples = build_demo_training_data(500)
        result = detector.train(samples)
        if not result["success"]:
            raise HTTPException(status_code=503, detail=result["reason"])

    sample = req.model_dump(exclude={"service"})
    prediction = detector.predict(sample)
    contributions = detector.feature_contributions(sample) if prediction.get("is_anomaly") else {}

    return {
        "service": req.service,
        **prediction,
        "feature_contributions": contributions,
        "threshold": settings.ANOMALY_THRESHOLD,
    }


@router.post("/train")
async def train_model():
    """(Re)train the anomaly detection model on demo baseline data."""
    samples = build_demo_training_data(500)
    detector = get_detector()
    result = detector.train(samples)
    return result


@router.get("/status")
async def model_status():
    """Return current model status."""
    detector = get_detector()
    return {
        "trained": detector.is_trained,
        "training_sample_count": detector._training_sample_count,
        "contamination": settings.ANOMALY_CONTAMINATION,
        "threshold": settings.ANOMALY_THRESHOLD,
    }
