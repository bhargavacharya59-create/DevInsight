import clsx from 'clsx';
import type { Severity } from '../../types';

export default function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span className={clsx(
      'inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold border uppercase tracking-wide',
      severity === 'critical' && 'bg-red-900/50 text-red-300 border-red-700/50',
      severity === 'high' && 'bg-orange-900/50 text-orange-300 border-orange-700/50',
      severity === 'medium' && 'bg-yellow-900/50 text-yellow-300 border-yellow-700/50',
      severity === 'low' && 'bg-blue-900/50 text-blue-300 border-blue-700/50',
    )}>
      {severity}
    </span>
  );
}
