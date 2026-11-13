export type Severity = 'critical' | 'high' | 'medium' | 'low';
export type IncidentStatus = 'open' | 'investigating' | 'resolved' | 'closed';
export type ServiceStatus = 'healthy' | 'degraded' | 'unhealthy' | 'unknown';
export type RCAStatus = 'pending' | 'in_progress' | 'completed' | 'insufficient_data';

export interface Incident {
  id: string;
  title: string;
  description?: string;
  severity: Severity;
  status: IncidentStatus;
  affected_service?: string;
  detected_at: string;
  started_at?: string;
  resolved_at?: string;
  updated_at: string;
  anomaly_score?: number;
  rca_status: RCAStatus;
  probable_root_cause?: string;
  confidence_score?: number;
  ai_explanation?: string;
  related_metrics?: Record<string, unknown>;
  related_logs?: unknown[];
  related_traces?: unknown[];
  is_demo: boolean;
  acknowledged: boolean;
  acknowledged_at?: string;
  events?: IncidentEvent[];
  rca_results?: RCAResult[];
  recommendations?: Recommendation[];
}

export interface IncidentEvent {
  id: string;
  incident_id: string;
  event_type: string;
  description: string;
  created_at: string;
  metadata?: Record<string, unknown>;
}

export interface RCAResult {
  id: string;
  incident_id: string;
  created_at: string;
  root_cause_summary?: string;
  confidence: number;
  candidates?: RCACandidate[];
  evidence_metrics?: EvidenceMetric[];
  evidence_logs?: EvidenceLog[];
  evidence_traces?: EvidenceTrace[];
  deployment_correlation?: DeploymentCorrelation;
  ai_explanation?: string;
  ai_available: boolean;
}

export interface RCACandidate {
  rank: number;
  title: string;
  description?: string;
  confidence: number;
  evidence?: Evidence[];
  reasoning?: string;
  recommended_investigation?: string;
}

export interface Evidence {
  kind: 'metric' | 'log' | 'trace' | 'deployment';
  description: string;
  weight: number;
  source: string;
}

export interface EvidenceMetric {
  type: string;
  service: string;
  metric: string;
  current: number;
  baseline: number;
  change_pct: number;
  severity: string;
  description: string;
}

export interface EvidenceLog {
  type: string;
  service: string;
  count?: number;
  weight: number;
  description: string;
  sample_message?: string;
}

export interface EvidenceTrace {
  type: string;
  service: string;
  description: string;
  error_rate?: number;
}

export interface DeploymentCorrelation {
  correlated: boolean;
  deployments: DeploymentEvent[];
}

export interface DeploymentEvent {
  service: string;
  version?: string;
  deployed_at: string;
  deployed_by?: string;
  minutes_before_incident?: number;
  strong_correlation?: boolean;
}

export interface Recommendation {
  id: string;
  incident_id: string;
  category: string;
  action: string;
  priority: number;
  created_at: string;
}

export interface ServiceHealth {
  name: string;
  display_name: string;
  status: ServiceStatus;
  error_rate: number;
  latency_ms: number;
  request_rate: number;
  cpu_utilization?: number;
  memory_utilization?: number;
  dependencies: string[];
  is_demo: boolean;
}

export interface MetricDataPoint {
  timestamp: string;
  value: number;
}

export interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
  service: string;
  trace_id?: string;
  span_id?: string;
  request_id?: string;
  is_demo?: boolean;
}

export interface TraceSpan {
  trace_id: string;
  span_id: string;
  parent_span_id?: string;
  service: string;
  operation: string;
  start_time: string;
  duration_ms: number;
  status: string;
  error_message?: string;
  is_demo?: boolean;
}

export interface DemoScenario {
  id: string;
  name: string;
  description: string;
  category: string;
  duration_seconds: number;
}

export interface OverviewData {
  kpis: {
    total_incidents: number;
    critical_incidents: number;
    active_incidents: number;
    resolved_incidents: number;
    avg_detection_time_minutes: number;
    avg_resolution_time_minutes: number;
    system_health: string;
    system_health_score: number;
  };
  monitoring_mode: string;
  is_demo: boolean;
  current_metrics: Record<string, number>;
  services: ServiceHealth[];
  charts: Record<string, MetricDataPoint[]>;
  active_scenario?: string;
}
