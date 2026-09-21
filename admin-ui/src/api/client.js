/**
 * admin-ui/src/api/client.js
 * Centralized API Client with automated Bearer JWT injection, 
 * standardized error parsing, and session expiration interceptors.
 */

const TOKEN_STORAGE_KEY = 'ragai_admin_jwt';

export function getStoredToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY) || '';
}

export function setStoredToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
}

export async function apiFetch(endpoint, options = {}) {
  const token = getStoredToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const url = endpoint.startsWith('http') ? endpoint : endpoint;

  let response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (netErr) {
    throw new Error(`Network error: ${netErr.message || 'Server unreachable'}`);
  }

  // Handle Unauthorized (401)
  if (response.status === 401 && !endpoint.includes('/admin/auth/login')) {
    setStoredToken('');
    window.dispatchEvent(new CustomEvent('ragai-session-expired'));
    throw new Error('Your administrative session has expired. Please log in again.');
  }

  // Parse JSON or text
  const contentType = response.headers.get('content-type') || '';
  let data;
  if (contentType.includes('application/json')) {
    data = await response.json();
  } else {
    data = await response.text();
  }

  if (!response.ok) {
    const errorMsg =
      data?.detail?.error?.message ||
      data?.detail?.message ||
      (typeof data?.detail === 'string' ? data.detail : null) ||
      data?.message ||
      `HTTP Error ${response.status}: ${response.statusText}`;
    const error = new Error(errorMsg);
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
}

// -----------------------------------------------------------------------------
// ENDPOINT MODULES
// -----------------------------------------------------------------------------
export const adminApi = {
  // Authentication & Users
  auth: {
    login: (username, password) =>
      apiFetch('/api/v1/admin/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      }),
    getMe: () => apiFetch('/api/v1/admin/auth/me'),
    changePassword: (current_password, new_password) =>
      apiFetch('/api/v1/admin/auth/change-password', {
        method: 'POST',
        body: JSON.stringify({ current_password, new_password }),
      }),
    getUsers: () => apiFetch('/api/v1/admin/auth/users'),
    createUser: (userData) =>
      apiFetch('/api/v1/admin/auth/users', {
        method: 'POST',
        body: JSON.stringify(userData),
      }),
    toggleUserStatus: (userId, is_active) =>
      apiFetch(`/api/v1/admin/auth/users/${userId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ is_active }),
      }),
    deleteUser: (userId) =>
      apiFetch(`/api/v1/admin/auth/users/${userId}`, {
        method: 'DELETE',
      }),
  },

  // Brain Cortex
  brain: {
    getGraph: (dept = 'all') =>
      apiFetch(`/api/v1/admin/brain/graph${dept !== 'all' ? `?department=${encodeURIComponent(dept)}` : ''}`),
    getTelemetry: () => apiFetch('/api/v1/admin/brain/telemetry'),
    rebuild: () => apiFetch('/api/v1/admin/brain/rebuild', { method: 'POST' }),
    fireSynapse: (query, department = 'all') =>
      apiFetch('/api/v1/admin/brain/fire-synapse', {
        method: 'POST',
        body: JSON.stringify({ query, department }),
      }),
  },

  // Ingest & Watched Folders
  ingest: {
    getFolders: () => apiFetch('/api/v1/admin/folders'),
    registerFolder: (folderData) =>
      apiFetch('/api/v1/admin/folders', {
        method: 'POST',
        body: JSON.stringify(folderData),
      }),
    deleteFolder: (folderId) =>
      apiFetch(`/api/v1/admin/folders/${folderId}`, {
        method: 'DELETE',
      }),
    scanFolder: (folderId) =>
      apiFetch(`/api/v1/admin/folders/${folderId}/scan`, {
        method: 'POST',
      }),
  },

  // Ingestion Pipeline
  pipeline: {
    getStreamUrl: () => '/api/v1/admin/ingest/stream',
  },

  // Failed Files & DLQ
  failed: {
    getFailedFiles: (page = 1, pageSize = 50) =>
      apiFetch(`/api/v1/admin/failed-files?page=${page}&page_size=${pageSize}`),
    retry: (id) =>
      apiFetch(`/api/v1/admin/failed-files/${encodeURIComponent(id)}/retry`, {
        method: 'POST',
      }),
    retryAll: () =>
      apiFetch('/api/v1/admin/failed-files/retry-all', {
        method: 'POST',
      }),
    dismiss: (id) =>
      apiFetch(`/api/v1/admin/failed-files/${encodeURIComponent(id)}`, {
        method: 'DELETE',
      }),
    clearAll: () =>
      apiFetch('/api/v1/admin/failed-files/clear-all', {
        method: 'DELETE',
      }),
  },

  // Documents
  docs: {
    getDocuments: (params = '') =>
      apiFetch(`/api/v1/admin/documents${params ? `?${params}` : ''}`),
    getChunks: (docId) =>
      apiFetch(`/api/v1/admin/documents/${encodeURIComponent(docId)}/chunks`),
    deleteDocument: (docId) =>
      apiFetch(`/api/v1/admin/documents/${encodeURIComponent(docId)}`, {
        method: 'DELETE',
      }),
    purgeAll: () =>
      apiFetch('/api/v1/admin/documents/purge', {
        method: 'POST',
      }),
  },

  // API Keys
  apiKeys: {
    getKeys: () => apiFetch('/api/v1/admin/api-keys'),
    createKey: (keyData) =>
      apiFetch('/api/v1/admin/api-keys', {
        method: 'POST',
        body: JSON.stringify(keyData),
      }),
    toggleStatus: (keyId, is_active) =>
      apiFetch(`/api/v1/admin/api-keys/${keyId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ is_active }),
      }),
    deleteKey: (keyId) =>
      apiFetch(`/api/v1/admin/api-keys/${keyId}`, {
        method: 'DELETE',
      }),
  },

  // URL Firewall
  firewall: {
    getRules: () => apiFetch('/api/v1/admin/url-rules'),
    createRule: (ruleData) =>
      apiFetch('/api/v1/admin/url-rules', {
        method: 'POST',
        body: JSON.stringify(ruleData),
      }),
    toggleStatus: (ruleId, is_active) =>
      apiFetch(`/api/v1/admin/url-rules/${ruleId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ is_active }),
      }),
    deleteRule: (ruleId) =>
      apiFetch(`/api/v1/admin/url-rules/${ruleId}`, {
        method: 'DELETE',
      }),
    testRule: (url) =>
      apiFetch('/api/v1/admin/url-rules/test', {
        method: 'POST',
        body: JSON.stringify({ url }),
      }),
  },

  // Scraper & Crawler
  scraper: {
    getJobs: () => apiFetch('/api/v1/admin/scraper/jobs'),
    runJob: (jobId) =>
      apiFetch(`/api/v1/admin/scraper/jobs/${jobId}/run`, {
        method: 'POST',
      }),
    stopJob: () =>
      apiFetch('/api/v1/admin/scraper/stop', {
        method: 'POST',
      }),
    getStatus: () => apiFetch('/api/v1/admin/scraper/status'),
    getManifest: (params = '') =>
      apiFetch(`/api/v1/admin/scraper/manifest${params ? `?${params}` : ''}`),
    crawlSingle: (url, dept, sem, course) =>
      apiFetch('/api/v1/admin/scraper/crawl-single', {
        method: 'POST',
        body: JSON.stringify({ url, department: dept, semester: sem, course }),
      }),
    cleanupTemp: () =>
      apiFetch('/api/v1/admin/scraper/cleanup', {
        method: 'POST',
      }),
    purgeRagData: () =>
      apiFetch('/api/v1/admin/scraper/purge-rag-data', {
        method: 'POST',
      }),
  },

  // Cryptographic Manifest
  manifest: {
    getEntries: (params = '') =>
      apiFetch(`/api/v1/admin/manifest${params ? `?${params}` : ''}`),
    verifyIntegrity: () =>
      apiFetch('/api/v1/admin/manifest/verify', {
        method: 'POST',
      }),
  },

  // Security Operations Center
  security: {
    getStats: () => apiFetch('/api/v1/admin/security/stats'),
    getIncidents: (params = '') =>
      apiFetch(`/api/v1/admin/security/incidents${params ? `?${params}` : ''}`),
    clearIncidents: () =>
      apiFetch('/api/v1/admin/security/incidents/clear', {
        method: 'POST',
      }),
    simulateEvent: (eventData) =>
      apiFetch('/api/v1/admin/security/simulate-event', {
        method: 'POST',
        body: JSON.stringify(eventData),
      }),
  },

  // Diagnostics Clinic & Self-Improver
  diagnostics: {
    getClinic: () => apiFetch('/api/v1/admin/rag/diagnostics'),
    getHistory: () => apiFetch('/api/v1/admin/rag/self-improve/history'),
    triggerSelfImprove: () =>
      apiFetch('/api/v1/admin/rag/self-improve', {
        method: 'POST',
      }),
    getPromptRules: () => apiFetch('/api/v1/admin/rag/prompt-rules'),
    resetRules: () =>
      apiFetch('/api/v1/admin/rag/prompt-rules/reset', {
        method: 'POST',
      }),
    clearDiagnostics: () =>
      apiFetch('/api/v1/admin/rag/diagnostics/clear', {
        method: 'POST',
      }),
  },

  // System & Models
  settings: {
    getModelStatus: () => apiFetch('/api/v1/admin/models/status'),
    saveHfToken: (token) =>
      apiFetch('/api/v1/admin/settings/hf-token', {
        method: 'POST',
        body: JSON.stringify({ token }),
      }),
    preloadModel: () =>
      apiFetch('/api/v1/admin/models/preload', {
        method: 'POST',
      }),
    getServicesHealth: () => apiFetch('/api/v1/admin/system/services-health'),
    flushCuda: () =>
      apiFetch('/api/v1/admin/system/flush-cuda', {
        method: 'POST',
      }),
  },

  // Server Migration
  migration: {
    getSourceStatus: () => apiFetch('/api/v1/admin/migration/source-status'),
    probeTarget: (spec) =>
      apiFetch('/api/v1/admin/migration/probe', {
        method: 'POST',
        body: JSON.stringify(spec),
      }),
    startMigration: (spec) =>
      apiFetch('/api/v1/admin/migration/start', {
        method: 'POST',
        body: JSON.stringify(spec),
      }),
    getStatus: () => apiFetch('/api/v1/admin/migration/status'),
    cancelMigration: () =>
      apiFetch('/api/v1/admin/migration/cancel', {
        method: 'POST',
      }),
    getParity: () => apiFetch('/api/v1/admin/migration/parity'),
    cutover: (spec) =>
      apiFetch('/api/v1/admin/migration/cutover', {
        method: 'POST',
        body: JSON.stringify(spec),
      }),
    rollback: () =>
      apiFetch('/api/v1/admin/migration/rollback', {
        method: 'POST',
      }),
  },
};
