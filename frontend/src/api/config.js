const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiConfig = {
  baseUrl: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
};

// ── In-memory access token (set by AuthContext) ──────────

let _accessToken = null;

export function setAccessToken(token) {
  _accessToken = token;
}

export function getAccessToken() {
  return _accessToken;
}

function getAuthHeaders() {
  return _accessToken ? { 'Authorization': `Bearer ${_accessToken}` } : {};
}

// ── API fetcher with auto-refresh on 401 ─────────────────

export async function apiFetch(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;

  const config = {
    ...options,
    credentials: 'include', // Send cookies for refresh token
    headers: {
      ...apiConfig.headers,
      ...getAuthHeaders(),
      ...options.headers,
    },
  };

  const response = await fetch(url, config);

  // Handle 401 Unauthorized — try silent refresh via cookie
  if (response.status === 401) {
    try {
      const refreshResponse = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });

      if (refreshResponse.ok) {
        const tokens = await refreshResponse.json();
        _accessToken = tokens.access_token;

        // Retry the original request with new token
        config.headers['Authorization'] = `Bearer ${tokens.access_token}`;
        const retryResponse = await fetch(url, config);

        if (!retryResponse.ok) {
          const error = await retryResponse.json().catch(() => ({ detail: 'Request failed' }));
          throw new Error(error.detail || `HTTP ${retryResponse.status}`);
        }
        return retryResponse;
      }
    } catch {
      // Refresh failed — session expired, reload to show login
      _accessToken = null;
      window.location.reload();
    }
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response;
}

/**
 * apiFetch variant for FormData uploads.
 * Omits Content-Type (browser sets multipart boundary automatically)
 * but still gets 401 auto-refresh.
 */
export async function apiFetchFormData(endpoint, formData, method = 'POST') {
  const url = `${API_BASE_URL}${endpoint}`;

  const buildConfig = () => ({
    method,
    credentials: 'include',
    headers: { ...getAuthHeaders() },   // NO Content-Type — browser sets it
    body: formData,
  });

  let response = await fetch(url, buildConfig());

  if (response.status === 401) {
    try {
      const refreshResponse = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });
      if (refreshResponse.ok) {
        const tokens = await refreshResponse.json();
        _accessToken = tokens.access_token;
        response = await fetch(url, buildConfig());
      }
    } catch {
      _accessToken = null;
      window.location.reload();
      throw new Error('Session expired');
    }
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response;
}

export async function apiJson(endpoint, options = {}) {
  const response = await apiFetch(endpoint, options);
  if (response.status === 204) return null;
  return response.json();
}
