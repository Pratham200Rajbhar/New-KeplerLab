import { useEffect, useRef, useCallback } from 'react';
import { usePodcast } from '../context/PodcastContext';

/**
 * Manages segment-level audio playback with lookahead prefetch,
 * speed control, and auto-advance.
 */
export default function usePodcastPlayer() {
  const {
    session,
    segments,
    currentSegmentIndex,
    isPlaying,
    playbackSpeed,
    audioRef,
    playSegment,
    prefetchSegment,
    pause,
    resume,
    togglePlayPause,
    nextSegment,
    prevSegment,
    changeSpeed,
    setCurrentSegmentIndex,
  } = usePodcast();

  // Prefetch cache: keep next 2 segments in browser cache
  const prefetchedRef = useRef(new Set());

  const prefetchAhead = useCallback(() => {
    if (!segments.length) return;
    for (let i = 1; i <= 2; i++) {
      const idx = currentSegmentIndex + i;
      if (idx < segments.length && !prefetchedRef.current.has(idx)) {
        prefetchedRef.current.add(idx);
        // Pre-warm the auth-gated blob URL cache in PodcastContext
        prefetchSegment(idx);
      }
    }
  }, [segments, currentSegmentIndex, prefetchSegment]);

  useEffect(() => {
    prefetchAhead();
  }, [prefetchAhead]);

  // Reset prefetch cache on session change
  useEffect(() => {
    prefetchedRef.current.clear();
  }, [session?.id]);

  // Seek within the current segment
  const seekTo = useCallback((timeInSeconds) => {
    if (audioRef.current) {
      audioRef.current.currentTime = timeInSeconds;
    }
  }, [audioRef]);

  // Skip forward/back by N seconds
  const skip = useCallback((deltaSeconds) => {
    if (audioRef.current) {
      audioRef.current.currentTime = Math.max(0, audioRef.current.currentTime + deltaSeconds);
    }
  }, [audioRef]);

  // Jump to a specific segment by index
  const jumpToSegment = useCallback((index) => {
    if (index >= 0 && index < segments.length) {
      playSegment(index);
    }
  }, [segments.length, playSegment]);

  // Duration of current segment audio
  const segmentDuration = audioRef.current?.duration || 0;

  return {
    isPlaying,
    currentSegmentIndex,
    playbackSpeed,
    segmentDuration,
    playSegment,
    pause,
    resume,
    togglePlayPause,
    nextSegment,
    prevSegment,
    changeSpeed,
    seekTo,
    skip,
    jumpToSegment,
  };
}
