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
  const res = await axios.post(`${API_URL}/auth/register`, { username, password, email }, { timeout: 45000 });
  return res.data;
};

export const loginUser = async (username, password) => {
  const res = await axios.post(`${API_URL}/auth/login`, { username, password }, { timeout: 45000 });
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

// ── Chat API (Mode A: General AI) ─────────────────────────────────────────────
export const sendMessage = async (message, sessionId, model = 'openai/gpt-oss-20b') => {
  const res = await axios.post(
    `${API_URL}/chat`,
    { message, session_id: sessionId, model },
    authHeaders()
  );
  return res.data;
};

// ── RAG Document & Query API (Mode B: Ask My Documents) ──────────────────────
export const uploadDocument = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const token = getToken();
  const res = await axios.post(`${API_URL}/api/documents/upload`, formData, {
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'multipart/form-data',
    },
    timeout: 60000,
  });
  return res.data;
};

export const getDocuments = async () => {
  const res = await axios.get(`${API_URL}/api/documents`, authHeaders());
  return res.data.documents;
};

export const deleteDocument = async (docId) => {
  const res = await axios.delete(`${API_URL}/api/documents/${docId}`, authHeaders());
  return res.data;
};

export const sendRAGQuery = async (query, model = 'openai/gpt-oss-20b', docIds = null, topK = 4) => {
  const res = await axios.post(
    `${API_URL}/api/rag/query`,
    { query, model, doc_ids: docIds, top_k: topK },
    authHeaders()
  );
  return res.data;
};