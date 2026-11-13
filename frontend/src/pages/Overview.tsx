import { useEffect, useState } from 'react';
import {
  AlertTriangle, TrendingUp, Clock, CheckCircle2,
  Activity, Cpu, HardDrive, Zap, RefreshCw, FlaskConical,
} from 'lucide-react';
import { getOverview } from '../api/client';
import type { OverviewData, ServiceHealth } from '../types';
import KPICard from '../components/ui/KPICard';
import MetricChart from '../components/charts/MetricChart';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import ErrorState from '../components/ui/ErrorState';
import { serviceStatusDot, serviceStatusColor, formatNumber, formatPercent } from '../utils/format';
import clsx from 'clsx';

function ServiceRow({ svc }: { svc: ServiceHealth }) {
  return (
    <div className="flex items-center gap-4 py-3 border-b border-slate-700/30 last:border-0">
      <div className="flex items-center gap-2 w-48 shrink-0">
        <span className={clsx('w-2 h-2 rounded-full shrink-0', serviceStatusDot(svc.status))} />
        <span className="text-sm font-medium text-slate-200 truncate">{svc.display_name}</span>
      </div>
      <span className={clsx('text-xs font-medium w-20 shrink-0 capitalize', serviceStatusColor(svc.status))}>
        {svc.status}
      </span>
      <div className="flex items-center gap-6 text-xs text-slate-400 flex-1">
        <span>
          <span className={clsx(svc.error_rate > 5 ? 'text-red-400' : svc.error_rate > 2 ? 'text-yellow-400' : 'text-slate-300')}>
            {formatPercent(svc.error_rate)}
          </span>
          <span className="text-slate-600 ml-1">err</span>
        </span>
        <span>
          <span className={clsx(svc.latency_ms > 1000 ? 'text-red-400' : svc.latency_ms > 500 ? 'text-yellow-400' : 'text-slate-300')}>
            {svc.latency_ms.toFixed(0)}ms
          </span>
          <span className="text-slate-600 ml-1">p95</span>
        </span>
        <span>
          <span className="text-slate-300">{formatNumber(svc.request_rate)}</span>
          <span className="text-slate-600 ml-1">req/s</span>
        </span>
      </div>
      {svc.is_demo && (
        <span className="demo-badge shrink-0">
          <FlaskConical size={10} />
          demo
        </span>
      )}
    </div>
  );
}

export default function Overview() {
  const [data, setData] = useState<OverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState(new Date());

  const load = () => {
    setLoading(true);
    setError(null);
    getOverview()
      .then(d => { setData(d); setLastRefresh(new Date()); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    const iv = setInterval(load, 30_000);
    return () => clearInterval(iv);
  }, []);

  if (loading && !data) return <LoadingSpinner size="lg" className="h-full" />;
  if (error && !data) return <ErrorState message={error} onRetry={load} />;
  if (!data) return null;

  const { kpis, services, charts } = data;

  const healthColor = {
    healthy: 'text-emerald-400',
    degraded: 'text-yellow-400',
    critical: 'text-red-400',
  }[kpis.system_health] || 'text-slate-400';

  return (
    <div className="p-6 space-y-6 max-w-screen-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Overview</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            ShopSphere platform health and incident summary
            {data.is_demo && (
              <span className="ml-2 demo-badge">
                <FlaskConical size={10} /> Demo
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-500">
            Updated {lastRefresh.toLocaleTimeString()}
          </span>
          <button onClick={load} disabled={loading} className="btn-secondary">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-7 gap-4">
        <KPICard label="Total Incidents" value={kpis.total_incidents} icon={AlertTriangle} iconColor="text-slate-400" />
        <KPICard label="Critical" value={kpis.critical_incidents} icon={AlertTriangle} iconColor="text-red-400" />
        <KPICard label="Active" value={kpis.active_incidents} icon={Activity} iconColor="text-yellow-400" />
        <KPICard label="Resolved" value={kpis.resolved_incidents} icon={CheckCircle2} iconColor="text-emerald-400" />
        <KPICard label="Avg Detection" value={`${kpis.avg_detection_time_minutes}m`} icon={Zap} iconColor="text-brand-400"
          subtext="Time to detect" />
        <KPICard label="Avg Resolution" value={kpis.avg_resolution_time_minutes > 0 ? `${kpis.avg_resolution_time_minutes.toFixed(0)}m` : '–'}
          icon={Clock} iconColor="text-purple-400" subtext="Mean time to resolve" />
        <div className="card p-5">
          <div className="flex items-start gap-3 mb-3">
            <div className="p-2.5 rounded-lg bg-surface-700">
              <TrendingUp size={18} className={healthColor} />
            </div>
          </div>
          <p className={clsx('text-2xl font-bold mb-0.5', healthColor)}>
            {kpis.system_health_score.toFixed(0)}%
          </p>
          <p className="text-sm text-slate-400">System Health</p>
          <p className={clsx('text-xs mt-1 capitalize font-medium', healthColor)}>{kpis.system_health}</p>
        </div>
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
        {charts.request_rate && (
          <div className="card p-5">
            <h3 className="text-sm font-medium text-slate-300 mb-4">Request Rate</h3>
            <MetricChart data={charts.request_rate} label="" unit=" req/s" color="#6366f1" height={150} />
          </div>
        )}
        {charts.error_rate && (
          <div className="card p-5">
            <h3 className="text-sm font-medium text-slate-300 mb-4">Error Rate</h3>
            <MetricChart data={charts.error_rate} label="" unit="%" color="#ef4444" height={150} thresholdValue={5} />
          </div>
        )}
        {charts.latency_ms && (
          <div className="card p-5">
            <h3 className="text-sm font-medium text-slate-300 mb-4">API Latency (p95)</h3>
            <MetricChart data={charts.latency_ms} label="" unit="ms" color="#f97316" height={150} thresholdValue={1000} />
          </div>
        )}
        {charts.cpu_utilization && (
          <div className="card p-5">
            <h3 className="text-sm font-medium text-slate-300 mb-4">CPU Utilization</h3>
            <MetricChart data={charts.cpu_utilization} label="" unit="%" color="#8b5cf6" height={150} thresholdValue={80} />
          </div>
        )}
        {charts.memory_utilization && (
          <div className="card p-5">
            <h3 className="text-sm font-medium text-slate-300 mb-4">Memory Utilization</h3>
            <MetricChart data={charts.memory_utilization} label="" unit="%" color="#06b6d4" height={150} thresholdValue={85} />
          </div>
        )}
      </div>

      {/* Service health table */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-slate-200 mb-4">Service Health</h3>
        <div>
          {services.map(svc => (
            <ServiceRow key={svc.name} svc={svc} />
          ))}
        </div>
      </div>
    </div>
  );
}
