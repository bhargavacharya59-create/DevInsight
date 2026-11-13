"""
Incident management service.
Handles creation, deduplication, update, and retrieval.
"""
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Any, Tuple
import hashlib
import uuid
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload

from app.models.incident import (
    Incident, IncidentEvent, AnomalyEvent, RCAResult,
    RootCauseCandidate, Recommendation,
    SeverityLevel, IncidentStatus, RCAStatus,
)
from app.schemas.incident import IncidentCreate, IncidentUpdate

logger = logging.getLogger("devinsight.incidents")


class IncidentService:

    # ── Creation / Deduplication ───────────────────────────────────────────────

    @staticmethod
    def _make_fingerprint(service: str, title_keyword: str) -> str:
        """Create a deduplication fingerprint."""
        raw = f"{service}:{title_keyword}".lower()
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    async def create_or_update(
        self,
        db: AsyncSession,
        data: IncidentCreate,
        dedup_window_minutes: int = 60,
    ) -> Tuple["Incident", bool]:
        """
        Create a new incident or deduplicate against an existing open one.
        Returns (incident, is_new).
        """
        fp = data.fingerprint or self._make_fingerprint(
            data.affected_service or "", data.title[:50]
        )

        # Check for existing open incident with the same fingerprint
        window_start = datetime.now(UTC) - timedelta(minutes=dedup_window_minutes)
        stmt = (
            select(Incident)
            .where(
                and_(
                    Incident.fingerprint == fp,
                    Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.INVESTIGATING]),
                    Incident.detected_at >= window_start,
                )
            )
            .order_by(desc(Incident.detected_at))
            .limit(1)
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update anomaly score if higher
            if data.anomaly_score and (existing.anomaly_score is None or data.anomaly_score > existing.anomaly_score):
                existing.anomaly_score = data.anomaly_score
            existing.updated_at = datetime.now(UTC)
            db.add(existing)

            # Add a dedup event
            event = IncidentEvent(
                id=str(uuid.uuid4()),
                incident_id=existing.id,
                event_type="dedup_merge",
                description=f"Duplicate detection merged into existing incident (anomaly_score={data.anomaly_score:.3f})",
                event_metadata={"anomaly_score": data.anomaly_score},
            )
            db.add(event)
            await db.flush()
            logger.info("Deduplicated incident %s", existing.id)
            return existing, False

        # New incident
        incident = Incident(
            id=str(uuid.uuid4()),
            title=data.title,
            description=data.description,
            severity=data.severity,
            status=IncidentStatus.OPEN,
            affected_service=data.affected_service,
            detected_at=datetime.now(UTC),
            started_at=data.started_at,
            anomaly_score=data.anomaly_score,
            related_metrics=data.related_metrics,
            related_logs=data.related_logs,
            related_traces=data.related_traces,
            is_demo=data.is_demo,
            fingerprint=fp,
            rca_status=RCAStatus.PENDING,
        )
        db.add(incident)

        # Created event
        event = IncidentEvent(
            id=str(uuid.uuid4()),
            incident_id=incident.id,
            event_type="incident_created",
            description=f"Incident detected by anomaly detection engine (score={data.anomaly_score:.3f})" if data.anomaly_score else "Incident created",
            event_metadata={"severity": str(data.severity), "service": data.affected_service},
        )
        db.add(event)
        await db.flush()
        logger.info("Created new incident %s: %s", incident.id, incident.title)
        return incident, True

    async def get(self, db: AsyncSession, incident_id: str) -> Optional[Incident]:
        stmt = (
            select(Incident)
            .where(Incident.id == incident_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_incidents(
        self,
        db: AsyncSession,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        service: Optional[str] = None,
        is_demo: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[int, List[Incident]]:
        conditions = []
        if status:
            conditions.append(Incident.status == status)
        if severity:
            conditions.append(Incident.severity == severity)
        if service:
            conditions.append(Incident.affected_service == service)
        if is_demo is not None:
            conditions.append(Incident.is_demo == is_demo)
        if search:
            conditions.append(
                or_(
                    Incident.title.ilike(f"%{search}%"),
                    Incident.description.ilike(f"%{search}%"),
                    Incident.affected_service.ilike(f"%{search}%"),
                )
            )

        count_stmt = select(func.count(Incident.id))
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        list_stmt = (
            select(Incident)
            .options(
                selectinload(Incident.events),
                selectinload(Incident.rca_results).selectinload(RCAResult.root_cause_candidates),
                selectinload(Incident.recommendations),
            )
            .order_by(desc(Incident.detected_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        if conditions:
            list_stmt = list_stmt.where(and_(*conditions))

        list_result = await db.execute(list_stmt)
        incidents = list_result.scalars().all()
        return total, list(incidents)

    async def update(
        self,
        db: AsyncSession,
        incident: Incident,
        update: IncidentUpdate,
        actor: str = "system",
    ) -> Incident:
        event_type = "status_updated"
        desc_parts = []

        if update.status and update.status != incident.status:
            old_status = incident.status
            incident.status = update.status
            desc_parts.append(f"Status changed from {old_status} to {update.status}")
            if update.status == IncidentStatus.RESOLVED:
                incident.resolved_at = datetime.now(UTC)
                event_type = "incident_resolved"

        if update.severity:
            incident.severity = update.severity
            desc_parts.append(f"Severity set to {update.severity}")

        if update.probable_root_cause:
            incident.probable_root_cause = update.probable_root_cause

        if update.confidence_score is not None:
            incident.confidence_score = update.confidence_score

        if update.ai_explanation:
            incident.ai_explanation = update.ai_explanation

        incident.updated_at = datetime.now(UTC)
        db.add(incident)

        if desc_parts:
            event = IncidentEvent(
                id=str(uuid.uuid4()),
                incident_id=incident.id,
                event_type=event_type,
                description="; ".join(desc_parts),
                event_metadata={"actor": actor},
            )
            db.add(event)

        await db.flush()
        return incident

    async def acknowledge(self, db: AsyncSession, incident: Incident) -> Incident:
        incident.acknowledged = True
        incident.acknowledged_at = datetime.now(UTC)
        incident.status = IncidentStatus.INVESTIGATING
        incident.updated_at = datetime.now(UTC)
        db.add(incident)

        event = IncidentEvent(
            id=str(uuid.uuid4()),
            incident_id=incident.id,
            event_type="incident_acknowledged",
            description="Incident acknowledged and moved to Investigating status",
        )
        db.add(event)
        await db.flush()
        return incident

    async def resolve(self, db: AsyncSession, incident: Incident) -> Incident:
        incident.status = IncidentStatus.RESOLVED
        incident.resolved_at = datetime.now(UTC)
        incident.updated_at = datetime.now(UTC)
        db.add(incident)

        event = IncidentEvent(
            id=str(uuid.uuid4()),
            incident_id=incident.id,
            event_type="incident_resolved",
            description="Incident resolved",
        )
        db.add(event)
        await db.flush()
        return incident

    async def save_rca(
        self,
        db: AsyncSession,
        incident: Incident,
        rca_data: Dict[str, Any],
        ai_data: Optional[Dict[str, Any]] = None,
    ) -> RCAResult:
        """Persist RCA results for an incident."""
        rca = RCAResult(
            id=str(uuid.uuid4()),
            incident_id=incident.id,
            root_cause_summary=rca_data.get("root_cause_summary"),
            confidence=rca_data.get("confidence", 0.0),
            candidates=rca_data.get("candidates"),
            evidence_metrics=rca_data.get("evidence_metrics"),
            evidence_logs=rca_data.get("evidence_logs"),
            evidence_traces=rca_data.get("evidence_traces"),
            deployment_correlation=rca_data.get("deployment_correlation"),
            ai_explanation=ai_data.get("incident_explanation") if ai_data else None,
            ai_available=ai_data.get("ai_available", False) if ai_data else False,
        )
        db.add(rca)

        # Save individual candidates
        for candidate in rca_data.get("candidates", []):
            c = RootCauseCandidate(
                id=str(uuid.uuid4()),
                rca_result_id=rca.id,
                rank=candidate.get("rank", 1),
                title=candidate.get("title", ""),
                description=candidate.get("description"),
                confidence=candidate.get("confidence", 0.0),
                evidence=candidate.get("evidence"),
                reasoning=candidate.get("reasoning"),
                recommended_investigation=candidate.get("recommended_investigation"),
            )
            db.add(c)

        # Save recommendations from AI
        if ai_data:
            priority = 1
            for step in ai_data.get("remediation_steps", []):
                if step:
                    rec = Recommendation(
                        id=str(uuid.uuid4()),
                        incident_id=incident.id,
                        category="immediate",
                        action=step if isinstance(step, str) else str(step),
                        priority=priority,
                    )
                    db.add(rec)
                    priority += 1

            for step in ai_data.get("prevention", []):
                if step:
                    rec = Recommendation(
                        id=str(uuid.uuid4()),
                        incident_id=incident.id,
                        category="long_term",
                        action=step if isinstance(step, str) else str(step),
                        priority=priority,
                    )
                    db.add(rec)
                    priority += 1

        # Update incident with RCA summary
        incident.rca_status = RCAStatus.COMPLETED
        incident.probable_root_cause = rca_data.get("root_cause_summary")
        incident.confidence_score = rca_data.get("confidence", 0.0)
        if ai_data:
            incident.ai_explanation = ai_data.get("incident_explanation")
        incident.updated_at = datetime.now(UTC)
        db.add(incident)

        event = IncidentEvent(
            id=str(uuid.uuid4()),
            incident_id=incident.id,
            event_type="rca_completed",
            description=f"Root cause analysis completed (confidence={rca_data.get('confidence', 0):.1%})",
        )
        db.add(event)

        await db.flush()
        return rca

    async def get_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """Compute dashboard KPI statistics."""
        # Total counts by status
        stmt = select(Incident.status, func.count(Incident.id)).group_by(Incident.status)
        result = await db.execute(stmt)
        status_counts = dict(result.all())

        # Critical count
        crit_stmt = select(func.count(Incident.id)).where(Incident.severity == SeverityLevel.CRITICAL)
        crit_result = await db.execute(crit_stmt)
        critical_count = crit_result.scalar_one()

        # Average resolution time (resolved incidents with known resolved_at)
        res_stmt = select(Incident).where(
            and_(Incident.status == IncidentStatus.RESOLVED, Incident.resolved_at.isnot(None))
        ).limit(100)
        res_result = await db.execute(res_stmt)
        resolved = res_result.scalars().all()

        avg_resolution = 0.0
        if resolved:
            times = [
                (i.resolved_at - i.detected_at).total_seconds() / 60.0
                for i in resolved if i.resolved_at and i.detected_at
            ]
            avg_resolution = sum(times) / len(times) if times else 0.0

        total = sum(status_counts.values())
        active = status_counts.get(IncidentStatus.OPEN, 0) + status_counts.get(IncidentStatus.INVESTIGATING, 0)

        return {
            "total_incidents": total,
            "critical_incidents": critical_count,
            "active_incidents": active,
            "resolved_incidents": status_counts.get(IncidentStatus.RESOLVED, 0),
            "closed_incidents": status_counts.get(IncidentStatus.CLOSED, 0),
            "avg_resolution_time_minutes": round(avg_resolution, 1),
        }


_incident_service: Optional[IncidentService] = None


def get_incident_service() -> IncidentService:
    global _incident_service
    if _incident_service is None:
        _incident_service = IncidentService()
    return _incident_service


