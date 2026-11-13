import clsx from 'clsx';
import type { IncidentStatus } from '../../types';

export default function StatusBadge({ status }: { status: IncidentStatus }) {
  return (
    <span className={clsx(
      'inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium border capitalize',
      status === 'open' && 'bg-red-900/30 text-red-300 border-red-700/30',
      status === 'investigating' && 'bg-yellow-900/30 text-yellow-300 border-yellow-700/30',
      status === 'resolved' && 'bg-emerald-900/30 text-emerald-300 border-emerald-700/30',
      status === 'closed' && 'bg-slate-800 text-slate-400 border-slate-700/30',
    )}>
      <span className={clsx('w-1.5 h-1.5 rounded-full',
        status === 'open' && 'bg-red-400 animate-pulse',
        status === 'investigating' && 'bg-yellow-400',
        status === 'resolved' && 'bg-emerald-400',
        status === 'closed' && 'bg-slate-500',
      )} />
      {status}
    </span>
  );
}
