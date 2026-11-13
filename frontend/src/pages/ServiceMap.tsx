import { useEffect, useState, useRef } from 'react';
import { getServiceMap } from '../api/client';
import LoadingSpinner from '../components/ui/LoadingSpinner';
import ErrorState from '../components/ui/ErrorState';
import { serviceStatusColor, serviceStatusDot } from '../utils/format';
import { FlaskConical } from 'lucide-react';
import clsx from 'clsx';
import type { ServiceStatus } from '../types';

interface MapNode {
  id: string;
  label: string;
  status: ServiceStatus;
  error_rate: number;
  latency_ms: number;
  request_rate: number;
}

interface MapEdge {
  source: string;
  target: string;
  label: string;
}

// Simple SVG-based service map layout
const POSITIONS: Record<string, { x: number; y: number }> = {
  'shopsphere-frontend': { x: 50, y: 15 },
  'shopsphere-api': { x: 50, y: 35 },
  'order-service': { x: 25, y: 60 },
  'payment-service': { x: 75, y: 60 },
  'database': { x: 50, y: 85 },
};

export default function ServiceMap() {
  const [nodes, setNodes] = useState<MapNode[]>([]);
  const [edges, setEdges] = useState<MapEdge[]>([]);
  const [isDemo, setIsDemo] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<MapNode | null>(null);

  const load = () => {
    setLoading(true);
    getServiceMap()
      .then(d => { setNodes(d.nodes); setEdges(d.edges); setIsDemo(d.is_demo); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  if (loading) return <LoadingSpinner size="lg" className="h-full" />;
  if (error) return <ErrorState message={error} onRetry={load} />;

  const STATUS_COLORS: Record<string, string> = {
    healthy: '#10b981',
    degraded: '#f59e0b',
    unhealthy: '#ef4444',
    unknown: '#64748b',
  };

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Service Map</h1>
          {isDemo && <span className="demo-badge mt-1"><FlaskConical size={10} /> Simulated dependencies</span>}
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        {/* SVG map */}
        <div className="xl:col-span-2 card p-5">
          <svg viewBox="0 0 100 100" className="w-full" style={{ height: '500px' }}>
            {/* Edges */}
            {edges.map((e, i) => {
              const src = POSITIONS[e.source];
              const tgt = POSITIONS[e.target];
              if (!src || !tgt) return null;
              const srcNode = nodes.find(n => n.id === e.source);
              const color = srcNode ? STATUS_COLORS[srcNode.status] : '#475569';
              return (
                <g key={i}>
                  <line
                    x1={`${src.x}%`} y1={`${src.y}%`}
                    x2={`${tgt.x}%`} y2={`${tgt.y}%`}
                    stroke={color}
                    strokeWidth="0.5"
                    strokeOpacity="0.5"
                    strokeDasharray={srcNode?.status !== 'healthy' ? '2,2' : undefined}
                  />
                </g>
              );
            })}

            {/* Nodes */}
            {nodes.map(node => {
              const pos = POSITIONS[node.id];
              if (!pos) return null;
              const color = STATUS_COLORS[node.status] || '#475569';
              const isSelected = selected?.id === node.id;

              return (
                <g
                  key={node.id}
                  transform={`translate(${pos.x},${pos.y})`}
                  style={{ cursor: 'pointer' }}
                  onClick={() => setSelected(node)}
                >
                  <circle r="5" fill="#141c36" stroke={color} strokeWidth={isSelected ? 1.5 : 0.8} />
                  {node.status === 'unhealthy' && (
                    <circle r="6" fill="none" stroke={color} strokeWidth="0.5" opacity="0.4">
                      <animate attributeName="r" values="5;7;5" dur="2s" repeatCount="indefinite" />
                      <animate attributeName="opacity" values="0.4;0;0.4" dur="2s" repeatCount="indefinite" />
                    </circle>
                  )}
                  <text
                    y="8"
                    textAnchor="middle"
                    fill="#94a3b8"
                    fontSize="2.8"
                    style={{ userSelect: 'none' }}
                  >
                    {node.label}
                  </text>
                  <text
                    y="-7"
                    textAnchor="middle"
                    fill={color}
                    fontSize="2"
                    style={{ userSelect: 'none' }}
                  >
                    {node.error_rate.toFixed(1)}% err
                  </text>
                </g>
              );
            })}
          </svg>
          {isDemo && (
            <p className="text-xs text-slate-500 text-center mt-2">
              [DEMO] Dependency graph is based on simulated ShopSphere architecture
            </p>
          )}
        </div>

        {/* Node detail */}
        <div className="space-y-3">
          <h2 className="text-sm font-medium text-slate-400">
            {selected ? 'Service Details' : 'Click a service node to inspect'}
          </h2>

          {nodes.map(node => (
            <div
              key={node.id}
              onClick={() => setSelected(node)}
              className={clsx('card p-4 cursor-pointer transition-colors', selected?.id === node.id && 'border-brand-500/50')}
            >
              <div className="flex items-center gap-2 mb-2">
                <span className={clsx('w-2 h-2 rounded-full', serviceStatusDot(node.status))} />
                <span className="text-sm font-medium text-slate-200">{node.label}</span>
                <span className={clsx('text-xs ml-auto capitalize', serviceStatusColor(node.status))}>{node.status}</span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div>
                  <p className="text-slate-500">Error</p>
                  <p className={clsx('font-mono font-semibold', node.error_rate > 5 ? 'text-red-400' : 'text-slate-300')}>
                    {node.error_rate.toFixed(1)}%
                  </p>
                </div>
                <div>
                  <p className="text-slate-500">Latency</p>
                  <p className={clsx('font-mono font-semibold', node.latency_ms > 1000 ? 'text-red-400' : 'text-slate-300')}>
                    {node.latency_ms.toFixed(0)}ms
                  </p>
                </div>
                <div>
                  <p className="text-slate-500">Rate</p>
                  <p className="font-mono font-semibold text-slate-300">{node.request_rate.toFixed(0)}/s</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
