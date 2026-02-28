import { usePodcast } from '../../context/PodcastContext';

/**
 * Persistent mini player bar that shows when a podcast is playing
 * and the user navigates away from the podcast view.
 * Rendered at the StudioPanel level when podcast is active.
 */
export default function PodcastMiniPlayer({ onExpand }) {
  const {
    session,
    segments,
    currentSegmentIndex,
    isPlaying,
    totalDuration,
    togglePlayPause,
    nextSegment,
  } = usePodcast();

  if (!session || !segments.length) return null;

  const seg = segments[currentSegmentIndex];
  const elapsed = segments.slice(0, currentSegmentIndex).reduce((s, seg) => s + (seg.durationMs || 0), 0);
  const pct = totalDuration > 0 ? (elapsed / totalDuration) * 100 : 0;

  return (
    <div className="border-t border-border bg-surface-overlay px-3 py-2">
      {/* Tiny progress */}
      <div className="h-0.5 rounded-full bg-surface mb-1.5 overflow-hidden">
        <div className="h-full bg-accent rounded-full transition-all" style={{ width: `${pct}%` }} />
      </div>

      <div className="flex items-center gap-2">
        {/* Play/Pause */}
        <button onClick={togglePlayPause} className="flex-shrink-0">
          {isPlaying ? (
            <svg className="w-5 h-5 text-accent" fill="currentColor" viewBox="0 0 24 24">
              <rect x="6" y="4" width="4" height="16" rx="1" />
              <rect x="14" y="4" width="4" height="16" rx="1" />
            </svg>
          ) : (
            <svg className="w-5 h-5 text-accent" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 5v14l11-7z" />
            </svg>
          )}
        </button>

        {/* Info */}
        <div className="flex-1 min-w-0 cursor-pointer" onClick={onExpand}>
          <p className="text-[10px] font-medium text-text-primary truncate">
            {session.title || 'Podcast'}
          </p>
          <p className="text-[9px] text-text-muted truncate">
            {seg?.speaker}: {seg?.text?.slice(0, 40)}…
          </p>
        </div>

        {/* Next */}
        <button onClick={nextSegment} className="flex-shrink-0">
          <svg className="w-4 h-4 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M11.933 12.8a1 1 0 000-1.6L6.6 7.2A1 1 0 005 8v8a1 1 0 001.6.8l5.333-4zM19.933 12.8a1 1 0 000-1.6l-5.333-4A1 1 0 0013 8v8a1 1 0 001.6.8l5.333-4z" />
          </svg>
        </button>
      </div>
    </div>
  );
}
