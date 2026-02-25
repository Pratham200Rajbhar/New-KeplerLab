import { useState } from 'react';
import Modal from './Modal';

// File extensions that should be opened in the inline viewer instead of a new tab
const VIEWABLE_EXTS = new Set(['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt', '.odt', '.ods', '.odp', '.txt', '.csv', '.md', '.rtf']);

function getFileExt(url) {
    try {
        const path = new URL(url).pathname.toLowerCase();
        const dot = path.lastIndexOf('.');
        return dot !== -1 ? path.slice(dot) : '';
    } catch { return ''; }
}

function isFileUrl(url) {
    return VIEWABLE_EXTS.has(getFileExt(url));
}

function viewerHref(url) {
    return `/view?url=${encodeURIComponent(url)}`;
}

export default function WebSearchDialog({
    isOpen,
    onClose,
    results = [],
    onAddSelected,
    isSearching = false,
    error = null,
    query = ''
}) {
    const [selectedResults, setSelectedResults] = useState(new Set()); // Store full objects or IDs
    const [previewResult, setPreviewResult] = useState(null);

    const toggleSelection = (result) => {
        const next = new Set(selectedResults);
        const exists = Array.from(next).find(r => r.link === result.link);
        if (exists) {
            next.delete(exists);
        } else {
            next.add(result);
        }
        setSelectedResults(next);
    };

    const handleSelectAll = () => {
        if (selectedResults.size === results.length) {
            setSelectedResults(new Set());
        } else {
            setSelectedResults(new Set(results));
        }
    };

    const handleAdd = () => {
        onAddSelected(Array.from(selectedResults));
        onClose();
        setSelectedResults(new Set());
        setPreviewResult(null);
    };

    const getDomain = (url) => {
        try {
            return new URL(url).hostname.replace(/^www\./, '');
        } catch {
            return '';
        }
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={() => {
                onClose();
                setPreviewResult(null);
            }}
            title="Discover Web Resources"
            maxWidth="max-w-[1000px]" // Widen for two columns
            icon={
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <circle cx="12" cy="12" r="10" strokeWidth="1.5" /><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" strokeWidth="1.5" />
                </svg>
            }
            footer={
                <div className="flex justify-between items-center w-full">
                    <span className="text-sm text-gray-400 font-medium">
                        {selectedResults.size} resources selected
                    </span>
                    <div className="flex gap-3">
                        <button
                            className="px-4 py-2 text-sm font-medium text-gray-300 hover:text-white transition-colors"
                            onClick={() => {
                                onClose();
                                setPreviewResult(null);
                            }}
                        >
                            Cancel
                        </button>
                        <button
                            className="px-6 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-500 text-white rounded-xl shadow-lg shadow-blue-900/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                            onClick={handleAdd}
                            disabled={selectedResults.size === 0}
                        >
                            Add to Notebook
                        </button>
                    </div>
                </div>
            }
        >
            <div className="flex gap-6 h-[60vh] min-h-[450px]">
                {/* Left Side: Results List */}
                <div className="w-[55%] flex flex-col h-full border-r border-[#3A3F4B]/50 pr-6">
                    <div className="flex justify-between items-center pb-4 border-b border-[#3A3F4B]/50 shrink-0">
                        <p className="text-sm text-gray-400">
                            Results for <span className="text-blue-400 font-medium font-mono">"{query}"</span>
                        </p>
                        {results.length > 0 && (
                            <button
                                className="text-[13px] text-blue-400 hover:text-blue-300 font-medium transition-colors"
                                onClick={handleSelectAll}
                            >
                                {selectedResults.size === results.length ? 'Deselect All' : 'Select All'}
                            </button>
                        )}
                    </div>

                    <div className="flex-1 overflow-y-auto pt-4 pr-1 custom-scrollbar">
                        {isSearching ? (
                            <div className="flex flex-col items-center justify-center h-full space-y-4">
                                <div className="w-8 h-8 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
                                <p className="text-sm text-gray-400 animate-pulse font-medium">Scanning the vast expanse of the web...</p>
                            </div>
                        ) : error ? (
                            <div className="flex flex-col items-center justify-center h-full space-y-4 text-center px-4">
                                <div className="p-3 bg-red-500/10 rounded-full">
                                    <svg className="w-8 h-8 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                    </svg>
                                </div>
                                <div className="space-y-1">
                                    <p className="text-[15px] font-semibold text-red-400">Search Interrupted</p>
                                    <p className="text-sm text-gray-400 leading-relaxed mx-auto">
                                        {error}
                                    </p>
                                </div>
                            </div>
                        ) : results.length === 0 ? (
                            <div className="flex flex-col items-center justify-center h-full space-y-2 text-center">
                                <svg className="w-12 h-12 text-gray-600 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                </svg>
                                <p className="text-[15px] font-medium text-gray-400">No matching resources found</p>
                                <p className="text-sm text-gray-500">Try broadening your search or checking for typos.</p>
                            </div>
                        ) : (
                            <div className="space-y-2.5 pb-2">
                                {results.map((result, idx) => {
                                    const domain = getDomain(result.link);
                                    const isSelected = Array.from(selectedResults).some(r => r.link === result.link);
                                    const isPreviewed = previewResult?.link === result.link;

                                    return (
                                        <div
                                            key={idx}
                                            onMouseEnter={() => setPreviewResult(result)}
                                            onClick={() => {
                                                toggleSelection(result);
                                                setPreviewResult(result);
                                            }}
                                            className={`p-3 rounded-xl border transition-all cursor-pointer group 
                                                ${isSelected ? 'bg-blue-500/10 border-blue-500/40 shadow-[0_0_15px_rgba(59,130,246,0.1)]' : 'bg-[#2A2D35]/40 border-[#3A3F4B]/50 hover:bg-[#2C3039] hover:border-[#3A3F4B]'}
                                                ${isPreviewed && !isSelected ? 'ring-1 ring-blue-500/20' : ''}
                                            `}
                                        >
                                            <div className="flex items-center gap-3.5">
                                                <div className={`flex-shrink-0 w-5 h-5 rounded-md border flex items-center justify-center transition-all ${isSelected
                                                    ? 'bg-blue-600 border-blue-600 text-white shadow-lg shadow-blue-900/40'
                                                    : 'border-[#4A4E58] bg-[#1C1E26] group-hover:border-gray-400'
                                                    }`}>
                                                    {isSelected && (
                                                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3.5}>
                                                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                                                        </svg>
                                                    )}
                                                </div>

                                                {domain && (
                                                    <img
                                                        src={`https://www.google.com/s2/favicons?sz=64&domain=${domain}`}
                                                        alt=""
                                                        className="flex-shrink-0 w-6 h-6 rounded bg-white/5 object-contain"
                                                        onError={(e) => { e.target.style.display = 'none'; }}
                                                    />
                                                )}

                                                <div className="flex-1 min-w-0 flex flex-col justify-center gap-1">
                                                    <h3 className={`text-[14px] font-semibold transition-colors truncate ${isSelected ? 'text-blue-100' : 'text-gray-100 group-hover:text-blue-300'}`}>
                                                        {result.title}
                                                    </h3>

                                                    <div className="flex items-center gap-2 text-[12px]">
                                                        <span className="font-medium text-blue-400/80 truncate max-w-[130px] flex-shrink-0">
                                                            {domain}
                                                        </span>
                                                        <span className="text-gray-600 flex-shrink-0">•</span>
                                                        <span className="text-gray-500 truncate min-w-0" title={result.link}>
                                                            {result.link}
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                </div>

                {/* Right Side: Preview Panel */}
                <div className="w-[45%] flex flex-col h-full pl-0">
                    {previewResult ? (
                        <div className="flex flex-col h-full min-h-0 bg-gradient-to-br from-[#2A2D35]/80 to-[#1C1E26]/80 rounded-2xl border border-[#3A3F4B]/50 overflow-hidden relative shadow-inner">
                            {/* Decorative background blur */}
                            <div className="absolute top-0 right-0 w-48 h-48 bg-blue-500/5 rounded-full blur-3xl pointer-events-none transform translate-x-10 -translate-y-10"></div>

                            <div className="p-6 flex-1 overflow-y-auto custom-scrollbar relative z-10 flex flex-col">
                                <div className="flex items-center gap-3 mb-5">
                                    <img
                                        src={`https://www.google.com/s2/favicons?sz=64&domain=${getDomain(previewResult.link)}`}
                                        alt=""
                                        className="w-10 h-10 rounded-lg bg-white/5 object-contain p-1 border border-[#3A3F4B]/50"
                                        onError={(e) => { e.target.style.display = 'none'; }}
                                    />
                                    <div className="min-w-0">
                                        <h4 className="text-[13px] font-medium text-blue-400/80 tracking-wide uppercase">
                                            {getDomain(previewResult.link)}
                                        </h4>
                                    </div>
                                </div>
                                <h3 className="text-[19px] font-bold text-white mb-4 leading-snug">
                                    {previewResult.title}
                                </h3>
                                <div className="mb-6 pb-6 border-b border-[#3A3F4B]/50">
                                    <p className="text-[14.5px] text-gray-300 leading-[1.7] antialiased">
                                        {previewResult.snippet || "No additional snippet available for this resource."}
                                    </p>
                                </div>

                                <div className="mt-auto pt-2">
                                    {isFileUrl(previewResult.link) ? (
                                        // File URL → open in inline viewer
                                        <a
                                            href={viewerHref(previewResult.link)}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="inline-flex items-center justify-center gap-2 w-full px-4 py-3 bg-[#2A2D35] hover:bg-blue-600/20 hover:border-blue-500/50 hover:text-blue-300 text-gray-300 text-[14px] font-semibold rounded-xl transition-all border border-[#3A3F4B]/80 group"
                                        >
                                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                            </svg>
                                            <span>View File</span>
                                            <span className="text-xs font-normal text-gray-500 uppercase tracking-wide">
                                                {getFileExt(previewResult.link).slice(1)}
                                            </span>
                                        </a>
                                    ) : (
                                        // Regular webpage → open in new tab
                                        <a
                                            href={previewResult.link}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="inline-flex items-center justify-center gap-2 w-full px-4 py-3 bg-[#2A2D35] hover:bg-blue-600/20 hover:border-blue-500/50 hover:text-blue-300 text-gray-300 text-[14px] font-semibold rounded-xl transition-all border border-[#3A3F4B]/80 group"
                                        >
                                            <span>Visit Website</span>
                                            <svg className="w-4 h-4 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                            </svg>
                                        </a>
                                    )}
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="flex flex-col items-center justify-center h-full text-center p-8 bg-[#2A2D35]/10 rounded-2xl border border-dashed border-[#3A3F4B]/50">
                            <div className="w-16 h-16 bg-[#2A2D35]/40 rounded-full flex items-center justify-center mb-4 transition-transform duration-500 hover:scale-110">
                                <svg className="w-8 h-8 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                </svg>
                            </div>
                            <p className="text-gray-300 font-semibold text-[15px]">Select a resource</p>
                            <p className="text-[13.5px] text-gray-500 mt-2 max-w-[220px] leading-relaxed">
                                Hover over or click any result to read a snippet and see details here.
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </Modal>
    );
}
