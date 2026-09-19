import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:5000';

// ── Token helpers ─────────────────────────────────────────────────────────────
export const getToken    = () => localStorage.getItem('authToken');
export const getUsername = () => localStorage.getItem('chatUsername');
export const isAuthenticated = () => !!getToken();

export const logout = () => {
  localStorage.removeItem('authToken');
  localStorage.removeItem('chatUsername');
};

const authHeaders = () => ({
  headers: {
    Authorization: `Bearer ${getToken()}`,
    'Content-Type': 'application/json',
  },
});

// ── Auth API ──────────────────────────────────────────────────────────────────
export const registerUser = async (username, password, email) => {
  const res = await axios.post(`${API_URL}/auth/register`, { username, password, email }, { timeout: 15000 });
  return res.data;
};

export const loginUser = async (username, password) => {
  const res = await axios.post(`${API_URL}/auth/login`, { username, password }, { timeout: 15000 });
  return res.data;
};

// ── Session API ───────────────────────────────────────────────────────────────
export const createSession = async () => {
  const res = await axios.post(`${API_URL}/session/new`, {}, authHeaders());
  return res.data.session_id;
};

export const getSessions = async () => {
  const res = await axios.get(`${API_URL}/sessions`, authHeaders());
  return res.data.sessions;
};

export const getSessionMessages = async (sessionId) => {
  const res = await axios.get(`${API_URL}/sessions/${sessionId}`, authHeaders());
  return res.data;
};

export const renameSession = async (sessionId, title) => {
  const res = await axios.patch(`${API_URL}/sessions/${sessionId}/rename`, { title }, authHeaders());
  return res.data;
};

export const deleteSession = async (sessionId) => {
  const res = await axios.delete(`${API_URL}/sessions/${sessionId}`, authHeaders());
  return res.data;
};

// ── Models API ────────────────────────────────────────────────────────────────
export const getModels = async () => {
  const res = await axios.get(`${API_URL}/models`, authHeaders());
  return res.data.models;
};

// ── Chat API ──────────────────────────────────────────────────────────────────
export const sendMessage = async (message, sessionId, model = 'llama-3.1-8b-instant') => {
  const res = await axios.post(
    `${API_URL}/chat`,
    { message, session_id: sessionId, model },
    authHeaders()
  );
  return res.data;
};