import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getIncidents } from '../api/client';
import type { Incident } from '../types';
import { Search, ChevronRight, FlaskConical, AlertTriangle } from 'lucide-react';
import SeverityBadge from '../components/ui/SeverityBadge';
import StatusBadge from '../components/ui/StatusBadge';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { formatRelative, confidenceColor } from '../utils/format';
import clsx from 'clsx';

export default function RCAPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getIncidents({ page_size: 50 })
      .then(d => setIncidents(d.incidents))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LoadingSpinner size="lg" className="h-full" />;

  const withRCA = incidents.filter(i => i.rca_status === 'completed');
  const pending = incidents.filter(i => i.rca_status !== 'completed');

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-xl font-semibold text-white">Root Cause Analysis</h1>
        <p className="text-sm text-slate-400 mt-0.5">
          Investigation flow: Telemetry → Anomaly Detection → Incident → Evidence Correlation → Root Cause → AI Explanation → Recommendations
        </p>
      </div>

      {/* Investigation flow visual */}
      <div className="card p-5">
        <div className="flex items-center gap-1 flex-wrap">
          {[
            'Telemetry', 'Anomaly Detection', 'Incident', 'Evidence Correlation',
            'Root Cause', 'AI Explanation', 'Recommendations',
          ].map((step, i, arr) => (
            <div key={step} className="flex items-center gap-1">
              <div className="px-3 py-1.5 bg-surface-700 rounded-full text-xs text-slate-300 border border-slate-700/50">
                {step}
              </div>
              {i < arr.length - 1 && <ChevronRight size={14} className="text-slate-600 shrink-0" />}
            </div>
          ))}
        </div>
      </div>

      {/* Completed RCAs */}
      <div>
        <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-3">
          Completed Investigations ({withRCA.length})
        </h2>
        {withRCA.length === 0 ? (
          <div className="card p-8 text-center text-slate-500">No completed RCA investigations yet</div>
        ) : (
          <div className="space-y-3">
            {withRCA.map(inc => (
              <Link key={inc.id} to={`/incidents/${inc.id}`} className="card-hover p-4 block">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <SeverityBadge severity={inc.severity} />
                      <StatusBadge status={inc.status} />
                      {inc.is_demo && <span className="demo-badge"><FlaskConical size={9} /> demo</span>}
                    </div>
                    <p className="text-sm font-medium text-slate-200 truncate">{inc.title}</p>
                    {inc.probable_root_cause && (
                      <p className="text-xs text-slate-400 mt-1">
                        <span className="text-brand-400">→</span> {inc.probable_root_cause}
                      </p>
                    )}
                  </div>
                  <div className="text-right shrink-0">
                    {inc.confidence_score != null && (
                      <p className={clsx('text-sm font-semibold', confidenceColor(inc.confidence_score))}>
                        {(inc.confidence_score * 100).toFixed(0)}%
                      </p>
                    )}
                    <p className="text-xs text-slate-500">{formatRelative(inc.detected_at)}</p>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Pending */}
      {pending.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wide mb-3">
            Awaiting Investigation ({pending.length})
          </h2>
          <div className="space-y-2">
            {pending.map(inc => (
              <Link key={inc.id} to={`/incidents/${inc.id}`} className="card-hover p-4 flex items-center gap-4">
                <AlertTriangle size={16} className="text-yellow-400 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-300 truncate">{inc.title}</p>
                  <p className="text-xs text-slate-500">{formatRelative(inc.detected_at)}</p>
                </div>
                <span className="text-xs text-slate-500 shrink-0 capitalize">{inc.rca_status}</span>
                <ChevronRight size={14} className="text-slate-600" />
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
