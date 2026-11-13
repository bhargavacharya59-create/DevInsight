import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'Request failed';
    return Promise.reject(new Error(message));
  }
);

export default api;

// ── Health ────────────────────────────────────────────────────────────────────
export const getHealth = () => axios.get('/health').then(r => r.data);

// ── Dashboard ─────────────────────────────────────────────────────────────────
export const getOverview = () => api.get('/dashboard/overview').then(r => r.data);

// ── Incidents ─────────────────────────────────────────────────────────────────
export const getIncidents = (params?: Record<string, unknown>) =>
  api.get('/incidents', { params }).then(r => r.data);

export const getIncident = (id: string) =>
  api.get(`/incidents/${id}`).then(r => r.data);

export const createIncident = (data: Record<string, unknown>) =>
  api.post('/incidents', data).then(r => r.data);

export const acknowledgeIncident = (id: string) =>
  api.post(`/incidents/${id}/acknowledge`).then(r => r.data);

export const resolveIncident = (id: string) =>
  api.post(`/incidents/${id}/resolve`).then(r => r.data);

export const getIncidentRCA = (id: string) =>
  api.get(`/incidents/${id}/rca`).then(r => r.data);

// ── Metrics ───────────────────────────────────────────────────────────────────
export const getMetrics = (params?: Record<string, unknown>) =>
  api.get('/metrics', { params }).then(r => r.data);

export const getCurrentMetrics = () =>
  api.get('/metrics/current').then(r => r.data);

// ── Logs ──────────────────────────────────────────────────────────────────────
export const getLogs = (params?: Record<string, unknown>) =>
  api.get('/logs', { params }).then(r => r.data);

// ── Traces ────────────────────────────────────────────────────────────────────
export const getTraces = (params?: Record<string, unknown>) =>
  api.get('/traces', { params }).then(r => r.data);

// ── Services ──────────────────────────────────────────────────────────────────
export const getServices = () => api.get('/services').then(r => r.data);
export const getServiceMap = () => api.get('/services/map').then(r => r.data);
export const getTelemetrySources = () => api.get('/services/telemetry-sources').then(r => r.data);

// ── Anomaly ───────────────────────────────────────────────────────────────────
export const detectAnomaly = (data: Record<string, unknown>) =>
  api.post('/anomaly/detect', data).then(r => r.data);

export const trainModel = () => api.post('/anomaly/train').then(r => r.data);
export const getModelStatus = () => api.get('/anomaly/status').then(r => r.data);

// ── RCA ───────────────────────────────────────────────────────────────────────
export const runRCA = (data: { incident_id: string; include_demo_evidence?: boolean }) =>
  api.post('/rca/investigate', data).then(r => r.data);

// ── Demo ──────────────────────────────────────────────────────────────────────
export const getDemoScenarios = () => api.get('/demo/scenarios').then(r => r.data);
export const startScenario = (id: string) => api.post(`/demo/scenarios/${id}/start`).then(r => r.data);
export const stopScenario = (id: string) => api.post(`/demo/scenarios/${id}/stop`).then(r => r.data);
export const resetDemo = () => api.post('/demo/reset').then(r => r.data);
export const getDemoStatus = () => api.get('/demo/status').then(r => r.data);

// ── AI ────────────────────────────────────────────────────────────────────────
export const explainIncident = (incident_id: string) =>
  api.post('/ai/explain', { incident_id }).then(r => r.data);

export const askQuestion = (data: { question: string; incident_id?: string; context?: Record<string, unknown> }) =>
  api.post('/ai/ask', data).then(r => r.data);

// ── GitHub ────────────────────────────────────────────────────────────────────
export const getGithubStatus = () => api.get('/github/status').then(r => r.data);
export const getCommits = (branch = 'main') => api.get('/github/commits', { params: { branch } }).then(r => r.data);
export const getCommitDiff = (sha: string) => api.get(`/github/commits/${sha}`).then(r => r.data);
export const getPullRequests = (state = 'open') => api.get('/github/pull-requests', { params: { state } }).then(r => r.data);
export const getWorkflowRuns = () => api.get('/github/workflows').then(r => r.data);
export const getWorkflowJobs = (runId: number) => api.get(`/github/workflows/${runId}/jobs`).then(r => r.data);

// ── Remediation ───────────────────────────────────────────────────────────────
export const startRemediation = (data: { incident_id: string; retry_count?: number }) =>
  api.post('/remediation/start', data).then(r => r.data);
export const getDemoRemediation = () => api.get('/remediation/demo').then(r => r.data);

// ── Deployments ───────────────────────────────────────────────────────────────
export const getDeployments = () => api.get('/deployments').then(r => r.data);
export const compareDeployment = (id: string) => api.get(`/deployments/${id}/compare`).then(r => r.data);

// ── Integrations ──────────────────────────────────────────────────────────────
export const getIntegrations = () => api.get('/integrations').then(r => r.data);

// ── Webhook events ────────────────────────────────────────────────────────────
export const getWebhookEvents = () => api.get('/webhook/events').then(r => r.data);
