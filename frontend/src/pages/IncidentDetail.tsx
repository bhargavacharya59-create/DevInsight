import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft, AlertTriangle, CheckCircle2, Clock,
  Search, Zap, FlaskConical, ChevronDown, ChevronUp,
  ExternalLink, Play,
} from 'lucide-react';
import {
  getIncident, getIncidentRCA, runRCA,
  acknowledgeIncident, resolveIncident,
} from '../api/client';
import type { Incident, RCAResult } from '../types';
import SeverityBadge from '../components/ui/SeverityBadge';
import StatusBadge from '../components/ui/StatusBadge';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import ErrorState from '../components/ui/ErrorState';
import { formatDate, formatRelative, formatDuration, confidenceColor } from '../utils/format';
import clsx from 'clsx';

function TimelineEvent({ event }: { event: { event_type: string; description: string; created_at: string } }) {
  const iconMap: Record<string, JSX.Element> = {
    incident_created: <Zap size={12} className="text-yellow-400" />,
    incident_acknowledged: <CheckCircle2 size={12} className="text-blue-400" />,
    rca_completed: <Search size={12} className="text-brand-400" />,
    incident_resolved: <CheckCircle2 size={12} className="text-emerald-400" />,
    status_updated: <Clock size={12} className="text-slate-400" />,
    dedup_merge: <AlertTriangle size={12} className="text-purple-400" />,
  };
  return (
    <div className="flex gap-3">
      <div className="flex flex-col items-center">
        <div className="w-6 h-6 rounded-full bg-surface-700 border border-slate-600/50 flex items-center justify-center shrink-0">
          {iconMap[event.event_type] || <Clock size={12} className="text-slate-400" />}
        </div>
        <div className="w-px bg-slate-700/50 flex-1 mt-1" />
      </div>
      <div className="pb-4 flex-1 min-w-0">
        <p className="text-sm text-slate-200">{event.description}</p>
        <p className="text-xs text-slate-500 mt-0.5">{formatDate(event.created_at)}</p>
      </div>
    </div>
  );
}

export default function IncidentDetail() {
  const { id } = useParams<{ id: string }>();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [rca, setRca] = useState<Record<string, unknown> | null>(null);

  // Typed accessors for RCA data
  const rcaCandidates = (rca?.candidates as Array<{rank: number; title: string; confidence: number; description?: string; reasoning?: string}> | undefined) ?? [];
  const aiExplanation = rca?.ai_explanation as string | undefined;
  const aiInvestigationSteps = (rca?.ai_investigation_steps as string[] | undefined) ?? [];
  const aiRemediationSteps = (rca?.ai_remediation_steps as string[] | undefined) ?? [];
  const evidenceMetrics = (rca?.evidence_metrics as Array<{description: string; change_pct: number}> | undefined) ?? [];
  const evidenceLogs = (rca?.evidence_logs as Array<{description: string; count?: number}> | undefined) ?? [];
  const [loading, setLoading] = useState(true);
  const [rcaLoading, setRcaLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showEvidence, setShowEvidence] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const loadIncident = () => {
    if (!id) return;
    setLoading(true);
    getIncident(id)
      .then(d => { setIncident(d); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  };

  const loadRca = () => {
    if (!id) return;
    getIncidentRCA(id).then(d => setRca(d)).catch(() => null);
  };

  const handleRunRCA = async () => {
    if (!id) return;
    setRcaLoading(true);
    try {
      const result = await runRCA({ incident_id: id, include_demo_evidence: true });
      setRca(result);
      loadIncident(); // refresh incident status
    } catch (e: unknown) {
      console.error(e);
    } finally {
      setRcaLoading(false);
    }
  };

  const handleAck = async () => {
    if (!id || actionLoading) return;
    setActionLoading(true);
    await acknowledgeIncident(id).catch(() => null);
    loadIncident();
    setActionLoading(false);
  };

  const handleResolve = async () => {
    if (!id || actionLoading) return;
    setActionLoading(true);
    await resolveIncident(id).catch(() => null);
    loadIncident();
    setActionLoading(false);
  };

  useEffect(() => { loadIncident(); loadRca(); }, [id]);

  if (loading) return <LoadingSpinner size="lg" className="h-full" />;
  if (error || !incident) return <ErrorState message={error || 'Incident not found'} onRetry={loadIncident} />;

  const candidates = rcaCandidates;
  const aiAvailable = rca?.ai_available as boolean;

  return (
    <div className="p-6 space-y-5 max-w-6xl mx-auto">
      {/* Back */}
      <Link to="/incidents" className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-slate-200 transition-colors">
        <ArrowLeft size={14} /> Back to Incidents
      </Link>

      {/* Header */}
      <div className="card p-6">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <SeverityBadge severity={incident.severity} />
              <StatusBadge status={incident.status} />
              {incident.is_demo && (
                <span className="demo-badge"><FlaskConical size={10} /> demo</span>
              )}
            </div>
            <h1 className="text-xl font-semibold text-white leading-tight">{incident.title}</h1>
            {incident.description && (
              <p className="text-sm text-slate-400 mt-2">{incident.description}</p>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {incident.status === 'open' && !incident.acknowledged && (
              <button onClick={handleAck} disabled={actionLoading} className="btn-secondary">
                <CheckCircle2 size={14} /> Acknowledge
              </button>
            )}
            {(incident.status === 'open' || incident.status === 'investigating') && (
              <button onClick={handleResolve} disabled={actionLoading} className="btn-primary">
                <CheckCircle2 size={14} /> Resolve
              </button>
            )}
          </div>
        </div>

        {/* Meta grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-5 pt-5 border-t border-slate-700/50">
          <div>
            <p className="text-xs text-slate-500 mb-0.5">Affected Service</p>
            <p className="text-sm text-slate-200 font-mono">{incident.affected_service || '–'}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500 mb-0.5">Detected</p>
            <p className="text-sm text-slate-200">{formatRelative(incident.detected_at)}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500 mb-0.5">Duration</p>
            <p className="text-sm text-slate-200">{formatDuration(incident.detected_at, incident.resolved_at)}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500 mb-0.5">Anomaly Score</p>
            <p className={clsx('text-sm font-mono font-semibold',
              incident.anomaly_score && incident.anomaly_score > 0.7 ? 'text-red-400' :
              incident.anomaly_score && incident.anomaly_score > 0.4 ? 'text-orange-400' : 'text-yellow-400'
            )}>
              {incident.anomaly_score?.toFixed(3) || '–'}
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Main content */}
        <div className="lg:col-span-2 space-y-5">
          {/* RCA Section */}
          <div className="card p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-slate-200 flex items-center gap-2">
                <Search size={16} className="text-brand-400" />
                <span>Root Cause Analysis</span>
              </h2>
              {incident.rca_status !== 'completed' && (
                <button
                  onClick={handleRunRCA}
                  disabled={rcaLoading}
                  className="btn-primary text-xs"
                >
                  {rcaLoading ? (
                    <><LoadingSpinner size="sm" /><span>Running...</span></>
                  ) : (
                    <><Play size={12} /> Run RCA</>
                  )}
                </button>
              )}
            </div>

            {incident.probable_root_cause && (
              <div className="p-3 bg-brand-900/20 border border-brand-700/30 rounded-lg mb-4">
                <p className="text-xs text-brand-400 mb-1 font-medium">Probable Root Cause</p>
                <p className="text-sm text-slate-200">{incident.probable_root_cause}</p>
                {incident.confidence_score && (
                  <p className={clsx('text-xs mt-1 font-medium', confidenceColor(incident.confidence_score))}>
                    {(incident.confidence_score * 100).toFixed(0)}% confidence
                  </p>
                )}
              </div>
            )}

            {candidates.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs text-slate-400 mb-2">Ranked Candidates</p>
                {candidates.map((c, i) => (
                  <div key={i} className="p-3 bg-surface-700 rounded-lg border border-slate-700/30">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-start gap-2 flex-1 min-w-0">
                        <span className="text-xs text-slate-500 font-mono mt-0.5">#{c.rank}</span>
                        <div>
                          <p className="text-sm font-medium text-slate-200">{c.title}</p>
                          {c.description && <p className="text-xs text-slate-500 mt-0.5">{c.description}</p>}
                        </div>
                      </div>
                      <span className={clsx('text-xs font-semibold shrink-0', confidenceColor(c.confidence))}>
                        {(c.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {!rca && incident.rca_status === 'pending' && (
              <p className="text-sm text-slate-500 text-center py-4">
                Click "Run RCA" to start the investigation engine.
              </p>
            )}
          </div>

          {/* AI Explanation */}
          {(incident.ai_explanation || aiExplanation) && (
            <div className="card p-5">
              <div className="flex items-center gap-2 mb-4">
                <Zap size={16} className="text-yellow-400" />
                <h2 className="font-semibold text-slate-200">AI Explanation</h2>
                {!aiAvailable && (
                  <span className="text-xs text-slate-500 bg-surface-700 px-2 py-0.5 rounded">fallback</span>
                )}
              </div>
              <p className="text-sm text-slate-300 leading-relaxed">
                {(rca?.ai_explanation as string) || incident.ai_explanation}
              </p>

              {rca && (rca.ai_investigation_steps as string[] || []).length > 0 && (
                <div className="mt-4">
                  <p className="text-xs font-medium text-slate-400 mb-2">Investigation Steps</p>
                  <ol className="space-y-1">
                    {(rca.ai_investigation_steps as string[]).map((step, i) => (
                      <li key={i} className="flex gap-2 text-sm text-slate-300">
                        <span className="text-brand-400 font-mono shrink-0">{i + 1}.</span>
                        {step}
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              {rca && (rca.ai_remediation_steps as string[] || []).length > 0 && (
                <div className="mt-4">
                  <p className="text-xs font-medium text-slate-400 mb-2">Remediation Steps</p>
                  <ol className="space-y-1">
                    {(rca.ai_remediation_steps as string[]).map((step, i) => (
                      <li key={i} className="flex gap-2 text-sm text-slate-300">
                        <span className="text-emerald-400 font-mono shrink-0">{i + 1}.</span>
                        {step}
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </div>
          )}

          {/* Evidence */}
          {rca && (
            <div className="card p-5">
              <button
                onClick={() => setShowEvidence(v => !v)}
                className="flex items-center justify-between w-full"
              >
                <h2 className="font-semibold text-slate-200">Evidence Details</h2>
                {showEvidence ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </button>

              {showEvidence && (
                <div className="mt-4 space-y-4">
                  {(rca.evidence_metrics as unknown[] || []).length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-slate-400 mb-2">Metric Signals</p>
                      {(rca.evidence_metrics as Array<{description: string; change_pct: number}>).map((m, i) => (
                        <div key={i} className="flex items-center gap-2 py-1.5 border-b border-slate-700/20">
                          <span className="w-1.5 h-1.5 rounded-full bg-brand-400 shrink-0" />
                          <span className="text-xs text-slate-300">{m.description}</span>
                          {m.change_pct > 0 && (
                            <span className="text-xs text-red-400 ml-auto">+{m.change_pct.toFixed(0)}%</span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {(rca.evidence_logs as unknown[] || []).length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-slate-400 mb-2">Log Patterns</p>
                      {(rca.evidence_logs as Array<{description: string; count?: number}>).map((l, i) => (
                        <div key={i} className="flex items-center gap-2 py-1.5 border-b border-slate-700/20">
                          <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 shrink-0" />
                          <span className="text-xs text-slate-300">{l.description}</span>
                          {l.count && <span className="text-xs text-slate-500 ml-auto">×{l.count}</span>}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Sidebar: Timeline + Recommendations */}
        <div className="space-y-5">
          <div className="card p-5">
            <h3 className="font-semibold text-slate-200 mb-4">Timeline</h3>
            <div>
              {(incident.events || []).map(ev => (
                <TimelineEvent key={ev.id} event={ev} />
              ))}
              {!incident.events?.length && (
                <p className="text-sm text-slate-500">No events recorded.</p>
              )}
            </div>
          </div>

          {(incident.recommendations || []).length > 0 && (
            <div className="card p-5">
              <h3 className="font-semibold text-slate-200 mb-4">Recommendations</h3>
              <div className="space-y-2">
                {incident.recommendations!.map((rec, i) => (
                  <div key={i} className="flex gap-2 text-sm">
                    <span className={clsx('shrink-0 text-xs px-1.5 py-0.5 rounded mt-0.5',
                      rec.category === 'immediate' ? 'bg-red-900/30 text-red-400' : 'bg-blue-900/30 text-blue-400'
                    )}>
                      {rec.category}
                    </span>
                    <span className="text-slate-300">{rec.action}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
