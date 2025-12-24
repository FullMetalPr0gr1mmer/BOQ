// src/api.js
// Centralized API utility for global error handling and token management

const VITE_API_URL = import.meta.env.VITE_API_URL;

// Global toast function - will be set by App.jsx
let globalShowToast = null;

export const setGlobalToast = (showToastFn) => {
  globalShowToast = showToastFn;
};

// Flag to prevent multiple refresh attempts
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

const handleUnauthorized = (message = 'Unauthorized access. Redirecting to login...') => {
  // Show toast notification
  if (globalShowToast) {
    globalShowToast(message, 'error', 3000);
  }

  // Clear auth data
  localStorage.removeItem('token');
  localStorage.removeItem('refreshToken');
  localStorage.removeItem('user');
  localStorage.removeItem('activeSection');

  // Redirect after 3 seconds
  setTimeout(() => {
    window.location.href = '/login';
  }, 3000);
};

export const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  if (token) {
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    };
  }
  return { 'Content-Type': 'application/json' };
};

// Refresh access token using refresh token
const refreshAccessToken = async () => {
  const refreshToken = localStorage.getItem('refreshToken');

  if (!refreshToken) {
    throw new Error('No refresh token available');
  }

  try {
    const response = await fetch(`${VITE_API_URL}/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ refresh_token: refreshToken })
    });

    if (!response.ok) {
      throw new Error('Failed to refresh token');
    }

    const data = await response.json();

    // Store new access token
    localStorage.setItem('token', data.access_token);

    return data.access_token;
  } catch (error) {
    // If refresh fails, clear everything and redirect to login
    handleUnauthorized('Session expired. Please log in again.');
    throw error;
  }
};

export async function apiCall(endpoint, options = {}) {
  const url = `${VITE_API_URL}${endpoint}`;
  const defaultHeaders = getAuthHeaders();
  const config = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...(options.headers || {})
    }
  };

  // If sending FormData, let the browser set the Content-Type
  if (config.body instanceof FormData) {
    if (config.headers && config.headers['Content-Type']) {
      delete config.headers['Content-Type'];
    }
  }

  // If DELETE/GET request with no body, remove Content-Type header
  if ((config.method === 'DELETE' || config.method === 'GET') && !config.body) {
    if (config.headers && config.headers['Content-Type']) {
      delete config.headers['Content-Type'];
    }
  }

  try {
    const response = await fetch(url, config);
    if (!response.ok) {
      let errorData = {};
      try {
        errorData = await response.json();
      } catch {}

      // Handle 401 - Try to refresh token
      if (response.status === 401) {
        // Don't try to refresh for login/register endpoints
        if (endpoint.includes('/login') || endpoint.includes('/register') || endpoint.includes('/auth/refresh')) {
          const errorMessage = errorData?.detail || 'Unauthorized access';
          throw new Error(errorMessage);
        }

        // If already refreshing, queue this request
        if (isRefreshing) {
          return new Promise((resolve, reject) => {
            failedQueue.push({ resolve, reject });
          })
            .then(token => {
              config.headers['Authorization'] = `Bearer ${token}`;
              return fetch(url, config).then(res => res.json());
            })
            .catch(err => {
              throw err;
            });
        }

        isRefreshing = true;

        try {
          const newToken = await refreshAccessToken();
          isRefreshing = false;
          processQueue(null, newToken);

          // Retry original request with new token
          config.headers['Authorization'] = `Bearer ${newToken}`;
          const retryResponse = await fetch(url, config);
          if (!retryResponse.ok) {
            const retryError = await retryResponse.json().catch(() => ({}));
            throw new Error(retryError?.detail || `HTTP error! status: ${retryResponse.status}`);
          }
          return retryResponse.json();
        } catch (refreshError) {
          isRefreshing = false;
          processQueue(refreshError, null);
          handleUnauthorized('Session expired. Please log in again.');
          throw refreshError;
        }
      }

      // Handle 403
      if (response.status === 403) {
        const errorMessage = errorData?.detail || 'Unauthorized access. Redirecting to login...';
        handleUnauthorized(errorMessage);
        throw new Error(errorMessage);
      }
      if (errorData && typeof errorData.detail !== 'undefined') {
        const detail = errorData.detail;
        // If backend reports invalid credentials in any form, force logout
        if (typeof detail === 'string' && /invalid\s*credentials|unauthorized|token\s*(expired|invalid)/i.test(detail)) {
          handleUnauthorized('Session expired. Redirecting to login...');
          throw new Error('Session expired. Please log in again.');
        }
        if (detail && typeof detail === 'object') {
          const err = new Error('API_VALIDATION_ERROR');
          err.payload = detail;
          throw err;
        }
        throw new Error(detail);
      }
      throw new Error(`HTTP error! status: ${response.status}`);}
    if (response.status === 204) {
      return null;
    }
    const contentType = response.headers.get('content-type') || '';
    // If not JSON, or body is empty, return null/string
    if (!contentType.includes('application/json')) {
      const text = await response.text();
      return text?.length ? text : null;
    }
    // Parse JSON, but guard against empty body
    const text = await response.text();
    if (!text) return null;
    return JSON.parse(text);
  } catch (error) {
    // Don't log AbortError - it's expected when requests are cancelled
    if (error.name !== 'AbortError') {
      console.error('API call failed:', error);
    }
    throw error;
  }
}

// Logout function
export const logout = async () => {
  const token = localStorage.getItem('token');

  if (token) {
    try {
      // Call logout endpoint to blacklist token
      await fetch(`${VITE_API_URL}/logout`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
    } catch (error) {
      console.error('Logout error:', error);
      // Continue with local logout even if backend call fails
    }
  }

  // Clear local storage
  localStorage.removeItem('token');
  localStorage.removeItem('refreshToken');
  localStorage.removeItem('user');
  localStorage.removeItem('activeSection');

  // Redirect to login
  window.location.href = '/login';
};

// Helper: set message then auto-clear after ms (default 5s)
export function setTransient(setter, message, ms = 3000) {
  setter(message);
  if (ms > 0) {
    setTimeout(() => setter(''), ms);
  }
}
