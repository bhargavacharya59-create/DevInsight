"""Pydantic schemas for services and telemetry."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from app.models.service import ServiceStatus


class ServiceSchema(BaseModel):
    id: str
    name: str
    display_name: str
    description: Optional[str] = None
    status: ServiceStatus
    error_rate: Optional[float] = None
    latency_ms: Optional[float] = None
    request_rate: Optional[float] = None
    dependencies: Optional[List[str]] = None
    last_checked: Optional[datetime] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class TelemetrySourceSchema(BaseModel):
    id: str
    name: str
    url: Optional[str] = None
    connected: bool
    last_successful_connection: Optional[datetime] = None
    error_message: Optional[str] = None
    updated_at: datetime

    model_config = {"from_attributes": True}


class DemoScenarioSchema(BaseModel):
    id: str
    name: str
    description: str
    category: str
    duration_seconds: int
    active: bool
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    config: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


class MetricDataPoint(BaseModel):
    timestamp: datetime
    value: float
    labels: Optional[Dict[str, str]] = None


class MetricSeries(BaseModel):
    name: str
    service: str
    unit: str
    data_points: List[MetricDataPoint]
    current_value: Optional[float] = None
    anomaly_markers: Optional[List[datetime]] = None


class LogEntry(BaseModel):
    timestamp: datetime
    level: str
    message: str
    service: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    request_id: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


class TraceSpan(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    service: str
    operation: str
    start_time: datetime
    duration_ms: float
    status: str  # ok, error, timeout
    error_message: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None


class OverviewStats(BaseModel):
    total_incidents: int
    critical_incidents: int
    active_incidents: int
    resolved_incidents: int
    avg_detection_time_minutes: float
    avg_resolution_time_minutes: float
    system_health: str  # healthy, degraded, critical
    system_health_score: float  # 0-100
    monitoring_mode: str
    is_demo: bool


class DeploymentEventSchema(BaseModel):
    id: str
    service: str
    version: Optional[str] = None
    deployed_at: datetime
    deployed_by: Optional[str] = None
    description: Optional[str] = None
    is_demo: bool

    model_config = {"from_attributes": True}
