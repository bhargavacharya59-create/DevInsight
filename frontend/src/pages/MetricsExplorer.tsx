import { useEffect, useState } from 'react';
import { getMetrics } from '../api/client';
import MetricChart from '../components/charts/MetricChart';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import ErrorState from '../components/ui/ErrorState';
import { FlaskConical } from 'lucide-react';

const METRIC_LABELS: Record<string, string> = {
  request_rate: 'Request Rate (req/s)',
  error_rate: 'Error Rate (%)',
  latency_ms: 'Response Latency (ms)',
  cpu_utilization: 'CPU Utilization (%)',
  memory_utilization: 'Memory Utilization (%)',
  db_query_latency: 'DB Query Latency (ms)',
};

const METRIC_COLORS: Record<string, string> = {
  request_rate: '#6366f1',
  error_rate: '#ef4444',
  latency_ms: '#f97316',
  cpu_utilization: '#8b5cf6',
  memory_utilization: '#06b6d4',
  db_query_latency: '#10b981',
};

const SERVICES = [
  { id: 'shopsphere-api', label: 'ShopSphere API' },
  { id: 'order-service', label: 'Order Service' },
  { id: 'payment-service', label: 'Payment Service' },
  { id: 'database', label: 'Database' },
  { id: 'shopsphere-frontend', label: 'Frontend' },
];

export default function MetricsExplorer() {
  const [data, setData] = useState<Record<string, Record<string, unknown>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [service, setService] = useState('shopsphere-api');
  const [duration, setDuration] = useState(60);
  const [isDemo, setIsDemo] = useState(true);

  const load = () => {
    setLoading(true);
    getMetrics({ service, duration_minutes: duration })
      .then(d => { setData(d.metrics); setIsDemo(d.is_demo); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [service, duration]);

  const svcData = data?.[service] || {};

  return (
    <div className="p-6 space-y-5 max-w-screen-2xl mx-auto">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold text-white">Metrics Explorer</h1>
          {isDemo && (
            <span className="demo-badge mt-1">
              <FlaskConical size={10} /> Synthetic demo metrics
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <select
            value={service}
            onChange={e => setService(e.target.value)}
            className="bg-surface-700 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-slate-200"
          >
            {SERVICES.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}
          </select>
          <select
            value={duration}
            onChange={e => setDuration(Number(e.target.value))}
            className="bg-surface-700 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-slate-200"
          >
            <option value={30}>Last 30 min</option>
            <option value={60}>Last 1 hour</option>
            <option value={180}>Last 3 hours</option>
            <option value={720}>Last 12 hours</option>
          </select>
        </div>
      </div>

      {loading ? (
        <LoadingSpinner size="lg" className="py-16" />
      ) : error ? (
        <ErrorState message={error} onRetry={load} />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {Object.entries(METRIC_LABELS).map(([key, label]) => {
            const series = svcData[key] as { data_points: { timestamp: string; value: number }[]; current_value: number; unit: string } | undefined;
            if (!series) return null;
            return (
              <div key={key} className="card p-5">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-medium text-slate-300">{label}</h3>
                  <span className="text-lg font-bold text-white font-mono">
                    {series.current_value?.toFixed(1)}{series.unit}
                  </span>
                </div>
                <MetricChart
                  data={series.data_points}
                  label=""
                  unit={series.unit}
                  color={METRIC_COLORS[key] || '#6366f1'}
                  height={160}
                />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
