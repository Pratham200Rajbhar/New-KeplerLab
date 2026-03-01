import useMindMap from '../hooks/useMindMap';
import MindMapCanvas from './MindMapCanvas';

export default function MindMapView({ notebookId, selectedSources, onGenerated }) {
    const {
        status,
        mapData,
        isCanvasOpen,
        errorMessage,
        regenerate,
        openCanvas,
        closeCanvas,
    } = useMindMap({ notebookId, selectedSources, onGenerated });

    return (
        <>
            <div
                className={`rounded-xl border border-border bg-surface-raised p-4 ${status === 'ready' && !isCanvasOpen ? 'cursor-pointer' : ''}`}
                onClick={status === 'ready' && !isCanvasOpen ? openCanvas : undefined}
            >
                {/* Header */}
                <div className="flex items-center gap-2 mb-3">
                    <span className="text-lg">🗺</span>
                    <h3 className="text-sm font-semibold text-text-primary">Mind Map</h3>
                    {status === 'ready' && (
                        <span className="ml-auto text-xs text-green-400">✅</span>
                    )}
                </div>

                {/* Body by status */}
                {status === 'checking' && (
                    <p className="text-xs text-text-muted">Checking saved map...</p>
                )}

                {status === 'generating' && (
                    <div>
                        <div className="flex items-center gap-3 mb-3">
                            <div className="w-24 h-8 rounded bg-surface-overlay animate-pulse" />
                            <div className="flex flex-col gap-2">
                                <div className="w-16 h-6 rounded bg-surface-overlay animate-pulse" />
                                <div className="w-16 h-6 rounded bg-surface-overlay animate-pulse" />
                            </div>
                            <div className="flex flex-col gap-2">
                                <div className="w-12 h-5 rounded bg-surface-overlay animate-pulse" />
                                <div className="w-12 h-5 rounded bg-surface-overlay animate-pulse" />
                                <div className="w-12 h-5 rounded bg-surface-overlay animate-pulse" />
                            </div>
                        </div>
                        <p className="text-xs text-text-muted animate-pulse">
                            Analyzing materials and building concept graph...
                        </p>
                    </div>
                )}

                {status === 'ready' && !isCanvasOpen && (
                    <div>
                        <div className="blur-sm select-none">
                            <p className="text-sm text-text-secondary">
                                {mapData?.nodes?.length || 0} concepts mapped
                            </p>
                        </div>
                        <div className="flex items-center justify-center mt-3">
                            <span className="text-xs text-text-muted">👆 Click to Open</span>
                        </div>
                    </div>
                )}

                {status === 'error' && (
                    <div>
                        <p className="text-xs text-red-400 mb-2">{errorMessage}</p>
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                regenerate();
                            }}
                            className="text-xs px-3 py-1.5 rounded-lg bg-accent/10 text-accent hover:bg-accent/20 transition-colors"
                        >
                            Retry
                        </button>
                    </div>
                )}

                {status === 'idle' && (
                    <p className="text-xs text-text-muted">Select sources to generate a mind map.</p>
                )}
            </div>

            {/* Canvas overlay */}
            {isCanvasOpen && mapData && (
                <MindMapCanvas
                    mapData={mapData}
                    onClose={closeCanvas}
                    onRegenerate={regenerate}
                />
            )}
        </>
    );
}
