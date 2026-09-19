window.AgentRagApi = (() => {
  async function request(url, options = {}) {
    const response = await fetch(url, options);
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      const error = new Error(body.message || `请求失败 (${response.status})`);
      error.code = body.code || 'request_failed';
      error.status = response.status;
      throw error;
    }
    return response.status === 204 ? null : response.json();
  }

  return {
    health: () => request('/api/health'),
    listKnowledgeBases: () => request("/api/kbs"),
    createKnowledgeBase: (payload) => request('/api/kbs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }),
    deleteKnowledgeBase: (id) => request(`/api/kbs/${id}`, { method: 'DELETE' }),
    uploadDocument: (kbId, file) => {
      const body = new FormData();
      body.append('file', file);
      return request(`/api/kbs/${kbId}/documents`, { method: 'POST', body });
    },
    getDocument: (id) => request(`/api/documents/${id}`),
    deleteDocument: (id) => request(`/api/documents/${id}`, { method: 'DELETE' })
  };
})();
