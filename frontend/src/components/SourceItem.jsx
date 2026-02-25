import { useState, useRef, useEffect, memo } from 'react';

export default memo(function SourceItem({ source, checked, active, anySelected, onClick, onToggle, onSeeText, onRename, onRemove }) {
    const [menuOpen, setMenuOpen] = useState(false);
    const menuRef = useRef(null);

    const sourceType = source.source_type || (source.sourceType) || inferSourceType(source.filename);

    function inferSourceType(filename) {
        if (!filename) return 'file';
        const lower = filename.toLowerCase();
        if (lower.startsWith('http://') || lower.startsWith('https://')) {
            if (lower.includes('youtube.com') || lower.includes('youtu.be')) return 'youtube';
            return 'url';
        }
        return 'file';
    }

    function getSourceIcon(type, filename) {
        const ext = filename?.split('.').pop()?.toLowerCase();

        if (type === 'youtube') {
            return (
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
                </svg>
            );
        }

        if (type === 'url') {
            return (
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
                </svg>
            );
        }

        if (ext === 'pdf') {
            return (
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M20 2H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-8.5 7.5c0 .83-.67 1.5-1.5 1.5H9v2H7.5V7H10c.83 0 1.5.67 1.5 1.5v1zm5 2c0 .83-.67 1.5-1.5 1.5h-2.5V7H15c.83 0 1.5.67 1.5 1.5v3zm4-3H19v1h1.5V11H19v2h-1.5V7h3v1.5zM9 9.5h1v-1H9v1zM4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm10 5.5h1v-3h-1v3z" />
                </svg>
            );
        }

        if (ext === 'docx' || ext === 'doc') {
            return (
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zM6 20V4h7v5h5v11H6z" />
                    <path d="M14.5 13.5h-5v1h5v-1zm0-2h-5v1h5v-1zm-5 4h5v1h-5v-1z" />
                </svg>
            );
        }

        if (ext === 'pptx' || ext === 'ppt') {
            return (
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V5h14v14z" />
                    <path d="M10 8.5h3c.83 0 1.5.67 1.5 1.5v1c0 .83-.67 1.5-1.5 1.5h-1.5v2H10v-6zm1.5 2.5h1v-1h-1v1z" />
                </svg>
            );
        }

        if (ext === 'xlsx' || ext === 'xls' || ext === 'csv') {
            return (
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V5h14v14z" />
                    <path d="M7 12h2v2H7zm0-3h2v2H7zm0 6h2v2H7zm4-3h2v2h-2zm0-3h2v2h-2zm0 6h2v2h-2zm4-3h2v2h-2zm0-3h2v2h-2zm0 6h2v2h-2z" />
                </svg>
            );
        }

        if (ext === 'mp3' || ext === 'wav' || ext === 'ogg' || ext === 'm4a') {
            return (
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z" />
                </svg>
            );
        }

        if (ext === 'mp4' || ext === 'avi' || ext === 'mov' || ext === 'mkv' || ext === 'webm') {
            return (
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4h-4z" />
                </svg>
            );
        }

        if (ext === 'zip' || ext === 'rar' || ext === '7z' || ext === 'tar' || ext === 'gz') {
            return (
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M20 6h-8l-2-2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2z" />
                    <path d="M12 9h2v2h-2zm0 3h2v2h-2zm0 3h2v2h-2z" />
                </svg>
            );
        }

        if (ext === 'png' || ext === 'jpg' || ext === 'jpeg' || ext === 'gif' || ext === 'svg' || ext === 'webp') {
            return (
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z" />
                </svg>
            );
        }

        if (type === 'text' || ext === 'txt') {
            return (
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z" />
                </svg>
            );
        }

        // Default file icon
        return (
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm4 18H6V4h7v5h5v11z" />
            </svg>
        );
    }

    useEffect(() => {
        if (!menuOpen) return;
        const handleClickOutside = (e) => {
            if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false);
        };
        document.addEventListener('click', handleClickOutside);
        return () => document.removeEventListener('click', handleClickOutside);
    }, [menuOpen]);

    const displayName = source.title || source.filename;

    const handleRename = (e) => {
        e.stopPropagation();
        setMenuOpen(false);
        const newName = window.prompt('Rename source', displayName);
        if (newName != null && newName.trim()) {
            onRename?.(source, newName.trim());
        }
    };

    const handleRemove = (e) => {
        e.stopPropagation();
        setMenuOpen(false);
        if (window.confirm(`Remove "${displayName}" from sources?`)) {
            onRemove?.(source);
        }
    };

    const handleSeeText = (e) => {
        e.stopPropagation();
        setMenuOpen(false);
        onSeeText?.(source);
    };

    function getSourceTypeLabel(type, filename) {
        const ext = filename?.split('.').pop()?.toLowerCase();

        if (type === 'youtube') return 'YouTube';
        if (type === 'url') return 'Website';
        if (ext === 'pdf') return 'PDF';
        if (ext === 'docx' || ext === 'doc') return 'Word';
        if (ext === 'pptx' || ext === 'ppt') return 'PowerPoint';
        if (ext === 'xlsx' || ext === 'xls' || ext === 'csv') return 'Excel';
        if (ext === 'mp3' || ext === 'wav' || ext === 'ogg' || ext === 'm4a') return 'Audio';
        if (ext === 'mp4' || ext === 'avi' || ext === 'mov' || ext === 'mkv' || ext === 'webm') return 'Video';
        if (ext === 'zip' || ext === 'rar' || ext === '7z' || ext === 'tar' || ext === 'gz') return 'Archive';
        if (ext === 'png' || ext === 'jpg' || ext === 'jpeg' || ext === 'gif' || ext === 'svg' || ext === 'webp') return 'Image';
        if (type === 'text' || ext === 'txt') return 'Text';
        return 'Document';
    }

    function getSourceTypeColor(type, filename) {
        const ext = filename?.split('.').pop()?.toLowerCase();

        if (type === 'youtube') return 'text-red-500 bg-gradient-to-br from-red-500/20 to-red-600/5 border-red-500/20';
        if (type === 'url') return 'text-blue-500 bg-gradient-to-br from-blue-500/20 to-blue-600/5 border-blue-500/20';
        if (ext === 'pdf') return 'text-red-500 bg-gradient-to-br from-red-500/20 to-red-600/5 border-red-500/20';
        if (ext === 'docx' || ext === 'doc') return 'text-blue-500 bg-gradient-to-br from-blue-500/20 to-blue-600/5 border-blue-500/20';
        if (ext === 'pptx' || ext === 'ppt') return 'text-orange-500 bg-gradient-to-br from-orange-500/20 to-orange-600/5 border-orange-500/20';
        if (ext === 'xlsx' || ext === 'xls' || ext === 'csv') return 'text-green-500 bg-gradient-to-br from-green-500/20 to-green-600/5 border-green-500/20';
        if (ext === 'mp3' || ext === 'wav' || ext === 'ogg' || ext === 'm4a') return 'text-purple-500 bg-gradient-to-br from-purple-500/20 to-purple-600/5 border-purple-500/20';
        if (ext === 'mp4' || ext === 'avi' || ext === 'mov' || ext === 'mkv' || ext === 'webm') return 'text-pink-500 bg-gradient-to-br from-pink-500/20 to-pink-600/5 border-pink-500/20';
        if (ext === 'zip' || ext === 'rar' || ext === '7z' || ext === 'tar' || ext === 'gz') return 'text-amber-500 bg-gradient-to-br from-amber-500/20 to-amber-600/5 border-amber-500/20';
        if (ext === 'png' || ext === 'jpg' || ext === 'jpeg' || ext === 'gif' || ext === 'svg' || ext === 'webp') return 'text-teal-500 bg-gradient-to-br from-teal-500/20 to-teal-600/5 border-teal-500/20';
        if (type === 'text' || ext === 'txt') return 'text-gray-400 bg-gradient-to-br from-gray-500/20 to-gray-600/5 border-gray-500/20';
        return 'text-slate-400 bg-gradient-to-br from-slate-500/20 to-slate-600/5 border-slate-500/20';
    }

    const getStatusLabel = (status) => {
        if (!status) return null;
        switch (status) {
            case 'pending': return 'Waiting...';
            case 'processing': return 'Parsing...';
            case 'ocr_running': return 'Running OCR...';
            case 'transcribing': return 'Transcribing...';
            case 'embedding': return 'Embedding...';
            case 'failed': return 'Failed';
            default: return null;
        }
    };

    const isProcessing = source.status && !['completed', 'failed'].includes(source.status);
    const isFailed = source.status === 'failed';
    const statusLabel = getStatusLabel(source.status);

    const getStatusStyle = (status) => {
        if (!status) return null;
        switch (status) {
            case 'pending': return { bg: 'bg-gray-500/20', text: 'text-gray-400', border: 'border-gray-500/30' };
            case 'processing': return { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/30' };
            case 'ocr_running': return { bg: 'bg-indigo-500/20', text: 'text-indigo-400', border: 'border-indigo-500/30' };
            case 'transcribing': return { bg: 'bg-purple-500/20', text: 'text-purple-400', border: 'border-purple-500/30' };
            case 'embedding': return { bg: 'bg-teal-500/20', text: 'text-teal-400', border: 'border-teal-500/30' };
            case 'failed': return { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/30' };
            default: return { bg: 'bg-gray-500/20', text: 'text-gray-400', border: 'border-gray-500/30' };
        }
    };

    const statusStyle = getStatusStyle(source.status);

    return (
        <div
            className={`source-item group flex items-start gap-3 px-3 py-2.5 rounded-lg transition-colors border border-transparent 
            ${checked ? 'bg-[#2A2D35]' : 'hover:bg-[#20222A]'} 
            ${isProcessing ? 'bg-[#2A2D35]/50' : ''}`}
        >
            {/* Icon with type color (Left) */}
            <div className={`flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-lg border backdrop-blur-sm shadow-inner ${getSourceTypeColor(sourceType, source.filename)} ${isProcessing ? 'animate-pulse' : ''} ${isFailed ? 'grayscale opacity-50' : ''}`}>
                <div className="scale-90 flex items-center justify-center drop-shadow-md">
                    {getSourceIcon(sourceType, source.filename)}
                </div>
            </div>

            {/* Name + type label (Middle) */}
            <div className={`flex-1 min-w-0 flex flex-col justify-center pt-0.5 max-w-full`}>
                <p className={`text-[13px] truncate leading-tight ${active ? 'text-white font-medium' : isFailed ? 'text-red-400 line-through' : 'text-gray-200 font-medium'}`}>
                    {displayName}
                </p>

                {(isProcessing || isFailed) && (
                    <div className="mt-2 mb-1 flex items-center gap-2">
                        <div className={`relative inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border ${statusStyle.bg} ${statusStyle.border} ${isProcessing ? 'animate-pulse' : ''}`}>
                            {isProcessing && (
                                <div className={`w-1.5 h-1.5 rounded-full bg-current ${statusStyle.text} animate-ping absolute left-2 opacity-75`}></div>
                            )}
                            <div className={`w-1.5 h-1.5 rounded-full fill-current bg-current ${statusStyle.text} ${isProcessing ? 'ml-3' : ''}`}></div>
                            <span className={`text-[10px] font-semibold tracking-wide uppercase ${statusStyle.text}`}>
                                {statusLabel}
                            </span>
                        </div>
                        {isProcessing && (
                            <div className="flex-1 max-w-[100px] h-1 bg-gray-700/50 rounded-full overflow-hidden">
                                <div className={`h-full bg-current rounded-full ${statusStyle.text} animate-[progress_2s_ease-in-out_infinite]`}></div>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Context menu (3 dots) - Appears on hover, AHEAD of checkbox */}
            <div className="relative flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity" ref={menuRef}>
                <button
                    onClick={(e) => {
                        e.stopPropagation();
                        setMenuOpen((o) => !o);
                    }}
                    title="More actions"
                    className="p-1.5 rounded-md text-gray-400 hover:text-white hover:bg-[#3A3F4B] transition-colors"
                >
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                        <circle cx="12" cy="6" r="1.5" />
                        <circle cx="12" cy="12" r="1.5" />
                        <circle cx="12" cy="18" r="1.5" />
                    </svg>
                </button>
                {menuOpen && (
                    <div
                        className="absolute right-0 top-full mt-1 z-20 min-w-[160px] py-1 rounded-xl bg-[#20222A] border border-[#3A3F4B] shadow-xl"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <button
                            onClick={handleSeeText}
                            className="w-full px-3 py-2 text-left text-sm text-gray-300 hover:bg-[#2A2D35] hover:text-white flex items-center gap-2"
                        >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                            </svg>
                            View text
                        </button>
                        <button
                            onClick={handleRename}
                            className="w-full px-3 py-2 text-left text-sm text-gray-300 hover:bg-[#2A2D35] hover:text-white flex items-center gap-2"
                        >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                            </svg>
                            Rename
                        </button>
                        <button
                            onClick={handleRemove}
                            className="w-full px-3 py-2 text-left text-sm text-red-400 hover:bg-red-500/10 flex items-center gap-2"
                        >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                            Remove source
                        </button>
                    </div>
                )}
            </div>

            {/* Checkbox / Loading Spinner (Far Right) */}
            {isProcessing ? (
                <div className="flex-shrink-0 w-4 h-4 flex items-center justify-center mt-0.5">
                    <svg className={`w-4 h-4 animate-spin ${statusStyle.text}`} fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                </div>
            ) : (
                <button
                    onClick={(e) => { e.stopPropagation(); onToggle(source); }}
                    className={`flex-shrink-0 w-4 h-4 mt-0.5 rounded-[4px] border flex items-center justify-center transition-colors ${checked
                        ? 'bg-transparent border-white text-white'
                        : 'border-[#4A4E58] bg-transparent hover:border-gray-400'
                        }`}
                    title={checked ? 'Deselect' : 'Select'}
                    disabled={isFailed}
                >
                    {checked && (
                        <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                    )}
                </button>
            )}
        </div>
    );
});
