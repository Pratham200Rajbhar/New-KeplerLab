import { useState, useRef, useCallback, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { generateFlashcards, generateQuiz, generatePodcast, downloadPodcast, downloadBlob, generatePresentation } from '../api/generation';
import { apiConfig } from '../api/config';
import { saveGeneratedContent, getGeneratedContent, deleteGeneratedContent, updateGeneratedContent } from '../api/notebooks';
import { fetchExplainerVideoBlob } from '../api/explainer';
import FeatureCard from './FeatureCard';
import InlinePresentationView, { PresentationConfigDialog } from './PresentationView';
import ExplainerDialog from './ExplainerDialog';
import { jsPDF } from 'jspdf';
import Modal from './Modal';

const AudioIcon = () => (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
    </svg>
);

const FlashcardsIcon = () => (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
    </svg>
);

const QuizIcon = () => (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
    </svg>
);


const PresentationIcon = () => (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
);

const BackIcon = () => (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
    </svg>
);

const ExplainerVideoIcon = () => (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
    </svg>
);

export default function StudioPanel() {
    const { currentMaterial, currentNotebook, draftMode, setFlashcards, setQuiz, loading, setLoadingState, selectedSources, materials } = useApp();

    // Effective material: first selected source (checkbox only)
    const effectiveMaterial = selectedSources.size > 0
        ? materials.find(m => selectedSources.has(m.id)) || null
        : null;

    // All selected material IDs for multi-source generation
    const selectedMaterialIds = [...selectedSources];

    // View state: null = grid view, 'audio' | 'flashcards' | 'quiz' | 'explainer' = inline view
    const [activeView, setActiveView] = useState(null);

    const [flashcardsData, setFlashcardsData] = useState(null);
    const [quizData, setQuizData] = useState(null);
    const [audioData, setAudioData] = useState(null);
    const [presentationData, setPresentationData] = useState(null);
    const [explainerData, setExplainerData] = useState(null);
    const [showPresentationConfig, setShowPresentationConfig] = useState(false);
    const [showQuizConfig, setShowQuizConfig] = useState(false);
    const [showFlashcardConfig, setShowFlashcardConfig] = useState(false);
    const [showExplainerDialog, setShowExplainerDialog] = useState(false);
    const [contentHistory, setContentHistory] = useState([]); // all saved items across types
    const [activeHistoryMenu, setActiveHistoryMenu] = useState(null);
    const [showRenameHistoryModal, setShowRenameHistoryModal] = useState(false);
    const [renamingHistoryItem, setRenamingHistoryItem] = useState(null);
    const [newHistoryTitle, setNewHistoryTitle] = useState('');
    const [width, setWidth] = useState(360);
    const [isResizing, setIsResizing] = useState(false);
    const [actionError, setActionError] = useState(null);
    const panelRef = useRef(null);
    const abortControllerRef = useRef({});

    const handleCancelGeneration = useCallback((type) => {
        abortControllerRef.current[type]?.abort();
    }, []);

    const minWidth = 260;
    const maxWidth = 600;

    useEffect(() => {
        // Reset all content state when notebook changes
        setFlashcardsData(null);
        setQuizData(null);
        setAudioData(null);
        setPresentationData(null);
        setShowPresentationConfig(false);
        setShowQuizConfig(false);
        setShowFlashcardConfig(false);
        setShowExplainerDialog(false);
        setContentHistory([]);
        setFlashcards(null);
        setQuiz(null);
        setActiveView(null);

        const loadSavedContent = async () => {
            if (currentNotebook?.id && !currentNotebook.isDraft && !draftMode) {
                try {
                    const contents = await getGeneratedContent(currentNotebook.id);
                    // Backend returns newest first (createdAt desc).
                    // Load ALL items into history; set individual data state from newest per type.
                    setContentHistory(contents.map(c => ({ ...c })));
                    const seen = new Set();
                    for (const c of contents) {
                        if (seen.has(c.content_type)) continue;
                        seen.add(c.content_type);
                        switch (c.content_type) {
                            case 'flashcards':
                                setFlashcardsData(c.data);
                                setFlashcards(c.data);
                                break;
                            case 'quiz':
                                setQuizData(c.data);
                                setQuiz(c.data);
                                break;
                            case 'audio':
                                setAudioData(c.data);
                                break;
                            case 'presentation':
                                setPresentationData(c.data);
                                break;
                        }
                    }
                } catch (error) {
                    console.error('Failed to load saved content:', error);
                }
            }
        };
        loadSavedContent();
    }, [currentNotebook?.id]);

    const handleMouseMove = useCallback((e) => {
        if (isResizing && panelRef.current) {
            const rect = panelRef.current.getBoundingClientRect();
            const newWidth = rect.right - e.clientX;
            if (newWidth >= minWidth && newWidth <= maxWidth) {
                setWidth(newWidth);
            }
        }
    }, [isResizing]);

    const handleMouseUp = useCallback(() => {
        setIsResizing(false);
    }, []);

    useEffect(() => {
        if (isResizing) {
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
        }
        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };
    }, [isResizing, handleMouseMove, handleMouseUp]);

    const canSave = currentNotebook?.id && !currentNotebook.isDraft && !draftMode;

    // Helper: save content with error handling; returns saved record with data included
    const trySave = async (contentType, data, title) => {
        if (!canSave) return null;
        try {
            const saved = await saveGeneratedContent(currentNotebook.id, contentType, data, title, effectiveMaterial?.id);
            return { ...saved, data };
        } catch (error) {
            console.error(`Failed to save ${contentType}:`, error);
            return null;
        }
    };

    const handleGenerateAudio = async () => {
        if (!effectiveMaterial) return;
        setLoadingState('audio', true);
        const ac = new AbortController();
        abortControllerRef.current.audio = ac;
        try {
            const data = await generatePodcast(effectiveMaterial.id, ac.signal);
            setAudioData(data);
            setActiveView('audio');
            const saved = await trySave('audio', data, data.title || 'Audio Overview');
            if (saved) setContentHistory(prev => [saved, ...prev]);
        } catch (error) {
            if (error.name === 'AbortError') return;
            console.error('Failed to generate podcast:', error);
            setActionError(error.message || 'Failed to generate audio overview. Please try again.');
            setTimeout(() => setActionError(null), 5000);
        } finally {
            setLoadingState('audio', false);
        }
    };

    const handleFlashcardsClick = () => {
        setShowFlashcardConfig(true);
        setActiveView('flashcard-config');
    };

    const handleGenerateFlashcards = async (options = {}) => {
        if (!effectiveMaterial) return;
        setShowFlashcardConfig(false);
        setLoadingState('flashcards', true);
        const ac = new AbortController();
        abortControllerRef.current.flashcards = ac;
        try {
            const data = await generateFlashcards(effectiveMaterial.id, { ...options, materialIds: selectedMaterialIds, signal: ac.signal });
            setFlashcardsData(data);
            setFlashcards(data);
            setActiveView('flashcards');
            const saved = await trySave('flashcards', data, data.title || `${data.flashcards?.length || 0} Flashcards`);
            if (saved) setContentHistory(prev => [saved, ...prev]);
        } catch (error) {
            if (error.name === 'AbortError') return;
            console.error('Failed to generate flashcards:', error);
            setActionError(error.message || 'Failed to generate flashcards. Please try again.');
            setTimeout(() => setActionError(null), 5000);
        } finally {
            setLoadingState('flashcards', false);
        }
    };

    const handleQuizClick = () => {
        setShowQuizConfig(true);
        setActiveView('quiz-config');
    };

    const handleGenerateQuiz = async (options = {}) => {
        if (!effectiveMaterial) return;
        setShowQuizConfig(false);
        setLoadingState('quiz', true);
        const ac = new AbortController();
        abortControllerRef.current.quiz = ac;
        try {
            const data = await generateQuiz(effectiveMaterial.id, { ...options, materialIds: selectedMaterialIds, signal: ac.signal });
            setQuizData(data);
            setQuiz(data);
            setActiveView('quiz');
            const saved = await trySave('quiz', data, data.title || `${data.questions?.length || 0} Questions`);
            if (saved) setContentHistory(prev => [saved, ...prev]);
        } catch (error) {
            if (error.name === 'AbortError') return;
            console.error('Failed to generate quiz:', error);
            setActionError(error.message || 'Failed to generate quiz. Please try again.');
            setTimeout(() => setActionError(null), 5000);
        } finally {
            setLoadingState('quiz', false);
        }
    };

    // Presentation: show config dialog first
    const handlePresentationClick = () => {
        setShowPresentationConfig(true);
        setActiveView('presentation-config');
    };

    const handleGeneratePresentation = async (options = {}) => {
        if (!effectiveMaterial) return;
        setShowPresentationConfig(false); // Close the modal
        setLoadingState('presentation', true);
        setActiveView('presentation');
        const ac = new AbortController();
        abortControllerRef.current.presentation = ac;
        try {
            const data = await generatePresentation(effectiveMaterial.id, { ...options, materialIds: selectedMaterialIds, signal: ac.signal });
            setPresentationData(data);
            const saved = await trySave('presentation', data, data.title || 'Presentation');
            if (saved) setContentHistory(prev => [saved, ...prev]);
        } catch (error) {
            if (error.name === 'AbortError') { setActiveView(null); return; }
            console.error('Failed to generate presentation:', error);
            setPresentationData(null);
            setActionError(error.message || 'Failed to generate presentation. Please try again.');
            setTimeout(() => setActionError(null), 5000);
        } finally {
            setLoadingState('presentation', false);
        }
    };


    // Open a history item in the inline viewer
    const handleViewHistoryItem = (item) => {
        switch (item.content_type) {
            case 'audio':
                setAudioData(item.data);
                setActiveView('audio');
                break;
            case 'flashcards':
                setFlashcardsData(item.data);
                setFlashcards(item.data);
                setActiveView('flashcards');
                break;
            case 'quiz':
                setQuizData(item.data);
                setQuiz(item.data);
                setActiveView('quiz');
                break;
            case 'presentation':
                setPresentationData(item.data);
                setActiveView('presentation');
                break;
            case 'explainer':
                setExplainerData(item.data);
                setActiveView('explainer');
                break;
        }
    };

    const handleHistoryRename = async (e) => {
        e.preventDefault();
        if (!newHistoryTitle.trim() || !renamingHistoryItem || !currentNotebook) return;

        try {
            const updated = await updateGeneratedContent(currentNotebook.id, renamingHistoryItem.id, newHistoryTitle.trim());

            // Re-sync local history list state with the matching ID
            setContentHistory(prev => prev.map(item => item.id === renamingHistoryItem.id ? updated : item));

            // Sync currently active view properties if valid
            switch (updated.content_type) {
                case 'flashcards':
                    if (flashcardsData?.id === updated.id) setFlashcardsData(updated);
                    break;
                case 'quiz':
                    if (quizData?.id === updated.id) setQuizData(updated);
                    break;
                case 'presentation':
                    if (presentationData?.id === updated.id) setPresentationData(updated);
                    break;
                case 'audio':
                    if (audioData?.id === updated.id) setAudioData(updated);
                    break;
            }

            setShowRenameHistoryModal(false);
            setRenamingHistoryItem(null);
            setNewHistoryTitle('');
        } catch (err) {
            console.error('Failed to rename content:', err);
        }
    };

    const [showDeleteConfirm, setShowDeleteConfirm] = useState(null); // item to delete

    const handleHistoryDelete = async (item, e) => {
        e.stopPropagation();
        setActiveHistoryMenu(null);
        setShowDeleteConfirm(item);
    };

    const confirmHistoryDelete = async () => {
        const item = showDeleteConfirm;
        if (!currentNotebook || !item) return;
        setShowDeleteConfirm(null);

        try {
            await deleteGeneratedContent(currentNotebook.id, item.id);
            setContentHistory(prev => prev.filter(c => c.id !== item.id));

            // Empty the active view if that's what was deleted
            if (activeView === item.content_type) {
                switch (item.content_type) {
                    case 'flashcards':
                        if (flashcardsData?.id === item.id) { setFlashcardsData(null); setFlashcards(null); setActiveView(null); }
                        break;
                    case 'quiz':
                        if (quizData?.id === item.id) { setQuizData(null); setQuiz(null); setActiveView(null); }
                        break;
                    case 'presentation':
                        if (presentationData?.id === item.id) { setPresentationData(null); setActiveView(null); }
                        break;
                    case 'audio':
                        if (audioData?.id === item.id) { setAudioData(null); setActiveView(null); }
                        break;
                }
            }
        } catch (err) {
            console.error('Failed to delete content:', err);
            setActionError('Failed to delete content. Please try again.');
            setTimeout(() => setActionError(null), 5000);
        }
    };

    const handleHistoryShare = async (item, e) => {
        e.stopPropagation();
        setActiveHistoryMenu(null);
        try {
            const contentStr = JSON.stringify(item.data, null, 2);
            await navigator.clipboard.writeText(contentStr);
        } catch {
            // clipboard API not available — silent fallback
        }
    };

    const handleHistoryDownload = (item, e) => {
        e.stopPropagation();
        setActiveHistoryMenu(null);

        // Use basic generic downloader as JSON blob if specific ones are skipped
        try {
            let contentStr = '';
            let fileExt = 'json';
            let blobType = 'application/json';

            if (item.content_type === 'audio' && typeof item.data === 'string') {
                // Base64 blob wrapper handler natively down below handles Audio downloads
                alert('Please open the audio block sequentially and click native Download in viewer.');
                return;
            } else {
                contentStr = JSON.stringify(item.data, null, 2);
            }

            const blob = new Blob([contentStr], { type: blobType });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${item.title || item.content_type}.${fileExt}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } catch (err) {
            console.error('Failed to export raw content', err);
        }
    };

    const openHistoryRenameModal = (item, e) => {
        e.stopPropagation();
        setActiveHistoryMenu(null);
        setRenamingHistoryItem(item);
        setNewHistoryTitle(item.title || item.content_type);
        setShowRenameHistoryModal(true);
    };

    const contentTypeIcon = (type) => {
        switch (type) {
            case 'audio': return <AudioIcon />;
            case 'flashcards': return <FlashcardsIcon />;
            case 'quiz': return <QuizIcon />;
            case 'presentation': return <PresentationIcon />;
            case 'explainer': return <ExplainerVideoIcon />;
            default: return null;
        }
    };

    const contentSubtitle = (item) => {
        switch (item.content_type) {
            case 'flashcards': return `${item.data?.flashcards?.length || 0} cards`;
            case 'quiz': return `${item.data?.questions?.length || 0} questions`;
            case 'presentation': return `${item.data?.slide_count || 0} slides`;
            case 'explainer': {
                const duration = item.data?.duration || 0;
                const mins = Math.floor(duration / 60);
                const secs = duration % 60;
                return mins ? `${mins}m ${secs}s video` : `${secs}s video`;
            }
            default: return 'Ready to play';
        }
    };

    const outputs = [
        { id: 'audio', title: 'Audio Overview', description: 'Listen to a podcast-style summary', icon: <AudioIcon />, onClick: handleGenerateAudio, onCancel: () => handleCancelGeneration('audio') },
        { id: 'flashcards', title: 'Flashcards', description: 'Study with spaced repetition', icon: <FlashcardsIcon />, onClick: handleFlashcardsClick, onCancel: () => handleCancelGeneration('flashcards') },
        { id: 'quiz', title: 'Practice Quiz', description: 'Test your understanding', icon: <QuizIcon />, onClick: handleQuizClick, onCancel: () => handleCancelGeneration('quiz') },
        { id: 'presentation', title: 'Presentation', description: 'Generate a slide deck from content', icon: <PresentationIcon />, onClick: handlePresentationClick, onCancel: () => handleCancelGeneration('presentation') },
        { id: 'explainer', title: 'Explainer Video', description: 'Create a narrated video from slides', icon: <ExplainerVideoIcon />, onClick: () => setShowExplainerDialog(true) },
    ];

    const viewTitles = {
        audio: 'Audio Overview',
        flashcards: 'Flashcards',
        quiz: 'Quiz',
        presentation: 'Presentation',
        explainer: 'Explainer Video',
    };

    const renderInlineContent = () => {
        switch (activeView) {
            case 'audio':
                return <InlineAudioView data={audioData} materialId={effectiveMaterial?.id} />;
            case 'flashcards':
                return <InlineFlashcardsView data={flashcardsData} />;
            case 'quiz':
                return <InlineQuizView data={quizData} />;
            case 'presentation':
                return loading['presentation'] ? (
                    <div className="flex flex-col items-center justify-center py-12 gap-3">
                        <div className="loading-spinner w-8 h-8" />
                        <p className="text-sm text-text-muted">Generating presentation...</p>
                        <p className="text-xs text-text-muted">This may take a minute</p>
                        <button
                            onClick={() => handleCancelGeneration('presentation')}
                            className="mt-2 flex items-center gap-2 px-3 py-1.5 rounded-lg bg-red-500/15 text-red-400 hover:bg-red-500/25 text-sm transition-colors"
                        >
                            <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                                <rect x="6" y="6" width="12" height="12" rx="2" />
                            </svg>
                            Cancel
                        </button>
                    </div>
                ) : (
                    <InlinePresentationView
                        data={presentationData}
                        onRegenerate={() => setShowPresentationConfig(true)}
                        loading={loading['presentation']}
                    />
                );
            case 'explainer':
                return <InlineExplainerView data={explainerData} />;
            default:
                return null;
        }
    };

    return (
        <>
            {/* Delete Confirmation Dialog */}
            {showDeleteConfirm && (
                <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={() => setShowDeleteConfirm(null)}>
                    <div className="bg-surface-raised border border-border rounded-xl shadow-2xl p-6 max-w-sm w-full mx-4" onClick={e => e.stopPropagation()}>
                        <h3 className="text-base font-semibold text-text-primary mb-2">Delete content?</h3>
                        <p className="text-sm text-text-secondary mb-5">
                            "{showDeleteConfirm.title || showDeleteConfirm.content_type}" will be permanently deleted.
                        </p>
                        <div className="flex justify-end gap-2">
                            <button onClick={() => setShowDeleteConfirm(null)} className="px-4 py-2 text-sm rounded-lg text-text-secondary hover:bg-bg-secondary transition-colors">Cancel</button>
                            <button onClick={confirmHistoryDelete} className="px-4 py-2 text-sm rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 font-medium transition-colors">Delete</button>
                        </div>
                    </div>
                </div>
            )}

            {/* History Item Rename Modal - Rendered outside sidebar */}
            <HistoryRenameModal
                isOpen={showRenameHistoryModal}
                onClose={() => {
                    setShowRenameHistoryModal(false);
                    setRenamingHistoryItem(null);
                    setNewHistoryTitle('');
                }}
                itemName={renamingHistoryItem?.title || renamingHistoryItem?.content_type || ''}
                newTitle={newHistoryTitle}
                setNewTitle={setNewHistoryTitle}
                onSave={handleHistoryRename}
            />

            {/* Presentation Config Modal - Rendered outside sidebar */}
            {showPresentationConfig && (
                <PresentationConfigDialog
                    onGenerate={handleGeneratePresentation}
                    onCancel={() => {
                        setShowPresentationConfig(false);
                        if (activeView === 'presentation-config') {
                            setActiveView(null);
                        }
                    }}
                    loading={loading['presentation']}
                />
            )}

            {showQuizConfig && (
                <QuizConfigDialog
                    onGenerate={handleGenerateQuiz}
                    onCancel={() => {
                        setShowQuizConfig(false);
                        if (activeView === 'quiz-config') {
                            setActiveView(null);
                        }
                    }}
                    loading={loading['quiz']}
                />
            )}

            {showFlashcardConfig && (
                <FlashcardConfigDialog
                    onGenerate={handleGenerateFlashcards}
                    onCancel={() => {
                        setShowFlashcardConfig(false);
                        if (activeView === 'flashcard-config') {
                            setActiveView(null);
                        }
                    }}
                    loading={loading['flashcards']}
                />
            )}

            {/* Explainer Video Dialog */}
            <ExplainerDialog
                isOpen={showExplainerDialog}
                onClose={() => setShowExplainerDialog(false)}
                materialIds={selectedMaterialIds}
                notebookId={currentNotebook?.id}
            />

            <aside
                ref={panelRef}
                className="glass-light h-full overflow-hidden flex flex-col relative border-l border-border"
                style={{ width: `${width}px`, minWidth: `${minWidth}px` }}
            >
                {/* Resize Handle */}
                <div
                    className={`absolute top-0 left-0 w-1.5 h-full cursor-col-resize transition-colors z-10 group ${isResizing ? 'bg-accent/50' : 'hover:bg-accent/30'}`}
                    onMouseDown={() => setIsResizing(true)}
                >
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-1 h-8 rounded-full bg-text-muted/20 opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>

                {/* Header with Breadcrumb */}
                <div className="panel-header">
                    <div className="flex items-center gap-2">
                        {activeView ? (
                            <>
                                <button
                                    onClick={() => setActiveView(null)}
                                    className="btn-icon-sm -ml-1"
                                >
                                    <BackIcon />
                                </button>
                                <span className="text-text-muted text-sm">Studio</span>
                                <svg className="w-4 h-4 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                </svg>
                                <span className="panel-title">{viewTitles[activeView]}</span>
                            </>
                        ) : (
                            <>
                                <svg className="w-5 h-5 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                                </svg>
                                <span className="panel-title">Studio</span>
                            </>
                        )}
                    </div>
                </div>

                {/* Content Area */}
                <div className="flex-1 overflow-y-auto p-4 relative">
                    {/* Error Toast */}
                    {actionError && (
                        <div className="absolute top-4 left-4 right-4 z-50 animate-fade-in fade-up">
                            <div className="bg-[#ef4444]/10 border border-[#ef4444]/30 p-3 rounded-xl shadow-lg backdrop-blur-md flex items-start gap-3">
                                <div className="mt-0.5 w-6 h-6 rounded-full bg-[#ef4444]/20 flex items-center justify-center flex-shrink-0">
                                    <svg className="w-4 h-4 text-[#ef4444]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                    </svg>
                                </div>
                                <div className="flex-1">
                                    <h5 className="text-sm font-bold text-[#f87171]">Generation Failed</h5>
                                    <p className="text-xs text-text-secondary mt-0.5">{actionError}</p>
                                </div>
                                <button onClick={() => setActionError(null)} className="text-text-muted hover:text-text-primary p-1">
                                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                    </svg>
                                </button>
                            </div>
                        </div>
                    )}

                    {activeView ? (
                        // Inline Content View
                        renderInlineContent()
                    ) : effectiveMaterial ? (
                        // Grid View
                        <>
                            <p className="text-xs text-text-muted mb-4">
                                {selectedSources.size > 1
                                    ? <>Generate from <span className="text-text-secondary">{selectedSources.size} selected sources</span> (using first selected)</>
                                    : <>Create study materials from <span className="text-text-secondary">{effectiveMaterial.filename}</span></>}
                            </p>

                            <div className="space-y-2.5">
                                {outputs.map((output, i) => (
                                    <div
                                        key={output.id}
                                        className="animate-fade-up"
                                        style={{ animationDelay: `${i * 60}ms`, animationFillMode: 'backwards' }}
                                    >
                                        <FeatureCard
                                            icon={output.icon}
                                            title={output.title}
                                            description={output.description}
                                            onClick={output.onClick}
                                            loading={loading[output.id]}
                                            disabled={!effectiveMaterial}
                                            onCancel={output.onCancel}
                                        />
                                    </div>
                                ))}
                            </div>

                            {contentHistory.length > 0 && (
                                <>
                                    <div className="divider my-5" />
                                    <h3 className="text-xs font-medium text-text-muted uppercase tracking-wider mb-3">Created</h3>
                                    <div className="space-y-2">
                                        {contentHistory.map((item) => (
                                            <div
                                                key={item.id}
                                                className="relative group w-full"
                                            >
                                                <div
                                                    className="output-card w-full text-left cursor-pointer flex items-center pr-10"
                                                    onClick={() => handleViewHistoryItem(item)}
                                                >
                                                    <div className="output-card-icon bg-accent/10">
                                                        <span className="text-accent-light">{contentTypeIcon(item.content_type)}</span>
                                                    </div>
                                                    <div className="flex-1 min-w-0 pr-2">
                                                        <h4 className="text-sm font-medium text-text-primary truncate">{item.title || item.content_type}</h4>
                                                        <p className="text-xs text-text-muted">{contentSubtitle(item)}</p>
                                                    </div>
                                                </div>

                                                {/* 3-dot menu button */}
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        setActiveHistoryMenu(activeHistoryMenu === item.id ? null : item.id);
                                                    }}
                                                    className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 rounded-lg hover:bg-surface-overlay text-text-muted opacity-0 group-hover:opacity-100 transition-all z-10"
                                                >
                                                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
                                                    </svg>
                                                </button>

                                                {/* Actions submenu */}
                                                {activeHistoryMenu === item.id && (
                                                    <>
                                                        <div className="fixed inset-0 z-40" onClick={(e) => { e.stopPropagation(); setActiveHistoryMenu(null); }} />
                                                        <div className="absolute right-4 top-[80%] mt-1 w-36 glass-strong rounded-lg shadow-glass overflow-hidden z-50">
                                                            <button
                                                                onClick={(e) => openHistoryRenameModal(item, e)}
                                                                className="w-full px-3 py-2 text-left text-sm text-text-secondary hover:bg-glass-light flex items-center gap-2 transition-colors"
                                                            >
                                                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                                                                </svg>
                                                                Rename
                                                            </button>
                                                            <button
                                                                onClick={(e) => handleHistoryDownload(item, e)}
                                                                className="w-full px-3 py-2 text-left text-sm text-text-secondary hover:bg-glass-light flex items-center gap-2 transition-colors"
                                                            >
                                                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                                                </svg>
                                                                Export
                                                            </button>
                                                            <button
                                                                onClick={(e) => handleHistoryShare(item, e)}
                                                                className="w-full px-3 py-2 text-left text-sm text-text-secondary hover:bg-glass-light flex items-center gap-2 transition-colors"
                                                            >
                                                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
                                                                </svg>
                                                                Share
                                                            </button>
                                                            <button
                                                                onClick={(e) => handleHistoryDelete(item, e)}
                                                                className="w-full px-3 py-2 text-left text-sm text-red-400 hover:bg-red-500/10 flex items-center gap-2 transition-colors border-t border-border/50"
                                                            >
                                                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                                                </svg>
                                                                Delete
                                                            </button>
                                                        </div>
                                                    </>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </>
                            )}
                        </>
                    ) : (
                        <div className="empty-state h-full">
                            <div className="empty-state-icon">
                                <svg className="w-8 h-8 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                                </svg>
                            </div>
                            <p className="empty-state-title">No source selected</p>
                            <p className="empty-state-description">Select a source to generate study materials</p>
                        </div>
                    )}
                </div>
            </aside>
        </>
    );
}

// ==================== INLINE VIEW COMPONENTS ====================

function FlashcardConfigDialog({ onGenerate, onCancel, loading }) {
    const [cardCount, setCardCount] = useState('');
    const [difficulty, setDifficulty] = useState('Medium');
    const [additionalInstructions, setAdditionalInstructions] = useState('');

    const difficulties = ['Easy', 'Medium', 'Hard'];

    const handleSubmit = (e) => {
        e.preventDefault();
        onGenerate({
            cardCount: cardCount ? parseInt(cardCount, 10) : null,
            difficulty: difficulty,
            additionalInstructions: additionalInstructions.trim() || null,
        });
    };

    const modalIcon = (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
    );

    return (
        <Modal
            isOpen={true}
            onClose={onCancel}
            title="Flashcard Options"
            icon={modalIcon}
            maxWidth="max-w-xl"
            showClose={!loading}
        >
            <p className="text-sm text-text-muted mb-6 leading-relaxed">
                Customize your flashcard generation settings.
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
                {/* Card Count */}
                <div className="form-group">
                    <label className="form-label">
                        Number of Flashcards <span className="form-label-hint">(optional)</span>
                    </label>
                    <input
                        type="number"
                        min="1"
                        max="50"
                        value={cardCount}
                        onChange={e => setCardCount(e.target.value)}
                        className="input"
                        placeholder="AI decides"
                        disabled={loading}
                    />
                </div>

                {/* Difficulty */}
                <div className="form-group">
                    <label className="form-label">
                        Difficulty Level
                    </label>
                    <div className="chip-group">
                        {difficulties.map(d => (
                            <button
                                key={d}
                                type="button"
                                className={`chip${difficulty === d ? ' selected' : ''}`}
                                onClick={() => setDifficulty(d)}
                                disabled={loading}
                            >
                                {d}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Instructions */}
                <div className="form-group">
                    <label className="form-label">
                        Additional Instructions <span className="form-label-hint">(optional)</span>
                    </label>
                    <textarea
                        value={additionalInstructions}
                        onChange={e => setAdditionalInstructions(e.target.value)}
                        placeholder="e.g. Focus on definitions, emphasize cause and effect, include specific vocabulary..."
                        rows={3}
                        className="textarea"
                        disabled={loading}
                    />
                </div>

                {/* Action buttons */}
                <div className="flex flex-col gap-2 pt-2">
                    <button type="submit" className="btn-primary w-full" disabled={loading}>
                        {loading ? (
                            <>
                                <div className="loading-spinner w-4 h-4" />
                                Generating Cards…
                            </>
                        ) : (
                            <>
                                <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" className="mr-2">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                </svg>
                                Generate Cards
                            </>
                        )}
                    </button>

                    <button
                        type="button"
                        className="btn-secondary w-full"
                        onClick={onCancel}
                        disabled={loading}
                    >
                        Cancel
                    </button>
                </div>
            </form>
        </Modal>
    );
}

function QuizConfigDialog({ onGenerate, onCancel, loading }) {
    const [mcqCount, setMcqCount] = useState('');
    const [difficulty, setDifficulty] = useState('Medium');
    const [additionalInstructions, setAdditionalInstructions] = useState('');

    const difficulties = ['Easy', 'Medium', 'Hard'];

    const handleSubmit = (e) => {
        e.preventDefault();
        onGenerate({
            mcqCount: mcqCount ? parseInt(mcqCount, 10) : null,
            difficulty: difficulty,
            additionalInstructions: additionalInstructions.trim() || null,
        });
    };

    const modalIcon = (
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
        </svg>
    );

    return (
        <Modal
            isOpen={true}
            onClose={onCancel}
            title="Quiz Options"
            icon={modalIcon}
            maxWidth="max-w-xl"
            showClose={!loading}
        >
            <p className="text-sm text-text-muted mb-6 leading-relaxed">
                Customize your practice quiz settings.
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
                {/* MCQ Count */}
                <div className="form-group">
                    <label className="form-label">
                        Number of Questions <span className="form-label-hint">(optional)</span>
                    </label>
                    <input
                        type="number"
                        min="1"
                        max="50"
                        value={mcqCount}
                        onChange={e => setMcqCount(e.target.value)}
                        className="input"
                        placeholder="AI decides"
                        disabled={loading}
                    />
                </div>

                {/* Difficulty */}
                <div className="form-group">
                    <label className="form-label">
                        Difficulty Level
                    </label>
                    <div className="chip-group">
                        {difficulties.map(d => (
                            <button
                                key={d}
                                type="button"
                                className={`chip${difficulty === d ? ' selected' : ''}`}
                                onClick={() => setDifficulty(d)}
                                disabled={loading}
                            >
                                {d}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Instructions */}
                <div className="form-group">
                    <label className="form-label">
                        Additional Instructions <span className="form-label-hint">(optional)</span>
                    </label>
                    <textarea
                        value={additionalInstructions}
                        onChange={e => setAdditionalInstructions(e.target.value)}
                        placeholder="e.g. Focus specifically on the second chapter, include tricky distractors, etc..."
                        rows={3}
                        className="textarea"
                        disabled={loading}
                    />
                </div>

                {/* Action buttons */}
                <div className="flex flex-col gap-2 pt-2">
                    <button type="submit" className="btn-primary w-full" disabled={loading}>
                        {loading ? (
                            <>
                                <div className="loading-spinner w-4 h-4" />
                                Generating Quiz…
                            </>
                        ) : (
                            <>
                                <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" className="mr-2">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                </svg>
                                Generate Quiz
                            </>
                        )}
                    </button>

                    <button
                        type="button"
                        className="btn-secondary w-full"
                        onClick={onCancel}
                        disabled={loading}
                    >
                        Cancel
                    </button>
                </div>
            </form>
        </Modal>
    );
}

function InlineAudioView({ data, materialId }) {
    const [downloading, setDownloading] = useState(false);
    const [isPlaying, setIsPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [playbackSpeed, setPlaybackSpeed] = useState(1);
    const [activeCaptionIndex, setActiveCaptionIndex] = useState(-1);
    const audioRef = useRef(null);
    const captionRefs = useRef([]);
    const captionContainerRef = useRef(null);

    const audioFilename = data?.audio_filename;
    const userId = data?.user_id;
    const title = data?.title || 'Audio Overview';
    const dialogue = data?.dialogue || [];

    const handleDownload = async () => {
        setDownloading(true);
        try {
            const blob = await downloadPodcast(materialId);
            downloadBlob(blob, `${title.replace(/\s+/g, '_')}.wav`);
        } catch (error) {
            console.error('Failed to download audio:', error);
        } finally {
            setDownloading(false);
        }
    };

    const audioUrl = (audioFilename && userId) ? `${apiConfig.baseUrl}/podcast/audio/${encodeURIComponent(userId)}/${encodeURIComponent(audioFilename)}` : null;

    const formatTime = (seconds) => {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    };

    const togglePlay = () => {
        if (audioRef.current) {
            if (isPlaying) {
                audioRef.current.pause();
            } else {
                audioRef.current.play();
            }
            setIsPlaying(!isPlaying);
        }
    };

    const handleTimeUpdate = () => {
        if (audioRef.current) {
            const time = audioRef.current.currentTime;
            setCurrentTime(time);

            // Find active caption based on current time
            const activeIndex = dialogue.findIndex(
                (segment) => time >= segment.start_time && time < segment.end_time
            );

            if (activeIndex !== activeCaptionIndex) {
                setActiveCaptionIndex(activeIndex);

                // Auto-scroll to active caption
                if (activeIndex >= 0 && captionRefs.current[activeIndex] && captionContainerRef.current) {
                    const container = captionContainerRef.current;
                    const caption = captionRefs.current[activeIndex];
                    const containerRect = container.getBoundingClientRect();
                    const captionRect = caption.getBoundingClientRect();

                    // Check if caption is not fully visible
                    if (captionRect.top < containerRect.top || captionRect.bottom > containerRect.bottom) {
                        caption.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                }
            }
        }
    };

    const handleLoadedMetadata = () => {
        if (audioRef.current) {
            setDuration(audioRef.current.duration);
        }
    };

    const handleSeek = (e) => {
        const rect = e.currentTarget.getBoundingClientRect();
        const percent = (e.clientX - rect.left) / rect.width;
        const newTime = percent * duration;
        if (audioRef.current) {
            audioRef.current.currentTime = newTime;
            setCurrentTime(newTime);
        }
    };

    const seekToCaption = (startTime) => {
        if (audioRef.current) {
            audioRef.current.currentTime = startTime;
            setCurrentTime(startTime);
            if (!isPlaying) {
                audioRef.current.play();
                setIsPlaying(true);
            }
        }
    };

    const skip = (seconds) => {
        if (audioRef.current) {
            audioRef.current.currentTime = Math.max(0, Math.min(duration, audioRef.current.currentTime + seconds));
        }
    };

    const cycleSpeed = () => {
        const speeds = [1, 1.5, 2];
        const nextIndex = (speeds.indexOf(playbackSpeed) + 1) % speeds.length;
        const newSpeed = speeds[nextIndex];
        setPlaybackSpeed(newSpeed);
        if (audioRef.current) {
            audioRef.current.playbackRate = newSpeed;
        }
    };

    const progress = duration > 0 ? (currentTime / duration) * 100 : 0;

    if (!audioUrl) {
        return (
            <div className="flex items-center justify-center h-40 text-text-muted glass rounded-xl">
                <p>Unable to load audio</p>
            </div>
        );
    }

    return (
        <div className="space-y-6 animate-fade-in mb-2 mt-4 px-1">
            {/* Hidden audio element */}
            <audio
                ref={audioRef}
                src={audioUrl}
                onTimeUpdate={handleTimeUpdate}
                onLoadedMetadata={handleLoadedMetadata}
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
                onEnded={() => setIsPlaying(false)}
            />

            {/* Premium Player Card */}
            <div className="bg-gradient-to-br from-surface-raised via-surface to-surface-overlay rounded-[2rem] p-6 shadow-2xl border border-border/40 relative overflow-hidden backdrop-blur-xl">
                {/* Decorative glow */}
                <div className="absolute top-0 right-0 w-64 h-64 bg-accent/10 rounded-full blur-3xl -mr-10 -mt-20 pointer-events-none" />
                <div className="absolute bottom-0 left-0 w-48 h-48 bg-purple-500/10 rounded-full blur-2xl -ml-10 -mb-10 pointer-events-none" />

                <div className="relative z-10 space-y-8">
                    {/* Header line */}
                    <div className="flex items-start justify-between">
                        <div>
                            <div className="flex items-center gap-2 mb-1.5">
                                <span className="px-2.5 py-1 rounded-full bg-accent/10 text-accent text-[10px] font-bold uppercase tracking-widest">Audio Deep Dive</span>
                                {isPlaying && (
                                    <span className="flex items-end gap-0.5 h-3">
                                        <span className="w-1 bg-accent/60 h-1/2 animate-[bounce_1s_infinite_0ms]" />
                                        <span className="w-1 bg-accent/60 h-full animate-[bounce_1s_infinite_200ms]" />
                                        <span className="w-1 bg-accent/60 h-3/4 animate-[bounce_1s_infinite_400ms]" />
                                    </span>
                                )}
                            </div>
                            <h3 className="text-xl font-bold text-text-primary leading-tight">{title}</h3>
                            <p className="text-sm text-text-secondary mt-1 tracking-wide">{dialogue.length} segments ready</p>
                        </div>
                        <button
                            onClick={handleDownload}
                            disabled={downloading}
                            className="btn-secondary text-xs flex items-center gap-1.5 rounded-full px-4 py-2 hover:shadow-md transition-all border-border bg-surface/50 backdrop-blur-sm"
                            title="Download Audio (.wav)"
                        >
                            {downloading ? (
                                <div className="loading-spinner w-3 h-3" />
                            ) : (
                                <svg className="w-4 h-4 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                </svg>
                            )}
                            <span className="font-medium">Get Audio</span>
                        </button>
                    </div>

                    {/* Timeline Controls */}
                    <div className="space-y-4">
                        <div className="flex items-center gap-4">
                            <span className="text-xs font-mono text-text-secondary w-10 text-right">{formatTime(currentTime)}</span>

                            <div
                                className="flex-1 h-2 bg-surface-overlay/80 rounded-full cursor-pointer relative group flex items-center shadow-inner"
                                onClick={handleSeek}
                            >
                                <div
                                    className="absolute left-0 h-full bg-gradient-to-r from-accent to-purple-500 rounded-full pointer-events-none"
                                    style={{ width: `${progress}%` }}
                                />
                                {/* Scrubber dot */}
                                <div
                                    className="absolute w-4 h-4 bg-white rounded-full shadow-[0_0_10px_rgba(59,130,246,0.5)] transform -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity scale-75 group-hover:scale-100 duration-200"
                                    style={{ left: `${progress}%` }}
                                />
                            </div>

                            <span className="text-xs font-mono text-text-secondary w-10">{formatTime(duration)}</span>
                        </div>

                        {/* Central Playback Controls */}
                        <div className="flex items-center justify-center gap-6">
                            <button
                                onClick={cycleSpeed}
                                className="w-10 h-10 flex items-center justify-center text-xs font-bold text-text-secondary hover:text-accent hover:bg-accent/10 rounded-full transition-all"
                                title="Playback Speed"
                            >
                                {playbackSpeed}x
                            </button>

                            <button
                                onClick={() => skip(-10)}
                                className="w-10 h-10 flex items-center justify-center text-text-secondary hover:text-text-primary hover:bg-surface-raised rounded-full transition-all"
                                title="Rewind 10 seconds"
                            >
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12.066 11.2a1 1 0 000 1.6l5.334 4A1 1 0 0019 16V8a1 1 0 00-1.6-.8l-5.333 4zM4.066 11.2a1 1 0 000 1.6l5.334 4A1 1 0 0011 16V8a1 1 0 00-1.6-.8l-5.334 4z" />
                                </svg>
                            </button>

                            <button
                                onClick={togglePlay}
                                className="w-16 h-16 rounded-full bg-gradient-to-br from-accent to-purple-600 flex items-center justify-center hover:from-accent-light hover:to-purple-500 transition-all shadow-lg hover:shadow-accent/30 hover:scale-105 transform duration-300"
                            >
                                {isPlaying ? (
                                    <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
                                        <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
                                    </svg>
                                ) : (
                                    <svg className="w-8 h-8 text-white ml-1" fill="currentColor" viewBox="0 0 24 24">
                                        <path d="M8 5v14l11-7z" />
                                    </svg>
                                )}
                            </button>

                            <button
                                onClick={() => skip(10)}
                                className="w-10 h-10 flex items-center justify-center text-text-secondary hover:text-text-primary hover:bg-surface-raised rounded-full transition-all"
                                title="Forward 10 seconds"
                            >
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.933 12.8a1 1 0 000-1.6L6.6 7.2A1 1 0 005 8v8a1 1 0 001.6.8l5.333-4zM19.933 12.8a1 1 0 000-1.6l-5.333-4A1 1 0 0013 8v8a1 1 0 001.6.8l5.333-4z" />
                                </svg>
                            </button>

                            {/* Empty div for balance if needed, or an options button */}
                            <div className="w-10" />
                        </div>
                    </div>
                </div>
            </div>

            {/* Captions Section */}
            {dialogue.length > 0 && (
                <div className="space-y-3 mt-8">
                    <div className="flex items-center gap-2 pl-2">
                        <div className="w-6 h-6 rounded-full bg-surface-overlay flex items-center justify-center">
                            <svg className="w-3.5 h-3.5 text-text-secondary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                            </svg>
                        </div>
                        <h4 className="text-sm font-semibold text-text-primary font-mono tracking-tight uppercase">Interactive Transcript</h4>
                    </div>

                    <div
                        ref={captionContainerRef}
                        className="bg-surface/30 border border-border/30 rounded-2xl p-3 max-h-[300px] overflow-y-auto space-y-2 custom-scrollbar shadow-inner backdrop-blur-sm"
                    >
                        {dialogue.map((segment, index) => {
                            const isActive = index === activeCaptionIndex;
                            const isHost = segment.speaker === 'host';

                            return (
                                <div
                                    key={index}
                                    ref={(el) => (captionRefs.current[index] = el)}
                                    onClick={() => seekToCaption(segment.start_time)}
                                    className={`p-4 rounded-xl cursor-pointer transition-all duration-300 ease-out border ${isActive
                                        ? 'bg-gradient-to-r from-accent/15 to-transparent border-accent/40 shadow-sm translate-x-1'
                                        : 'bg-transparent border-transparent hover:bg-surface/50 hover:border-border/50'
                                        }`}
                                >
                                    <div className="flex items-center justify-between gap-3 mb-2">
                                        <div className="flex items-center gap-2">
                                            <div className={`w-2 h-2 rounded-full ${isHost ? 'bg-blue-500' : 'bg-purple-500'} ${isActive ? 'animate-pulse' : ''}`} />
                                            <span className={`text-xs font-bold uppercase tracking-wider ${isHost ? 'text-blue-400' : 'text-purple-400'}`}>
                                                {isHost ? 'Host' : 'Guest'}
                                            </span>
                                        </div>
                                        <span className={`text-[11px] font-mono px-2 py-0.5 rounded-md ${isActive ? 'bg-accent/20 text-accent-light' : 'bg-surface-overlay text-text-muted'}`}>
                                            {formatTime(segment.start_time)}
                                        </span>
                                    </div>

                                    <p className={`text-sm leading-relaxed pl-4 border-l-2 transition-colors duration-300 ${isActive ? 'text-text-primary border-accent/50' : 'text-text-secondary border-surface-overlay'}`}>
                                        {segment.text}
                                    </p>
                                </div>
                            );
                        })}
                    </div>

                    <p className="text-xs text-text-muted text-center pt-2 italic opacity-60">
                        Select any segment to jump to that moment
                    </p>
                </div>
            )}
        </div>
    );
}

function InlineFlashcardsView({ data }) {
    const [currentIndex, setCurrentIndex] = useState(0);
    const [flipped, setFlipped] = useState(false);
    const [isAnimating, setIsAnimating] = useState(false);
    const [viewMode, setViewMode] = useState('card'); // 'card' | 'list'
    const [downloading, setDownloading] = useState(false);
    const flashcards = data?.flashcards || [];

    const next = useCallback(() => {
        if (isAnimating) return;
        setFlipped(false);
        setTimeout(() => setCurrentIndex((prev) => (prev + 1) % flashcards.length), 150);
    }, [isAnimating, flashcards.length]);

    const prev = useCallback(() => {
        if (isAnimating) return;
        setFlipped(false);
        setTimeout(() => setCurrentIndex((prev) => (prev - 1 + flashcards.length) % flashcards.length), 150);
    }, [isAnimating, flashcards.length]);

    const handleFlip = useCallback(() => {
        setIsAnimating(true);
        setFlipped(f => !f);
        setTimeout(() => setIsAnimating(false), 450);
    }, []);

    const downloadPDF = () => {
        setDownloading(true);
        try {
            const doc = new jsPDF();
            const pageWidth = doc.internal.pageSize.getWidth();
            const pageHeight = doc.internal.pageSize.getHeight();
            const margin = 20;
            const contentWidth = pageWidth - (margin * 2);
            let yPos = margin;

            // Title page
            doc.setFillColor(59, 130, 246);
            doc.rect(0, 0, pageWidth, 60, 'F');

            doc.setTextColor(255, 255, 255);
            doc.setFontSize(28);
            doc.setFont('helvetica', 'bold');
            doc.text('Flashcards', margin, 38);

            doc.setFontSize(14);
            doc.setFont('helvetica', 'normal');
            doc.text(`${flashcards.length} cards for studying`, margin, 50);

            yPos = 80;

            // Instructions
            doc.setTextColor(100, 100, 100);
            doc.setFontSize(10);
            doc.text('Study tip: Cover the answers with a piece of paper while reviewing questions!', margin, yPos);
            yPos += 20;

            // Cards
            flashcards.forEach((card, index) => {
                const cardHeight = 55;
                if (yPos + cardHeight > pageHeight - margin) {
                    doc.addPage();
                    yPos = margin;
                }

                doc.setFillColor(59, 130, 246);
                doc.roundedRect(margin, yPos, 24, 10, 2, 2, 'F');
                doc.setTextColor(255, 255, 255);
                doc.setFontSize(9);
                doc.setFont('helvetica', 'bold');
                doc.text(`#${index + 1}`, margin + 7, yPos + 7);

                doc.setFillColor(239, 246, 255);
                doc.roundedRect(margin, yPos + 12, contentWidth, 18, 3, 3, 'F');
                doc.setTextColor(59, 130, 246);
                doc.setFontSize(8);
                doc.setFont('helvetica', 'bold');
                doc.text('QUESTION', margin + 5, yPos + 20);
                doc.setTextColor(30, 30, 30);
                doc.setFontSize(10);
                doc.setFont('helvetica', 'normal');
                const questionLines = doc.splitTextToSize(card.question, contentWidth - 10);
                doc.text(questionLines.slice(0, 2).join(' '), margin + 5, yPos + 27);

                doc.setFillColor(245, 245, 245);
                doc.roundedRect(margin, yPos + 32, contentWidth, 18, 3, 3, 'F');
                doc.setTextColor(80, 80, 80);
                doc.setFontSize(8);
                doc.setFont('helvetica', 'bold');
                doc.text('ANSWER', margin + 5, yPos + 40);
                doc.setTextColor(30, 30, 30);
                doc.setFontSize(10);
                doc.setFont('helvetica', 'normal');
                const answerLines = doc.splitTextToSize(card.answer, contentWidth - 10);
                doc.text(answerLines.slice(0, 2).join(' '), margin + 5, yPos + 47);

                yPos += cardHeight + 8;
            });

            doc.setTextColor(150, 150, 150);
            doc.setFontSize(8);
            doc.text(`Generated by KeplerLab • ${new Date().toLocaleDateString()}`, margin, pageHeight - 10);
            doc.save('flashcards-study-sheet.pdf');
        } catch (error) {
            console.error('Failed to generate PDF:', error);
        } finally {
            setDownloading(false);
        }
    };

    useEffect(() => {
        const handleKeyDown = (e) => {
            // Only handle keyboard shortcuts when no input/textarea is focused
            const tag = document.activeElement?.tagName?.toLowerCase();
            if (tag === 'input' || tag === 'textarea' || tag === 'select' || document.activeElement?.isContentEditable) {
                return;
            }
            if (e.key === 'ArrowRight') next();
            if (e.key === 'ArrowLeft') prev();
            if (e.key === ' ') { e.preventDefault(); handleFlip(); }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [flashcards.length, isAnimating, next, prev, handleFlip]);

    if (flashcards.length === 0) return <p className="text-text-muted text-center py-8">No flashcards available</p>;

    const card = flashcards[currentIndex];

    // ── List view ──────────────────────────────────────────────────────────
    if (viewMode === 'list') {
        return (
            <div className="flex flex-col gap-3 animate-fade-in">
                <div className="flex items-center justify-between">
                    <div>
                        <p className="text-sm font-semibold text-text-primary">All Cards</p>
                        <p className="text-xs text-text-muted mt-0.5">{flashcards.length} total</p>
                    </div>
                    <button
                        onClick={() => setViewMode('card')}
                        className="btn-primary text-xs px-3 py-1.5 flex items-center gap-1.5"
                    >
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                        </svg>
                        Back to Study
                    </button>
                </div>

                <div className="space-y-1 max-h-[500px] overflow-y-auto custom-scrollbar">
                    {flashcards.map((fc, i) => (
                        <button
                            key={i}
                            onClick={() => { setCurrentIndex(i); setFlipped(false); setViewMode('card'); }}
                            className={`w-full text-left rounded-lg border px-3 py-2.5 transition-colors ${
                                i === currentIndex
                                    ? 'border-accent bg-accent/5'
                                    : 'border-border bg-surface-raised hover:bg-surface-overlay'
                            }`}
                        >
                            <div className="flex items-start gap-2.5">
                                <span className={`flex-shrink-0 w-5 h-5 rounded text-[11px] font-semibold flex items-center justify-center mt-0.5 ${
                                    i === currentIndex ? 'bg-accent/10 text-accent' : 'bg-surface-overlay text-text-muted'
                                }`}>
                                    {i + 1}
                                </span>
                                <div className="min-w-0 flex-1">
                                    <p className="text-sm font-medium text-text-primary leading-snug line-clamp-1">{fc.question}</p>
                                    <p className="text-xs text-text-muted mt-0.5 line-clamp-1">{fc.answer}</p>
                                </div>
                            </div>
                        </button>
                    ))}
                </div>
            </div>
        );
    }

    // ── Card study view ─────────────────────────────────────────────────────
    return (
        <div className="flex flex-col gap-3 animate-fade-in">

            {/* Top bar */}
            <div className="flex items-center justify-between">
                <span className="text-xs text-text-secondary tabular-nums">
                    <span className="font-semibold text-text-primary">{currentIndex + 1}</span>
                    {' '}/{' '}{flashcards.length}
                </span>
                <div className="flex items-center gap-1">
                    <button
                        onClick={() => setViewMode('list')}
                        className="btn-secondary text-xs px-2.5 py-1.5 flex items-center gap-1.5"
                    >
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h7" />
                        </svg>
                        All
                    </button>
                    <button
                        onClick={downloadPDF}
                        disabled={downloading}
                        className="btn-secondary text-xs px-2.5 py-1.5 flex items-center gap-1.5"
                    >
                        {downloading ? <div className="loading-spinner w-3 h-3" /> : (
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                        )}
                        PDF
                    </button>
                </div>
            </div>

            {/* Segmented progress */}
            <div className="flex gap-1">
                {flashcards.map((_, i) => (
                    <button
                        key={i}
                        onClick={() => { setCurrentIndex(i); setFlipped(false); }}
                        title={`Card ${i + 1}`}
                        className={`h-1 flex-1 rounded-full transition-all duration-200 ${
                            i === currentIndex
                                ? 'bg-accent'
                                : i < currentIndex
                                ? 'bg-border-strong'
                                : 'bg-surface-overlay'
                        }`}
                    />
                ))}
            </div>

            {/* Flashcard */}
            <div
                className="cursor-pointer select-none"
                style={{ perspective: '1000px' }}
                onClick={handleFlip}
            >
                <div
                    className="relative will-change-transform"
                    style={{
                        transformStyle: 'preserve-3d',
                        transition: 'transform 0.45s cubic-bezier(0.4,0,0.2,1)',
                        transform: flipped ? 'rotateY(180deg)' : 'rotateY(0deg)',
                        minHeight: '240px',
                    }}
                >
                    {/* Front — Question */}
                    <div
                        className="rounded-xl border border-border bg-surface-raised flex flex-col min-h-[240px]"
                        style={{
                            backfaceVisibility: 'hidden',
                            boxShadow: '0 1px 3px rgba(0,0,0,0.07), 0 6px 20px rgba(0,0,0,0.04)',
                        }}
                    >
                        <div className="flex items-center justify-between px-4 pt-4 pb-0">
                            <span className="text-[10px] font-bold uppercase tracking-[0.14em] text-text-muted">Question</span>
                            <span className="text-[10px] text-text-muted tabular-nums">{currentIndex + 1} / {flashcards.length}</span>
                        </div>
                        <div className="flex-1 flex items-center justify-center px-6 py-5">
                            <p className="text-text-primary text-[15px] leading-relaxed text-center font-medium">{card.question}</p>
                        </div>
                        <div className="flex items-center justify-center gap-1.5 border-t border-border px-4 py-2.5">
                            <svg className="w-3 h-3 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                            </svg>
                            <span className="text-[11px] text-text-muted">Click to reveal answer</span>
                        </div>
                    </div>

                    {/* Back — Answer */}
                    <div
                        className="absolute inset-0 rounded-xl border border-border bg-surface-raised flex flex-col min-h-[240px]"
                        style={{
                            backfaceVisibility: 'hidden',
                            transform: 'rotateY(180deg)',
                            boxShadow: '0 1px 3px rgba(0,0,0,0.07), 0 6px 20px rgba(0,0,0,0.04)',
                        }}
                    >
                        <div className="px-4 pt-4 pb-0 flex items-center justify-between">
                            <span className="text-[10px] font-bold uppercase tracking-[0.14em] text-accent">Answer</span>
                            <span className="text-[10px] text-text-muted tabular-nums">{currentIndex + 1} / {flashcards.length}</span>
                        </div>
                        <div className="flex-1 flex items-center justify-center px-6 py-5 overflow-y-auto custom-scrollbar">
                            <p className="text-text-primary text-[15px] leading-relaxed text-center">{card.answer}</p>
                        </div>
                        <div className="flex items-center justify-center gap-1.5 border-t border-border px-4 py-2.5">
                            <svg className="w-3 h-3 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                            </svg>
                            <span className="text-[11px] text-text-muted">Click to flip back</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Navigation */}
            <div className="flex items-center gap-2">
                <button
                    onClick={prev}
                    className="btn-secondary flex-1 flex items-center justify-center gap-1.5 py-2.5 text-sm font-medium"
                >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" />
                    </svg>
                    Prev
                </button>
                <button
                    onClick={handleFlip}
                    className="flex items-center justify-center gap-1.5 px-4 py-2.5 text-sm font-medium rounded-lg border border-border bg-surface-raised text-text-secondary hover:text-text-primary hover:bg-surface-overlay transition-colors"
                >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                    </svg>
                    Flip
                </button>
                <button
                    onClick={next}
                    className="btn-primary flex-1 flex items-center justify-center gap-1.5 py-2.5 text-sm font-medium"
                >
                    Next
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5l7 7-7 7" />
                    </svg>
                </button>
            </div>

            {/* Keyboard hints */}
            <div className="flex items-center justify-center gap-4 text-[11px] text-text-muted">
                <span className="flex items-center gap-1">
                    <kbd className="px-1.5 py-0.5 rounded bg-surface-overlay border border-border font-mono text-[10px]">←</kbd>
                    <kbd className="px-1.5 py-0.5 rounded bg-surface-overlay border border-border font-mono text-[10px]">→</kbd>
                    Navigate
                </span>
                <span className="flex items-center gap-1">
                    <kbd className="px-2 py-0.5 rounded bg-surface-overlay border border-border font-mono text-[10px]">Space</kbd>
                    Flip
                </span>
            </div>
        </div>
    );
}

function InlineQuizView({ data }) {
    const [currentIndex, setCurrentIndex] = useState(0);
    const [selectedAnswer, setSelectedAnswer] = useState(null);
    const [showResult, setShowResult] = useState(false);
    const [score, setScore] = useState(0);
    const questions = data?.questions || [];

    const handleAnswer = (index) => {
        setSelectedAnswer(index);
        if (index === questions[currentIndex].correct_answer) setScore(prev => prev + 1);
    };

    const next = () => {
        if (currentIndex < questions.length - 1) {
            setSelectedAnswer(null);
            setCurrentIndex(prev => prev + 1);
        } else {
            setShowResult(true);
        }
    };

    const restart = () => {
        setCurrentIndex(0);
        setSelectedAnswer(null);
        setShowResult(false);
        setScore(0);
    };

    if (questions.length === 0) return <p className="text-text-muted text-center py-8">No quiz questions available</p>;

    const question = questions[currentIndex];
    const progress = ((currentIndex + 1) / questions.length) * 100;
    const scorePercent = Math.round((score / questions.length) * 100);

    if (showResult) {
        return (
            <div className="text-center py-10 px-6 glass rounded-2xl animate-fade-up flex flex-col items-center justify-center min-h-[300px] border border-accent/20">
                <div className="w-24 h-24 rounded-full flex items-center justify-center mb-6 bg-gradient-to-tr from-accent to-purple-500 shadow-glow animate-scale-in">
                    <span className="text-4xl">{scorePercent >= 80 ? '🏆' : scorePercent >= 50 ? '⭐' : '📚'}</span>
                </div>
                <h4 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-accent to-purple-400 mb-2">
                    {scorePercent >= 80 ? 'Outstanding!' : scorePercent >= 50 ? 'Great job!' : 'Keep practicing!'}
                </h4>
                <p className="text-text-secondary text-base mb-8">
                    You scored <span className="font-semibold text-text-primary">{score}</span> out of <span className="font-semibold text-text-primary">{questions.length}</span> ({scorePercent}%)
                </p>
                <button onClick={restart} className="btn-primary px-8 py-3 rounded-xl shadow-lg hover:-translate-y-1 transition-all">
                    Retake Quiz
                </button>
            </div>
        );
    }

    return (
        <div className="space-y-6 animate-fade-in relative">
            <div className="flex items-center justify-between px-1">
                <span className="text-xs font-semibold uppercase tracking-wider text-accent">Question {currentIndex + 1} of {questions.length}</span>
                <div className="flex items-center gap-1.5 bg-accent/10 px-2 py-1 rounded-md text-accent text-xs font-bold">
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                    </svg>
                    Score: {score}
                </div>
            </div>

            <div className="progress-bar h-1.5 bg-surface-overlay overflow-hidden rounded-full shadow-inner">
                <div className="h-full bg-gradient-to-r from-accent to-purple-500 rounded-full transition-all duration-500 ease-out" style={{ width: `${progress}%` }} />
            </div>

            <h3 className="text-lg font-semibold text-text-primary leading-snug px-1">
                {question.question}
            </h3>

            <div className="space-y-3">
                {question.options?.map((option, idx) => {
                    const isSelected = selectedAnswer === idx;
                    const isCorrect = idx === question.correct_answer;
                    const showState = selectedAnswer !== null;

                    let stateClass = 'border-border bg-surface-raised hover:border-accent/50 hover:bg-accent/5 hover:-translate-y-0.5 hover:shadow-md cursor-pointer';

                    if (showState) {
                        if (isCorrect) {
                            stateClass = 'border-[#10b981] bg-[#10b981]/10 shadow-[0_0_15px_rgba(16,185,129,0.15)]';
                        } else if (isSelected) {
                            stateClass = 'border-[#ef4444] bg-[#ef4444]/10';
                        } else {
                            stateClass = 'border-border bg-surface opacity-40 grayscale-[50%]';
                        }
                    }

                    return (
                        <button
                            key={idx}
                            onClick={() => handleAnswer(idx)}
                            disabled={selectedAnswer !== null}
                            className={`w-full p-4 text-left rounded-xl border-2 transition-all duration-300 ease-out text-sm ${stateClass} flex items-center justify-between group`}
                        >
                            <span className={`flex-1 leading-relaxed ${showState && isCorrect ? 'font-medium text-text-primary' : 'text-text-secondary group-hover:text-text-primary'}`}>
                                {option}
                            </span>
                            {showState && isCorrect && (
                                <span className="flex-shrink-0 ml-3 w-6 h-6 rounded-full bg-[#10b981] text-white flex items-center justify-center animate-scale-in">
                                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>
                                </span>
                            )}
                            {showState && isSelected && !isCorrect && (
                                <span className="flex-shrink-0 ml-3 w-6 h-6 rounded-full bg-[#ef4444] text-white flex items-center justify-center animate-scale-in">
                                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" /></svg>
                                </span>
                            )}
                        </button>
                    );
                })}
            </div>

            {selectedAnswer !== null && (
                <div className={`p-5 rounded-xl text-sm animate-fade-up flex flex-col gap-3 border backdrop-blur-sm ${selectedAnswer === question.correct_answer
                    ? 'bg-gradient-to-r from-[#10b981]/10 to-[#10b981]/5 border-[#10b981]/30 shadow-[0_4px_20px_rgba(16,185,129,0.1)]'
                    : 'bg-gradient-to-r from-[#ef4444]/10 to-[#ef4444]/5 border-[#ef4444]/30 shadow-[0_4px_20px_rgba(239,68,68,0.1)]'
                    }`}>
                    {selectedAnswer === question.correct_answer ? (
                        <div className="flex items-center gap-2 text-[#10b981] font-bold text-base">
                            <span className="animate-bounce">
                                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                            </span>
                            Excellent! That's correct.
                        </div>
                    ) : (
                        <div>
                            <div className="flex items-center gap-2 text-[#ef4444] font-bold text-base mb-2">
                                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                Not quite right.
                            </div>
                            <p className="text-sm text-text-primary bg-surface/50 p-3 rounded-lg border border-border/50">
                                The correct answer is: <strong className="text-text-primary block mt-1">{question.options[question.correct_answer]}</strong>
                            </p>
                        </div>
                    )}

                    {question.explanation && (
                        <div className="mt-1 pt-3 border-t border-border/40">
                            <p className="text-sm text-text-secondary leading-relaxed">
                                <span className="font-semibold text-text-primary">Explanation: </span> {question.explanation}
                            </p>
                        </div>
                    )}
                </div>
            )}

            {selectedAnswer !== null && (
                <div className="pt-2 animate-fade-in" style={{ animationDelay: '0.2s' }}>
                    <button onClick={next} className="btn-primary w-full py-3.5 text-base font-medium shadow-md hover:shadow-lg hover:-translate-y-0.5 transition-all">
                        {currentIndex < questions.length - 1 ? 'Next Question →' : 'See Final Results ✨'}
                    </button>
                </div>
            )}
        </div>
    );
}

// ==================== INLINE EXPLAINER VIEW ====================
function InlineExplainerView({ data }) {
    const [videoBlobUrl, setVideoBlobUrl] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const explainerId = data?.explainer_id;
    const duration = data?.duration || 0;
    const chapters = data?.chapters || [];
    const mins = Math.floor(duration / 60);
    const secs = duration % 60;

    useEffect(() => {
        if (!explainerId) {
            setLoading(false);
            setError('No explainer ID found');
            return;
        }

        let cancelled = false;
        setLoading(true);
        setError(null);

        fetchExplainerVideoBlob(explainerId)
            .then(blobUrl => {
                if (!cancelled) {
                    setVideoBlobUrl(blobUrl);
                    setLoading(false);
                }
            })
            .catch(err => {
                if (!cancelled) {
                    setError('Failed to load video');
                    setLoading(false);
                }
            });

        return () => {
            cancelled = true;
            if (videoBlobUrl) URL.revokeObjectURL(videoBlobUrl);
        };
    }, [explainerId]);

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center py-12 gap-3">
                <div className="loading-spinner w-8 h-8" />
                <p className="text-sm text-text-muted">Loading video...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center py-12 gap-3">
                <svg className="w-8 h-8 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-sm text-red-400">{error}</p>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {/* Video Player */}
            {videoBlobUrl && (
                <div className="rounded-lg overflow-hidden bg-black">
                    <video
                        controls
                        className="w-full"
                        src={videoBlobUrl}
                        style={{ maxHeight: '300px' }}
                    >
                        Your browser does not support the video element.
                    </video>
                </div>
            )}

            {/* Duration & Info */}
            <div className="flex items-center justify-between text-xs text-text-muted px-1">
                <span>Duration: {mins}m {secs}s</span>
                <span>{chapters.length} chapters</span>
            </div>

            {/* Chapters */}
            {chapters.length > 0 && (
                <div className="space-y-2">
                    <h4 className="text-xs font-medium text-text-secondary uppercase tracking-wider">Chapters</h4>
                    <div className="space-y-1 max-h-48 overflow-y-auto pr-1">
                        {chapters.map((ch, i) => (
                            <div key={i} className="flex items-center gap-3 text-xs text-text-muted py-1.5 px-2 rounded hover:bg-glass-light transition-colors">
                                <span className="text-text-secondary tabular-nums font-mono">
                                    {Math.floor(ch.start_time / 60)}:{String(Math.floor(ch.start_time % 60)).padStart(2, '0')}
                                </span>
                                <span className="text-text-primary truncate">{ch.title}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Download Button */}
            {videoBlobUrl && (
                <a
                    href={videoBlobUrl}
                    download={`explainer_${explainerId}.mp4`}
                    className="btn-primary w-full text-center"
                >
                    <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    Download Video
                </a>
            )}
        </div>
    );
}

// ==================== HISTORY MODALS ====================
function HistoryRenameModal({ isOpen, onClose, itemName, newTitle, setNewTitle, onSave }) {
    if (!isOpen) return null;

    const handleSubmit = (e) => {
        e.preventDefault();
        onSave(e);
    };

    return (
        <div className="modal-backdrop" onClick={onClose}>
            <div className="modal w-full max-w-md mx-4" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h3 className="text-base font-medium text-text-primary">Rename Content</h3>
                    <button onClick={onClose} className="btn-icon-sm">
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>
                <form onSubmit={handleSubmit} className="modal-body space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-text-secondary mb-2 whitespace-nowrap overflow-hidden text-ellipsis">
                            Name for {itemName}
                        </label>
                        <input
                            type="text"
                            value={newTitle}
                            onChange={(e) => setNewTitle(e.target.value)}
                            placeholder="Data Title"
                            className="input w-full"
                            autoFocus
                            required
                        />
                    </div>
                    <div className="modal-footer">
                        <button type="button" onClick={onClose} className="btn-secondary">Cancel</button>
                        <button type="submit" disabled={!newTitle.trim()} className="btn-primary">
                            Save
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
