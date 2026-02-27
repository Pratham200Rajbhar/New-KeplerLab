import { apiJson, apiFetch, apiConfig } from './config';

/**
 * Check if presentations already exist for the given materials.
 */
export async function checkExplainerPresentations(materialIds, notebookId, { signal } = {}) {
  return apiJson('/explainer/check-presentations', {
    method: 'POST',
    body: JSON.stringify({ material_ids: materialIds, notebook_id: notebookId }),
    ...(signal ? { signal } : {}),
  });
}

/**
 * Start explainer video generation.
 *
 * @param {Object} options
 * @param {string[]} options.materialIds
 * @param {string} options.notebookId
 * @param {string} options.pptLanguage
 * @param {string} options.narrationLanguage
 * @param {string} options.voiceGender
 * @param {string} [options.presentationId]
 * @param {boolean} [options.createNewPpt]
 * @returns {Promise<{explainer_id: string, status: string, estimated_time_minutes: number}>}
 */
export async function generateExplainer(options = {}) {
  const body = {
    material_ids: options.materialIds,
    notebook_id: options.notebookId,
    ppt_language: options.pptLanguage || 'en',
    narration_language: options.narrationLanguage || 'en',
    voice_gender: options.voiceGender || 'female',
    create_new_ppt: options.createNewPpt || false,
  };
  if (options.presentationId) body.presentation_id = options.presentationId;

  return apiJson('/explainer/generate', {
    method: 'POST',
    body: JSON.stringify(body),
    ...(options.signal ? { signal: options.signal } : {}),
  });
}

/**
 * Poll the status of an explainer video generation.
 */
export async function getExplainerStatus(explainerId, { signal } = {}) {
  return apiJson(`/explainer/${explainerId}/status`, {
    ...(signal ? { signal } : {}),
  });
}

/**
 * Get the video download URL for a completed explainer.
 * Returns the raw URL (for reference) - use fetchExplainerVideoBlob for playback.
 */
export function getExplainerVideoUrl(explainerId) {
  return `${apiConfig.baseUrl}/explainer/${explainerId}/video`;
}

/**
 * Fetch the explainer video as a blob (handles authentication).
 * Returns a blob URL that can be used for video playback.
 */
export async function fetchExplainerVideoBlob(explainerId, { signal } = {}) {
  const response = await apiFetch(`/explainer/${explainerId}/video`, {
    ...(signal ? { signal } : {}),
  });
  if (!response.ok) {
    throw new Error('Failed to fetch video');
  }
  const blob = await response.blob();
  return URL.createObjectURL(blob);
}
