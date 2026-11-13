"""Incident and related ORM models."""
from datetime import datetime, UTC
from typing import Optional, List
import uuid
from sqlalchemy import (
    String, Text, Float, Integer, Boolean, DateTime,
    ForeignKey, JSON, Enum as SAEnum, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.base import Base


class SeverityLevel(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IncidentStatus(str, enum.Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


class RCAStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    INSUFFICIENT_DATA = "insufficient_data"


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(
        SAEnum(SeverityLevel, native_enum=False), nullable=False, default=SeverityLevel.MEDIUM
    )
    status: Mapped[str] = mapped_column(
        SAEnum(IncidentStatus, native_enum=False), nullable=False, default=IncidentStatus.OPEN
    )
    affected_service: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )
    anomaly_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rca_status: Mapped[str] = mapped_column(
        SAEnum(RCAStatus, native_enum=False), default=RCAStatus.PENDING, nullable=False
    )
    probable_root_cause: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    related_metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    related_logs: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    related_traces: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Deduplication fingerprint
    fingerprint: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    events: Mapped[List["IncidentEvent"]] = relationship(
        "IncidentEvent", back_populates="incident", cascade="all, delete-orphan"
    )
    rca_results: Mapped[List["RCAResult"]] = relationship(
        "RCAResult", back_populates="incident", cascade="all, delete-orphan"
    )
    recommendations: Mapped[List["Recommendation"]] = relationship(
        "Recommendation", back_populates="incident", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_incidents_severity", "severity"),
        Index("ix_incidents_status", "status"),
        Index("ix_incidents_detected_at", "detected_at"),
        Index("ix_incidents_affected_service", "affected_service"),
        Index("ix_incidents_is_demo", "is_demo"),
    )


class IncidentEvent(Base):
    __tablename__ = "incident_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id: Mapped[str] = mapped_column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    event_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="events")

    __table_args__ = (Index("ix_incident_events_incident_id", "incident_id"),)


class AnomalyEvent(Base):
    __tablename__ = "anomaly_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False, index=True)
    service: Mapped[str] = mapped_column(String(255), nullable=False)
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=False)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    features: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    incident_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("incidents.id"), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class RCAResult(Base):
    __tablename__ = "rca_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id: Mapped[str] = mapped_column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    root_cause_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    candidates: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # ranked list
    evidence_metrics: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    evidence_logs: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    evidence_traces: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    deployment_correlation: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ai_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="rca_results")
    root_cause_candidates: Mapped[List["RootCauseCandidate"]] = relationship(
        "RootCauseCandidate", back_populates="rca_result", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_rca_results_incident_id", "incident_id"),)


class RootCauseCandidate(Base):
    __tablename__ = "root_cause_candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    rca_result_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("rca_results.id", ondelete="CASCADE"), nullable=False
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommended_investigation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    rca_result: Mapped["RCAResult"] = relationship("RCAResult", back_populates="root_cause_candidates")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id: Mapped[str] = mapped_column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)  # immediate, short_term, long_term
    action: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    incident: Mapped["Incident"] = relationship("Incident", back_populates="recommendations")


