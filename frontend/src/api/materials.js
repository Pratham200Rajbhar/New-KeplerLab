import { apiJson, apiFetchFormData, apiConfig } from './config';

// ── Upload limits (configurable via backend) ─────────────────────
const DEFAULT_MAX_UPLOAD_SIZE_MB = 25;
let _maxUploadSizeMB = DEFAULT_MAX_UPLOAD_SIZE_MB;

export function getMaxUploadSizeMB() {
  return _maxUploadSizeMB;
}

export function setMaxUploadSizeMB(mb) {
  _maxUploadSizeMB = mb;
}

/**
 * Validate files client-side before uploading.
 * Returns null if OK, or an error object { error_code, message, details } if invalid.
 */
export function validateFiles(files) {
  const maxBytes = _maxUploadSizeMB * 1024 * 1024;
  for (const file of files) {
    if (file.size > maxBytes) {
      const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
      return {
        error_code: 'FILE_TOO_LARGE',
        message: `File exceeds the ${_maxUploadSizeMB} MB limit`,
        details: `"${file.name}" is ${sizeMB} MB. Maximum allowed is ${_maxUploadSizeMB} MB.`,
      };
    }
  }
  return null;
}

export async function uploadMaterial(file, notebookId = null) {
  const sizeErr = validateFiles([file]);
  if (sizeErr) throw Object.assign(new Error(sizeErr.message), sizeErr);

  const formData = new FormData();
  formData.append('file', file);
  if (notebookId) {
    formData.append('notebook_id', notebookId);
  }

  const response = await apiFetchFormData('/upload', formData);
  return response.json();
}


export async function uploadBatch(files, notebookId = null) {
  const sizeErr = validateFiles(files);
  if (sizeErr) throw Object.assign(new Error(sizeErr.message), sizeErr);

  const formData = new FormData();
  files.forEach(file => formData.append('files', file));
  if (notebookId) {
    formData.append('notebook_id', notebookId);
  }

  const response = await apiFetchFormData('/upload/batch', formData);
  return response.json();
}

export async function uploadBatchWithAutoNotebook(files) {
  const sizeErr = validateFiles(files);
  if (sizeErr) throw Object.assign(new Error(sizeErr.message), sizeErr);

  const formData = new FormData();
  files.forEach(file => formData.append('files', file));
  formData.append('auto_create_notebook', 'true');

  const response = await apiFetchFormData('/upload/batch', formData);
  return response.json();
}

export async function uploadUrl(url, notebookId = null, autoCreateNotebook = false, sourceType = 'auto', title = null) {
  return apiJson('/upload/url', {
    method: 'POST',
    body: JSON.stringify({
      url,
      notebook_id: notebookId,
      auto_create_notebook: autoCreateNotebook,
      source_type: sourceType,
      title: title,
    }),
  });
}

export async function webSearch(query, fileType = null) {
  return apiJson('/search/web', {
    method: 'POST',
    body: JSON.stringify({
      query,
      file_type: fileType,
    }),
  });
}

export async function uploadText(text, title, notebookId = null, autoCreateNotebook = false) {
  return apiJson('/upload/text', {
    method: 'POST',
    body: JSON.stringify({
      text,
      title,
      notebook_id: notebookId,
      auto_create_notebook: autoCreateNotebook,
    }),
  });
}

export async function getSupportedFormats() {
  const response = await fetch(`${apiConfig.baseUrl}/upload/supported-formats`);
  if (!response.ok) {
    throw new Error('Failed to fetch supported formats');
  }
  const data = await response.json();
  // Cache max upload size from backend
  if (data.max_upload_size_mb) {
    _maxUploadSizeMB = data.max_upload_size_mb;
  }
  return data;
}

export async function getMaterials(notebookId = null) {
  const query = notebookId ? `?notebook_id=${notebookId}` : '';
  return apiJson(`/materials${query}`);
}

export async function deleteMaterial(materialId) {
  return apiJson(`/materials/${materialId}`, { method: 'DELETE' });
}

export async function updateMaterial(materialId, { filename, title }) {
  const body = {};
  if (filename != null) body.filename = filename;
  if (title != null) body.title = title;
  return apiJson(`/materials/${materialId}`, { method: 'PATCH', body: JSON.stringify(body) });
}

export async function getMaterialText(materialId) {
  return apiJson(`/materials/${materialId}/text`);
}
