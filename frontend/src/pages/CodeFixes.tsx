import { useEffect, useState } from 'react';
import { getIncidents, startRemediation, getDemoRemediation, runRCA } from '../api/client';
import type { Incident } from '../types';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import SeverityBadge from '../components/ui/SeverityBadge';
import { Wrench, Play, CheckCircle2, XCircle, Clock, FlaskConical, ExternalLink, ChevronDown, ChevronUp, GitBranch, GitPullRequest } from 'lucide-react';
import { formatRelative } from '../utils/format';
import clsx from 'clsx';

interface RemediationResult {
  branch?: string;
  pr_number?: number;
  pr_url?: string;
  status: string;
  error?: string;
  is_demo?: boolean;
  patch?: {
    affected_files: string[];
    patch_description: string;
    changes: Array<{
      file: string;
      original_snippet: string;
      fixed_snippet: string;
      explanation: string;
    }>;
    risk_assessment: string;
    suggested_test: string;
    confidence: number;
  };
  steps: Array<{ name: string; status: string; detail: string; timestamp: string }>;
  retry_count: number;
}

function StepList({ steps }: { steps: RemediationResult['steps'] }) {
  return (
    <div className="space-y-2">
      {steps.map((step, i) => (
        <div key={i} className="flex items-start gap-2 text-sm">
          <div className="shrink-0 mt-0.5">
            {step.status === 'completed' ? (
              <CheckCircle2 size={14} className="text-emerald-400" />
            ) : step.status === 'failed' ? (
              <XCircle size={14} className="text-red-400" />
            ) : (
              <Clock size={14} className="text-yellow-400 animate-pulse" />
            )}
          </div>
          <div>
            <p className="text-slate-200 font-medium">{step.name}</p>
            {step.detail && <p className="text-slate-500 text-xs mt-0.5">{step.detail}</p>}
          </div>
          <span className="ml-auto text-xs text-slate-600 shrink-0">
            {step.timestamp ? new Date(step.timestamp).toLocaleTimeString() : ''}
          </span>
        </div>
      ))}
    </div>
  );
}

function DiffView({ original, fixed, file }: { original: string; fixed: string; file: string }) {
  return (
    <div className="rounded-lg overflow-hidden border border-slate-700/30">
      <div className="bg-surface-900 px-3 py-1.5 text-xs text-slate-400 font-mono border-b border-slate-700/30">
        {file}
      </div>
      <div className="grid grid-cols-2 divide-x divide-slate-700/30">
        <div>
          <div className="bg-red-900/20 px-2 py-1 text-xs text-red-400 font-semibold">− Before</div>
          <pre className="p-3 text-xs text-red-300 font-mono overflow-x-auto whitespace-pre-wrap bg-red-900/5">
            {original}
          </pre>
        </div>
        <div>
          <div className="bg-emerald-900/20 px-2 py-1 text-xs text-emerald-400 font-semibold">+ After</div>
          <pre className="p-3 text-xs text-emerald-300 font-mono overflow-x-auto whitespace-pre-wrap bg-emerald-900/5">
            {fixed}
          </pre>
        </div>
      </div>
    </div>
  );
}

export default function CodeFixes() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [remediation, setRemediation] = useState<RemediationResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showDemo, setShowDemo] = useState(false);

  useEffect(() => {
    getIncidents({ page_size: 20 })
      .then(d => setIncidents(d.incidents || []))
      .finally(() => setLoading(false));
  }, []);

  const handleRunRemediation = async (incident: Incident) => {
    setRunning(true);
    setRemediation(null);
    setError(null);
    setSelectedIncident(incident);
    try {
      // First run RCA if not done
      if (incident.rca_status !== 'completed') {
        await runRCA({ incident_id: incident.id, include_demo_evidence: true });
      }
      const result = await startRemediation({ incident_id: incident.id });
      setRemediation(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Remediation failed');
    } finally {
      setRunning(false);
    }
  };

  const handleLoadDemo = async () => {
    setRunning(true);
    setRemediation(null);
    setError(null);
    try {
      const r = await getDemoRemediation();
      setRemediation(r);
      setShowDemo(true);
    } finally {
      setRunning(false);
    }
  };

  if (loading) return <LoadingSpinner size="lg" className="h-full" />;

  return (
    <div className="p-6 space-y-5 max-w-screen-xl mx-auto">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold text-white">Code Fixes & Remediation</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            AI-generated patches, branch creation, and PR workflow
          </p>
        </div>
        <button onClick={handleLoadDemo} disabled={running} className="btn-secondary text-xs">
          <FlaskConical size={13} /> Load Demo Fix
        </button>
      </div>

      {/* Workflow visual */}
      <div className="card p-4">
        <div className="flex items-center gap-1 flex-wrap text-xs">
          {['Incident Detected', 'RCA Completed', 'Source Retrieved', 'Patch Generated',
            'Branch Created', 'Changes Committed', 'PR Opened', 'CI/CD Running', 'Developer Approval'].map((step, i, arr) => (
            <div key={step} className="flex items-center gap-1">
              <span className="px-2 py-1 bg-surface-700 rounded-full text-slate-400 border border-slate-700/50">
                {step}
              </span>
              {i < arr.length - 1 && <span className="text-slate-600">→</span>}
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        {/* Incident selector */}
        <div className="card overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-700/50">
            <h2 className="text-sm font-semibold text-slate-200">Select Incident to Remediate</h2>
          </div>
          <div className="divide-y divide-slate-700/20">
            {incidents.filter(i => i.status !== 'resolved' && i.status !== 'closed').map(inc => (
              <div key={inc.id}
                className={clsx('p-4 cursor-pointer hover:bg-surface-700/50 transition-colors',
                  selectedIncident?.id === inc.id && 'bg-brand-900/20 border-l-2 border-brand-500'
                )}
                onClick={() => setSelectedIncident(inc)}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <SeverityBadge severity={inc.severity} />
                      {inc.is_demo && <span className="demo-badge"><FlaskConical size={9} /> demo</span>}
                    </div>
                    <p className="text-sm text-slate-200 leading-tight truncate">{inc.title}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{formatRelative(inc.detected_at)}</p>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleRunRemediation(inc); }}
                    disabled={running}
                    className="btn-primary text-xs shrink-0 disabled:opacity-40"
                  >
                    {running && selectedIncident?.id === inc.id ? (
                      <><LoadingSpinner size="sm" /><span>Running…</span></>
                    ) : (
                      <><Wrench size={12} /> Fix</>
                    )}
                  </button>
                </div>
              </div>
            ))}
            {incidents.filter(i => i.status !== 'resolved').length === 0 && (
              <p className="text-slate-500 text-sm text-center py-10">No active incidents to remediate.</p>
            )}
          </div>
        </div>

        {/* Remediation result */}
        <div className="space-y-4">
          {running && !remediation && (
            <div className="card p-8 flex flex-col items-center gap-3">
              <LoadingSpinner size="lg" />
              <p className="text-slate-400 text-sm">Running remediation workflow…</p>
            </div>
          )}

          {error && (
            <div className="card p-4 bg-red-900/10 border-red-700/30">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          {remediation && (
            <>
              {/* Status */}
              <div className="card p-4">
                <div className="flex items-center gap-3 mb-3">
                  <div className={clsx('w-8 h-8 rounded-full flex items-center justify-center',
                    remediation.status === 'pr_open' ? 'bg-emerald-900/30' :
                    remediation.status === 'error' ? 'bg-red-900/30' : 'bg-yellow-900/30'
                  )}>
                    {remediation.status === 'pr_open' ? <CheckCircle2 size={16} className="text-emerald-400" /> :
                     remediation.status === 'error' ? <XCircle size={16} className="text-red-400" /> :
                     <Clock size={16} className="text-yellow-400" />}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-200 capitalize">{remediation.status.replace('_', ' ')}</p>
                    {remediation.is_demo && <span className="demo-badge"><FlaskConical size={9} /> demo</span>}
                  </div>
                  {remediation.pr_url && remediation.pr_url !== '#' && (
                    <a href={remediation.pr_url} target="_blank" rel="noopener noreferrer"
                      className="ml-auto flex items-center gap-1 text-xs text-brand-400 hover:text-brand-300">
                      <GitPullRequest size={12} /> PR #{remediation.pr_number}
                      <ExternalLink size={10} />
                    </a>
                  )}
                </div>

                {remediation.branch && (
                  <div className="flex items-center gap-2 text-xs text-slate-400 mt-2 p-2 bg-surface-700 rounded">
                    <GitBranch size={12} />
                    <span className="font-mono">{remediation.branch}</span>
                  </div>
                )}
              </div>

              {/* Steps */}
              <div className="card p-4">
                <h3 className="text-sm font-semibold text-slate-200 mb-3">Workflow Steps</h3>
                <StepList steps={remediation.steps} />
              </div>

              {/* Patch details */}
              {remediation.patch && (
                <div className="card p-4 space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-slate-200">Generated Patch</h3>
                    <span className="text-xs text-slate-400">
                      Confidence: <span className="text-emerald-400">{(remediation.patch.confidence * 100).toFixed(0)}%</span>
                    </span>
                  </div>

                  <div className="p-3 bg-surface-700 rounded-lg">
                    <p className="text-sm text-slate-200">{remediation.patch.patch_description}</p>
                    <p className="text-xs text-slate-500 mt-1">Risk: {remediation.patch.risk_assessment}</p>
                  </div>

                  {remediation.patch.changes.map((change, i) => (
                    <DiffView
                      key={i}
                      file={change.file}
                      original={change.original_snippet}
                      fixed={change.fixed_snippet}
                    />
                  ))}

                  {remediation.patch.suggested_test && (
                    <div>
                      <p className="text-xs font-medium text-slate-400 mb-1">Suggested Test</p>
                      <pre className="text-xs font-mono text-slate-300 bg-surface-700 p-3 rounded overflow-x-auto">
                        {remediation.patch.suggested_test}
                      </pre>
                    </div>
                  )}

                  <div className="p-3 bg-yellow-900/20 border border-yellow-700/30 rounded-lg text-xs text-yellow-300">
                    ⚠ Review all changes carefully before approving the pull request. Never merge AI-generated fixes without human review and passing CI/CD.
                  </div>
                </div>
              )}
            </>
          )}

          {!remediation && !running && (
            <div className="card p-10 text-center text-slate-500">
              <Wrench size={32} className="mx-auto mb-3 opacity-30" />
              <p>Select an incident and click Fix to start autonomous remediation.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
