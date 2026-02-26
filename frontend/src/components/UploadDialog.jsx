import { useState, useRef, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    uploadBatch,
    uploadBatchWithAutoNotebook,
    uploadUrl,
    uploadText,
    validateFiles,
    getMaxUploadSizeMB,
} from '../api/materials';

/* ── Icons ── */
const CloseIcon = () => (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
);
const UploadCloudIcon = ({ className = "w-10 h-10" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
    </svg>
);
const GlobeIcon = () => (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
    </svg>
);
const FileIcon = () => (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
    </svg>
);
const TextIcon = () => (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
);
const SpinnerIcon = () => (
    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
);
const LinkIcon = () => (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
    </svg>
);
const CheckCircleIcon = () => (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
);

const TABS = [
    { id: 'files', label: 'Upload Files', icon: FileIcon },
    { id: 'web', label: 'Website / URL', icon: GlobeIcon },
    { id: 'text', label: 'Paste Text', icon: TextIcon },
];

const FORMAT_GROUPS = [
    { icon: '📄', label: 'Documents', formats: 'PDF, DOCX, TXT, PPTX, XLSX' },
    { icon: '🖼️', label: 'Images', formats: 'JPG, PNG, GIF (OCR)' },
    { icon: '🎵', label: 'Media', formats: 'MP3, MP4, WAV, AVI, MOV' },
    { icon: '🌐', label: 'Web', formats: 'Webpages, YouTube' },
];

const UploadDialog = ({ isOpen, onClose, currentNotebook, draftMode, onMaterialAdded, setCurrentNotebook, setDraftMode }) => {
    const [activeTab, setActiveTab] = useState('files');
    const [dragActive, setDragActive] = useState(false);
    const [loading, setLoading] = useState(false);
    const [url, setUrl] = useState('');
    const [textContent, setTextContent] = useState('');
    const [textTitle, setTextTitle] = useState('');
    const [toast, setToast] = useState(null); // {type: 'error'|'success', message}
    const navigate = useNavigate();

    const fileInputRef = useRef(null);

    // Reset state when dialog opens
    useEffect(() => {
        if (isOpen) {
            setActiveTab('files');
            setUrl('');
            setTextContent('');
            setTextTitle('');
            setToast(null);
            setDragActive(false);
        }
    }, [isOpen]);

    const showToast = (type, message) => {
        setToast({ type, message });
        setTimeout(() => setToast(null), 4000);
    };

    const handleDrag = useCallback((e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true);
        } else if (e.type === 'dragleave') {
            setDragActive(false);
        }
    }, []);

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleFileUpload(Array.from(e.dataTransfer.files));
        }
    };

    const handleFileUpload = async (files) => {
        if (!files || files.length === 0) return;

        // ── Client-side validation ──
        const validationErr = validateFiles(files);
        if (validationErr) {
            showToast('error', validationErr.details || validationErr.message);
            return;
        }

        setLoading(true);
        try {
            let result;
            if (draftMode && currentNotebook?.isDraft) {
                result = await uploadBatchWithAutoNotebook(files);
                if (result.notebook) {
                    setCurrentNotebook(result.notebook);
                    setDraftMode(false);
                    navigate(`/notebook/${result.notebook.id}`, { replace: true });
                }
            } else {
                const nbId = currentNotebook?.isDraft ? null : currentNotebook?.id;
                result = await uploadBatch(files, nbId);
            }

            // add all created materials to the app state
            if (result.materials) {
                result.materials.forEach(m => {
                    if (m.status !== 'error') {
                        onMaterialAdded({
                            id: m.material_id,
                            filename: m.filename,
                            title: m.title || m.filename,
                            chunkCount: m.chunk_count,
                            status: m.status,
                            sourceType: 'file'
                        });
                    }
                });
            }
            onClose();
        } catch (error) {
            console.error('Batch upload failed:', error);
            const msg = error.details || error.message || 'Upload failed';
            showToast('error', msg);
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    const handleUrlUpload = async () => {
        if (!url.trim()) {
            showToast('error', 'Please enter a URL');
            return;
        }
        // Basic URL validation
        try {
            const parsed = new URL(url.trim());
            if (!['http:', 'https:'].includes(parsed.protocol)) {
                showToast('error', 'Only HTTP and HTTPS URLs are supported');
                return;
            }
        } catch {
            showToast('error', 'Please enter a valid URL (e.g. https://example.com)');
            return;
        }
        setLoading(true);
        try {
            const autoCreate = !currentNotebook || currentNotebook.isDraft || draftMode;
            const notebookId = autoCreate ? null : currentNotebook.id;
            const result = await uploadUrl(
                url.trim(),
                notebookId,
                autoCreate,
                'auto'
            );
            if (result.notebook) {
                setCurrentNotebook(result.notebook);
                setDraftMode(false);
                navigate(`/notebook/${result.notebook.id}`, { replace: true });
            }
            onMaterialAdded({
                id: result.material_id,
                filename: result.filename,
                title: result.title || result.filename,
                chunkCount: result.chunk_count,
                status: result.status,
                sourceType: result.source_type ?? 'url',
            });
            setUrl('');
            onClose();
        } catch (error) {
            console.error('URL upload failed:', error);
            const msg = error.details || error.message || 'URL upload failed';
            showToast('error', msg);
        } finally {
            setLoading(false);
        }
    };

    const handleTextUpload = async () => {
        if (!textContent.trim() || !textTitle.trim()) {
            showToast('error', 'Please enter both title and content');
            return;
        }
        setLoading(true);
        try {
            const autoCreate = !currentNotebook || currentNotebook.isDraft || draftMode;
            const notebookId = autoCreate ? null : currentNotebook.id;
            const result = await uploadText(
                textContent.trim(),
                textTitle.trim(),
                notebookId,
                autoCreate
            );
            if (result.notebook) {
                setCurrentNotebook(result.notebook);
                setDraftMode(false);
                navigate(`/notebook/${result.notebook.id}`, { replace: true });
            }
            onMaterialAdded({
                id: result.material_id,
                filename: result.filename,
                title: result.title || result.filename,
                chunkCount: result.chunk_count,
                status: result.status,
                sourceType: 'text',
            });
            setTextContent('');
            setTextTitle('');
            onClose();
        } catch (error) {
            console.error('Text upload failed:', error);
            const msg = error.details || error.message || 'Text upload failed';
            showToast('error', msg);
        } finally {
            setLoading(false);
        }
    };

    return (
        /* ── BACKDROP ── */
        <div
            className="fixed inset-0 z-50 flex items-center justify-center animate-fade-in"
            style={{ background: 'var(--backdrop, rgba(0,0,0,0.7))', backdropFilter: 'blur(6px)' }}
            onClick={(e) => { if (e.target === e.currentTarget && !loading) onClose(); }}
        >
            {/* ── MODAL ── */}
            <div
                className="relative w-full max-w-[680px] mx-4 flex flex-col rounded-2xl overflow-hidden animate-scale-in"
                style={{
                    background: 'var(--surface-raised)',
                    border: '1px solid var(--border)',
                    boxShadow: 'var(--shadow-glass)',
                    maxHeight: '88vh',
                }}
            >
                {/* ── HEADER ── */}
                <div className="flex items-center justify-between px-6 py-5" style={{ borderBottom: '1px solid var(--border)' }}>
                    <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: 'var(--accent-subtle)' }}>
                            <UploadCloudIcon className="w-5 h-5 text-accent-light" />
                        </div>
                        <div>
                            <h2 className="text-base font-semibold text-text-primary leading-tight">Add Sources</h2>
                            <p className="text-xs text-text-muted mt-0.5">Upload files, links, or paste text to your notebook</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        disabled={loading}
                        className="btn-icon w-8 h-8 rounded-lg"
                        title="Close"
                    >
                        <CloseIcon />
                    </button>
                </div>

                {/* ── TABS ── */}
                <div className="px-6 pt-4 pb-0">
                    <div className="flex gap-1 p-1 rounded-xl" style={{ background: 'var(--surface-overlay)' }}>
                        {TABS.map((tab) => {
                            const TabIcon = tab.icon;
                            return (
                                <button
                                    key={tab.id}
                                    onClick={() => setActiveTab(tab.id)}
                                    className={`
                                    flex items-center justify-center gap-2 flex-1 px-3 py-2 rounded-lg text-sm font-medium
                                    transition-all duration-150
                                    ${activeTab === tab.id
                                            ? 'text-text-primary'
                                            : 'text-text-muted hover:text-text-secondary'}
                                `}
                                    style={activeTab === tab.id ? {
                                        background: 'var(--surface-raised)',
                                        boxShadow: '0 1px 4px rgba(0,0,0,0.15)',
                                    } : {}}
                                >
                                    <TabIcon />
                                    {tab.label}
                                </button>
                            );
                        })}
                    </div>
                </div>

                {/* ── CONTENT ── */}
                <div className="flex-1 overflow-y-auto px-6 py-5">
                    {/* FILES TAB */}
                    {activeTab === 'files' && (
                        <div className="space-y-5">
                            {/* Drop zone */}
                            <div
                                className={`
                                    relative flex flex-col items-center justify-center rounded-2xl
                                    border-2 border-dashed transition-all duration-200 cursor-pointer
                                    ${dragActive
                                        ? 'border-accent bg-accent/5'
                                        : 'border-border hover:border-accent/30 hover:bg-surface-overlay'}
                                `}
                                style={{ padding: '3rem 2rem' }}
                                onDragEnter={handleDrag}
                                onDragLeave={handleDrag}
                                onDragOver={handleDrag}
                                onDrop={handleDrop}
                                onClick={() => !loading && fileInputRef.current?.click()}
                            >
                                <div
                                    className={`
                                        w-14 h-14 rounded-2xl flex items-center justify-center mb-4
                                        transition-all duration-200
                                        ${dragActive ? 'scale-110' : ''}
                                    `}
                                    style={{
                                        background: dragActive ? 'var(--accent-subtle)' : 'var(--surface-overlay)',
                                        border: `1px solid ${dragActive ? 'var(--accent-border)' : 'var(--border-light)'}`,
                                    }}
                                >
                                    <UploadCloudIcon className={`w-7 h-7 ${dragActive ? 'text-accent-light' : 'text-text-muted'}`} />
                                </div>

                                <p className="text-sm font-medium text-text-primary mb-1">
                                    {dragActive ? 'Drop files here' : 'Drag & drop files here'}
                                </p>
                                <p className="text-xs text-text-muted mb-4">
                                    or click to browse • max {getMaxUploadSizeMB()} MB per file
                                </p>

                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    multiple
                                    className="hidden"
                                    accept=".pdf,.txt,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.csv,.jpg,.jpeg,.png,.gif,.bmp,.tiff,.mp3,.wav,.m4a,.mp4,.avi,.mov,.mkv"
                                    onChange={(e) => e.target.files && handleFileUpload(Array.from(e.target.files))}
                                />
                                <button
                                    onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click(); }}
                                    disabled={loading}
                                    className="btn-primary text-sm px-5 py-2"
                                >
                                    {loading ? <><SpinnerIcon /> Uploading…</> : 'Choose Files'}
                                </button>
                            </div>

                            {/* Format chips */}
                            <div className="grid grid-cols-2 gap-2">
                                {FORMAT_GROUPS.map(({ icon, label, formats }) => (
                                    <div
                                        key={label}
                                        className="flex items-start gap-2.5 px-3 py-2.5 rounded-xl"
                                        style={{ background: 'var(--surface-overlay)', border: '1px solid var(--border-light)' }}
                                    >
                                        <span className="text-base leading-none mt-0.5">{icon}</span>
                                        <div className="min-w-0">
                                            <p className="text-xs font-medium text-text-secondary">{label}</p>
                                            <p className="text-2xs text-text-muted truncate">{formats}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* WEB / URL TAB */}
                    {activeTab === 'web' && (
                        <div className="space-y-5">
                            {/* URL input */}
                            <div>
                                <label className="block text-xs font-medium text-text-secondary mb-2">
                                    Website or YouTube URL
                                </label>
                                <div className="flex gap-2.5">
                                    <div className="relative flex-1">
                                        <div className="absolute left-3.5 top-1/2 -translate-y-1/2 text-text-muted">
                                            <LinkIcon />
                                        </div>
                                        <input
                                            type="url"
                                            placeholder="https://example.com or YouTube link…"
                                            value={url}
                                            onChange={(e) => setUrl(e.target.value)}
                                            onKeyDown={(e) => e.key === 'Enter' && handleUrlUpload()}
                                            className="input pl-10"
                                        />
                                    </div>
                                    <button
                                        onClick={handleUrlUpload}
                                        disabled={loading || !url.trim()}
                                        className="btn-primary whitespace-nowrap px-5"
                                    >
                                        {loading ? <><SpinnerIcon /> Processing…</> : 'Add Source'}
                                    </button>
                                </div>
                            </div>

                            {/* Info cards */}
                            <div className="grid grid-cols-2 gap-2.5">
                                {[
                                    { icon: '🌐', title: 'Any Website', desc: 'Articles, blogs, docs' },
                                    { icon: '▶️', title: 'YouTube', desc: 'Auto transcript extraction' },
                                    { icon: '📰', title: 'News & Wikis', desc: 'Rich content parsing' },
                                    { icon: '🔍', title: 'Auto Detect', desc: 'Smart source recognition' },
                                ].map(({ icon, title, desc }) => (
                                    <div
                                        key={title}
                                        className="flex items-center gap-3 px-3.5 py-3 rounded-xl"
                                        style={{ background: 'var(--surface-overlay)', border: '1px solid var(--border-light)' }}
                                    >
                                        <span className="text-lg">{icon}</span>
                                        <div>
                                            <p className="text-xs font-medium text-text-secondary">{title}</p>
                                            <p className="text-2xs text-text-muted">{desc}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* TEXT TAB */}
                    {activeTab === 'text' && (
                        <div className="space-y-4">
                            <div>
                                <label className="block text-xs font-medium text-text-secondary mb-2">Title</label>
                                <input
                                    type="text"
                                    placeholder="Give your content a title…"
                                    value={textTitle}
                                    onChange={(e) => setTextTitle(e.target.value)}
                                    className="input"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-text-secondary mb-2">Content</label>
                                <textarea
                                    placeholder="Paste or type your text here…"
                                    value={textContent}
                                    onChange={(e) => setTextContent(e.target.value)}
                                    rows={7}
                                    className="input resize-none"
                                    style={{ lineHeight: '1.6' }}
                                />
                            </div>
                            <button
                                onClick={handleTextUpload}
                                disabled={loading || !textContent.trim() || !textTitle.trim()}
                                className="btn-primary w-full justify-center py-2.5"
                            >
                                {loading ? <><SpinnerIcon /> Adding…</> : <><CheckCircleIcon /> Add Text Source</>}
                            </button>
                        </div>
                    )}
                </div>

                {/* ── TOAST ── */}
                {toast && (
                    <div
                        className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium animate-fade-up"
                        style={{
                            background: toast.type === 'error' ? 'rgba(239,68,68,0.15)' : 'rgba(34,197,94,0.15)',
                            border: `1px solid ${toast.type === 'error' ? 'rgba(239,68,68,0.3)' : 'rgba(34,197,94,0.3)'}`,
                            color: toast.type === 'error' ? '#fca5a5' : '#86efac',
                            backdropFilter: 'blur(12px)',
                        }}
                    >
                        {toast.type === 'error' ? (
                            <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        ) : (
                            <CheckCircleIcon />
                        )}
                        <span>{toast.message}</span>
                    </div>
                )}

                {/* ── LOADING OVERLAY ── */}
                {loading && (
                    <div className="absolute inset-0 rounded-2xl flex items-center justify-center z-10" style={{ background: 'rgba(17,17,24,0.6)', backdropFilter: 'blur(2px)' }}>
                        <div className="flex flex-col items-center gap-3">
                            <div className="loading-spinner w-8 h-8" />
                            <p className="text-sm text-text-secondary">Processing your source…</p>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default UploadDialog;