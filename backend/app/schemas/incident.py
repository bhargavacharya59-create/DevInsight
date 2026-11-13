"""Pydantic schemas for incidents."""
from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field
from app.models.incident import SeverityLevel, IncidentStatus, RCAStatus


class IncidentEventSchema(BaseModel):
    id: str
    incident_id: str
    event_type: str
    description: str
    created_at: datetime
    event_metadata: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


class RootCauseCandidateSchema(BaseModel):
    id: str
    rca_result_id: str
    rank: int
    title: str
    description: Optional[str] = None
    confidence: float
    evidence: Optional[List[Any]] = None
    reasoning: Optional[str] = None
    recommended_investigation: Optional[str] = None

    model_config = {"from_attributes": True}


class RCAResultSchema(BaseModel):
    id: str
    incident_id: str
    created_at: datetime
    root_cause_summary: Optional[str] = None
    confidence: float
    candidates: Optional[List[Any]] = None
    evidence_metrics: Optional[List[Any]] = None
    evidence_logs: Optional[List[Any]] = None
    evidence_traces: Optional[List[Any]] = None
    deployment_correlation: Optional[Dict[str, Any]] = None
    ai_explanation: Optional[str] = None
    ai_available: bool
    root_cause_candidates: List[RootCauseCandidateSchema] = []

    model_config = {"from_attributes": True}


class RecommendationSchema(BaseModel):
    id: str
    incident_id: str
    category: str
    action: str
    priority: int
    created_at: datetime

    model_config = {"from_attributes": True}


class IncidentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    description: Optional[str] = None
    severity: SeverityLevel = SeverityLevel.MEDIUM
    affected_service: Optional[str] = None
    anomaly_score: Optional[float] = None
    is_demo: bool = False
    fingerprint: Optional[str] = None


class IncidentCreate(IncidentBase):
    started_at: Optional[datetime] = None
    related_metrics: Optional[Dict[str, Any]] = None
    related_logs: Optional[List[Any]] = None
    related_traces: Optional[List[Any]] = None


class IncidentUpdate(BaseModel):
    status: Optional[IncidentStatus] = None
    severity: Optional[SeverityLevel] = None
    probable_root_cause: Optional[str] = None
    confidence_score: Optional[float] = None
    ai_explanation: Optional[str] = None
    resolved_at: Optional[datetime] = None


class IncidentResponse(IncidentBase):
    id: str
    status: IncidentStatus
    detected_at: datetime
    started_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    updated_at: datetime
    rca_status: RCAStatus
    probable_root_cause: Optional[str] = None
    confidence_score: Optional[float] = None
    ai_explanation: Optional[str] = None
    related_metrics: Optional[Dict[str, Any]] = None
    related_logs: Optional[List[Any]] = None
    related_traces: Optional[List[Any]] = None
    acknowledged: bool
    acknowledged_at: Optional[datetime] = None
    events: List[IncidentEventSchema] = []
    rca_results: List[RCAResultSchema] = []
    recommendations: List[RecommendationSchema] = []

    model_config = {"from_attributes": True}


class IncidentListResponse(BaseModel):
    total: int
    incidents: List[IncidentResponse]
    page: int
    page_size: int


class AnomalyEventSchema(BaseModel):
    id: str
    detected_at: datetime
    service: str
    anomaly_score: float
    is_anomaly: bool
    features: Optional[Dict[str, Any]] = None
    incident_id: Optional[str] = None
    is_demo: bool

    model_config = {"from_attributes": True}
