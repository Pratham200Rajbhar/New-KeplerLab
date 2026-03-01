import { memo } from 'react';

/**
 * Colored badge for a slash command.
 * Used inside the chat input (with onRemove ✕ button) and in chat message history.
 *
 * Props:
 *   command  — slash command definition object { command, label, color, bgClass }
 *   onRemove — if provided, shows ✕ button (input mode); omit for history mode
 *   small    — if true, renders a smaller badge (for message history)
 */
export default memo(function CommandBadge({ command, onRemove, small = false }) {
  if (!command) return null;

  const sizeClass = small
    ? 'text-[10px] px-1.5 py-0.5 gap-1'
    : 'text-xs px-2.5 py-1 gap-1.5';

  return (
    <span
      className={`command-badge inline-flex items-center font-medium rounded-lg border ${sizeClass}`}
      style={{
        borderColor: `${command.color}40`,
        backgroundColor: `${command.color}15`,
        color: command.color,
      }}
    >
      <span className="font-mono">{command.command}</span>
      {onRemove && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="ml-0.5 rounded-full hover:bg-white/10 transition-colors w-4 h-4 flex items-center justify-center leading-none"
          style={{ color: command.color }}
          title="Remove command"
        >
          ✕
        </button>
      )}
    </span>
  );
});
