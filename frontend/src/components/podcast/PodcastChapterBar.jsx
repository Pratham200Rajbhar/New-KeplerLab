import { usePodcast } from '../../context/PodcastContext';

/**
 * Horizontal chapter/topic navigation.
 * Chapters are defined in the script generation output.
 */
export default function PodcastChapterBar() {
  const { chapters, currentSegmentIndex, playSegment, bookmarks } = usePodcast();

  if (!chapters || !chapters.length) {
    return (
      <p className="text-xs text-text-muted text-center py-4">
        No chapters defined for this session.
      </p>
    );
  }

  return (
    <div className="space-y-1">
      {chapters.map((ch, i) => {
        const nextChapterStart = chapters[i + 1]?.startSegment ?? Infinity;
        const isActive = currentSegmentIndex >= ch.startSegment && currentSegmentIndex < nextChapterStart;
        const chapterBookmarks = bookmarks.filter(
          b => b.segmentIndex >= ch.startSegment && b.segmentIndex < nextChapterStart
        );

        return (
          <button
            key={i}
            onClick={() => playSegment(ch.startSegment)}
            className={`w-full text-left p-2.5 rounded-lg border transition-all ${
              isActive
                ? 'border-accent/30 bg-accent/5'
                : 'border-transparent hover:bg-surface-overlay'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className={`text-xs font-medium ${isActive ? 'text-accent' : 'text-text-secondary'}`}>
                {ch.title}
              </span>
              <span className="text-[9px] text-text-muted">
                Seg {ch.startSegment + 1}
              </span>
            </div>
            {ch.summary && (
              <p className="text-[10px] text-text-muted mt-0.5 line-clamp-2">
                {ch.summary}
              </p>
            )}
            {chapterBookmarks.length > 0 && (
              <div className="flex items-center gap-1 mt-1">
                <svg className="w-2.5 h-2.5 text-accent" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                </svg>
                <span className="text-[9px] text-accent">{chapterBookmarks.length}</span>
              </div>
            )}
          </button>
        );
      })}
    </div>
  );
}
