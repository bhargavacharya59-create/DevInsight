import { useEffect, useState } from 'react';
import { getHealth, getModelStatus, trainModel } from '../api/client';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import { CheckCircle2, XCircle, Zap } from 'lucide-react';

export default function Settings() {
  const [health, setHealth] = useState<Record<string, unknown> | null>(null);
  const [modelStatus, setModelStatus] = useState<Record<string, unknown> | null>(null);
  const [training, setTraining] = useState(false);
  const [trainResult, setTrainResult] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => null);
    getModelStatus().then(setModelStatus).catch(() => null);
  }, []);

  const handleTrain = async () => {
    setTraining(true);
    const r = await trainModel().catch(() => null);
    setTrainResult(r);
    getModelStatus().then(setModelStatus).catch(() => null);
    setTraining(false);
  };

  return (
    <div className="p-6 space-y-5 max-w-3xl mx-auto">
      <div>
        <h1 className="text-xl font-semibold text-white">Settings</h1>
        <p className="text-sm text-slate-400">Platform configuration and status</p>
      </div>

      {/* Backend status */}
      <div className="card p-5">
        <h2 className="font-semibold text-slate-200 mb-4">Backend Status</h2>
        {health ? (
          <div className="space-y-2 text-sm">
            {Object.entries(health).map(([k, v]) => (
              <div key={k} className="flex items-center justify-between py-1.5 border-b border-slate-700/20">
                <span className="text-slate-400 capitalize">{k.replace(/_/g, ' ')}</span>
                <span className={typeof v === 'string' ? 'text-slate-200' : 'text-slate-300 font-mono'}>
                  {String(v)}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <LoadingSpinner size="sm" />
        )}
      </div>

      {/* ML Model */}
      <div className="card p-5">
        <h2 className="font-semibold text-slate-200 mb-4">Anomaly Detection Model</h2>
        {modelStatus && (
          <div className="space-y-2 text-sm mb-4">
            <div className="flex items-center justify-between py-1.5 border-b border-slate-700/20">
              <span className="text-slate-400">Trained</span>
              <div className="flex items-center gap-1">
                {modelStatus.trained ? (
                  <CheckCircle2 size={14} className="text-emerald-400" />
                ) : (
                  <XCircle size={14} className="text-red-400" />
                )}
                <span className={modelStatus.trained ? 'text-emerald-400' : 'text-red-400'}>
                  {modelStatus.trained ? 'Yes' : 'No'}
                </span>
              </div>
            </div>
            <div className="flex items-center justify-between py-1.5 border-b border-slate-700/20">
              <span className="text-slate-400">Training samples</span>
              <span className="text-slate-200">{String(modelStatus.training_sample_count)}</span>
            </div>
            <div className="flex items-center justify-between py-1.5 border-b border-slate-700/20">
              <span className="text-slate-400">Contamination</span>
              <span className="text-slate-200">{String(modelStatus.contamination)}</span>
            </div>
            <div className="flex items-center justify-between py-1.5">
              <span className="text-slate-400">Anomaly threshold</span>
              <span className="text-slate-200">{String(modelStatus.threshold)}</span>
            </div>
          </div>
        )}

        <button onClick={handleTrain} disabled={training} className="btn-primary">
          {training ? <LoadingSpinner size="sm" /> : <Zap size={14} />}
          {training ? 'Training…' : 'Retrain Model (Demo Data)'}
        </button>
        {trainResult && (
          <p className="text-xs text-emerald-400 mt-2">
            {trainResult.success ? `Trained on ${String(trainResult.sample_count)} samples` : String(trainResult.reason)}
          </p>
        )}
      </div>

      {/* Environment configuration guidance */}
      <div className="card p-5">
        <h2 className="font-semibold text-slate-200 mb-3">Environment Variables</h2>
        <p className="text-sm text-slate-400 mb-3">
          Copy <code className="text-brand-400">.env.example</code> to <code className="text-brand-400">.env</code> in the backend directory and configure:
        </p>
        <div className="bg-surface-900 rounded-lg p-4 font-mono text-xs text-slate-300 space-y-1">
          <p className="text-slate-500"># Required for AI explanations</p>
          <p>GEMINI_API_KEY=<span className="text-yellow-400">your_key_here</span></p>
          <p>GEMINI_MODEL=<span className="text-emerald-400">gemini-1.5-flash</span></p>
          <p className="text-slate-500 mt-2"># Monitoring mode</p>
          <p>MONITORING_MODE=<span className="text-emerald-400">demo</span></p>
          <p className="text-slate-500 mt-2"># Database</p>
          <p>DATABASE_URL=<span className="text-yellow-400">postgresql+asyncpg://...</span></p>
        </div>
      </div>
    </div>
  );
}
