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
};
