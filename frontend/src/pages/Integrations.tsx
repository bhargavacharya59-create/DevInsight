import { useEffect, useState } from 'react';
import { getIntegrations } from '../api/client';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { CheckCircle2, XCircle, AlertCircle, RefreshCw, ExternalLink } from 'lucide-react';
import clsx from 'clsx';

interface Integration {
  name: string;
  category: string;
  status: 'connected' | 'error' | 'not_configured' | 'demo' | 'unknown';
  message: string;
  configured: boolean;
  config_keys: string[];
}

const CATEGORY_LABELS: Record<string, string> = {
  source_control: 'Source Control',
  cicd: 'CI/CD',
  ai: 'AI & ML',
  monitoring: 'Monitoring',
  logs: 'Logs',
  tracing: 'Tracing',
  application: 'Application',
  visualization: 'Visualization',
};

function StatusIcon({ status }: { status: Integration['status'] }) {
  if (status === 'connected') return <CheckCircle2 size={16} className="text-emerald-400" />;
  if (status === 'error') return <XCircle size={16} className="text-red-400" />;
  if (status === 'demo') return <AlertCircle size={16} className="text-purple-400" />;
  return <AlertCircle size={16} className="text-slate-500" />;
}

function StatusBadge({ status }: { status: Integration['status'] }) {
  const styles: Record<string, string> = {
    connected: 'bg-emerald-900/30 text-emerald-400 border-emerald-700/30',
    error: 'bg-red-900/30 text-red-400 border-red-700/30',
    demo: 'bg-purple-900/30 text-purple-400 border-purple-700/30',
    not_configured: 'bg-slate-800 text-slate-400 border-slate-700/30',
    unknown: 'bg-slate-800 text-slate-500 border-slate-700/30',
  };
  return (
    <span className={clsx('text-xs px-2 py-0.5 rounded border capitalize', styles[status] || styles.unknown)}>
      {status.replace('_', ' ')}
    </span>
  );
}

export default function Integrations() {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState('demo');

  const load = async () => {
    setLoading(true);
    try {
      const d = await getIntegrations();
      setIntegrations(d.integrations || []);
      setMode(d.monitoring_mode);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) return <LoadingSpinner size="lg" className="h-full" />;

  const grouped = integrations.reduce<Record<string, Integration[]>>((acc, int) => {
    const key = int.category;
    if (!acc[key]) acc[key] = [];
    acc[key].push(int);
    return acc;
  }, {});

  const connected = integrations.filter(i => i.status === 'connected').length;
  const total = integrations.length;

  return (
    <div className="p-6 space-y-5 max-w-4xl mx-auto">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold text-white">Integrations</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            {connected}/{total} connected · Mode: <span className="capitalize font-medium text-slate-300">{mode}</span>
          </p>
        </div>
        <button onClick={load} className="btn-secondary"><RefreshCw size={14} /> Refresh</button>
      </div>

      {/* Quick setup guide */}
      <div className="card p-5">
        <h2 className="text-sm font-semibold text-slate-200 mb-3">Quick Setup</h2>
        <p className="text-sm text-slate-400 mb-3">
          Edit <code className="text-brand-400 bg-surface-700 px-1.5 py-0.5 rounded">backend/.env</code> to configure integrations:
        </p>
        <div className="bg-surface-900 rounded-lg p-4 font-mono text-xs space-y-1 text-slate-300">
          <p className="text-slate-500"># ① Gemini AI — Required for AI features</p>
          <p>GEMINI_API_KEY=<span className="text-yellow-400">your_key_here</span>  <span className="text-slate-600"># ← ADD HERE</span></p>
          <p className="text-slate-500 mt-2"># ② GitHub — Required for CI/CD and code fix features</p>
          <p>GITHUB_TOKEN=<span className="text-yellow-400">ghp_your_token</span></p>
          <p>GITHUB_REPO_OWNER=<span className="text-yellow-400">your-username</span></p>
          <p>GITHUB_REPO_NAME=<span className="text-yellow-400">shopsphere</span></p>
          <p className="text-slate-500 mt-2"># ③ Live monitoring (optional)</p>
          <p>MONITORING_MODE=<span className="text-emerald-400">demo</span>  <span className="text-slate-600"># change to live when ready</span></p>
        </div>
      </div>

      {/* Integration cards by category */}
      {Object.entries(grouped).map(([category, items]) => (
        <div key={category}>
          <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
            {CATEGORY_LABELS[category] || category}
          </h2>
          <div className="space-y-2">
            {items.map(int => (
              <div key={int.name} className="card p-4">
                <div className="flex items-start gap-4">
                  <StatusIcon status={int.status} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-slate-200">{int.name}</span>
                      <StatusBadge status={int.status} />
                    </div>
                    <p className="text-xs text-slate-400">{int.message}</p>
                    {int.config_keys.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {int.config_keys.map(key => (
                          <code key={key} className="text-xs bg-surface-700 text-slate-400 px-1.5 py-0.5 rounded">
                            {key}
                          </code>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* Webhook setup */}
      <div className="card p-5">
        <h2 className="text-sm font-semibold text-slate-200 mb-3">GitHub Webhook Setup</h2>
        <p className="text-sm text-slate-400 mb-3">
          To receive real-time events from GitHub, add a webhook to your ShopSphere repository:
        </p>
        <ol className="text-sm text-slate-400 space-y-1 list-decimal list-inside">
          <li>Go to your GitHub repo → Settings → Webhooks → Add webhook</li>
          <li>Payload URL: <code className="text-brand-400 bg-surface-700 px-1 rounded">http://your-server:8000/api/webhook/github</code></li>
          <li>Content type: <code className="text-brand-400">application/json</code></li>
          <li>Secret: use your <code className="text-brand-400">GITHUB_WEBHOOK_SECRET</code> value</li>
          <li>Events: <strong className="text-slate-300">push</strong>, <strong className="text-slate-300">pull_request</strong>, <strong className="text-slate-300">workflow_run</strong></li>
        </ol>
      </div>
    </div>
  );
}
