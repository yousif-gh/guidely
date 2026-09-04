// Thin API client. In dev, Vite proxies /api/* to the FastAPI server.
const BASE = '/api';

async function handle(res) {
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const message = body.detail || body.error || `Request failed (${res.status})`;
    const err = new Error(message);
    err.status = res.status;
    throw err;
  }
  return body;
}

export function ask(question, { topK = 3, history = null } = {}) {
  return fetch(`${BASE}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, top_k: topK, history }),
  }).then(handle);
}

export function listDocuments() {
  return fetch(`${BASE}/documents`).then(handle);
}

export function getDocumentContent(id) {
  return fetch(`${BASE}/documents/${id}/content`).then(handle);
}

export function uploadDocument(file, tags = '') {
  const form = new FormData();
  form.append('file', file);
  form.append('tags', tags);
  return fetch(`${BASE}/documents`, { method: 'POST', body: form }).then(handle);
}

export function editDocument(id, content) {
  return fetch(`${BASE}/documents/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  }).then(handle);
}

export function deleteDocument(id) {
  return fetch(`${BASE}/documents/${id}`, { method: 'DELETE' }).then(handle);
}

export function reindex() {
  return fetch(`${BASE}/documents/reindex`, { method: 'POST' }).then(handle);
}

export function getMetrics() {
  return fetch(`${BASE}/metrics`).then(handle);
}

export function translate(text, targetLang = 'Arabic') {
  return fetch(`${BASE}/translate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, target_lang: targetLang }),
  }).then(handle);
}
