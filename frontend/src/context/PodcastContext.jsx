import { createContext, useContext, useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { useApp } from './AppContext';
import { fetchAudioObjectUrl } from '../api/config';
import {
  createPodcastSession,
  getPodcastSession,
  listPodcastSessions,
  startPodcastGeneration,
  submitPodcastQuestion,
  getPodcastDoubts,
  addPodcastBookmark,
  deletePodcastBookmark,
  addPodcastAnnotation,
  deletePodcastAnnotation,
  deletePodcastSession,
  triggerPodcastExport,
  generatePodcastSummary,
} from '../api/podcast';

const PodcastContext = createContext(null);

/** Session status constants matching backend enum */
export const SESSION_STATUS = {
  CREATED: 'created',
  SCRIPT_GEN: 'script_generating',
  AUDIO_GEN: 'audio_generating',
  READY: 'ready',
  PLAYING: 'playing',
  PAUSED: 'paused',
  COMPLETED: 'completed',
  FAILED: 'failed',
};

export function PodcastProvider({ children }) {
  const { currentNotebook, selectedSources, podcastWsHandlerRef } = useApp();

  // ── Session state ──────────────────────────────────────
  const [session, setSession] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [segments, setSegments] = useState([]);
  const [chapters, setChapters] = useState([]);
  const [doubts, setDoubts] = useState([]);
  const [bookmarks, setBookmarks] = useState([]);
  const [annotations, setAnnotations] = useState([]);

  // ── Playback state ─────────────────────────────────────
  const [currentSegmentIndex, setCurrentSegmentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [currentTime, setCurrentTime] = useState(0); // within segment
  const [totalElapsed, setTotalElapsed] = useState(0);

  // ── UI state ───────────────────────────────────────────
  const [phase, setPhase] = useState('idle'); // idle | generating | player
  const [interruptOpen, setInterruptOpen] = useState(false);
  const [generationProgress, setGenerationProgress] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  // Audio element ref
  const audioRef = useRef(new Audio());
  // Cache: segment audio path → blob objectURL (avoids re-fetching on every play)
  const audioCacheRef = useRef(new Map());

  // ── Reset on notebook change ───────────────────────────
  useEffect(() => {
    setSession(null);
    setSessions([]);
    setSegments([]);
    setChapters([]);
    setDoubts([]);
    setBookmarks([]);
    setAnnotations([]);
    setCurrentSegmentIndex(0);
    setIsPlaying(false);
    setPhase('idle');
    setGenerationProgress(null);
    setError(null);
    audioRef.current.pause();
    audioRef.current.src = '';
    // Revoke cached object URLs to free memory
    audioCacheRef.current.forEach(url => URL.revokeObjectURL(url));
    audioCacheRef.current.clear();
  }, [currentNotebook?.id]);

  // ── Load sessions for current notebook ─────────────────
  const loadSessions = useCallback(async () => {
    if (!currentNotebook?.id || currentNotebook.isDraft) return;
    try {
      const data = await listPodcastSessions(currentNotebook.id);
      setSessions(data || []);
    } catch (err) {
      console.error('Failed to load podcast sessions:', err);
    }
  }, [currentNotebook?.id, currentNotebook?.isDraft]);

  // ── Load full session details ──────────────────────────
  const loadSession = useCallback(async (sessionId) => {
    try {
      setLoading(true);
      const data = await getPodcastSession(sessionId);
      setSession(data);
      setSegments(data.segments || []);
      setChapters(data.chapters || []);
      setDoubts(data.doubts || []);
      setBookmarks(data.bookmarks || []);
      setAnnotations(data.annotations || []);
      setCurrentSegmentIndex(data.currentSegment || 0);

      const status = data.status;
      if (status === SESSION_STATUS.READY || status === SESSION_STATUS.PLAYING ||
          status === SESSION_STATUS.PAUSED || status === SESSION_STATUS.COMPLETED) {
        setPhase('player');
      } else if (status === SESSION_STATUS.SCRIPT_GEN || status === SESSION_STATUS.AUDIO_GEN) {
        setPhase('generating');
      } else {
        setPhase('idle');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Create new session (with guard against duplicate creation) ───
  const creatingRef = useRef(false);
  const create = useCallback(async ({ mode, topic, language, hostVoice, guestVoice }) => {
    if (!currentNotebook?.id) return;
    if (creatingRef.current) return; // prevent double-invocation
    creatingRef.current = true;
    try {
      setLoading(true);
      setError(null);
      const materialIds = [...selectedSources];
      const data = await createPodcastSession({
        notebook_id: currentNotebook.id,
        material_ids: materialIds,
        mode,
        topic: topic || undefined,
        language: language || 'en',
        host_voice: hostVoice || undefined,
        guest_voice: guestVoice || undefined,
      });
      setSession(data);
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
      creatingRef.current = false;
    }
  }, [currentNotebook?.id, selectedSources]);

  // ── Start generation ───────────────────────────────────
  const startGeneration = useCallback(async (sessionId) => {
    try {
      setError(null);
      setPhase('generating');
      setGenerationProgress({ stage: 'script', pct: 0, message: 'Starting generation…' });
      await startPodcastGeneration(sessionId || session?.id);
    } catch (err) {
      setError(err.message);
      setPhase('idle');
    }
  }, [session?.id]);

  // ── Playback controls ─────────────────────────────────
  /**
   * Fetch segment audio with auth, cache the blob URL, then play.
   * Audio endpoints require Bearer auth — HTMLAudioElement.src cannot
   * send custom headers, so we fetch as a blob and use an objectURL.
   */
  const playSegment = useCallback(async (index) => {
    if (!segments[index]) return;
    const seg = segments[index];
    if (!seg.audioPath) return;

    // Update index + show loading state immediately
    setCurrentSegmentIndex(index);
    setCurrentTime(0);

    try {
      // Use cache when available
      let blobUrl = audioCacheRef.current.get(seg.audioPath);
      if (!blobUrl) {
        blobUrl = await fetchAudioObjectUrl(seg.audioPath);
        audioCacheRef.current.set(seg.audioPath, blobUrl);
      }

      audioRef.current.pause();
      audioRef.current.src = blobUrl;
      audioRef.current.playbackRate = playbackSpeed;
      await audioRef.current.play();
      setIsPlaying(true);
    } catch (err) {
      console.error('Failed to play segment', index, err);
      setIsPlaying(false);
    }
  }, [segments, playbackSpeed]);

  /**
   * Pre-warm the blob URL cache for a segment without playing it.
   * Used by usePodcastPlayer for lookahead prefetch.
   */
  const prefetchSegment = useCallback(async (index) => {
    if (!segments[index]) return;
    const seg = segments[index];
    if (!seg.audioPath || audioCacheRef.current.has(seg.audioPath)) return;
    try {
      const blobUrl = await fetchAudioObjectUrl(seg.audioPath);
      audioCacheRef.current.set(seg.audioPath, blobUrl);
    } catch (_) {
      // Prefetch failure is non-fatal
    }
  }, [segments]);

  const pause = useCallback(() => {
    audioRef.current.pause();
    setIsPlaying(false);
  }, []);

  const resume = useCallback(() => {
    // If no src loaded yet, load the current segment
    if (!audioRef.current.src || audioRef.current.src === window.location.href) {
      playSegment(currentSegmentIndex);
      return;
    }
    audioRef.current.play().catch(() => {});
    setIsPlaying(true);
  }, [currentSegmentIndex, playSegment]);

  const togglePlayPause = useCallback(() => {
    if (isPlaying) pause();
    else resume();
  }, [isPlaying, pause, resume]);

  const nextSegment = useCallback(() => {
    if (currentSegmentIndex < segments.length - 1) {
      playSegment(currentSegmentIndex + 1);
    }
  }, [currentSegmentIndex, segments.length, playSegment]);

  const prevSegment = useCallback(() => {
    if (currentSegmentIndex > 0) {
      playSegment(currentSegmentIndex - 1);
    }
  }, [currentSegmentIndex, playSegment]);

  const changeSpeed = useCallback((speed) => {
    setPlaybackSpeed(speed);
    audioRef.current.playbackRate = speed;
  }, []);

  // Auto-advance to next segment on end + time tracking
  const currentSegmentIndexRef = useRef(currentSegmentIndex);
  const segmentsRef = useRef(segments);
  useEffect(() => { currentSegmentIndexRef.current = currentSegmentIndex; }, [currentSegmentIndex]);
  useEffect(() => { segmentsRef.current = segments; }, [segments]);

  useEffect(() => {
    const audio = audioRef.current;
    const onEnded = () => {
      const idx = currentSegmentIndexRef.current;
      const segs = segmentsRef.current;
      if (idx < segs.length - 1) {
        playSegment(idx + 1);
      } else {
        setIsPlaying(false);
      }
    };
    const onTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
    };
    audio.addEventListener('ended', onEnded);
    audio.addEventListener('timeupdate', onTimeUpdate);
    return () => {
      audio.removeEventListener('ended', onEnded);
      audio.removeEventListener('timeupdate', onTimeUpdate);
    };
  }, [playSegment]); // stable deps only — refs handle mutable values

  // ── Q&A ────────────────────────────────────────────────
  const askQuestion = useCallback(async (questionText) => {
    if (!session?.id) return;
    try {
      pause();
      setInterruptOpen(true);
      const result = await submitPodcastQuestion(session.id, {
        question_text: questionText,
        paused_at_segment: currentSegmentIndex,
      });
      setDoubts(prev => [result, ...prev]);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, [session?.id, currentSegmentIndex, pause]);

  const loadDoubts = useCallback(async () => {
    if (!session?.id) return;
    try {
      const data = await getPodcastDoubts(session.id);
      setDoubts(data || []);
    } catch (err) {
      console.error('Failed to load doubts:', err);
    }
  }, [session?.id]);

  // ── Bookmarks ──────────────────────────────────────────
  const addBookmarkAction = useCallback(async (segmentIndex, label) => {
    if (!session?.id) return;
    const data = await addPodcastBookmark(session.id, { segment_index: segmentIndex, label });
    setBookmarks(prev => [...prev, data]);
    return data;
  }, [session?.id]);

  const removeBookmark = useCallback(async (bookmarkId) => {
    if (!session?.id) return;
    await deletePodcastBookmark(session.id, bookmarkId);
    setBookmarks(prev => prev.filter(b => b.id !== bookmarkId));
  }, [session?.id]);

  // ── Annotations ────────────────────────────────────────
  const addAnnotationAction = useCallback(async (segmentIndex, text) => {
    if (!session?.id) return;
    const data = await addPodcastAnnotation(session.id, { segment_index: segmentIndex, note: text });
    setAnnotations(prev => [...prev, data]);
    return data;
  }, [session?.id]);

  const removeAnnotation = useCallback(async (annotationId) => {
    if (!session?.id) return;
    await deletePodcastAnnotation(session.id, annotationId);
    setAnnotations(prev => prev.filter(a => a.id !== annotationId));
  }, [session?.id]);

  // ── Delete session ─────────────────────────────────────
  const removeSession = useCallback(async (sessionId) => {
    await deletePodcastSession(sessionId);
    setSessions(prev => prev.filter(s => s.id !== sessionId));
    if (session?.id === sessionId) {
      setSession(null);
      setPhase('idle');
    }
  }, [session?.id]);

  // ── Export ─────────────────────────────────────────────
  const exportSession = useCallback(async (format) => {
    if (!session?.id) return;
    return triggerPodcastExport(session.id, format);
  }, [session?.id]);

  const generateSummaryAction = useCallback(async () => {
    if (!session?.id) return;
    return generatePodcastSummary(session.id);
  }, [session?.id]);

  // ── WS event handler (called via podcastWsHandlerRef from Sidebar) ─
  const handleWsEvent = useCallback((event) => {
    // Backend sends flat messages: { type, session_id, phase, message, progress, ... }
    const { type, ...rest } = event;
    switch (type) {
      case 'podcast_progress': {
        // Map flat progress fields to generationProgress format
        const pct = (rest.progress ?? 0) * 100;
        setGenerationProgress({
          stage: rest.phase || 'script',
          pct,
          message: rest.message || 'Generating…',
        });
        // If error phase, set error and go idle
        if (rest.phase === 'error') {
          setError(rest.message || 'Generation failed');
          setPhase('idle');
        }
        break;
      }
      case 'podcast_ready':
        loadSession(rest.session_id || event.session_id);
        break;
      case 'podcast_segment_ready':
        // Add segment to list as it arrives for early playback
        if (rest.segment) {
          setSegments(prev => {
            const exists = prev.some(s => s.index === rest.segment.index);
            if (exists) return prev;
            return [...prev, rest.segment].sort((a, b) => a.index - b.index);
          });
        }
        break;
      case 'podcast_paused':
        pause();
        break;
      case 'podcast_answer':
        setDoubts(prev => [rest, ...prev]);
        break;
      case 'podcast_auto_resume':
        setInterruptOpen(false);
        resume();
        break;
      case 'podcast_resume_prompt':
        break;
      case 'podcast_export_ready':
        break;
      default:
        break;
    }
  }, [loadSession, pause, resume]);

  // Register WS handler so Sidebar can forward podcast_* events here
  useEffect(() => {
    if (podcastWsHandlerRef) {
      podcastWsHandlerRef.current = handleWsEvent;
    }
    return () => {
      if (podcastWsHandlerRef) {
        podcastWsHandlerRef.current = null;
      }
    };
  }, [handleWsEvent, podcastWsHandlerRef]);

  // ── Computed values ────────────────────────────────────
  const totalDuration = useMemo(() => {
    return segments.reduce((sum, s) => sum + (s.durationMs || 0), 0);
  }, [segments]);

  const currentChapter = useMemo(() => {
    if (!chapters.length) return null;
    for (let i = chapters.length - 1; i >= 0; i--) {
      if (currentSegmentIndex >= chapters[i].startSegment) return chapters[i];
    }
    return chapters[0];
  }, [chapters, currentSegmentIndex]);

  const value = useMemo(() => ({
    // Session
    session, sessions, segments, chapters, doubts, bookmarks, annotations,
    // Playback
    currentSegmentIndex, isPlaying, playbackSpeed, currentTime, totalElapsed, totalDuration, currentChapter,
    audioRef,
    // UI
    phase, interruptOpen, generationProgress, error, loading,
    // Actions
    loadSessions, loadSession, create, startGeneration,
    playSegment, prefetchSegment, pause, resume, togglePlayPause, nextSegment, prevSegment, changeSpeed,
    askQuestion, loadDoubts,
    addBookmark: addBookmarkAction, removeBookmark,
    addAnnotation: addAnnotationAction, removeAnnotation,
    removeSession, exportSession, generateSummary: generateSummaryAction,
    handleWsEvent,
    // Setters
    setPhase, setSession, setInterruptOpen, setError, setGenerationProgress,
    setCurrentSegmentIndex, setSegments, setBookmarks, setAnnotations, setDoubts,
  }), [
    session, sessions, segments, chapters, doubts, bookmarks, annotations,
    currentSegmentIndex, isPlaying, playbackSpeed, currentTime, totalElapsed, totalDuration, currentChapter,
    phase, interruptOpen, generationProgress, error, loading,
    loadSessions, loadSession, create, startGeneration,
    playSegment, prefetchSegment, pause, resume, togglePlayPause, nextSegment, prevSegment, changeSpeed,
    askQuestion, loadDoubts,
    addBookmarkAction, removeBookmark,
    addAnnotationAction, removeAnnotation,
    removeSession, exportSession, generateSummaryAction,
    handleWsEvent,
  ]);

  return (
    <PodcastContext.Provider value={value}>
      {children}
    </PodcastContext.Provider>
  );
}

export function usePodcast() {
  const context = useContext(PodcastContext);
  if (!context) {
    throw new Error('usePodcast must be used within a PodcastProvider');
  }
  return context;
}
