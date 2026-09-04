const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

async function fetchApi(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errorData.detail || `API Error: ${response.status}`);
  }

  return response.json();
}

export const api = {
  createSession: (data = { title: 'New Research' }) => 
    fetchApi('/sessions/', { method: 'POST', body: JSON.stringify(data) }),

  getSessions: (limit = 20, cursor = null) => {
    const query = new URLSearchParams({ limit });
    if (cursor) query.append('cursor', cursor);
    return fetchApi(`/sessions/?${query.toString()}`);
  },

  getSession: (id) => fetchApi(`/sessions/${id}`),

  submitQuery: (sessionId, text, mode = 'deep') => 
    fetchApi(`/sessions/${sessionId}/queries/`, {
      method: 'POST',
      body: JSON.stringify({ text, mode }),
    }),

  getQuery: (queryId) => fetchApi(`/queries/${queryId}`),

  getEvidence: (queryId) => fetchApi(`/queries/${queryId}/evidence`),
  
  resolveContradiction: (id, resolutionData) => fetchApi(`/contradictions/${id}/resolve`, {
    method: 'POST',
    body: JSON.stringify(resolutionData),
  }),

  getDecisionMemo: (queryId) => fetchApi(`/queries/${queryId}/artifacts/decision-memo`),
  generateDecisionMemo: (queryId) => fetchApi(`/queries/${queryId}/artifacts/decision-memo`, { method: 'POST' }),
  
  getResearchReport: (queryId) => fetchApi(`/queries/${queryId}/artifacts/research-report`),
  generateResearchReport: (queryId) => fetchApi(`/queries/${queryId}/artifacts/research-report`, { method: 'POST' }),
  
  getComparisonTable: (queryId) => fetchApi(`/queries/${queryId}/artifacts/comparison-table`),
  getExportPackageUrl: (queryId) => `${BASE_URL}/queries/${queryId}/artifacts/export-package`,
  
  getSources: (queryId, sourceType = null) => {
    const params = sourceType ? `?source_type=${sourceType}` : '';
    return fetchApi(`/queries/${queryId}/sources${params}`);
  },

  // Phase 12 Continuous Intelligence Monitoring Endpoints (/api/v1/monitoring/*)
  listMonitoringJobs: (params = {}) => {
    const search = new URLSearchParams();
    if (params.project_id) search.append('project_id', params.project_id);
    if (params.session_id) search.append('session_id', params.session_id);
    if (params.status) search.append('status', params.status);
    const q = search.toString() ? `?${search.toString()}` : '';
    return fetchApi(`/monitoring/jobs${q}`);
  },

  getMonitoringJob: (id) => fetchApi(`/monitoring/jobs/${id}`),

  createMonitoringJob: (data) =>
    fetchApi('/monitoring/jobs', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateMonitoringJob: (id, data) =>
    fetchApi(`/monitoring/jobs/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  deleteMonitoringJob: (id) =>
    fetchApi(`/monitoring/jobs/${id}`, {
      method: 'DELETE',
    }),

  triggerMonitoringJobRun: (id, payload = {}) =>
    fetchApi(`/monitoring/jobs/${id}/run`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getMonitoringJobLogs: (id) => fetchApi(`/monitoring/jobs/${id}/logs`),

  createBaselineSnapshot: (data) =>
    fetchApi('/monitoring/baselines', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getBaselineSnapshot: (id) => fetchApi(`/monitoring/baselines/${id}`),

  listDecisionAlerts: (params = {}) => {
    const search = new URLSearchParams();
    if (params.job_id) search.append('job_id', params.job_id);
    if (params.project_id) search.append('project_id', params.project_id);
    if (params.session_id) search.append('session_id', params.session_id);
    if (params.status) search.append('status', params.status);
    if (params.severity) search.append('severity', params.severity);
    const q = search.toString() ? `?${search.toString()}` : '';
    return fetchApi(`/monitoring/alerts${q}`);
  },

  acknowledgeDecisionAlert: (id) =>
    fetchApi(`/monitoring/alerts/${id}/acknowledge`, {
      method: 'POST',
    }),

  // Phase 12 Project Memory & Research Heuristics Endpoints (/api/v1/memory/*)
  listMemoryItems: (params = {}) => {
    const search = new URLSearchParams();
    if (params.project_id) search.append('project_id', params.project_id);
    if (params.session_id) search.append('session_id', params.session_id);
    if (params.memory_type) search.append('memory_type', params.memory_type);
    if (params.validity_status) search.append('validity_status', params.validity_status);
    if (params.human_approval_status) search.append('human_approval_status', params.human_approval_status);
    if (params.key) search.append('key', params.key);
    const q = search.toString() ? `?${search.toString()}` : '';
    return fetchApi(`/memory/items${q}`);
  },

  getMemoryItem: (id) => fetchApi(`/memory/items/${id}`),

  createMemoryItem: (data) =>
    fetchApi('/memory/items', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateMemoryItem: (id, data) =>
    fetchApi(`/memory/items/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  approveMemoryItem: (id, approval_status = 'APPROVED') =>
    fetchApi(`/memory/items/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ approval_status }),
    }),

  getResearchHeuristics: (domain, project_id = null) => {
    const search = new URLSearchParams({ domain });
    if (project_id) search.append('project_id', project_id);
    return fetchApi(`/memory/heuristics?${search.toString()}`);
  },

  createOrUpdateHeuristics: (data) =>
    fetchApi('/memory/heuristics', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  injectMemoryContext: (data) =>
    fetchApi('/memory/inject-context', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

