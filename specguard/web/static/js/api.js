/**
 * SpecGuard Local API Client
 * Clean asynchronous HTTP client communicating with localhost FastAPI backend.
 * Guaranteed 100% offline — Zero external requests.
 */

class ApiClient {
  constructor(baseUrl = "/api") {
    this.baseUrl = baseUrl;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = options.headers || {};

    if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }

    try {
      const response = await fetch(url, { ...options, headers });
      if (!response.ok) {
        let errMessage = `HTTP ${response.status}: ${response.statusText}`;
        try {
          const errData = await response.json();
          errMessage = errData.detail || errMessage;
        } catch (_) {}
        throw new Error(errMessage);
      }
      return await response.json();
    } catch (err) {
      console.error(`[API Error] ${endpoint}:`, err);
      throw err;
    }
  }

  // Dashboard
  dashboard = {
    getStats: () => this.request("/dashboard/stats"),
    getRecent: (limit = 8) => this.request(`/dashboard/recent?limit=${limit}`)
  };

  // Analysis
  analysis = {
    upload: (file) => {
      const formData = new FormData();
      formData.append("file", file);
      return this.request("/analysis/upload", { method: "POST", body: formData });
    },
    getSamples: () => this.request("/analysis/samples"),
    start: (data) => this.request("/analysis/start", { method: "POST", body: JSON.stringify(data) }),
    getJob: (jobId) => this.request(`/analysis/jobs/${jobId}`),
    cancel: (jobId) => this.request(`/analysis/jobs/${jobId}/cancel`, { method: "POST" })
  };

  // Documents & Pages
  documents = {
    getInfo: (docId) => this.request(`/documents/${encodeURIComponent(docId)}`),
    getPageImageUrl: (docId, pageNum, zoom = 1.5) =>
      `${this.baseUrl}/documents/${encodeURIComponent(docId)}/pages/${pageNum}/image?zoom=${zoom}`,
    downloadFileUrl: (docId) =>
      `${this.baseUrl}/documents/${encodeURIComponent(docId)}/file`
  };

  // Findings
  findings = {
    list: (params = {}) => {
      const qs = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== "") qs.append(k, v);
      });
      return this.request(`/findings?${qs.toString()}`);
    },
    get: (findingId, sessionId = null) => {
      const qs = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : "";
      return this.request(`/findings/${encodeURIComponent(findingId)}${qs}`);
    }
  };

  // History & Revision Comparisons
  history = {
    list: (params = {}) => {
      const qs = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== "") qs.append(k, v);
      });
      return this.request(`/history?${qs.toString()}`);
    },
    get: (comparisonId) => this.request(`/history/${encodeURIComponent(comparisonId)}`),
    delete: (comparisonId) => this.request(`/history/${encodeURIComponent(comparisonId)}`, { method: "DELETE" }),
    diff: (id1, id2) => this.request(`/history/diff/${encodeURIComponent(id1)}/${encodeURIComponent(id2)}`)
  };

  // Reports
  reports = {
    generate: (data) => this.request("/reports/generate", { method: "POST", body: JSON.stringify(data) }),
    previewUrl: (sessionId) => `${this.baseUrl}/reports/preview/${encodeURIComponent(sessionId)}`
  };

  // Standards & Templates
  standards = {
    list: () => this.request("/standards"),
    getDomain: (domain) => this.request(`/standards/${encodeURIComponent(domain)}`)
  };

  // ML Models & Diagnostics
  models = {
    list: (params = {}) => {
      const qs = new URLSearchParams(params).toString();
      return this.request(`/models${qs ? `?${qs}` : ""}`);
    },
    hardware: () => this.request("/models/hardware"),
    datasetHealth: (domain = null) => {
      const qs = domain ? `?domain=${encodeURIComponent(domain)}` : "";
      return this.request(`/models/dataset-health${qs}`);
    },
    activate: (id) => this.request(`/models/${encodeURIComponent(id)}/activate`, { method: "POST" }),
    deactivate: (id) => this.request(`/models/${encodeURIComponent(id)}/deactivate`, { method: "POST" }),
    verifyHash: (id) => this.request(`/models/${encodeURIComponent(id)}/verify-hash`, { method: "POST" }),
    compare: (id1, id2) => this.request(`/models/compare/${encodeURIComponent(id1)}/${encodeURIComponent(id2)}`)
  };

  // Settings & Storage Telemetry
  settings = {
    health: () => this.request("/settings/health"),
    storage: () => this.request("/settings/storage"),
    audit: (params = {}) => {
      const qs = new URLSearchParams(params).toString();
      return this.request(`/settings/audit${qs ? `?${qs}` : ""}`);
    }
  };
}

// Export singleton instance
window.api = new ApiClient();
