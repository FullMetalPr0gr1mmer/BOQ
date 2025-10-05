// src/api.js
// Centralized API utility for global error handling and token management

const VITE_API_URL = import.meta.env.VITE_API_URL;

// Global toast function - will be set by App.jsx
let globalShowToast = null;

export const setGlobalToast = (showToastFn) => {
  globalShowToast = showToastFn;
};

const handleUnauthorized = (message = 'Unauthorized access. Redirecting to login...') => {
  // Show toast notification
  if (globalShowToast) {
    globalShowToast(message, 'error', 3000);
  }

  // Clear auth data
  localStorage.removeItem('token');
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

  try {
    const response = await fetch(url, config);
    if (!response.ok) {
      let errorData = {};
      try {
        errorData = await response.json();
      } catch {}
      // Handle 401/403 globally
      if (response.status === 401 || response.status === 403) {
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
    // Optionally, you can emit a global event or use a state manager for error messages
    console.error('API call failed:', error);
    throw error;
  }
}

// Helper: set message then auto-clear after ms (default 5s)
export function setTransient(setter, message, ms = 3000) {
  setter(message);
  if (ms > 0) {
    setTimeout(() => setter(''), ms);
  }
}
