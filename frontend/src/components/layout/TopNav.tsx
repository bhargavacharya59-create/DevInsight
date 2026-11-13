import { Bell, Search, User, Zap, FlaskConical, Activity } from 'lucide-react';
import { useState, useEffect } from 'react';
import clsx from 'clsx';
import { getHealth } from '../../api/client';

interface TopNavProps {
  monitoringMode?: string;
  isDemo?: boolean;
}

export default function TopNav({ monitoringMode = 'demo', isDemo = true }: TopNavProps) {
  const [health, setHealth] = useState<string>('unknown');
  const [searchOpen, setSearchOpen] = useState(false);

  useEffect(() => {
    getHealth()
      .then((d: { status: string }) => setHealth(d.status))
      .catch(() => setHealth('error'));

    const interval = setInterval(() => {
      getHealth()
        .then((d: { status: string }) => setHealth(d.status))
        .catch(() => setHealth('error'));
    }, 30_000);
    return () => clearInterval(interval);
  }, []);

  const healthColor = {
    healthy: 'text-emerald-400',
    degraded: 'text-yellow-400',
    critical: 'text-red-400',
    error: 'text-red-400',
    unknown: 'text-slate-400',
  }[health] || 'text-slate-400';

  const healthDot = {
    healthy: 'bg-emerald-500',
    degraded: 'bg-yellow-500',
    critical: 'bg-red-500 animate-pulse',
    error: 'bg-red-500 animate-pulse',
    unknown: 'bg-slate-500',
  }[health] || 'bg-slate-500';

  return (
    <header className="h-16 bg-surface-800 border-b border-slate-700/50 flex items-center px-6 gap-4 shrink-0">
      {/* Left: Title */}
      <div className="flex items-center gap-3 mr-4">
        <div className="hidden md:flex items-center gap-2">
          {/* Monitoring Mode Badge */}
          {isDemo ? (
            <span className="flex items-center gap-1.5 px-2.5 py-1 bg-purple-900/40 border border-purple-700/50 rounded-full text-xs font-medium text-purple-300">
              <FlaskConical size={11} />
              Demo Mode
            </span>
          ) : (
            <span className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-900/40 border border-emerald-700/50 rounded-full text-xs font-medium text-emerald-300">
              <Activity size={11} />
              Live Monitoring
            </span>
          )}
        </div>

        {/* System health */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 bg-surface-700 rounded-full text-xs">
          <span className={clsx('w-2 h-2 rounded-full', healthDot)} />
          <span className={clsx('font-medium capitalize', healthColor)}>{health}</span>
        </div>
      </div>

      {/* Center: Search */}
      <div className="flex-1 max-w-md">
        <button
          onClick={() => setSearchOpen(s => !s)}
          className="w-full flex items-center gap-2 px-3 py-2 bg-surface-700 border border-slate-700/50 rounded-lg text-sm text-slate-400 hover:border-brand-500/50 transition-colors"
        >
          <Search size={14} />
          <span>Search incidents, metrics, logs…</span>
          <kbd className="ml-auto text-xs bg-surface-600 px-1.5 py-0.5 rounded border border-slate-600/50 font-mono">⌘K</kbd>
        </button>
      </div>

      {/* Right: actions */}
      <div className="flex items-center gap-2 ml-auto">
        <button className="relative p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-surface-700 transition-colors">
          <Bell size={18} />
          <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-red-500 rounded-full" />
        </button>
        <button className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-surface-700 transition-colors">
          <User size={18} />
        </button>
      </div>
    </header>
  );
}
