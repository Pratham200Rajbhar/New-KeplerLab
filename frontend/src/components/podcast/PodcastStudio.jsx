import { useEffect, useState } from 'react';
import { usePodcast, SESSION_STATUS } from '../../context/PodcastContext';
import PodcastGenerating from './PodcastGenerating';
import PodcastPlayer from './PodcastPlayer';

function formatTime(ms) {
  if (!ms) return '';
  const secs = Math.floor(ms / 1000);
  const mins = Math.floor(secs / 60);
  return mins > 0 ? `${mins}m ${secs % 60}s` : `${secs}s`;
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleDateString(undefined, {
    month: 'short', day: 'numeric',
  });
}

/**
 * Podcast sidebar view — clean and simple.
 * Shows: generating → player → session list (idle)
 */
export default function PodcastStudio({ onRequestNew }) {
  const {
    phase, loadSessions, loadSession, sessions,
    removeSession,
  } = usePodcast();

  const [deleteConfirmId, setDeleteConfirmId] = useState(null);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  // Generating state — progress shown inline on the card now, just show minimal indicator
  if (phase === 'generating') {
    return <PodcastGenerating />;
  }

  // Player state
  if (phase === 'player') {
    return <PodcastPlayer />;
  }

  const handleDelete = async (id) => {
    await removeSession(id);
    setDeleteConfirmId(null);
  };

  // Filter out sessions that are still generating
  const completedSessions = sessions.filter(s => 
    s.status !== SESSION_STATUS.SCRIPT_GEN && 
    s.status !== SESSION_STATUS.AUDIO_GEN &&
    s.status !== SESSION_STATUS.CREATED
  );

  // Idle state: show session list or empty state
  return (
    <div className="space-y-4 animate-fade-in">
      {/* Empty state */}
      {completedSessions.length === 0 ? (
        <div className="text-center py-12">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-accent/10 border border-accent/10 flex items-center justify-center mb-4">
            <svg className="w-7 h-7 text-accent/60" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
          </div>
          <p className="text-sm font-medium text-text-secondary">No podcasts yet</p>
          <p className="text-xs text-text-muted mt-1 mb-4">
            Generate an AI podcast from your sources
          </p>
          <button
            onClick={onRequestNew}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-accent hover:bg-accent-light text-white text-sm font-medium transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Create Podcast
          </button>
        </div>
      ) : (
        /* Session list */
        <>
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-medium text-text-muted uppercase tracking-wider">Your Podcasts</h4>
            <button
              onClick={onRequestNew}
              className="flex items-center gap-1 px-2 py-1 rounded-md bg-accent/10 hover:bg-accent/20 text-accent text-xs font-medium transition-colors"
            >
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
              </svg>
              New
            </button>
          </div>
          <div className="space-y-2">
            {completedSessions.map((s) => {
              const isFailed = s.status === SESSION_STATUS.FAILED;
              return (
                <div
                  key={s.id}
                  className="group relative p-3 rounded-xl border border-border hover:border-accent/30 hover:bg-surface-overlay/50 cursor-pointer transition-all"
                  onClick={() => loadSession(s.id)}
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${
                      isFailed ? 'bg-red-500/10' : 'bg-accent/10'
                    }`}>
                      <svg className={`w-4 h-4 ${isFailed ? 'text-red-400' : 'text-accent'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                          d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                      </svg>
                    </div>
                    <div className="flex-1 min-w-0">
                      <h5 className="text-sm font-medium text-text-primary truncate">
                        {s.title || 'Untitled Podcast'}
                      </h5>
                      <div className="flex items-center gap-2 text-[11px] text-text-muted">
                        {s.language && <span className="uppercase">{s.language}</span>}
                        {s.totalDurationMs > 0 && <span>{formatTime(s.totalDurationMs)}</span>}
                        <span>{formatDate(s.createdAt)}</span>
                      </div>
                    </div>
                    <button
                      onClick={(e) => { e.stopPropagation(); setDeleteConfirmId(s.id); }}
                      className="p-1.5 rounded-md opacity-0 group-hover:opacity-100 hover:bg-red-500/10 text-text-muted hover:text-red-400 transition-all"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* Delete confirmation */}
      {deleteConfirmId && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 backdrop-blur-sm"
          onClick={() => setDeleteConfirmId(null)}
        >
          <div className="bg-surface-raised border border-border rounded-xl shadow-2xl p-5 max-w-xs w-full mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            <h4 className="text-sm font-semibold text-text-primary mb-2">Delete podcast?</h4>
            <p className="text-xs text-text-secondary mb-4">
              This will permanently delete this podcast.
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
