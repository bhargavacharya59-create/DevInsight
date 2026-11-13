"""
Root Cause Analysis engine.
Uses deterministic evidence-based scoring — NOT Gemini.
Gemini provides explanation on top of the RCA results.
"""
from datetime import datetime, UTC, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging

logger = logging.getLogger("devinsight.rca")


# ── Evidence types ────────────────────────────────────────────────────────────

class Evidence:
    def __init__(self, kind: str, description: str, weight: float, source: str):
        self.kind = kind          # metric, log, trace, deployment
        self.description = description
        self.weight = weight      # 0.0 – 1.0
        self.source = source

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "description": self.description,
            "weight": self.weight,
            "source": self.source,
        }


class RCACandidate:
    def __init__(self, title: str, description: str, base_score: float):
        self.title = title
        self.description = description
        self.score = base_score
        self.evidence: List[Evidence] = []
        self.reasoning: str = ""
        self.recommended_investigation: str = ""

    def add_evidence(self, ev: Evidence) -> None:
        self.evidence.append(ev)
        self.score += ev.weight

    @property
    def confidence(self) -> float:
        """Clamp score to [0, 1]."""
        return min(1.0, max(0.0, self.score))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "confidence": round(self.confidence, 3),
            "evidence": [e.to_dict() for e in self.evidence],
            "reasoning": self.reasoning,
            "recommended_investigation": self.recommended_investigation,
        }


# ── RCA Engine ────────────────────────────────────────────────────────────────

class RCAEngine:
    """
    Evidence-based root cause analysis engine.

    Algorithm:
    1. Build candidate hypotheses.
    2. For each candidate, search for supporting/contradicting evidence in
       metrics, logs, traces, and deployment events.
    3. Score each candidate.
    4. Rank and return.
    """

    MIN_CONFIDENCE_TO_REPORT = 0.25

    def investigate(
        self,
        incident: Dict[str, Any],
        metrics: Optional[List[Dict[str, Any]]] = None,
        logs: Optional[List[Dict[str, Any]]] = None,
        traces: Optional[List[Dict[str, Any]]] = None,
        deployments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Run RCA investigation for an incident.
        Returns ranked root cause candidates with evidence.
        """
        metrics = metrics or []
        logs = logs or []
        traces = traces or []
        deployments = deployments or []

        logger.info("Starting RCA for incident %s", incident.get("id", "unknown"))

        # ── Step 1: Analyze metric signals ────────────────────────────────────
        metric_signals = self._analyze_metrics(metrics)

        # ── Step 2: Analyze log patterns ──────────────────────────────────────
        log_patterns = self._analyze_logs(logs)

        # ── Step 3: Analyze trace patterns ────────────────────────────────────
        trace_signals = self._analyze_traces(traces)

        # ── Step 4: Check deployment correlation ──────────────────────────────
        deployment_corr = self._analyze_deployments(
            deployments, incident.get("detected_at")
        )

        # ── Step 5: Build candidates ───────────────────────────────────────────
        candidates = self._build_candidates(
            incident, metric_signals, log_patterns, trace_signals, deployment_corr
        )

        # ── Step 6: Filter and rank ────────────────────────────────────────────
        valid = [c for c in candidates if c.confidence >= self.MIN_CONFIDENCE_TO_REPORT]
        valid.sort(key=lambda c: c.confidence, reverse=True)

        if not valid:
            summary = "Root cause could not be determined confidently. Insufficient evidence collected."
            top_confidence = 0.0
        else:
            top = valid[0]
            summary = top.title
            top_confidence = top.confidence

        ranked = [
            {**c.to_dict(), "rank": i + 1}
            for i, c in enumerate(valid[:5])
        ]

        return {
            "root_cause_summary": summary,
            "confidence": top_confidence,
            "candidates": ranked,
            "evidence_metrics": metric_signals,
            "evidence_logs": log_patterns,
            "evidence_traces": trace_signals,
            "deployment_correlation": deployment_corr,
            "investigation_timestamp": datetime.now(UTC).isoformat(),
        }

    # ── Metric analysis ───────────────────────────────────────────────────────

    def _analyze_metrics(self, metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        signals = []
        for m in metrics:
            name = m.get("name", "")
            current = m.get("current_value", 0.0) or 0.0
            baseline = m.get("baseline_value", 0.0) or 0.0
            service = m.get("service", "unknown")

            if baseline <= 0:
                continue

            change_pct = ((current - baseline) / baseline) * 100.0

            if name == "error_rate" and change_pct > 50:
                signals.append({
                    "type": "error_rate_spike",
                    "service": service,
                    "metric": name,
                    "current": current,
                    "baseline": baseline,
                    "change_pct": round(change_pct, 1),
                    "severity": "high" if change_pct > 200 else "medium",
                    "description": f"Error rate on {service} increased {change_pct:.0f}% above baseline",
                })
            elif name == "latency_ms" and change_pct > 50:
                signals.append({
                    "type": "latency_increase",
                    "service": service,
                    "metric": name,
                    "current": current,
                    "baseline": baseline,
                    "change_pct": round(change_pct, 1),
                    "severity": "high" if change_pct > 150 else "medium",
                    "description": f"Response latency on {service} increased {change_pct:.0f}% above baseline",
                })
            elif name == "cpu_utilization" and current > 80:
                signals.append({
                    "type": "cpu_spike",
                    "service": service,
                    "metric": name,
                    "current": current,
                    "baseline": baseline,
                    "change_pct": round(change_pct, 1),
                    "severity": "high" if current > 90 else "medium",
                    "description": f"CPU utilization on {service} at {current:.1f}%",
                })
            elif name == "memory_utilization" and current > 80:
                signals.append({
                    "type": "memory_spike",
                    "service": service,
                    "metric": name,
                    "current": current,
                    "baseline": baseline,
                    "change_pct": round(change_pct, 1),
                    "severity": "high" if current > 90 else "medium",
                    "description": f"Memory utilization on {service} at {current:.1f}%",
                })
            elif name == "db_query_latency" and change_pct > 100:
                signals.append({
                    "type": "db_latency_spike",
                    "service": service,
                    "metric": name,
                    "current": current,
                    "baseline": baseline,
                    "change_pct": round(change_pct, 1),
                    "severity": "high",
                    "description": f"Database query latency increased {change_pct:.0f}% on {service}",
                })

        return signals

    # ── Log analysis ──────────────────────────────────────────────────────────

    def _analyze_logs(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        patterns = []
        error_counts: Dict[str, int] = {}
        pattern_map: Dict[str, Dict] = {}

        error_keywords = {
            "connection timeout": ("db_connection_issue", 0.4),
            "pool exhausted": ("db_connection_issue", 0.5),
            "nullpointerexception": ("code_error", 0.4),
            "outofmemoryerror": ("memory_leak", 0.5),
            "circuit breaker": ("cascading_failure", 0.45),
            "502 bad gateway": ("upstream_failure", 0.35),
            "503 service unavailable": ("service_down", 0.4),
            "500 internal server error": ("code_error", 0.35),
            "heap space": ("memory_leak", 0.45),
            "cpu throttling": ("cpu_issue", 0.4),
            "deployment": ("deployment_issue", 0.3),
            "exception": ("code_error", 0.25),
            "timeout": ("latency_issue", 0.3),
        }

        for log in logs:
            msg = (log.get("message") or "").lower()
            svc = log.get("service", "unknown")
            level = (log.get("level") or "INFO").upper()

            if level in ("ERROR", "CRITICAL", "FATAL"):
                error_counts[svc] = error_counts.get(svc, 0) + 1

                for keyword, (pattern_type, weight) in error_keywords.items():
                    if keyword in msg:
                        key = f"{svc}:{pattern_type}"
                        if key not in pattern_map:
                            pattern_map[key] = {
                                "type": pattern_type,
                                "service": svc,
                                "count": 0,
                                "weight": weight,
                                "sample_message": log.get("message", ""),
                                "description": f"Pattern '{keyword}' detected in {svc} logs",
                            }
                        pattern_map[key]["count"] += 1

        patterns = list(pattern_map.values())

        # Add error count summaries
        for svc, count in error_counts.items():
            if count > 5:
                patterns.append({
                    "type": "elevated_error_count",
                    "service": svc,
                    "count": count,
                    "weight": min(0.4, count * 0.03),
                    "description": f"{count} error-level log entries in {svc}",
                })

        return sorted(patterns, key=lambda p: p.get("weight", 0), reverse=True)

    # ── Trace analysis ────────────────────────────────────────────────────────

    def _analyze_traces(self, traces: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        signals = []
        error_by_service: Dict[str, int] = {}
        slow_by_service: Dict[str, List[float]] = {}
        total_by_service: Dict[str, int] = {}

        SLOW_THRESHOLD_MS = 500.0

        for trace in traces:
            spans = []
            if "root_span" in trace:
                spans.append(trace["root_span"])
                spans.extend(trace.get("child_spans", []))
            elif isinstance(trace, dict) and "span_id" in trace:
                spans.append(trace)

            for span in spans:
                svc = span.get("service", "unknown")
                duration = span.get("duration_ms", 0.0)
                status = span.get("status", "ok")

                total_by_service[svc] = total_by_service.get(svc, 0) + 1

                if status == "error":
                    error_by_service[svc] = error_by_service.get(svc, 0) + 1

                if duration > SLOW_THRESHOLD_MS:
                    if svc not in slow_by_service:
                        slow_by_service[svc] = []
                    slow_by_service[svc].append(duration)

        for svc, error_count in error_by_service.items():
            total = total_by_service.get(svc, 1)
            error_rate = error_count / total
            if error_rate > 0.1:
                signals.append({
                    "type": "trace_error_rate",
                    "service": svc,
                    "error_count": error_count,
                    "total_spans": total,
                    "error_rate": round(error_rate, 3),
                    "description": f"High trace error rate in {svc}: {error_count}/{total} spans failed",
                })

        for svc, durations in slow_by_service.items():
            avg = sum(durations) / len(durations)
            signals.append({
                "type": "slow_spans",
                "service": svc,
                "slow_span_count": len(durations),
                "avg_duration_ms": round(avg, 1),
                "max_duration_ms": round(max(durations), 1),
                "description": f"{len(durations)} slow spans in {svc}, avg {avg:.0f}ms",
            })

        return sorted(signals, key=lambda s: s.get("error_rate", 0), reverse=True)

    # ── Deployment analysis ───────────────────────────────────────────────────

    def _analyze_deployments(
        self,
        deployments: List[Dict[str, Any]],
        incident_time: Optional[str],
    ) -> Dict[str, Any]:
        if not deployments or not incident_time:
            return {"correlated": False, "deployments": []}

        try:
            if isinstance(incident_time, str):
                inc_dt = datetime.fromisoformat(incident_time.replace("Z", ""))
            else:
                inc_dt = incident_time
        except Exception:
            return {"correlated": False, "deployments": []}

        correlated = []
        for dep in deployments:
            try:
                dep_time_str = dep.get("deployed_at", "")
                if isinstance(dep_time_str, str):
                    dep_dt = datetime.fromisoformat(dep_time_str.replace("Z", ""))
                else:
                    dep_dt = dep_time_str
                delta_minutes = (inc_dt - dep_dt).total_seconds() / 60.0
                if 0 <= delta_minutes <= 60:
                    correlated.append({
                        **dep,
                        "minutes_before_incident": round(delta_minutes, 1),
                        "strong_correlation": delta_minutes <= 15,
                    })
            except Exception:
                continue

        return {
            "correlated": len(correlated) > 0,
            "deployments": sorted(correlated, key=lambda d: d["minutes_before_incident"]),
        }

    # ── Candidate builder ─────────────────────────────────────────────────────

    def _build_candidates(
        self,
        incident: Dict[str, Any],
        metric_signals: List[Dict[str, Any]],
        log_patterns: List[Dict[str, Any]],
        trace_signals: List[Dict[str, Any]],
        deployment_corr: Dict[str, Any],
    ) -> List[RCACandidate]:

        affected_svc = incident.get("affected_service", "")
        candidates: List[RCACandidate] = []

        # ── Candidate: Deployment regression ──────────────────────────────────
        if deployment_corr.get("correlated"):
            dep_candidate = RCACandidate(
                title="Deployment Regression",
                description="A recent deployment preceded the incident, suggesting a code or configuration change introduced the issue.",
                base_score=0.3,
            )
            for dep in deployment_corr["deployments"]:
                w = 0.4 if dep.get("strong_correlation") else 0.2
                dep_candidate.add_evidence(Evidence(
                    kind="deployment",
                    description=f"Deployment of {dep.get('service', 'unknown')} {dep.get('version', '')} "
                                f"{dep['minutes_before_incident']:.0f} minutes before incident",
                    weight=w,
                    source="deployment_events",
                ))
            dep_candidate.reasoning = (
                "The temporal proximity of a deployment to the incident onset is a strong indicator of "
                "deployment-related regression. The pattern of immediate post-deployment metric degradation "
                "further supports this hypothesis."
            )
            dep_candidate.recommended_investigation = (
                "1. Review the diff of the deployment that preceded the incident.\n"
                "2. Check for changes to the affected endpoint or service logic.\n"
                "3. Consider rolling back to the previous version as a mitigation step.\n"
                "4. Verify whether rolling back resolves the anomaly."
            )
            candidates.append(dep_candidate)

        # ── Candidate: Database issues ─────────────────────────────────────────
        db_metric_signals = [s for s in metric_signals if s["type"] in ("db_latency_spike", "db_connection_issue")]
        db_log_patterns = [p for p in log_patterns if p["type"] in ("db_connection_issue",)]
        db_traces = [t for t in trace_signals if "database" in t.get("service", "")]

        db_score = sum(s.get("weight", 0.1) for s in db_metric_signals) + \
                   sum(p.get("weight", 0.1) for p in db_log_patterns) + \
                   (0.2 if db_traces else 0)

        if db_metric_signals or db_log_patterns or db_traces:
            db_candidate = RCACandidate(
                title="Database Performance Degradation",
                description="Database latency spike or connection pool exhaustion causing cascading failures across dependent services.",
                base_score=max(0.2, db_score),
            )
            for s in db_metric_signals:
                db_candidate.add_evidence(Evidence(
                    kind="metric",
                    description=s["description"],
                    weight=0.3,
                    source="prometheus",
                ))
            for p in db_log_patterns:
                db_candidate.add_evidence(Evidence(
                    kind="log",
                    description=p["description"],
                    weight=p.get("weight", 0.2),
                    source="loki",
                ))
            db_candidate.reasoning = (
                "Database metric degradation combined with log evidence of connection or query issues "
                "strongly suggests a database root cause. Cascading latency in dependent services "
                "(Order, Payment) is consistent with upstream database starvation."
            )
            db_candidate.recommended_investigation = (
                "1. Check current database connection pool utilization.\n"
                "2. Review slow query log for queries executing during the incident window.\n"
                "3. Verify index health on high-traffic tables.\n"
                "4. Check for lock contention or deadlocks in the database error log."
            )
            candidates.append(db_candidate)

        # ── Candidate: Application code error ─────────────────────────────────
        code_signals = [s for s in metric_signals if s["type"] == "error_rate_spike"]
        code_logs = [p for p in log_patterns if p["type"] in ("code_error",)]
        code_traces = [t for t in trace_signals if t.get("type") == "trace_error_rate"]

        if code_signals or code_logs or code_traces:
            code_candidate = RCACandidate(
                title="Application Code Error / Unhandled Exception",
                description="Elevated error rate and log evidence of unhandled exceptions suggest a code-level bug in the affected service.",
                base_score=0.15,
            )
            for s in code_signals:
                code_candidate.add_evidence(Evidence(
                    kind="metric",
                    description=s["description"],
                    weight=0.25,
                    source="prometheus",
                ))
            for p in code_logs:
                code_candidate.add_evidence(Evidence(
                    kind="log",
                    description=p["description"],
                    weight=p.get("weight", 0.2),
                    source="loki",
                ))
            for t in code_traces:
                code_candidate.add_evidence(Evidence(
                    kind="trace",
                    description=t["description"],
                    weight=0.2,
                    source="opentelemetry",
                ))
            code_candidate.reasoning = (
                "High error rates and exception log patterns indicate application-level failures. "
                "The pattern is consistent with an unhandled edge case or a regression introduced by recent code changes."
            )
            code_candidate.recommended_investigation = (
                "1. Review application error logs for stack traces during the incident window.\n"
                "2. Identify the specific endpoint or function generating the exceptions.\n"
                "3. Check recent code changes to the affected service.\n"
                "4. Review unit and integration test coverage for the affected code path."
            )
            candidates.append(code_candidate)

        # ── Candidate: Infrastructure (CPU/Memory) ─────────────────────────────
        infra_signals = [s for s in metric_signals if s["type"] in ("cpu_spike", "memory_spike")]
        infra_logs = [p for p in log_patterns if p["type"] in ("memory_leak", "cpu_issue")]

        if infra_signals or infra_logs:
            if any(s["type"] == "memory_spike" for s in infra_signals) or \
               any(p["type"] == "memory_leak" for p in infra_logs):
                title = "Memory Leak / Memory Pressure"
                desc = "Memory utilization increasing towards system limits, consistent with a memory leak or insufficient heap allocation."
            else:
                title = "CPU Saturation"
                desc = "CPU utilization spike causing request queuing and increased response latency."

            infra_candidate = RCACandidate(title=title, description=desc, base_score=0.15)
            for s in infra_signals:
                infra_candidate.add_evidence(Evidence(
                    kind="metric",
                    description=s["description"],
                    weight=0.25,
                    source="prometheus",
                ))
            for p in infra_logs:
                infra_candidate.add_evidence(Evidence(
                    kind="log",
                    description=p["description"],
                    weight=p.get("weight", 0.2),
                    source="loki",
                ))
            infra_candidate.reasoning = (
                "Infrastructure resource saturation (CPU or memory) can cause service-level degradation "
                "through request queuing and increased GC pressure."
            )
            infra_candidate.recommended_investigation = (
                "1. Check host-level CPU and memory metrics for the affected service.\n"
                "2. Identify any background jobs, batch processes, or traffic spikes coinciding with the incident.\n"
                "3. Profile the application for memory allocation patterns.\n"
                "4. Consider horizontal scaling or vertical resource increase as a short-term mitigation."
            )
            candidates.append(infra_candidate)

        # ── Candidate: Upstream/downstream dependency failure ──────────────────
        cascade_logs = [p for p in log_patterns if p["type"] in ("cascading_failure", "upstream_failure", "service_down")]
        if cascade_logs:
            cascade_candidate = RCACandidate(
                title="Cascading Dependency Failure",
                description="A downstream or upstream service failure is propagating errors to the affected service.",
                base_score=0.1,
            )
            for p in cascade_logs:
                cascade_candidate.add_evidence(Evidence(
                    kind="log",
                    description=p["description"],
                    weight=p.get("weight", 0.2),
                    source="loki",
                ))
            cascade_candidate.reasoning = (
                "Circuit breaker activations and 502/503 responses indicate a dependency failure "
                "propagating through the service mesh."
            )
            cascade_candidate.recommended_investigation = (
                "1. Check the health of all dependencies of the affected service.\n"
                "2. Review circuit breaker state and trip history.\n"
                "3. Verify network connectivity and DNS resolution between services.\n"
                "4. Check external third-party service status pages."
            )
            candidates.append(cascade_candidate)

        return candidates


# ── Singleton ─────────────────────────────────────────────────────────────────

_rca_engine: Optional[RCAEngine] = None


def get_rca_engine() -> RCAEngine:
    global _rca_engine
    if _rca_engine is None:
        _rca_engine = RCAEngine()
    return _rca_engine


