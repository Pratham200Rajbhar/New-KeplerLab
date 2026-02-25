import { apiJson } from './config';

export async function getNotebooks() {
    return apiJson('/notebooks');
}

export async function createNotebook(name, description = null) {
    return apiJson('/notebooks', {
        method: 'POST',
        body: JSON.stringify({ name, description }),
    });
}

export async function getNotebook(notebookId) {
    return apiJson(`/notebooks/${notebookId}`);
}

export async function updateNotebook(notebookId, name, description) {
    return apiJson(`/notebooks/${notebookId}`, {
        method: 'PUT',
        body: JSON.stringify({ name, description }),
    });
}

export async function deleteNotebook(notebookId) {
    return apiJson(`/notebooks/${notebookId}`, { method: 'DELETE' });
}

// Generated Content APIs
export async function saveGeneratedContent(notebookId, contentType, data, title = null, materialId = null) {
    return apiJson(`/notebooks/${notebookId}/content`, {
        method: 'POST',
        body: JSON.stringify({
            content_type: contentType,
            title,
            data,
            material_id: materialId,
        }),
    });
}

export async function getGeneratedContent(notebookId) {
    return apiJson(`/notebooks/${notebookId}/content`);
}

export async function deleteGeneratedContent(notebookId, contentId) {
    return apiJson(`/notebooks/${notebookId}/content/${contentId}`, {
        method: 'DELETE',
    });
}

export async function updateGeneratedContent(notebookId, contentId, title) {
    return apiJson(`/notebooks/${notebookId}/content/${contentId}`, {
        method: 'PUT',
        body: JSON.stringify({ title }),
    });
}

