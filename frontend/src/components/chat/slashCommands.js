/**
 * Slash command definitions — shared between input UI and message display.
 *
 * Each command maps to an intent_override value sent to the backend.
 * The backend's intent.py uses this to skip AI intent detection.
 */

export const SLASH_COMMANDS = [
  { command: '/agent',     label: 'Agent',     description: 'Full agentic multi-step execution',       intent: 'RESEARCH',           color: '#f97316', bgClass: 'bg-orange-500/15 text-orange-400 border-orange-500/30' },
  { command: '/web',       label: 'Web',       description: 'Web search and synthesize',               intent: 'RESEARCH',           color: '#3b82f6', bgClass: 'bg-blue-500/15 text-blue-400 border-blue-500/30' },
  { command: '/code',      label: 'Code',      description: 'Write and run Python code',               intent: 'CODE_EXECUTION',     color: '#a855f7', bgClass: 'bg-purple-500/15 text-purple-400 border-purple-500/30' },
  { command: '/data',      label: 'Data',      description: 'Analyze uploaded data files',             intent: 'DATA_ANALYSIS',      color: '#eab308', bgClass: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30' },
  { command: '/quiz',      label: 'Quiz',      description: 'Generate quiz inline in chat',            intent: 'CONTENT_GENERATION', color: '#22c55e', bgClass: 'bg-green-500/15 text-green-400 border-green-500/30' },
  { command: '/flash',     label: 'Flash',     description: 'Generate flashcards inline in chat',      intent: 'CONTENT_GENERATION', color: '#14b8a6', bgClass: 'bg-teal-500/15 text-teal-400 border-teal-500/30' },
  { command: '/summarize', label: 'Summarize', description: 'Summarize selected materials',            intent: 'SUMMARIZE',          color: '#ec4899', bgClass: 'bg-pink-500/15 text-pink-400 border-pink-500/30' },
  { command: '/mindmap',   label: 'Mindmap',   description: 'Trigger mind map generation',             intent: 'MINDMAP',            color: '#6366f1', bgClass: 'bg-indigo-500/15 text-indigo-400 border-indigo-500/30' },
];

/**
 * Look up a slash command definition by its command string (e.g. "/agent").
 */
export function getSlashCommand(command) {
  return SLASH_COMMANDS.find(c => c.command === command) || null;
}

/**
 * Look up a slash command definition by its intent override value.
 * Returns the first match (e.g. "RESEARCH" → /agent).
 */
export function getSlashCommandByIntent(intent) {
  return SLASH_COMMANDS.find(c => c.intent === intent) || null;
}

/**
 * Parse a slash command from the beginning of a message string.
 * Returns { command, remainingMessage } or null if no slash command found.
 */
export function parseSlashCommand(message) {
  if (!message || !message.startsWith('/')) return null;
  const parts = message.trimStart().split(/\s+/);
  const cmd = parts[0].toLowerCase();
  const match = SLASH_COMMANDS.find(c => c.command === cmd);
  if (!match) return null;
  return {
    command: match,
    remainingMessage: parts.slice(1).join(' ').trim(),
  };
}
