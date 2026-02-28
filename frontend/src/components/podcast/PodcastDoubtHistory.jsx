import { usePodcast } from '../../context/PodcastContext';
import { useRef, useState } from 'react';
import { fetchAudioObjectUrl } from '../../api/config';

/**
 * List of past Q&A interactions during the podcast session.
 * Each doubt shows the question, answer text, and an inline play button.
 */
export default function PodcastDoubtHistory() {
  const { doubts, playSegment } = usePodcast();
  const [playingId, setPlayingId] = useState(null);
  const audioRef = useRef(new Audio());

  if (!doubts.length) {
    return (
      <div className="text-center py-6">
        <p className="text-xs text-text-muted">No questions asked yet</p>
        <p className="text-[10px] text-text-muted mt-1">
          Interrupt the podcast to ask the hosts a question
        </p>
      </div>
    );
  }

  const handlePlay = async (doubt) => {
    if (playingId === doubt.id) {
      audioRef.current.pause();
      setPlayingId(null);
      return;
    }
    if (doubt.audioPath) {
      try {
        const blobUrl = await fetchAudioObjectUrl(doubt.audioPath);
        audioRef.current.src = blobUrl;
        audioRef.current.play().catch(() => {});
        setPlayingId(doubt.id);
        audioRef.current.onended = () => {
          setPlayingId(null);
          URL.revokeObjectURL(blobUrl);
        };
      } catch (err) {
        console.error('Failed to load doubt audio:', err);
      }
    }
  };

  return (
    <div className="space-y-2">
      {doubts.map((d, i) => (
        <div key={d.id || i} className="p-2.5 rounded-lg border border-border">
          {/* Question */}
          <div className="flex items-start gap-2 mb-2">
            <svg className="w-3.5 h-3.5 text-accent mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01" />
            </svg>
            <p className="text-xs text-text-primary leading-relaxed">{d.questionText}</p>
          </div>

          {/* Answer */}
          <div className="pl-5">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[9px] font-bold uppercase px-1 py-0.5 rounded bg-purple-500/15 text-purple-400">
                GUEST
              </span>
              {d.audioPath && (
                <button
                  onClick={() => handlePlay(d)}
                  className="p-0.5 rounded hover:bg-surface-overlay transition-colors"
                >
                  {playingId === d.id ? (
                    <svg className="w-3 h-3 text-accent" fill="currentColor" viewBox="0 0 24 24">
                      <rect x="6" y="4" width="4" height="16" rx="1" />
                      <rect x="14" y="4" width="4" height="16" rx="1" />
                    </svg>
                  ) : (
                    <svg className="w-3 h-3 text-text-muted" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M8 5v14l11-7z" />
                    </svg>
                  )}
                </button>
              )}
            </div>
            <p className="text-xs text-text-secondary leading-relaxed">{d.answerText}</p>
          </div>

          {/* Jump to context */}
          {d.pausedAtSegment != null && (
            <button
              onClick={() => playSegment(d.pausedAtSegment)}
              className="mt-1.5 text-[9px] text-text-muted hover:text-accent transition-colors"
            >
              Asked at segment {d.pausedAtSegment + 1} →
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
