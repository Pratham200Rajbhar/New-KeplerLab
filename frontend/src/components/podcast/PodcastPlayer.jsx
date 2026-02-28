import { useState } from 'react';
import { usePodcast } from '../../context/PodcastContext';
import PodcastTranscript from './PodcastTranscript';
import PodcastChapterBar from './PodcastChapterBar';
import PodcastInterruptDrawer from './PodcastInterruptDrawer';
import PodcastExportBar from './PodcastExportBar';
import PodcastDoubtHistory from './PodcastDoubtHistory';

const SPEED_OPTIONS = [0.75, 1, 1.25, 1.5, 2];

function formatTime(ms) {
  if (!ms || ms <= 0) return '0:00';
  const totalSecs = Math.floor(ms / 1000);
  const mins = Math.floor(totalSecs / 60);
  const secs = totalSecs % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export default function PodcastPlayer() {
  const {
    session,
    segments,
    chapters,
    currentSegmentIndex,
    isPlaying,
    playbackSpeed,
    currentTime,
    totalDuration,
    interruptOpen,
    doubts,
    bookmarks,
    audioRef,
    setPhase,
    togglePlayPause,
    nextSegment,
    prevSegment,
    changeSpeed,
    playSegment,
    setInterruptOpen,
    addBookmark,
  } = usePodcast();

  const [showSpeedMenu, setShowSpeedMenu] = useState(false);
  const [showExport, setShowExport] = useState(false);
  const [showDoubts, setShowDoubts] = useState(false);
  const [tab, setTab] = useState('transcript'); // transcript | chapters | doubts

  const currentSeg = segments[currentSegmentIndex];
  const segDurationMs = currentSeg?.durationMs || 0;
  const progress = segDurationMs > 0 ? (currentTime * 1000 / segDurationMs) * 100 : 0;

  // Elapsed time across all completed segments + current segment time
  const elapsedMs = segments.slice(0, currentSegmentIndex).reduce((s, seg) => s + (seg.durationMs || 0), 0)
    + (currentTime * 1000);

  const isBookmarked = bookmarks.some(b => b.segmentIndex === currentSegmentIndex);

  const handleBookmark = () => {
    if (!isBookmarked) {
      addBookmark(currentSegmentIndex, `Seg ${currentSegmentIndex + 1}`);
    }
  };

  return (
    <div className="flex flex-col h-full animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <button
          onClick={() => setPhase('idle')}
          className="btn-icon-sm"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-text-primary truncate">
            {session?.title || 'Podcast'}
          </h3>
          <p className="text-[10px] text-text-muted">
            {segments.length} segments · {formatTime(totalDuration)}
          </p>
        </div>
        <button
          onClick={() => setShowExport(true)}
          className="btn-icon-sm"
          title="Export"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
        </button>
      </div>

      {/* Now playing */}
      {currentSeg && (
        <div className="mb-3 p-2.5 rounded-lg bg-surface-overlay border border-border">
          <div className="flex items-center gap-2 mb-1.5">
            <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${
              currentSeg.speaker === 'HOST'
                ? 'bg-blue-500/15 text-blue-400'
                : 'bg-purple-500/15 text-purple-400'
            }`}>
              {currentSeg.speaker}
            </span>
            <span className="text-[10px] text-text-muted">
              {currentSegmentIndex + 1}/{segments.length}
            </span>
          </div>
          <p className="text-xs text-text-secondary line-clamp-3 leading-relaxed">
            {currentSeg.text}
          </p>
        </div>
      )}

      {/* Progress bar (per segment) */}
      <div className="mb-2">
        <div className="h-1 rounded-full bg-surface-overlay overflow-hidden cursor-pointer"
          onClick={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const pct = (e.clientX - rect.left) / rect.width;
            if (audioRef?.current?.duration) {
              audioRef.current.currentTime = pct * audioRef.current.duration;
            }
          }}
        >
          <div
            className="h-full rounded-full bg-accent transition-all duration-200"
            style={{ width: `${Math.min(progress, 100)}%` }}
          />
        </div>
        <div className="flex justify-between mt-1">
          <span className="text-[9px] text-text-muted">{formatTime(elapsedMs)}</span>
          <span className="text-[9px] text-text-muted">{formatTime(totalDuration)}</span>
        </div>
      </div>

      {/* Transport controls */}
      <div className="flex items-center justify-center gap-3 mb-3">
        {/* Bookmark */}
        <button onClick={handleBookmark} className="btn-icon-sm" title="Bookmark">
          <svg className={`w-4 h-4 ${isBookmarked ? 'text-accent fill-accent' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
          </svg>
        </button>

        {/* Prev */}
        <button onClick={prevSegment} className="btn-icon-sm" disabled={currentSegmentIndex === 0}>
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12.066 11.2a1 1 0 000 1.6l5.334 4A1 1 0 0019 16V8a1 1 0 00-1.6-.8l-5.333 4zM4.066 11.2a1 1 0 000 1.6l5.334 4A1 1 0 0011 16V8a1 1 0 00-1.6-.8l-5.334 4z" />
          </svg>
        </button>

        {/* Play / Pause */}
        <button
          onClick={togglePlayPause}
          className="w-10 h-10 rounded-full bg-accent hover:bg-accent-light text-white flex items-center justify-center transition-colors"
        >
          {isPlaying ? (
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <rect x="6" y="4" width="4" height="16" rx="1" />
              <rect x="14" y="4" width="4" height="16" rx="1" />
            </svg>
          ) : (
            <svg className="w-5 h-5 ml-0.5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 5v14l11-7z" />
            </svg>
          )}
        </button>

        {/* Next */}
        <button onClick={nextSegment} className="btn-icon-sm" disabled={currentSegmentIndex >= segments.length - 1}>
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.933 12.8a1 1 0 000-1.6L6.6 7.2A1 1 0 005 8v8a1 1 0 001.6.8l5.333-4zM19.933 12.8a1 1 0 000-1.6l-5.333-4A1 1 0 0013 8v8a1 1 0 001.6.8l5.333-4z" />
          </svg>
        </button>

        {/* Speed */}
        <div className="relative">
          <button
            onClick={() => setShowSpeedMenu(!showSpeedMenu)}
            className="btn-icon-sm text-[10px] font-bold"
          >
            {playbackSpeed}x
          </button>
          {showSpeedMenu && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setShowSpeedMenu(false)} />
              <div className="absolute bottom-full mb-1 right-0 glass-strong rounded-lg shadow-glass overflow-hidden z-50 py-1">
                {SPEED_OPTIONS.map(s => (
                  <button
                    key={s}
                    onClick={() => { changeSpeed(s); setShowSpeedMenu(false); }}
                    className={`block w-full px-3 py-1.5 text-xs text-left transition-colors ${
                      playbackSpeed === s ? 'text-accent bg-accent/10' : 'text-text-secondary hover:bg-glass-light'
                    }`}
                  >
                    {s}x
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Interrupt button */}
      <button
        onClick={() => setInterruptOpen(true)}
        className="w-full py-2 rounded-lg border border-accent/30 bg-accent/5 hover:bg-accent/10 text-accent text-xs font-medium flex items-center justify-center gap-2 transition-colors mb-3"
      >
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Ask a Question
      </button>

      {/* Tabs */}
      <div className="flex border-b border-border mb-2">
        {[
          { id: 'transcript', label: 'Transcript' },
          { id: 'chapters', label: 'Chapters' },
          { id: 'doubts', label: `Q&A${doubts.length ? ` (${doubts.length})` : ''}` },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex-1 py-1.5 text-xs font-medium transition-colors border-b-2 ${
              tab === t.id
                ? 'border-accent text-accent'
                : 'border-transparent text-text-muted hover:text-text-secondary'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto min-h-0">
        {tab === 'transcript' && <PodcastTranscript />}
        {tab === 'chapters' && <PodcastChapterBar />}
        {tab === 'doubts' && <PodcastDoubtHistory />}
      </div>

      {/* Interrupt Drawer */}
      {interruptOpen && <PodcastInterruptDrawer />}

      {/* Export Dialog */}
      {showExport && <PodcastExportBar onClose={() => setShowExport(false)} />}
    </div>
  );
}
