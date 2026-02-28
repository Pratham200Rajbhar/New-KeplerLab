import { useEffect, useState } from 'react';
import { usePodcast, SESSION_STATUS } from '../../context/PodcastContext';

function formatTime(ms) {
  if (!ms) return '—';
  const secs = Math.floor(ms / 1000);
  const mins = Math.floor(secs / 60);
  return mins > 0 ? `${mins}m ${secs % 60}s` : `${secs}s`;
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleDateString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

const STATUS_BADGE = {
  [SESSION_STATUS.READY]: { label: 'Ready', cls: 'bg-green-500/15 text-green-400' },
  [SESSION_STATUS.PLAYING]: { label: 'Playing', cls: 'bg-blue-500/15 text-blue-400' },
  [SESSION_STATUS.COMPLETED]: { label: 'Done', cls: 'bg-text-muted/15 text-text-muted' },
  [SESSION_STATUS.FAILED]: { label: 'Failed', cls: 'bg-red-500/15 text-red-400' },
  [SESSION_STATUS.SCRIPT_GEN]: { label: 'Generating', cls: 'bg-yellow-500/15 text-yellow-400' },
  [SESSION_STATUS.AUDIO_GEN]: { label: 'Generating', cls: 'bg-yellow-500/15 text-yellow-400' },
  [SESSION_STATUS.PAUSED]: { label: 'Paused', cls: 'bg-orange-500/15 text-orange-400' },
};

export default function PodcastSessionLibrary() {
  const {
    sessions,
    loadSessions,
    loadSession,
    removeSession,
    setPhase,
  } = usePodcast();

  const [deleteConfirmId, setDeleteConfirmId] = useState(null);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const handleOpen = (session) => {
    loadSession(session.id);
  };

  const handleDelete = async (id) => {
    await removeSession(id);
    setDeleteConfirmId(null);
  };

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-text-primary">Podcasts</h3>
        <button
          onClick={() => setPhase('setup')}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent hover:bg-accent-light text-white text-xs font-medium transition-colors"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New
        </button>
      </div>

      {/* Empty state */}
      {sessions.length === 0 && (
        <div className="text-center py-8">
          <div className="w-12 h-12 mx-auto rounded-full bg-accent/10 flex items-center justify-center mb-3">
            <svg className="w-6 h-6 text-accent/60" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
          </div>
          <p className="text-xs text-text-muted">No podcasts yet</p>
          <p className="text-[10px] text-text-muted mt-1">
            Select sources and generate your first AI podcast
          </p>
        </div>
      )}

      {/* Session list */}
      <div className="space-y-2">
        {sessions.map(s => {
          const badge = STATUS_BADGE[s.status] || { label: s.status, cls: 'bg-surface-overlay text-text-muted' };
          return (
            <div
              key={s.id}
              className="group relative p-3 rounded-lg border border-border hover:border-accent/20 hover:bg-surface-overlay cursor-pointer transition-all"
              onClick={() => handleOpen(s)}
            >
              <div className="flex items-start justify-between mb-1">
                <h4 className="text-xs font-medium text-text-primary truncate flex-1 pr-2">
                  {s.title || 'Untitled Podcast'}
                </h4>
                <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded flex-shrink-0 ${badge.cls}`}>
                  {badge.label}
                </span>
              </div>

              <div className="flex items-center gap-3 text-[10px] text-text-muted">
                {s.mode && <span className="capitalize">{s.mode}</span>}
                {s.totalDurationMs > 0 && <span>{formatTime(s.totalDurationMs)}</span>}
                {s.language && <span className="uppercase">{s.language}</span>}
                <span>{formatDate(s.createdAt)}</span>
              </div>

              {s.tags?.length > 0 && (
                <div className="flex gap-1 mt-1.5 flex-wrap">
                  {s.tags.map((tag, i) => (
                    <span key={i} className="text-[9px] px-1.5 py-0.5 rounded bg-surface-overlay text-text-muted">
                      {tag}
                    </span>
                  ))}
                </div>
              )}

              {/* Delete button */}
              <button
                onClick={(e) => { e.stopPropagation(); setDeleteConfirmId(s.id); }}
                className="absolute right-2 top-2 p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-red-500/10 text-text-muted hover:text-red-400 transition-all"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          );
        })}
      </div>

      {/* Delete confirmation */}
      {deleteConfirmId && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 backdrop-blur-sm"
          onClick={() => setDeleteConfirmId(null)}
        >
          <div className="bg-surface-raised border border-border rounded-xl shadow-2xl p-5 max-w-xs w-full mx-4"
            onClick={e => e.stopPropagation()}
          >
            <h4 className="text-sm font-semibold text-text-primary mb-1.5">Delete podcast?</h4>
            <p className="text-xs text-text-secondary mb-4">
              This will permanently delete the session and all audio files.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setDeleteConfirmId(null)}
                className="px-3 py-1.5 text-xs rounded-lg text-text-secondary hover:bg-surface-overlay transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(deleteConfirmId)}
                className="px-3 py-1.5 text-xs rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 font-medium transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
