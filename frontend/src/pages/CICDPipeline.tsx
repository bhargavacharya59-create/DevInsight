import { useEffect, useState } from 'react';
import { getWorkflowRuns, getWorkflowJobs, getPullRequests, getGithubStatus } from '../api/client';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import ErrorState from '../components/ui/ErrorState';
import { GitPullRequest, CheckCircle2, XCircle, Clock, RefreshCw, FlaskConical, ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';
import { formatRelative } from '../utils/format';
import clsx from 'clsx';

interface WorkflowRun {
  id: number;
  name: string;
  branch: string;
  commit_sha: string;
  status: string;
  conclusion: string | null;
  created_at: string;
  updated_at: string;
  url: string;
  run_number: number;
  event: string;
  is_demo?: boolean;
}

interface PR {
  number: number;
  title: string;
  state: string;
  author: string;
  head: string;
  base: string;
  created_at: string;
  url: string;
  draft: boolean;
  is_demo?: boolean;
}

function ConclusionBadge({ status, conclusion }: { status: string; conclusion: string | null }) {
  if (status === 'in_progress' || status === 'queued') {
    return (
      <span className="flex items-center gap-1 text-yellow-400 text-xs font-medium">
        <Clock size={12} className="animate-pulse" /> {status.replace('_', ' ')}
      </span>
    );
  }
  if (conclusion === 'success') {
    return <span className="flex items-center gap-1 text-emerald-400 text-xs font-medium"><CheckCircle2 size={12} /> passed</span>;
  }
  if (conclusion === 'failure') {
    return <span className="flex items-center gap-1 text-red-400 text-xs font-medium"><XCircle size={12} /> failed</span>;
  }
  return <span className="text-slate-400 text-xs">{conclusion || status}</span>;
}

function RunRow({ run }: { run: WorkflowRun }) {
  const [expanded, setExpanded] = useState(false);
  const [jobs, setJobs] = useState<unknown[]>([]);
  const [jobsLoading, setJobsLoading] = useState(false);

  const toggleExpand = async () => {
    if (!expanded && jobs.length === 0) {
      setJobsLoading(true);
      try {
        const d = await getWorkflowJobs(run.id);
        setJobs(d.jobs || []);
      } catch { /* ignore */ }
      setJobsLoading(false);
    }
    setExpanded(e => !e);
  };

  const isDevInsightBranch = run.branch.startsWith('devinsight/');

  return (
    <div className="border-b border-slate-700/30 last:border-0">
      <div
        className="flex items-center gap-4 px-4 py-3 hover:bg-surface-700/30 cursor-pointer transition-colors"
        onClick={toggleExpand}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-slate-200">{run.name}</span>
            {isDevInsightBranch && (
              <span className="text-xs px-1.5 py-0.5 bg-brand-900/40 text-brand-400 border border-brand-700/30 rounded">
                AI Fix
              </span>
            )}
            {run.is_demo && <span className="demo-badge"><FlaskConical size={9} /> demo</span>}
          </div>
          <div className="flex items-center gap-3 mt-0.5 text-xs text-slate-500">
            <span className="font-mono">{run.branch}</span>
            <span>#{run.run_number}</span>
            <span className="font-mono">{run.commit_sha}</span>
            <span className="capitalize">{run.event}</span>
            <span>{formatRelative(run.updated_at)}</span>
          </div>
        </div>
        <ConclusionBadge status={run.status} conclusion={run.conclusion} />
        {run.url !== '#' && (
          <a href={run.url} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()}
            className="text-slate-500 hover:text-slate-300">
            <ExternalLink size={13} />
          </a>
        )}
        {expanded ? <ChevronUp size={14} className="text-slate-500" /> : <ChevronDown size={14} className="text-slate-500" />}
      </div>

      {expanded && (
        <div className="px-4 pb-3">
          {jobsLoading ? (
            <LoadingSpinner size="sm" className="py-3" />
          ) : (
            <div className="space-y-1">
              {(jobs as Array<{name: string; conclusion: string; steps?: Array<{name: string; conclusion: string}>}>).map((job, i) => (
                <div key={i} className="text-xs">
                  <div className="flex items-center gap-2 py-1">
                    {job.conclusion === 'success' ? (
                      <CheckCircle2 size={11} className="text-emerald-400" />
                    ) : job.conclusion === 'failure' ? (
                      <XCircle size={11} className="text-red-400" />
                    ) : (
                      <Clock size={11} className="text-yellow-400" />
                    )}
                    <span className="text-slate-300">{job.name}</span>
                  </div>
                  {(job.steps || []).map((step, j) => (
                    <div key={j} className="flex items-center gap-2 pl-5 py-0.5 text-slate-500">
                      <span className={clsx('w-1.5 h-1.5 rounded-full',
                        step.conclusion === 'success' ? 'bg-emerald-500' :
                        step.conclusion === 'failure' ? 'bg-red-500' : 'bg-yellow-500'
                      )} />
                      {step.name}
                    </div>
                  ))}
                </div>
              ))}
              {jobs.length === 0 && <p className="text-xs text-slate-500 py-2">No job details available.</p>}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function CICDPipeline() {
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [prs, setPrs] = useState<PR[]>([]);
  const [githubStatus, setGithubStatus] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDemo, setIsDemo] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [runsData, prsData, status] = await Promise.all([
        getWorkflowRuns(),
        getPullRequests('all'),
        getGithubStatus(),
      ]);
      setRuns(runsData.runs || []);
      setPrs(prsData.pull_requests || []);
      setGithubStatus(status);
      setIsDemo(runsData.is_demo ?? true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) return <LoadingSpinner size="lg" className="h-full" />;
  if (error) return <ErrorState message={error} onRetry={load} />;

  const passed = runs.filter(r => r.conclusion === 'success').length;
  const failed = runs.filter(r => r.conclusion === 'failure').length;
  const running = runs.filter(r => r.status === 'in_progress').length;

  return (
    <div className="p-6 space-y-5 max-w-screen-xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold text-white">CI/CD Pipelines</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            GitHub Actions workflow runs and pull requests
            {isDemo && <span className="ml-2 demo-badge"><FlaskConical size={10} /> Demo</span>}
          </p>
        </div>
        <button onClick={load} className="btn-secondary">
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* GitHub status banner */}
      {githubStatus && (
        <div className={clsx(
          'flex items-center gap-3 p-3 rounded-lg border text-sm',
          githubStatus.connected ? 'bg-emerald-900/20 border-emerald-700/30 text-emerald-300' :
          'bg-yellow-900/20 border-yellow-700/30 text-yellow-300'
        )}>
          <GitPullRequest size={14} />
          <span>{githubStatus.connected ? `Connected: ${githubStatus.message}` : `${githubStatus.message}`}</span>
        </div>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Runs', value: runs.length, color: 'text-slate-200' },
          { label: 'Passed', value: passed, color: 'text-emerald-400' },
          { label: 'Failed', value: failed, color: 'text-red-400' },
          { label: 'Running', value: running, color: 'text-yellow-400' },
        ].map(k => (
          <div key={k.label} className="card p-4">
            <p className={clsx('text-2xl font-bold', k.color)}>{k.value}</p>
            <p className="text-xs text-slate-400 mt-0.5">{k.label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        {/* Workflow runs */}
        <div className="xl:col-span-2 card overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-700/50">
            <h2 className="text-sm font-semibold text-slate-200">Recent Workflow Runs</h2>
          </div>
          {runs.length === 0 ? (
            <p className="text-slate-500 text-sm text-center py-10">No workflow runs found.</p>
          ) : (
            runs.map(run => <RunRow key={run.id} run={run} />)
          )}
        </div>

        {/* Pull Requests */}
        <div className="card overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-700/50">
            <h2 className="text-sm font-semibold text-slate-200">Pull Requests</h2>
          </div>
          <div className="divide-y divide-slate-700/30">
            {prs.length === 0 ? (
              <p className="text-slate-500 text-sm text-center py-10">No pull requests found.</p>
            ) : (
              prs.map(pr => (
                <div key={pr.number} className="p-4">
                  <div className="flex items-start gap-2">
                    <span className={clsx('text-xs px-1.5 py-0.5 rounded mt-0.5',
                      pr.state === 'open' ? 'bg-emerald-900/30 text-emerald-400' : 'bg-purple-900/30 text-purple-400'
                    )}>
                      {pr.state}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-slate-200 leading-tight">{pr.title}</p>
                      <div className="flex items-center gap-2 mt-1 text-xs text-slate-500">
                        <span>#{pr.number}</span>
                        <span>{pr.author}</span>
                        <span className="font-mono truncate max-w-24">{pr.head}</span>
                        {pr.is_demo && <span className="demo-badge"><FlaskConical size={9} /> demo</span>}
                      </div>
                    </div>
                    {pr.url !== '#' && (
                      <a href={pr.url} target="_blank" rel="noopener noreferrer"
                        className="text-slate-500 hover:text-slate-300 shrink-0">
                        <ExternalLink size={13} />
                      </a>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
