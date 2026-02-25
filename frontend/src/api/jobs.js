import { apiJson } from './config';

/**
 * Poll the status of a background job.
 * @param {string} jobId
 * @returns {Promise<{job_id, status, result?, error?}>}
 */
export async function getJobStatus(jobId) {
  return apiJson(`/jobs/${jobId}`);
}

/**
 * Get AI model status (public endpoint).
 * @returns {Promise<Object>}
 */
export async function getModelsStatus() {
  return apiJson('/models/status');
}

/**
 * Trigger a model reload (admin/dev use).
 * @returns {Promise<Object>}
 */
export async function reloadModels() {
  return apiJson('/models/reload', { method: 'POST' });
}

/**
 * Run an NL data analysis query via the agent.
 * Returns a raw Response for SSE streaming.
 * @param {string} query
 * @param {string} notebookId
 * @param {string[]} [materialIds]
 */
export async function streamAnalysis(query, notebookId, materialIds = []) {
  const { apiFetch } = await import('./config');
  return apiFetch('/agent/analyze', {
    method: 'POST',
    body: JSON.stringify({
      query,
      notebook_id: notebookId,
      material_ids: materialIds,
    }),
  });
}
