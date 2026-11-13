import { format, formatDistanceToNow, parseISO } from 'date-fns';
import type { Severity, ServiceStatus } from '../types';

export function formatDate(iso: string): string {
  try {
    return format(parseISO(iso), 'MMM d, yyyy HH:mm:ss');
  } catch {
    return iso;
  }
}

export function formatRelative(iso: string): string {
  try {
    return formatDistanceToNow(parseISO(iso), { addSuffix: true });
  } catch {
    return iso;
  }
}

export function formatDuration(start: string, end?: string): string {
  try {
    const s = parseISO(start);
    const e = end ? parseISO(end) : new Date();
    const diffMs = e.getTime() - s.getTime();
    const minutes = Math.floor(diffMs / 60000);
    const hours = Math.floor(minutes / 60);
    if (hours > 0) return `${hours}h ${minutes % 60}m`;
    return `${minutes}m`;
  } catch {
    return '–';
  }
}

export function severityColor(severity: Severity): string {
  switch (severity) {
    case 'critical': return 'text-red-400';
    case 'high': return 'text-orange-400';
    case 'medium': return 'text-yellow-400';
    case 'low': return 'text-blue-400';
    default: return 'text-slate-400';
  }
}

export function severityBg(severity: Severity): string {
  switch (severity) {
    case 'critical': return 'bg-red-500/10 border-red-500/30 text-red-400';
    case 'high': return 'bg-orange-500/10 border-orange-500/30 text-orange-400';
    case 'medium': return 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400';
    case 'low': return 'bg-blue-500/10 border-blue-500/30 text-blue-400';
    default: return 'bg-slate-500/10 border-slate-500/30 text-slate-400';
  }
}

export function statusColor(status: string): string {
  switch (status.toLowerCase()) {
    case 'open': return 'text-red-400';
    case 'investigating': return 'text-yellow-400';
    case 'resolved': return 'text-emerald-400';
    case 'closed': return 'text-slate-400';
    default: return 'text-slate-400';
  }
}

export function serviceStatusColor(status: ServiceStatus): string {
  switch (status) {
    case 'healthy': return 'text-emerald-400';
    case 'degraded': return 'text-yellow-400';
    case 'unhealthy': return 'text-red-400';
    default: return 'text-slate-400';
  }
}

export function serviceStatusDot(status: ServiceStatus): string {
  switch (status) {
    case 'healthy': return 'bg-emerald-500';
    case 'degraded': return 'bg-yellow-500';
    case 'unhealthy': return 'bg-red-500 animate-pulse';
    default: return 'bg-slate-500';
  }
}

export function formatNumber(n: number, decimals = 1): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toFixed(decimals);
}

export function formatPercent(n: number): string {
  return `${n.toFixed(1)}%`;
}

export function confidenceColor(confidence: number): string {
  if (confidence >= 0.8) return 'text-emerald-400';
  if (confidence >= 0.6) return 'text-yellow-400';
  if (confidence >= 0.4) return 'text-orange-400';
  return 'text-red-400';
}

export function anomalyScoreColor(score: number): string {
  if (score >= 0.7) return 'text-red-400';
  if (score >= 0.4) return 'text-orange-400';
  if (score >= 0.2) return 'text-yellow-400';
  return 'text-emerald-400';
}
