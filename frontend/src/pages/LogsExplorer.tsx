import { useEffect, useState } from 'react';
import { getLogs } from '../api/client';
import type { LogEntry } from '../types';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import ErrorState from '../components/ui/ErrorState';
import { FlaskConical, Search } from 'lucide-react';
import { format, parseISO } from 'date-fns';
import clsx from 'clsx';

const LEVEL_STYLES: Record<string, string> = {
  INFO: 'text-blue-400 bg-blue-900/20',
  DEBUG: 'text-slate-400 bg-slate-800',
  WARN: 'text-yellow-400 bg-yellow-900/20',
  WARNING: 'text-yellow-400 bg-yellow-900/20',
  ERROR: 'text-red-400 bg-red-900/20',
  CRITICAL: 'text-red-300 bg-red-900/30',
  FATAL: 'text-red-200 bg-red-900/40',
};

export default function LogsExplorer() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [service, setService] = useState('');
  const [severity, setSeverity] = useState('');
  const [search, setSearch] = useState('');
  const [limit, setLimit] = useState(100);
  const [isDemo, setIsDemo] = useState(true);

  const load = () => {
    setLoading(true);
    const params: Record<string, unknown> = { limit };
    if (service) params.service = service;
    if (severity) params.severity = severity;
    if (search) params.search = search;

    getLogs(params)
      .then(d => { setLogs(d.logs); setIsDemo(d.is_demo); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [service, severity, search, limit]);

  return (
    <div className="p-6 space-y-5 max-w-screen-2xl mx-auto">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold text-white">Logs Explorer</h1>
          {isDemo && <span className="demo-badge mt-1"><FlaskConical size={10} /> Synthetic logs</span>}
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-48">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search log messages…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full bg-surface-700 border border-slate-700/50 rounded-lg pl-9 pr-3 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-brand-500/50"
          />
        </div>
        <select value={service} onChange={e => setService(e.target.value)}
          className="bg-surface-700 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-slate-200">
          <option value="">All Services</option>
          <option value="shopsphere-api">ShopSphere API</option>
          <option value="order-service">Order Service</option>
          <option value="payment-service">Payment Service</option>
          <option value="database">Database</option>
          <option value="shopsphere-frontend">Frontend</option>
        </select>
        <select value={severity} onChange={e => setSeverity(e.target.value)}
          className="bg-surface-700 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-slate-200">
          <option value="">All Levels</option>
          <option value="ERROR">Error</option>
          <option value="WARN">Warning</option>
          <option value="INFO">Info</option>
          <option value="DEBUG">Debug</option>
        </select>
        <select value={limit} onChange={e => setLimit(Number(e.target.value))}
          className="bg-surface-700 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-slate-200">
          <option value={50}>50 lines</option>
          <option value={100}>100 lines</option>
          <option value={200}>200 lines</option>
        </select>
      </div>

      {loading ? (
        <LoadingSpinner size="lg" className="py-16" />
      ) : error ? (
        <ErrorState message={error} onRetry={load} />
      ) : (
        <div className="card overflow-hidden">
          <div className="font-mono text-xs">
            {logs.map((log, i) => (
              <div
                key={i}
                className={clsx(
                  'flex gap-3 px-4 py-2 border-b border-slate-800/50 hover:bg-surface-700/30',
                  (log.level === 'ERROR' || log.level === 'CRITICAL' || log.level === 'FATAL') && 'bg-red-900/5'
                )}
              >
                <span className="text-slate-600 shrink-0 w-14 text-right">
                  {format(parseISO(log.timestamp), 'HH:mm:ss')}
                </span>
                <span className={clsx(
                  'px-1.5 py-0.5 rounded text-xs font-semibold shrink-0 self-start w-14 text-center',
                  LEVEL_STYLES[log.level] || 'text-slate-400 bg-slate-800'
                )}>
                  {log.level}
                </span>
                <span className="text-purple-400 shrink-0 w-32 truncate">{log.service}</span>
                <span className="text-slate-300 flex-1 break-all">{log.message}</span>
                {log.trace_id && (
                  <span className="text-slate-600 shrink-0 text-xs">{log.trace_id.slice(0, 8)}</span>
                )}
              </div>
            ))}
            {logs.length === 0 && (
              <div className="text-center py-12 text-slate-500">No logs found</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
