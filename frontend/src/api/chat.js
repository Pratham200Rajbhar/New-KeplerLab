import { apiFetch, apiJson } from './config';

/**
 * Stream a chat message via SSE (fetch-based so Bearer token works).
 * Returns the raw Response — caller reads .body as a ReadableStream.
 * The backend will yield SSE events:
 *   event: start  | event: step | event: token | event: meta | event: done | event: error
 */
export async function streamChat(materialId, message, notebookId, materialIds = null, sessionId = null, signal = null) {
  const body = {
    message,
    notebook_id: notebookId,
    stream: true,
  };
  if (sessionId) {
    body.session_id = sessionId;
  }

  if (materialIds && materialIds.length > 0) {
    body.material_ids = materialIds;
  } else {
    body.material_id = materialId;
  }

  // apiFetch handles Authorization header + 401 auto-refresh
  return apiFetch('/chat', {
    method: 'POST',
    body: JSON.stringify(body),
    ...(signal ? { signal } : {}),
  });
}

export async function sendChatMessage(materialId, message, notebookId, materialIds = null, sessionId = null) {
  const body = {
    message,
    notebook_id: notebookId,
    stream: false,
  };
  if (sessionId) {
    body.session_id = sessionId;
  }
  if (materialIds && materialIds.length > 0) {
    body.material_ids = materialIds;
  } else {
    body.material_id = materialId;
  }
  return apiJson('/chat', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export async function getChatHistory(notebookId, sessionId = null) {
  let url = `/chat/history/${notebookId}`;
  if (sessionId) {
    url += `?session_id=${sessionId}`;
  }
  return apiJson(url);
}

export async function clearChatHistory(notebookId, sessionId = null) {
  let url = `/chat/history/${notebookId}`;
  if (sessionId) {
    url += `?session_id=${sessionId}`;
  }
  return apiJson(url, {
    method: 'DELETE',
  });
}

/**
 * Chat Sessions API
 */

export async function getChatSessions(notebookId) {
  return apiJson(`/chat/sessions/${notebookId}`);
}

export async function createChatSession(notebookId, title = 'New Chat') {
  return apiJson('/chat/sessions', {
    method: 'POST',
    body: JSON.stringify({ notebook_id: notebookId, title }),
  });
}

export async function deleteChatSession(sessionId) {
  return apiJson(`/chat/sessions/${sessionId}`, {
    method: 'DELETE',
  });
}

/**
 * Stream a block-level follow-up action via SSE.
 * action: 'ask' | 'simplify' | 'translate' | 'explain'
 * Returns the raw Response for SSE reading.
 */
export async function getBlockFollowup(blockId, question, action = 'ask') {
  return apiFetch('/chat/block-followup', {
    method: 'POST',
    body: JSON.stringify({ block_id: blockId, question, action }),
  });
}

/**
 * Get prompt auto-complete suggestions.
 * Returns { suggestions: [{suggestion, confidence}] }
 */
export async function getSuggestions(partialInput, notebookId) {
  if (!partialInput || partialInput.trim().length < 3) return { suggestions: [] };
  return apiJson('/chat/suggestions', {
    method: 'POST',
    body: JSON.stringify({ partial_input: partialInput, notebook_id: notebookId }),
  });
}

/**
 * Stream a research task via SSE via /agent/research.
 */
export async function streamResearch(query, notebookId, materialIds = [], signal = null) {
  return apiFetch('/agent/research', {
    method: 'POST',
    body: JSON.stringify({ query, notebook_id: notebookId, material_ids: materialIds }),
    ...(signal ? { signal } : {}),
  });
}

/**
 * Execute user-provided code directly (REPL path) via SSE.
 */
export async function executeCode(code, notebookId) {
  return apiFetch('/agent/execute', {
    method: 'POST',
    body: JSON.stringify({ code, notebook_id: notebookId }),
  });
}
