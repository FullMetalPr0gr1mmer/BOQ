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
  const config = {
    headers: getAuthHeaders(),
    ...options,
  };

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
    return await response.json();
  } catch (error) {
    // Optionally, you can emit a global event or use a state manager for error messages
    console.error('API call failed:', error);
    throw error;
  }
}
