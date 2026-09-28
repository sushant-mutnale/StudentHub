import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: false,
});

let authToken = null;
let refreshPromise = null;
let onSessionExpired = null;
let onTokenRefreshed = null;

/**
 * Sanitized request logging.
 * NEVER log the full Axios config or response bodies: they contain the
 * Authorization header (Bearer token), PII, and resume/applicant data.
 * Log only the safe, non-sensitive signal.
 */
const logRequest = (config) => {
  if (import.meta.env.DEV) {
    console.info(`[API] ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`);
  }
};

export const setAuthToken = (token) => {
  authToken = token;
};

/**
 * Register a callback invoked when the session can no longer be refreshed
 * (a 401 that the refresh flow itself cannot recover from). The app (e.g.
 * AuthContext) uses this to clear persisted state and route to login.
 */
export const setOnSessionExpired = (cb) => {
  onSessionExpired = cb;
};

/**
 * Register a callback invoked whenever a silent refresh successfully issues a
 * new access token, so the app can persist it (e.g. to localStorage).
 */
export const setOnTokenRefreshed = (cb) => {
  onTokenRefreshed = cb;
};

/**
 * Attempt to obtain a fresh access token via /auth/refresh using the current
 * token. Coalesces concurrent refreshes into a single in-flight request.
 */
const refreshAccessToken = async () => {
  if (!authToken) {
    throw new Error('No token to refresh');
  }
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    try {
      const { data } = await axios.post(
        `${API_BASE_URL}/auth/refresh`,
        {},
        { headers: { Authorization: `Bearer ${authToken}` } }
      );
      authToken = data.access_token;
      if (typeof onTokenRefreshed === 'function') {
        onTokenRefreshed(data.access_token);
      }
      return data.access_token;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
};

api.interceptors.request.use((config) => {
  logRequest(config);
  if (!config.headers) {
    config.headers = {};
  }
  if (authToken) {
    config.headers.Authorization = `Bearer ${authToken}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;

    // Only attempt a one-shot refresh+retry on 401 for non-refresh requests.
    const isRefreshRequest = original?.url?.includes('/auth/refresh');
    const canRetry =
      error.response?.status === 401 &&
      original &&
      !original._retried &&
      !isRefreshRequest;

    if (canRetry) {
      original._retried = true;
      try {
        await refreshAccessToken();
        if (authToken) {
          original.headers.Authorization = `Bearer ${authToken}`;
        }
        return api(original);
      } catch (refreshError) {
        // Refresh failed — the session is unrecoverable.
        if (typeof onSessionExpired === 'function') {
          onSessionExpired();
        }
        return Promise.reject(new Error('Your session has expired. Please sign in again.'));
      }
    }

    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      'Unexpected error';
    // Log only a sanitized signal — no bodies, no headers, no tokens.
    if (import.meta.env.DEV) {
      console.warn(
        `[API] Error ${error.response?.status ?? 'network'} ${original?.url ?? ''}: ${message}`
      );
    }
    return Promise.reject(new Error(message));
  }
);
