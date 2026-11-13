import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, Search, Filter, ChevronRight, FlaskConical } from 'lucide-react';
import { getIncidents, acknowledgeIncident, resolveIncident } from '../api/client';
import type { Incident, Severity, IncidentStatus } from '../types';
import SeverityBadge from '../components/ui/SeverityBadge';
import StatusBadge from '../components/ui/StatusBadge';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import ErrorState from '../components/ui/ErrorState';
import { formatRelative, formatDate } from '../utils/format';
import clsx from 'clsx';

const SEVERITIES: Array<{ value: Severity | ''; label: string }> = [
  { value: '', label: 'All Severities' },
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
];

const STATUSES: Array<{ value: IncidentStatus | ''; label: string }> = [
  { value: '', label: 'All Statuses' },
  { value: 'open', label: 'Open' },
  { value: 'investigating', label: 'Investigating' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'closed', label: 'Closed' },
];

export default function Incidents() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [severity, setSeverity] = useState<Severity | ''>('');
  const [status, setStatus] = useState<IncidentStatus | ''>('');
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 20;

  const load = () => {
    setLoading(true);
    const params: Record<string, unknown> = { page, page_size: PAGE_SIZE };
    if (search) params.search = search;
    if (severity) params.severity = severity;
    if (status) params.status = status;

    getIncidents(params)
      .then(d => { setIncidents(d.incidents); setTotal(d.total); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [search, severity, status, page]);

  const handleAck = async (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();
    await acknowledgeIncident(id);
    load();
  };

  const handleResolve = async (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();
    await resolveIncident(id);
    load();
  };

  return (
    <div className="p-6 space-y-5 max-w-screen-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Incidents</h1>
          <p className="text-sm text-slate-400 mt-0.5">{total} total incidents</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-48">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search incidents…"
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }}
            className="w-full bg-surface-700 border border-slate-700/50 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-brand-500/50"
          />
        </div>
        <select
          value={severity}
          onChange={e => { setSeverity(e.target.value as Severity | ''); setPage(1); }}
          className="bg-surface-700 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-brand-500/50"
        >
          {SEVERITIES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
        <select
          value={status}
          onChange={e => { setStatus(e.target.value as IncidentStatus | ''); setPage(1); }}
          className="bg-surface-700 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-brand-500/50"
        >
          {STATUSES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
      </div>

      {/* Table */}
      {loading && incidents.length === 0 ? (
        <LoadingSpinner size="lg" className="py-16" />
      ) : error ? (
        <ErrorState message={error} onRetry={load} />
      ) : incidents.length === 0 ? (
        <div className="card p-12 text-center">
          <AlertTriangle size={32} className="text-slate-600 mx-auto mb-3" />
          <p className="text-slate-400">No incidents found</p>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700/50">
                <th className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">Incident</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider w-24">Severity</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider w-32">Status</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider w-36">Service</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider w-32">Detected</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider w-16">Score</th>
                <th className="text-right px-4 py-3 w-24" />
              </tr>
            </thead>
            <tbody>
              {incidents.map(inc => (
                <tr
                  key={inc.id}
                  className="border-b border-slate-700/20 hover:bg-surface-700/50 transition-colors"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-start gap-2">
                      <div>
                        <Link
                          to={`/incidents/${inc.id}`}
                          className="font-medium text-slate-200 hover:text-brand-400 transition-colors line-clamp-1"
                        >
                          {inc.title}
                        </Link>
                        {inc.description && (
                          <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">{inc.description}</p>
                        )}
                        {inc.is_demo && (
                          <span className="demo-badge mt-1">
                            <FlaskConical size={9} /> demo
                          </span>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3"><SeverityBadge severity={inc.severity} /></td>
                  <td className="px-4 py-3"><StatusBadge status={inc.status} /></td>
                  <td className="px-4 py-3">
                    <span className="text-xs text-slate-300 font-mono bg-surface-700 px-2 py-0.5 rounded">
                      {inc.affected_service || '–'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs text-slate-400" title={formatDate(inc.detected_at)}>
                      {formatRelative(inc.detected_at)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {inc.anomaly_score != null ? (
                      <span className={clsx('text-xs font-mono font-semibold',
                        inc.anomaly_score > 0.7 ? 'text-red-400' :
                        inc.anomaly_score > 0.4 ? 'text-orange-400' : 'text-yellow-400'
                      )}>
                        {inc.anomaly_score.toFixed(2)}
                      </span>
                    ) : '–'}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      {inc.status === 'open' && !inc.acknowledged && (
                        <button
                          onClick={e => handleAck(e, inc.id)}
                          className="text-xs px-2 py-1 bg-yellow-900/30 text-yellow-300 border border-yellow-700/30 rounded hover:bg-yellow-900/50 transition-colors"
                        >
                          Ack
                        </button>
                      )}
                      {(inc.status === 'open' || inc.status === 'investigating') && (
                        <button
                          onClick={e => handleResolve(e, inc.id)}
                          className="text-xs px-2 py-1 bg-emerald-900/30 text-emerald-300 border border-emerald-700/30 rounded hover:bg-emerald-900/50 transition-colors"
                        >
                          Resolve
                        </button>
                      )}
                      <Link
                        to={`/incidents/${inc.id}`}
                        className="p-1 text-slate-500 hover:text-slate-300 transition-colors"
                      >
                        <ChevronRight size={14} />
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Pagination */}
          {total > PAGE_SIZE && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-700/50">
              <span className="text-xs text-slate-400">
                {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, total)} of {total}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="btn-secondary py-1 px-3 text-xs disabled:opacity-40"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage(p => p + 1)}
                  disabled={page * PAGE_SIZE >= total}
                  className="btn-secondary py-1 px-3 text-xs disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
