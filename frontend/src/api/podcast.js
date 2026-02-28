import { apiJson, apiFetch } from './config';

// ── Session CRUD ─────────────────────────────────────────────

export async function createPodcastSession(data) {
  return apiJson('/podcast/session', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getPodcastSession(sessionId) {
  return apiJson(`/podcast/session/${sessionId}`);
}

export async function listPodcastSessions(notebookId) {
  return apiJson(`/podcast/sessions/${notebookId}`);
}

export async function updatePodcastSession(sessionId, data) {
  return apiJson(`/podcast/session/${sessionId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function deletePodcastSession(sessionId) {
  return apiJson(`/podcast/session/${sessionId}`, { method: 'DELETE' });
}

// ── Generation ───────────────────────────────────────────────

export async function startPodcastGeneration(sessionId) {
  return apiJson(`/podcast/session/${sessionId}/start`, { method: 'POST' });
}

// ── Audio URLs ───────────────────────────────────────────────

export function getSegmentAudioUrl(sessionId, segmentIndex) {
  const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  return `${base}/podcast/session/${sessionId}/segment/${segmentIndex}/audio`;
}

export function getSessionAudioUrl(sessionId, filename) {
  const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  return `${base}/podcast/session/${sessionId}/audio/${filename}`;
}

// ── Q&A ──────────────────────────────────────────────────────

export async function submitPodcastQuestion(sessionId, data) {
  return apiJson(`/podcast/session/${sessionId}/question`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getPodcastDoubts(sessionId) {
  return apiJson(`/podcast/session/${sessionId}/doubts`);
}

// ── Bookmarks ────────────────────────────────────────────────

export async function addPodcastBookmark(sessionId, data) {
  return apiJson(`/podcast/session/${sessionId}/bookmark`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getPodcastBookmarks(sessionId) {
  return apiJson(`/podcast/session/${sessionId}/bookmarks`);
}

export async function deletePodcastBookmark(sessionId, bookmarkId) {
  return apiJson(`/podcast/session/${sessionId}/bookmark/${bookmarkId}`, {
    method: 'DELETE',
  });
}

// ── Annotations ──────────────────────────────────────────────

export async function addPodcastAnnotation(sessionId, data) {
  return apiJson(`/podcast/session/${sessionId}/annotation`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function deletePodcastAnnotation(sessionId, annotationId) {
  return apiJson(`/podcast/session/${sessionId}/annotation/${annotationId}`, {
    method: 'DELETE',
  });
}

// ── Export ────────────────────────────────────────────────────

export async function triggerPodcastExport(sessionId, format) {
  return apiJson(`/podcast/session/${sessionId}/export`, {
    method: 'POST',
    body: JSON.stringify({ format }),
  });
}

export async function getPodcastExportStatus(exportId) {
  return apiJson(`/podcast/export/${exportId}`);
}

export function getPodcastExportUrl(sessionId, filename) {
  const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  return `${base}/podcast/export/file/${sessionId}/${filename}`;
}

// ── Summary ──────────────────────────────────────────────────

export async function generatePodcastSummary(sessionId) {
  return apiJson(`/podcast/session/${sessionId}/summary`, { method: 'POST' });
}

// ── Voice Discovery ──────────────────────────────────────────

export async function getVoicesForLanguage(language = 'en') {
  return apiJson(`/podcast/voices?language=${language}`);
}

export async function getAllVoices() {
  return apiJson('/podcast/voices/all');
}

export async function getLanguages() {
  return apiJson('/podcast/languages');
}

export function getVoicePreviewUrl(voiceId, language = 'en') {
  const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  return `${base}/podcast/voice/preview?voice_id=${encodeURIComponent(voiceId)}&language=${language}`;
}
