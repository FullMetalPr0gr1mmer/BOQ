// src/api.js
// Centralized API utility for global error handling and token management

const VITE_API_URL = import.meta.env.VITE_API_URL;

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
        localStorage.removeItem('token');
        window.location.href = '/login';
        throw new Error('Unauthorized or Forbidden access. Please log in again.');
      }
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }
    // Handle empty or no-content responses safely
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
