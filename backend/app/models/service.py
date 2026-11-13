"""Service and telemetry source models."""
from datetime import datetime, UTC
from typing import Optional
import uuid
from sqlalchemy import String, Text, Float, Boolean, DateTime, JSON, Enum as SAEnum, Index
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.db.base import Base


class ServiceStatus(str, enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class Service(Base):
    __tablename__ = "services"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        SAEnum(ServiceStatus, native_enum=False), default=ServiceStatus.UNKNOWN, nullable=False
    )
    error_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    request_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dependencies: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # list of service names
    last_checked: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )


class TelemetrySource(Base):
    __tablename__ = "telemetry_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)  # prometheus, loki, otel
    url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    connected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_successful_connection: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )


class DeploymentEvent(Base):
    __tablename__ = "deployment_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    service: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    deployed_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False, index=True)
    deployed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class DemoScenario(Base):
    __tablename__ = "demo_scenarios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    duration_seconds: Mapped[int] = mapped_column(nullable=False, default=120)
    active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


