import { usePodcast } from '../../context/PodcastContext';

export default function PodcastGenerating() {
  const { generationProgress, error, setPhase } = usePodcast();

  const pct = generationProgress?.pct ?? 0;
  const message = generationProgress?.message || 'Generating podcast…';

  return (
    <div className="flex flex-col items-center justify-center py-12 gap-4 animate-fade-in">
      {/* Spinner */}
      <div className="loading-spinner w-8 h-8" />

      {/* Message */}
      <div className="text-center">
        <p className="text-sm font-medium text-text-primary">{message}</p>
        <p className="text-xs text-text-muted mt-1">{Math.round(pct)}% complete</p>
      </div>

      {/* Progress bar */}
      <div className="w-48">
        <div className="h-1.5 rounded-full bg-surface-overlay overflow-hidden">
          <div
            className="h-full rounded-full bg-accent transition-all duration-500 ease-out"
            style={{ width: `${Math.max(pct, 5)}%` }}
          />
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="mt-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-400 max-w-xs text-center">
          <p className="font-medium mb-1">Generation failed</p>
          <p className="text-red-400/80">{error}</p>
          <button
            onClick={() => setPhase('idle')}
            className="mt-2 px-3 py-1 rounded-lg bg-red-500/15 hover:bg-red-500/25 text-red-300 text-xs transition-colors"
          >
            Try Again
          </button>
        </div>
      )}

      {/* Tip */}
      {!error && (
        <p className="text-[11px] text-text-muted text-center max-w-[180px]">
          This may take a minute
        </p>
      )}
    </div>
  );
}
