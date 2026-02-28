import { useState, useRef, useEffect } from 'react';
import { usePodcast } from '../../context/PodcastContext';
import useMicInput from '../../hooks/useMicInput';
import { fetchAudioObjectUrl } from '../../api/config';

/**
 * Slide-up drawer for asking questions during a podcast.
 * Supports typed input or voice (via mic).
 * Plays the answer audio inline and offers "resume" or "ask another".
 */
export default function PodcastInterruptDrawer() {
  const {
    session,
    setInterruptOpen,
    askQuestion,
    resume,
    error,
  } = usePodcast();

  const [question, setQuestion] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [answer, setAnswer] = useState(null);
  const [answerPlaying, setAnswerPlaying] = useState(false);
  const answerAudioRef = useRef(new Audio());
  const inputRef = useRef(null);

  const { isRecording, start: startMic, stop: stopMic } = useMicInput({
    onTranscript: (text) => setQuestion(prev => (prev ? prev + ' ' : '') + text),
  });

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = async () => {
    if (!question.trim()) return;
    try {
      setSubmitting(true);
      const result = await askQuestion(question.trim());
      setAnswer(result);

      // Play answer audio if available — must fetch with auth (token required)
      if (result?.audioPath) {
        try {
          const blobUrl = await fetchAudioObjectUrl(result.audioPath);
          answerAudioRef.current.src = blobUrl;
          answerAudioRef.current.play().catch(() => {});
          setAnswerPlaying(true);
          answerAudioRef.current.onended = () => {
            setAnswerPlaying(false);
            URL.revokeObjectURL(blobUrl);
          };
        } catch (audioErr) {
          console.error('Failed to load answer audio:', audioErr);
        }
      }
    } catch {
      // error in context
    } finally {
      setSubmitting(false);
    }
  };

  const handleResume = () => {
    answerAudioRef.current.pause();
    setInterruptOpen(false);
    resume();
  };

  const handleAskAnother = () => {
    answerAudioRef.current.pause();
    setAnswer(null);
    setQuestion('');
    setAnswerPlaying(false);
    inputRef.current?.focus();
  };

  const handleMicToggle = async () => {
    if (isRecording) {
      await stopMic();
    } else {
      await startMic();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 backdrop-blur-sm animate-fade-in"
      onClick={() => { setInterruptOpen(false); answerAudioRef.current.pause(); }}
    >
      <div
        className="w-full max-w-md glass-strong rounded-t-2xl shadow-glass p-4 animate-slide-up"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-semibold text-text-primary">Ask a Question</h4>
          <button
            onClick={() => { setInterruptOpen(false); answerAudioRef.current.pause(); }}
            className="btn-icon-sm"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Answer display */}
        {answer && (
          <div className="mb-3 p-3 rounded-lg bg-accent/5 border border-accent/20">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-purple-500/15 text-purple-400">
                GUEST
              </span>
              {answerPlaying && (
                <div className="flex gap-0.5">
                  <div className="w-1 h-3 bg-accent rounded-full animate-pulse" />
                  <div className="w-1 h-3 bg-accent rounded-full animate-pulse" style={{ animationDelay: '0.15s' }} />
                  <div className="w-1 h-3 bg-accent rounded-full animate-pulse" style={{ animationDelay: '0.3s' }} />
                </div>
              )}
            </div>
            <p className="text-xs text-text-secondary leading-relaxed">{answer.answerText}</p>

            {/* Resume / Ask Another */}
            <div className="flex gap-2 mt-3">
              <button
                onClick={handleResume}
                className="flex-1 py-2 rounded-lg bg-accent hover:bg-accent-light text-white text-xs font-medium transition-colors"
              >
                Resume Podcast
              </button>
              <button
                onClick={handleAskAnother}
                className="flex-1 py-2 rounded-lg border border-border hover:bg-surface-overlay text-text-secondary text-xs font-medium transition-colors"
              >
                Ask Another
              </button>
            </div>
          </div>
        )}

        {/* Input area */}
        {!answer && (
          <>
            <div className="flex gap-2">
              <input
                ref={inputRef}
                type="text"
                value={question}
                onChange={e => setQuestion(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSubmit()}
                placeholder="Type your question…"
                className="flex-1 px-3 py-2 text-sm rounded-lg bg-surface border border-border text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent"
                disabled={submitting}
              />

              {/* Mic button */}
              <button
                onClick={handleMicToggle}
                className={`p-2 rounded-lg border transition-all ${
                  isRecording
                    ? 'border-red-500 bg-red-500/10 text-red-400 animate-pulse'
                    : 'border-border hover:bg-surface-overlay text-text-muted'
                }`}
                title={isRecording ? 'Stop recording' : 'Start recording'}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                </svg>
              </button>
            </div>

            {/* Submit button */}
            <button
              onClick={handleSubmit}
              disabled={!question.trim() || submitting}
              className="w-full mt-2 py-2 rounded-lg bg-accent hover:bg-accent-light text-white text-xs font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {submitting ? (
                <>
                  <div className="loading-spinner w-3 h-3" />
                  Thinking…
                </>
              ) : (
                'Ask'
              )}
            </button>
          </>
        )}

        {/* Error */}
        {error && (
          <p className="text-[10px] text-red-400 mt-2 text-center">{error}</p>
        )}
      </div>
    </div>
  );
}
