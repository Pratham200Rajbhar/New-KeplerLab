import { useRef, useEffect } from 'react';
import { usePodcast } from '../../context/PodcastContext';

/**
 * Auto-scrolling transcript view that highlights the active segment
 * and allows click-to-jump navigation.
 */
export default function PodcastTranscript() {
  const { segments, currentSegmentIndex, playSegment, bookmarks, annotations } = usePodcast();
  const activeRef = useRef(null);

  // Auto-scroll active segment into view
  useEffect(() => {
    activeRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, [currentSegmentIndex]);

  if (!segments.length) {
    return <p className="text-xs text-text-muted text-center py-4">No segments yet.</p>;
  }

  return (
    <div className="space-y-1.5">
      {segments.map((seg, i) => {
        const isActive = i === currentSegmentIndex;
        const hasBookmark = bookmarks.some(b => b.segmentIndex === i);
        const segAnnotations = annotations.filter(a => a.segmentIndex === i);
        const isHost = seg.speaker === 'HOST';

        return (
          <div
            key={i}
            ref={isActive ? activeRef : undefined}
            onClick={() => playSegment(i)}
            className={`group p-2 rounded-lg cursor-pointer transition-all ${
              isActive
                ? 'bg-accent/10 border border-accent/20'
                : 'hover:bg-surface-overlay border border-transparent'
            }`}
          >
            <div className="flex items-start gap-2">
              {/* Speaker badge */}
              <span className={`flex-shrink-0 text-[9px] font-bold uppercase mt-0.5 px-1 py-0.5 rounded ${
                isHost
                  ? 'bg-blue-500/15 text-blue-400'
                  : 'bg-purple-500/15 text-purple-400'
              }`}>
                {seg.speaker}
              </span>

              <div className="flex-1 min-w-0">
                <p className={`text-xs leading-relaxed ${
                  isActive ? 'text-text-primary' : 'text-text-secondary'
                }`}>
                  {seg.text}
                </p>

                {/* Annotations */}
                {segAnnotations.map(a => (
                  <div key={a.id} className="mt-1 pl-2 border-l-2 border-yellow-500/40">
                    <p className="text-[10px] text-yellow-400/80 italic">{a.note}</p>
                  </div>
                ))}
              </div>

              {/* Indicators */}
              <div className="flex flex-col items-center gap-0.5 flex-shrink-0">
                {hasBookmark && (
                  <svg className="w-3 h-3 text-accent fill-accent" viewBox="0 0 24 24">
                    <path d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                  </svg>
                )}
                {isActive && (
                  <div className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
