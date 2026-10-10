import axios from 'axios';

const api = axios.create({ baseURL: '/api' });

api.interceptors.response.use(res => res.data);

export const getHealth = () => api.get('/health');
export const ingestRepo = (source) => api.post('/ingest', { source });
export const getRepos = async () => {
  const data = await api.get('/repos');
  return Array.isArray(data) ? data : Object.entries(data || {}).map(([key, val]) => ({ repo_id: key, ...val }));
};
export const submitTriage = (payload) => api.post('/triage', payload); // { repo_id, issue_text, issue_url }
export const getState = (thread_id) => api.get(`/state/${thread_id}`);
export const approvePatch = (payload) => api.post('/approve', payload); // { thread_id, action, edited_diff }
export const openPr = (payload) => api.post('/pr', payload); // { thread_id }
export const followupTriage = (payload) => api.post('/followup', payload); // { thread_id, message }
export const generateDigest = (repo_id) => api.post('/digest', { repo_id });
export const getDigest = (digest_id) => api.get(`/digest/${digest_id}`);
export const generateExplain = (repo_id) => api.post('/explain', { repo_id });
export const getHistory = () => api.get('/history');

export const streamUrl = (thread_id) => `/api/stream/${thread_id}`;


export default api;
