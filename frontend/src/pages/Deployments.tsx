import { useEffect, useState } from 'react';
import { getDeployments, compareDeployment } from '../api/client';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import ErrorState from '../components/ui/ErrorState';
import { History, TrendingUp, TrendingDown, Minus, ExternalLink, FlaskConical, RefreshCw } from 'lucide-react';
import { formatRelative } from '../utils/format';
import clsx from 'clsx';

interface Deployment {
  id: string;
  version: string;
  branch: string;
  deployed_at: string;
  status: string;
  workflow: string;
  run_number: number;
  url: string;
  is_demo?: boolean;
  metrics_comparison?: {
    error_rate_before: number;
    error_rate_after: number;
    latency_before: number;
    latency_after: number;
    verdict: 'improved' | 'degraded' | 'stable';
  };
}

interface Comparison {
  deployment_id: string;
  is_demo?: boolean;
  before: Record<string, number>;
  after: Record<string, number>;
  verdict: string;
  rollback_recommended: boolean;
  incidents_in_window: number;
  note?: string;
}

function VerdictBadge({ verdict }: { verdict: string }) {
  if (verdict === 'improved') return (
    <span className="flex items-center gap-1 text-emerald-400 text-xs font-medium">
      <TrendingUp size={12} /> Improved
    </span>
  );
  if (verdict === 'degraded') return (
    <span className="flex items-center gap-1 text-red-400 text-xs font-medium">
      <TrendingDown size={12} /> Degraded
    </span>
  );
  return <span className="flex items-center gap-1 text-slate-400 text-xs font-medium"><Minus size={12} /> Stable</span>;
}

function MetricRow({ label, before, after, unit = '', higherIsBad = false }: {
  label: string; before: number; after: number; unit?: string; higherIsBad?: boolean;
}) {
  const change = ((after - before) / before) * 100;
  const isWorse = higherIsBad ? change > 5 : change < -5;
  const isBetter = higherIsBad ? change < -5 : change > 5;

  return (
    <div className="flex items-center gap-4 py-2 border-b border-slate-700/20 text-sm">
      <span className="text-slate-400 w-40 shrink-0">{label}</span>
      <span className="text-slate-300 font-mono w-24">{before.toFixed(1)}{unit}</span>
      <span className="text-slate-300 font-mono w-24">{after.toFixed(1)}{unit}</span>
      <span className={clsx('text-xs font-medium',
        isWorse ? 'text-red-400' : isBetter ? 'text-emerald-400' : 'text-slate-400'
      )}>
        {change > 0 ? '+' : ''}{change.toFixed(1)}%
      </span>
    </div>
  );
}

export default function Deployments() {
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [selected, setSelected] = useState<Deployment | null>(null);
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [loading, setLoading] = useState(true);
  const [compLoading, setCompLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDemo, setIsDemo] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const d = await getDeployments();
      setDeployments(d.deployments || []);
      setIsDemo(d.is_demo ?? true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = async (dep: Deployment) => {
    setSelected(dep);
    setCompLoading(true);
    try {
      const c = await compareDeployment(dep.id);
      setComparison(c);
    } finally {
      setCompLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) return <LoadingSpinner size="lg" className="h-full" />;
  if (error) return <ErrorState message={error} onRetry={load} />;

  return (
    <div className="p-6 space-y-5 max-w-screen-xl mx-auto">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold text-white">Deployment History</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Version comparison and performance impact analysis
            {isDemo && <span className="ml-2 demo-badge"><FlaskConical size={10} /> Demo</span>}
          </p>
        </div>
        <button onClick={load} className="btn-secondary"><RefreshCw size={14} /> Refresh</button>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        {/* Deployment list */}
        <div className="card overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-700/50">
            <h2 className="text-sm font-semibold text-slate-200">Recent Deployments</h2>
          </div>
          <div className="divide-y divide-slate-700/20">
            {deployments.map(dep => (
              <div
                key={dep.id}
                onClick={() => handleSelect(dep)}
                className={clsx('p-4 cursor-pointer hover:bg-surface-700/50 transition-colors',
                  selected?.id === dep.id && 'bg-brand-900/20 border-l-2 border-brand-500'
                )}
              >
                <div className="flex items-center gap-3">
                  <div className={clsx('w-2 h-2 rounded-full shrink-0',
                    dep.status === 'success' ? 'bg-emerald-500' :
                    dep.status === 'failure' ? 'bg-red-500 animate-pulse' : 'bg-yellow-500'
                  )} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-slate-200">{dep.version}</span>
                      {dep.metrics_comparison && <VerdictBadge verdict={dep.metrics_comparison.verdict} />}
                      {dep.is_demo && <span className="demo-badge"><FlaskConical size={9} /> demo</span>}
                    </div>
                    <div className="flex items-center gap-2 mt-0.5 text-xs text-slate-500">
                      <span className="font-mono">{dep.branch}</span>
                      <span>#{dep.run_number}</span>
                      <span>{formatRelative(dep.deployed_at)}</span>
                    </div>
                  </div>
                  {dep.url !== '#' && (
                    <a href={dep.url} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()}>
                      <ExternalLink size={13} className="text-slate-500 hover:text-slate-300" />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Version comparison */}
        <div>
          {compLoading && <LoadingSpinner size="lg" className="h-48" />}
          {comparison && !compLoading && (
            <div className="card p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-200">Version Comparison</h3>
                <VerdictBadge verdict={comparison.verdict} />
              </div>

              {comparison.rollback_recommended && (
                <div className="p-3 bg-red-900/20 border border-red-700/30 rounded-lg">
                  <p className="text-sm text-red-300 font-medium">⚠ Rollback Recommended</p>
                  <p className="text-xs text-red-400 mt-1">
                    Metrics degraded significantly after this deployment.
                    {comparison.incidents_in_window > 0 && ` ${comparison.incidents_in_window} incident(s) detected in the deployment window.`}
                  </p>
                </div>
              )}

              <div>
                <div className="flex gap-4 text-xs text-slate-500 pb-2 border-b border-slate-700/30">
                  <span className="w-40">Metric</span>
                  <span className="w-24">Before</span>
                  <span className="w-24">After</span>
                  <span>Change</span>
                </div>
                <MetricRow label="Error Rate" before={comparison.before.error_rate} after={comparison.after.error_rate} unit="%" higherIsBad />
                <MetricRow label="Latency P95" before={comparison.before.latency_p95} after={comparison.after.latency_p95} unit="ms" higherIsBad />
                <MetricRow label="Request Rate" before={comparison.before.request_rate} after={comparison.after.request_rate} unit="/s" />
                <MetricRow label="CPU" before={comparison.before.cpu_utilization} after={comparison.after.cpu_utilization} unit="%" higherIsBad />
                <MetricRow label="Memory" before={comparison.before.memory_utilization} after={comparison.after.memory_utilization} unit="%" higherIsBad />
              </div>

              {comparison.note && (
                <p className="text-xs text-slate-500 italic">{comparison.note}</p>
              )}
            </div>
          )}
          {!comparison && !compLoading && (
            <div className="card p-10 text-center text-slate-500">
              <History size={32} className="mx-auto mb-3 opacity-30" />
              <p>Select a deployment to compare metrics.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
