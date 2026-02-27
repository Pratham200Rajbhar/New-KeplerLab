import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import Modal from './Modal';
import { checkExplainerPresentations, generateExplainer, getExplainerStatus, getExplainerVideoUrl, fetchExplainerVideoBlob } from '../api/explainer';

// ── Language options with flag emojis ─────────────────────

const LANGUAGES = [
    { code: 'en', name: 'English', flag: '🇺🇸' },
    { code: 'hi', name: 'Hindi', flag: '🇮🇳' },
    { code: 'gu', name: 'Gujarati', flag: '🇮🇳' },
    { code: 'es', name: 'Spanish', flag: '🇪🇸' },
    { code: 'fr', name: 'French', flag: '🇫🇷' },
    { code: 'de', name: 'German', flag: '🇩🇪' },
    { code: 'ta', name: 'Tamil', flag: '🇮🇳' },
    { code: 'te', name: 'Telugu', flag: '🇮🇳' },
    { code: 'mr', name: 'Marathi', flag: '🇮🇳' },
    { code: 'bn', name: 'Bengali', flag: '🇮🇳' },
];

// ── Step enum ─────────────────────────────────────────────

const STEPS = {
    PPT_SELECT: 'ppt_select',
    CONFIGURE: 'configure',
    GENERATING: 'generating',
    COMPLETE: 'complete',
};

const STATUS_LABELS = {
    pending: 'Preparing...',
    capturing_slides: 'Capturing slides...',
    generating_script: 'Generating narration scripts...',
    generating_audio: 'Creating voice narration...',
    composing_video: 'Composing video...',
    completed: 'Complete!',
    failed: 'Generation failed',
};

// ── Icons ─────────────────────────────────────────────────

const ExplainerIcon = () => (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
    </svg>
);

// ── Component ─────────────────────────────────────────────

export default function ExplainerDialog({ isOpen, onClose, materialIds, notebookId }) {
    const [step, setStep] = useState(STEPS.PPT_SELECT);
    const [existingPpts, setExistingPpts] = useState([]);
    const [selectedPptId, setSelectedPptId] = useState(null);
    const [createNewPpt, setCreateNewPpt] = useState(false);
    const [pptLanguage, setPptLanguage] = useState('en');
    const [narrationLanguage, setNarrationLanguage] = useState('en');
    const [voiceGender, setVoiceGender] = useState('female');
    const [loadingPpts, setLoadingPpts] = useState(false);
    const [explainerId, setExplainerId] = useState(null);
    const [status, setStatus] = useState(null);
    const [error, setError] = useState(null);
    const [videoBlobUrl, setVideoBlobUrl] = useState(null);
    const [loadingVideo, setLoadingVideo] = useState(false);

    const pollRef = useRef(null);
    const abortRef = useRef(null);
    const initializedRef = useRef(false);
    const prevOpenRef = useRef(false);

    // Stable key for materialIds to prevent unnecessary re-runs
    const materialIdsKey = useMemo(
        () => (materialIds || []).slice().sort().join(','),
        [materialIds]
    );

    // ── Check for existing presentations on open ─────────

    useEffect(() => {
        // Only initialize when dialog OPENS (transition from closed to open)
        const justOpened = isOpen && !prevOpenRef.current;
        prevOpenRef.current = isOpen;

        // Reset initialization flag when dialog closes
        if (!isOpen) {
            initializedRef.current = false;
            return;
        }

        // Skip if already initialized this session or no required data
        if (initializedRef.current || !materialIds?.length || !notebookId) return;

        // Mark as initialized
        initializedRef.current = true;

        // Reset state for new session
        setStep(STEPS.PPT_SELECT);
        setExistingPpts([]);
        setSelectedPptId(null);
        setCreateNewPpt(false);
        setExplainerId(null);
        setStatus(null);
        setError(null);
        setVideoBlobUrl(null);
        setLoadingVideo(false);

        const checkPpts = async () => {
            setLoadingPpts(true);
            try {
                const result = await checkExplainerPresentations(materialIds, notebookId);
                if (result.found && result.presentations.length > 0) {
                    setExistingPpts(result.presentations);
                    // Auto-select single PPT
                    if (result.presentations.length === 1) {
                        setSelectedPptId(result.presentations[0].id);
                    }
                } else {
                    // No existing PPTs — skip to configure with create_new
                    setCreateNewPpt(true);
                    setStep(STEPS.CONFIGURE);
                }
            } catch (err) {
                console.error('Failed to check PPTs:', err);
                setCreateNewPpt(true);
                setStep(STEPS.CONFIGURE);
            } finally {
                setLoadingPpts(false);
            }
        };

        checkPpts();
    }, [isOpen, materialIdsKey, notebookId]);

    // ── Poll status during generation ────────────────────

    const startPolling = useCallback((id) => {
        if (pollRef.current) clearInterval(pollRef.current);

        pollRef.current = setInterval(async () => {
            try {
                const result = await getExplainerStatus(id);
                setStatus(result);

                if (result.status === 'completed') {
                    clearInterval(pollRef.current);
                    pollRef.current = null;
                    
                    // Fetch the video blob for playback
                    setLoadingVideo(true);
                    try {
                        const blobUrl = await fetchExplainerVideoBlob(id);
                        setVideoBlobUrl(blobUrl);
                    } catch (err) {
                        console.error('Failed to load video:', err);
                    }
                    setLoadingVideo(false);
                    setStep(STEPS.COMPLETE);
                } else if (result.status === 'failed') {
                    clearInterval(pollRef.current);
                    pollRef.current = null;
                    setError(result.error || 'Video generation failed');
                }
            } catch (err) {
                console.error('Status poll failed:', err);
            }
        }, 2000);
    }, []);

    // Cleanup polling and blob URL on unmount
    useEffect(() => {
        return () => {
            if (pollRef.current) clearInterval(pollRef.current);
            if (abortRef.current) abortRef.current.abort();
            if (videoBlobUrl) URL.revokeObjectURL(videoBlobUrl);
        };
    }, [videoBlobUrl]);

    // ── Handle generate ──────────────────────────────────

    const handleGenerate = async () => {
        setError(null);
        setStep(STEPS.GENERATING);

        const ac = new AbortController();
        abortRef.current = ac;

        try {
            const result = await generateExplainer({
                materialIds,
                notebookId,
                pptLanguage,
                narrationLanguage,
                voiceGender,
                presentationId: createNewPpt ? null : selectedPptId,
                createNewPpt,
                signal: ac.signal,
            });

            setExplainerId(result.explainer_id);
            setStatus({ status: 'pending', progress: 0 });
            startPolling(result.explainer_id);
        } catch (err) {
            if (err.name === 'AbortError') return;
            setError(err.message || 'Failed to start generation');
            setStep(STEPS.CONFIGURE);
        }
    };

    // ── Proceed from PPT selection ───────────────────────

    const handlePptSelected = () => {
        if (!selectedPptId && !createNewPpt) return;
        setStep(STEPS.CONFIGURE);
    };

    const handleCreateNew = () => {
        setSelectedPptId(null);
        setCreateNewPpt(true);
        setStep(STEPS.CONFIGURE);
    };

    // ── Close handler ────────────────────────────────────

    const handleClose = () => {
        if (pollRef.current) clearInterval(pollRef.current);
        if (abortRef.current) abortRef.current.abort();
        onClose();
    };

    // ── Render steps ─────────────────────────────────────

    const renderPptSelection = () => (
        <div className="space-y-4">
            {loadingPpts ? (
                <div className="flex flex-col items-center py-8 gap-2">
                    <div className="loading-spinner w-6 h-6" />
                    <span className="text-sm text-text-muted">Checking existing presentations...</span>
                </div>
            ) : (
                <>
                    <p className="text-sm text-text-secondary">
                        {existingPpts.length === 1
                            ? 'A presentation was found for your selected materials.'
                            : `${existingPpts.length} presentations found for your selected materials.`}
                    </p>

                    <div className="grid gap-2 max-h-60 overflow-y-auto">
                        {existingPpts.map((ppt) => (
                            <button
                                key={ppt.id}
                                onClick={() => { setSelectedPptId(ppt.id); setCreateNewPpt(false); }}
                                className={`w-full text-left p-3 rounded-lg border transition-colors ${
                                    selectedPptId === ppt.id
                                        ? 'border-accent bg-accent/10'
                                        : 'border-border hover:border-border-hover bg-surface-raised'
                                }`}
                            >
                                <div className="font-medium text-sm text-text-primary truncate">{ppt.title}</div>
                                <div className="text-xs text-text-muted mt-0.5">
                                    {ppt.slide_count} slides{ppt.language ? ` • ${ppt.language.toUpperCase()}` : ''}
                                </div>
                            </button>
                        ))}
                    </div>

                    <div className="flex gap-2 pt-2">
                        <button
                            onClick={handlePptSelected}
                            disabled={!selectedPptId}
                            className="btn-primary flex-1"
                        >
                            Use Selected
                        </button>
                        <button onClick={handleCreateNew} className="btn-secondary flex-1">
                            Create New
                        </button>
                    </div>
                </>
            )}
        </div>
    );

    const renderConfigure = () => (
        <form onSubmit={(e) => { e.preventDefault(); handleGenerate(); }} className="space-y-4">
            {/* PPT Language */}
            <div className="form-group">
                <label className="form-label">Slide Content Language</label>
                <div className="grid grid-cols-5 gap-1.5">
                    {LANGUAGES.map((lang) => (
                        <button
                            key={lang.code}
                            type="button"
                            onClick={() => setPptLanguage(lang.code)}
                            className={`flex flex-col items-center p-2 rounded-lg border text-xs transition-colors ${
                                pptLanguage === lang.code
                                    ? 'border-accent bg-accent/10 text-accent'
                                    : 'border-border hover:border-border-hover text-text-secondary'
                            }`}
                        >
                            <span className="text-base">{lang.flag}</span>
                            <span className="mt-0.5 truncate w-full text-center">{lang.name}</span>
                        </button>
                    ))}
                </div>
            </div>

            {/* Narration Language */}
            <div className="form-group">
                <label className="form-label">Voice Narration Language</label>
                <div className="grid grid-cols-5 gap-1.5">
                    {LANGUAGES.map((lang) => (
                        <button
                            key={lang.code}
                            type="button"
                            onClick={() => setNarrationLanguage(lang.code)}
                            className={`flex flex-col items-center p-2 rounded-lg border text-xs transition-colors ${
                                narrationLanguage === lang.code
                                    ? 'border-accent bg-accent/10 text-accent'
                                    : 'border-border hover:border-border-hover text-text-secondary'
                            }`}
                        >
                            <span className="text-base">{lang.flag}</span>
                            <span className="mt-0.5 truncate w-full text-center">{lang.name}</span>
                        </button>
                    ))}
                </div>
            </div>

            {/* Info box if languages differ */}
            {pptLanguage !== narrationLanguage && (
                <div className="flex items-start gap-2 p-3 rounded-lg bg-blue-500/10 border border-blue-500/20 text-xs text-blue-300">
                    <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                    <span>
                        Slides will be in <strong>{LANGUAGES.find(l => l.code === pptLanguage)?.name}</strong> while
                        narration will be in <strong>{LANGUAGES.find(l => l.code === narrationLanguage)?.name}</strong>.
                        The AI will adapt the explanation accordingly.
                    </span>
                </div>
            )}

            {/* Voice Gender */}
            <div className="form-group">
                <label className="form-label">Voice</label>
                <div className="flex gap-2">
                    {['female', 'male'].map((g) => (
                        <button
                            key={g}
                            type="button"
                            onClick={() => setVoiceGender(g)}
                            className={`flex-1 py-2 px-3 rounded-lg border text-sm font-medium transition-colors ${
                                voiceGender === g
                                    ? 'border-accent bg-accent/10 text-accent'
                                    : 'border-border hover:border-border-hover text-text-secondary'
                            }`}
                        >
                            {g === 'female' ? '👩 Female' : '👨 Male'}
                        </button>
                    ))}
                </div>
            </div>

            {createNewPpt && (
                <p className="text-xs text-text-muted italic">
                    A new presentation will be auto-generated from your materials.
                </p>
            )}

            <div className="flex flex-col gap-2 pt-2">
                <button type="submit" className="btn-primary w-full">
                    Generate Explainer Video
                </button>
                <button type="button" className="btn-secondary w-full" onClick={handleClose}>
                    Cancel
                </button>
            </div>
        </form>
    );

    const renderGenerating = () => {
        const progress = status?.progress || 0;
        const label = STATUS_LABELS[status?.status] || 'Processing...';

        return (
            <div className="flex flex-col items-center py-6 gap-4">
                {error ? (
                    <>
                        <div className="w-10 h-10 rounded-full bg-red-500/15 flex items-center justify-center">
                            <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </div>
                        <div className="text-center">
                            <p className="text-sm font-medium text-red-400">Generation Failed</p>
                            <p className="text-xs text-text-muted mt-1">{error}</p>
                        </div>
                        <button onClick={() => { setError(null); setStep(STEPS.CONFIGURE); }} className="btn-secondary text-sm">
                            Try Again
                        </button>
                    </>
                ) : (
                    <>
                        <div className="loading-spinner w-8 h-8" />
                        <div className="text-center">
                            <p className="text-sm font-medium text-text-primary">{label}</p>
                            <p className="text-xs text-text-muted mt-1">{progress}% complete</p>
                        </div>

                        {/* Progress bar */}
                        <div className="w-full bg-bg-secondary rounded-full h-2 overflow-hidden">
                            <div
                                className="h-full bg-accent rounded-full transition-all duration-500 ease-out"
                                style={{ width: `${progress}%` }}
                            />
                        </div>

                        <button
                            onClick={handleClose}
                            className="text-xs text-text-muted hover:text-text-secondary transition-colors"
                        >
                            Cancel
                        </button>
                    </>
                )}
            </div>
        );
    };

    const renderComplete = () => {
        const downloadUrl = explainerId ? getExplainerVideoUrl(explainerId) : null;
        const chapters = status?.chapters || [];
        const duration = status?.duration || 0;
        const mins = Math.floor(duration / 60);
        const secs = duration % 60;

        return (
            <div className="space-y-4">
                {/* Video player */}
                {loadingVideo ? (
                    <div className="rounded-lg bg-black/50 flex items-center justify-center h-48">
                        <div className="loading-spinner w-6 h-6" />
                    </div>
                ) : videoBlobUrl ? (
                    <div className="rounded-lg overflow-hidden bg-black">
                        <video
                            controls
                            autoPlay
                            className="w-full"
                            src={videoBlobUrl}
                            style={{ maxHeight: '360px' }}
                        >
                            Your browser does not support the video element.
                        </video>
                    </div>
                ) : (
                    <div className="rounded-lg bg-red-500/10 flex items-center justify-center h-32 text-sm text-red-400">
                        Failed to load video
                    </div>
                )}

                {/* Duration */}
                <div className="flex items-center justify-between text-xs text-text-muted">
                    <span>Duration: {mins}m {secs}s</span>
                    <span>{chapters.length} chapters</span>
                </div>

                {/* Chapter list */}
                {chapters.length > 0 && (
                    <div className="space-y-1 max-h-40 overflow-y-auto">
                        <p className="text-xs font-medium text-text-secondary">Chapters</p>
                        {chapters.map((ch, i) => (
                            <div key={i} className="flex items-center gap-2 text-xs text-text-muted py-1">
                                <span className="text-text-secondary tabular-nums">
                                    {Math.floor(ch.start_time / 60)}:{String(Math.floor(ch.start_time % 60)).padStart(2, '0')}
                                </span>
                                <span className="text-text-primary truncate">{ch.title}</span>
                            </div>
                        ))}
                    </div>
                )}

                {/* Actions */}
                <div className="flex gap-2 pt-2">
                    {videoBlobUrl && (
                        <a
                            href={videoBlobUrl}
                            download={`explainer_${explainerId}.mp4`}
                            className="btn-primary flex-1 text-center"
                        >
                            Download Video
                        </a>
                    )}
                    <button onClick={handleClose} className="btn-secondary flex-1">
                        Close
                    </button>
                </div>
            </div>
        );
    };

    // ── Step titles ──────────────────────────────────────

    const stepTitles = {
        [STEPS.PPT_SELECT]: 'Select Presentation',
        [STEPS.CONFIGURE]: 'Configure Explainer Video',
        [STEPS.GENERATING]: 'Generating Video...',
        [STEPS.COMPLETE]: 'Explainer Video Ready',
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={handleClose}
            title={stepTitles[step]}
            icon={<ExplainerIcon />}
            maxWidth="max-w-lg"
            showClose={step !== STEPS.GENERATING}
        >
            {step === STEPS.PPT_SELECT && renderPptSelection()}
            {step === STEPS.CONFIGURE && renderConfigure()}
            {step === STEPS.GENERATING && renderGenerating()}
            {step === STEPS.COMPLETE && renderComplete()}
        </Modal>
    );
}
