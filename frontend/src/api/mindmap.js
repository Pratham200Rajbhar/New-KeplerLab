import { apiJson } from './config';

export async function generateMindMap({ notebookId, materialIds }) {
  return apiJson('/mindmap', {
    method: 'POST',
    body: JSON.stringify({
      notebook_id: notebookId,
      material_ids: materialIds,
    }),
  });
}

export async function getMindMap(notebookId) {
  return apiJson(`/mindmap/${notebookId}`);
}

export async function deleteMindMap(id) {
  return apiJson(`/mindmap/${id}`, { method: 'DELETE' });
}
