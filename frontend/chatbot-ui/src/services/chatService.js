import axios from 'axios';

const API_URL = 'http://127.0.0.1:5000';

// ── Token helpers ─────────────────────────────────────────────────────────────
export const getToken = () => localStorage.getItem('authToken');
export const getUsername = () => localStorage.getItem('chatUsername');
export const isAuthenticated = () => !!getToken();

export const logout = () => {
  localStorage.removeItem('authToken');
  localStorage.removeItem('chatUsername');
};

const getAuthHeaders = () => ({
  headers: {
    'Authorization': `Bearer ${getToken()}`,
    'Content-Type': 'application/json'
  }
});

// ── Auth API ──────────────────────────────────────────────────────────────────
export const registerUser = async (username, password) => {
  const response = await axios.post(`${API_URL}/auth/register`, { username, password });
  return response.data;
};

export const loginUser = async (username, password) => {
  const response = await axios.post(`${API_URL}/auth/login`, { username, password });
  return response.data;
};

// ── Chat API ──────────────────────────────────────────────────────────────────
export const createSession = async () => {
  const response = await axios.post(`${API_URL}/session/new`, {}, getAuthHeaders());
  return response.data.session_id;
};

export const sendMessage = async (message, sessionId) => {
  const response = await axios.post(`${API_URL}/chat`, {
    message,
    session_id: sessionId
  }, getAuthHeaders());
  return response.data;
};