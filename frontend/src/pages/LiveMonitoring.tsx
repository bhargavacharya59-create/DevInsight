import { useEffect, useState } from 'react';
import { getTelemetrySources, getDemoScenarios, startScenario, stopScenario, resetDemo } from '../api/client';
import type { DemoScenario } from '../types';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { FlaskConical, Wifi, WifiOff, Play, Square, RotateCcw } from 'lucide-react';
import clsx from 'clsx';

interface TelemetrySource {
  name: string;
  status: string;
  url?: string;
  error?: string;
  message?: string;
}

export default function LiveMonitoring() {
  const [sources, setSources] = useState<TelemetrySource[]>([]);
  const [scenarios, setScenarios] = useState<DemoScenario[]>([]);
  const [activeScenario, setActiveScenario] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [isDemo, setIsDemo] = useState(true);

  const load = async () => {
    setLoading(true);
    const [srcData, scenData] = await Promise.all([
      getTelemetrySources().catch(() => ({ sources: [] })),
      getDemoScenarios().catch(() => ({ scenarios: [], active_scenario: null })),
    ]);
    setSources(srcData.sources || []);
    setScenarios(scenData.scenarios || []);
    setActiveScenario(scenData.active_scenario || null);
    setIsDemo(srcData.is_demo ?? true);
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const handleStart = async (id: string) => {
    setActionLoading(id);
    const result = await startScenario(id).catch(() => null);
    if (result?.success) {
      setActiveScenario(id);
      setSuccessMsg(result.message);
      setTimeout(() => setSuccessMsg(null), 5000);
    }
    setActionLoading(null);
  };

  const handleStop = async (id: string) => {
    setActionLoading(id);
    await stopScenario(id).catch(() => null);
    setActiveScenario('normal_operation');
    setActionLoading(null);
  };

  const handleReset = async () => {
    setActionLoading('reset');
    await resetDemo().catch(() => null);
    setActiveScenario(null);
    setSuccessMsg('Demo reset to normal operation.');
    setTimeout(() => setSuccessMsg(null), 3000);
    setActionLoading(null);
  };

  if (loading) return <LoadingSpinner size="lg" className="h-full" />;

  const CATEGORY_COLORS: Record<string, string> = {
    baseline: 'bg-emerald-900/30 text-emerald-400 border-emerald-700/30',
    database: 'bg-blue-900/30 text-blue-400 border-blue-700/30',
    api: 'bg-yellow-900/30 text-yellow-400 border-yellow-700/30',
    payment: 'bg-orange-900/30 text-orange-400 border-orange-700/30',
    infrastructure: 'bg-purple-900/30 text-purple-400 border-purple-700/30',
    deployment: 'bg-red-900/30 text-red-400 border-red-700/30',
  };

  return (
    <div className="p-6 space-y-6 max-w-screen-xl mx-auto">
      <div>
        <h1 className="text-xl font-semibold text-white">Live Monitoring</h1>
        <p className="text-sm text-slate-400 mt-0.5">
          {isDemo ? 'Demo mode — configure telemetry sources in settings for live monitoring' : 'Live telemetry monitoring'}
        </p>
      </div>

      {/* Success message */}
      {successMsg && (
        <div className="p-3 bg-emerald-900/30 border border-emerald-700/30 rounded-lg text-sm text-emerald-300">
          {successMsg}
        </div>
      )}

      {/* Telemetry Sources */}
      <div className="card p-5">
        <h2 className="font-semibold text-slate-200 mb-4">Telemetry Sources</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {sources.map(src => (
            <div key={src.name} className="p-4 bg-surface-700 rounded-lg border border-slate-700/30">
              <div className="flex items-center gap-2 mb-2">
                {src.status === 'connected' ? (
                  <Wifi size={16} className="text-emerald-400" />
                ) : src.status === 'demo' ? (
                  <FlaskConical size={16} className="text-purple-400" />
                ) : (
                  <WifiOff size={16} className="text-red-400" />
                )}
                <span className="text-sm font-medium text-slate-200 capitalize">{src.name}</span>
                <span className={clsx('text-xs ml-auto px-1.5 py-0.5 rounded border capitalize',
                  src.status === 'connected' && 'bg-emerald-900/30 text-emerald-400 border-emerald-700/30',
                  src.status === 'demo' && 'bg-purple-900/30 text-purple-400 border-purple-700/30',
                  src.status === 'disconnected' && 'bg-red-900/30 text-red-400 border-red-700/30',
                )}>
                  {src.status}
                </span>
              </div>
              <p className="text-xs text-slate-500">
                {src.message || src.url || (src.error ? `Error: ${src.error}` : '–')}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Demo Scenarios */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="font-semibold text-slate-200">Demo Scenarios</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Activate a scenario to simulate failure conditions in the telemetry
            </p>
          </div>
          <button onClick={handleReset} disabled={actionLoading === 'reset'} className="btn-secondary text-xs">
            <RotateCcw size={12} />
            Reset Demo
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {scenarios.map(s => {
            const isActive = activeScenario === s.id;
            return (
              <div
                key={s.id}
                className={clsx('p-4 rounded-lg border transition-colors',
                  isActive ? 'bg-brand-900/20 border-brand-600/40' : 'bg-surface-700 border-slate-700/30'
                )}
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <span className="text-sm font-medium text-slate-200">{s.name}</span>
                  <span className={clsx('text-xs px-1.5 py-0.5 rounded border shrink-0',
                    CATEGORY_COLORS[s.category] || 'bg-slate-800 text-slate-400 border-slate-700'
                  )}>
                    {s.category}
                  </span>
                </div>
                <p className="text-xs text-slate-500 mb-3 leading-relaxed">{s.description}</p>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-600">{s.duration_seconds}s</span>
                  {isActive ? (
                    <button
                      onClick={() => handleStop(s.id)}
                      disabled={!!actionLoading}
                      className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-red-900/30 text-red-400 border border-red-700/30 rounded hover:bg-red-900/50 transition-colors disabled:opacity-50"
                    >
                      {actionLoading === s.id ? <LoadingSpinner size="sm" /> : <Square size={10} />}
                      Stop
                    </button>
                  ) : (
                    <button
                      onClick={() => handleStart(s.id)}
                      disabled={!!actionLoading}
                      className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-brand-900/30 text-brand-400 border border-brand-700/30 rounded hover:bg-brand-900/50 transition-colors disabled:opacity-50"
                    >
                      {actionLoading === s.id ? <LoadingSpinner size="sm" /> : <Play size={10} />}
                      Start
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Live mode instructions */}
      {isDemo && (
        <div className="card p-5">
          <h2 className="font-semibold text-slate-200 mb-2">Switching to Live Mode</h2>
          <p className="text-sm text-slate-400 mb-3">
            To connect to real ShopSphere telemetry, configure the following environment variables in your backend <code className="text-brand-400">.env</code>:
          </p>
          <div className="bg-surface-900 rounded-lg p-4 font-mono text-xs text-slate-300 space-y-1">
            <p>MONITORING_MODE=<span className="text-emerald-400">live</span></p>
            <p>PROMETHEUS_URL=<span className="text-yellow-400">http://your-prometheus:9090</span></p>
            <p>LOKI_URL=<span className="text-yellow-400">http://your-loki:3100</span></p>
            <p>OTEL_COLLECTOR_URL=<span className="text-yellow-400">http://your-otel:4318</span></p>
          </div>
        </div>
      )}
    </div>
  );
}
