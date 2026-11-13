import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Activity, AlertTriangle, Search,
  BarChart2, FileText, GitBranch, Bot, Settings,
  Zap, ChevronLeft, ChevronRight, GitPullRequest,
  Wrench, History, Plug,
} from 'lucide-react';
import { useState } from 'react';
import clsx from 'clsx';

const navItems = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, exact: true },
  { to: '/monitoring', label: 'Live Monitoring', icon: Activity },
  { to: '/incidents', label: 'Incidents', icon: AlertTriangle },
  { to: '/rca', label: 'Root Cause Analysis', icon: Search },
  { to: '/cicd', label: 'CI/CD Pipelines', icon: GitPullRequest },
  { to: '/code-fixes', label: 'Code Fixes', icon: Wrench },
  { to: '/deployments', label: 'Deployments', icon: History },
  { to: '/metrics', label: 'Metrics Explorer', icon: BarChart2 },
  { to: '/logs', label: 'Logs Explorer', icon: FileText },
  { to: '/service-map', label: 'Service Map', icon: GitBranch },
  { to: '/ai-assistant', label: 'AI Assistant', icon: Bot },
  { to: '/integrations', label: 'Integrations', icon: Plug },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={clsx(
        'flex flex-col bg-surface-800 border-r border-slate-700/50 transition-all duration-200 shrink-0',
        collapsed ? 'w-16' : 'w-60'
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-4 border-b border-slate-700/50 h-16">
        <div className="shrink-0 w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center">
          <Zap size={16} className="text-white" />
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <span className="block font-semibold text-white text-sm leading-tight">DevInsight AI</span>
            <span className="block text-xs text-slate-400">AIOps Platform</span>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
        {navItems.map(({ to, label, icon: Icon, exact }) => (
          <NavLink
            key={to}
            to={to}
            end={exact}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors group',
                isActive
                  ? 'bg-brand-600/20 text-brand-400 border border-brand-600/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-surface-700'
              )
            }
            title={collapsed ? label : undefined}
          >
            <Icon size={18} className="shrink-0" />
            {!collapsed && <span className="truncate">{label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Collapse toggle */}
      <div className="px-2 pb-3 border-t border-slate-700/50 pt-2">
        <button
          onClick={() => setCollapsed(c => !c)}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-surface-700 text-sm transition-colors"
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          {!collapsed && <span className="text-xs">Collapse</span>}
        </button>
      </div>
    </aside>
  );
}
