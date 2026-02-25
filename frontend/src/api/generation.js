import { apiJson, apiFetch } from './config';

export async function generateFlashcards(materialId, options = {}) {
  const { signal, ...rest } = options;
  const body = {};
  if (rest.materialIds && rest.materialIds.length > 0) {
    body.material_ids = rest.materialIds;
  } else {
    body.material_id = materialId;
  }
  if (rest.topic) body.topic = rest.topic;
  if (rest.cardCount) body.card_count = rest.cardCount;
  if (rest.difficulty) body.difficulty = rest.difficulty;
  if (rest.additionalInstructions) body.additional_instructions = rest.additionalInstructions;
  return apiJson('/flashcard', { method: 'POST', body: JSON.stringify(body), ...(signal ? { signal } : {}) });
}

export async function generateQuiz(materialId, options = {}) {
  const { signal, ...rest } = options;
  const body = {};
  if (rest.materialIds && rest.materialIds.length > 0) {
    body.material_ids = rest.materialIds;
  } else {
    body.material_id = materialId;
  }
  if (rest.topic) body.topic = rest.topic;
  if (rest.mcqCount) body.mcq_count = rest.mcqCount;
  if (rest.difficulty) body.difficulty = rest.difficulty;
  if (rest.additionalInstructions) body.additional_instructions = rest.additionalInstructions;
  return apiJson('/quiz', { method: 'POST', body: JSON.stringify(body), ...(signal ? { signal } : {}) });
}

export async function generatePodcast(materialId, signal = null) {
  return apiJson('/podcast', { method: 'POST', body: JSON.stringify({ material_id: materialId }), ...(signal ? { signal } : {}) });
}

export async function downloadPodcast(materialId) {
  const response = await apiFetch('/podcast/download', { method: 'POST', body: JSON.stringify({ material_id: materialId }) });
  return response.blob();
}

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Generate an HTML presentation from a material.
 * All options are optional — the AI picks smart defaults.
 *
 * @param {string} materialId - The material to generate from
 * @param {Object} [options]
 * @param {number} [options.maxSlides] - Target slide count (3-60)
 * @param {string} [options.theme] - Theme description
 * @param {string} [options.additionalInstructions] - Extra guidance
 * @returns {Promise<{title: string, slide_count: number, theme: string, html: string}>}
 */
export async function generatePresentation(materialId, options = {}) {
  const { signal, ...rest } = options;
  const body = {};
  if (rest.materialIds && rest.materialIds.length > 0) {
    body.material_ids = rest.materialIds;
  } else {
    body.material_id = materialId;
  }
  if (rest.maxSlides) body.max_slides = rest.maxSlides;
  if (rest.theme) body.theme = rest.theme;
  if (rest.additionalInstructions) body.additional_instructions = rest.additionalInstructions;
  return apiJson('/presentation', { method: 'POST', body: JSON.stringify(body), ...(signal ? { signal } : {}) });
}


