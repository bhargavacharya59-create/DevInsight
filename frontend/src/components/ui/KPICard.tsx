import clsx from 'clsx';
import type { LucideIcon } from 'lucide-react';

interface KPICardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  iconColor?: string;
  subtext?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
}

export default function KPICard({
  label, value, icon: Icon, iconColor = 'text-brand-400',
  subtext, trend, trendValue,
}: KPICardProps) {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between mb-3">
        <div className={clsx('p-2.5 rounded-lg bg-surface-700', iconColor)}>
          <Icon size={18} />
        </div>
        {trend && trendValue && (
          <span className={clsx('text-xs font-medium', {
            'text-red-400': trend === 'up',
            'text-emerald-400': trend === 'down',
            'text-slate-400': trend === 'neutral',
          })}>
            {trendValue}
          </span>
        )}
      </div>
      <div>
        <p className="text-2xl font-bold text-white mb-0.5">{value}</p>
        <p className="text-sm text-slate-400">{label}</p>
        {subtext && <p className="text-xs text-slate-500 mt-1">{subtext}</p>}
      </div>
    </div>
  );
}
