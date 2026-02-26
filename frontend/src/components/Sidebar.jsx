import { useState, useCallback, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { useAuth } from '../context/AuthContext';
import { uploadBatch, uploadBatchWithAutoNotebook, getMaterials, getMaterialText, deleteMaterial, updateMaterial, webSearch, uploadUrl } from '../api/materials';
import { useMaterialUpdates } from '../hooks/useMaterialUpdates';
import SourceItem from './SourceItem';
import UploadDialog from './UploadDialog';
import WebSearchDialog from './WebSearchDialog';
import { MarkdownRenderer } from './ChatMessage';

export default function Sidebar() {
    const {
        materials,
        setMaterials,
        currentMaterial,
        setCurrentMaterial,
        addMaterial,
        setLoadingState,
        loading,
        currentNotebook,
        setCurrentNotebook,
        draftMode,
        setDraftMode,
        selectedSources,
        setSelectedSources,
        toggleSourceSelection,
        selectAllSources,
        deselectAllSources,
    } = useApp();
    const [dragActive, setDragActive] = useState(false);
    const [width, setWidth] = useState(320); // Increased default width
    const [isResizing, setIsResizing] = useState(false);
    const [showTextModal, setShowTextModal] = useState(false);
    const [modalText, setModalText] = useState('');
    const [modalFilename, setModalFilename] = useState('');
    const [modalLoading, setModalLoading] = useState(false);
    const [showUploadDialog, setShowUploadDialog] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedFileType, setSelectedFileType] = useState(null);
    const [isSearching, setIsSearching] = useState(false);
    const [searchResults, setSearchResults] = useState([]);
    const [showSearchDialog, setShowSearchDialog] = useState(false);
    const [searchError, setSearchError] = useState(null);
    const navigate = useNavigate();
    const { user } = useAuth();

    const ALL_FILE_TYPES = [
        { id: '', label: 'Any type' },
        { id: 'pdf', label: 'PDF Document (.pdf)' },
        { id: 'doc', label: 'Word Document (.doc, .docx)' },
        { id: 'ppt', label: 'PowerPoint (.ppt, .pptx)' },
        { id: 'xls', label: 'Excel (.xls, .xlsx)' },
        { id: 'txt', label: 'Text File (.txt)' },
        { id: 'csv', label: 'CSV File (.csv)' },
        { id: 'rtf', label: 'Rich Text Format (.rtf)' },
        { id: 'md', label: 'Markdown (.md)' },
        { id: 'json', label: 'JSON (.json)' },
        { id: 'xml', label: 'XML (.xml)' }
    ];

    const minWidth = 260; // Increased min width
    const maxWidth = 600;

    const [loadError, setLoadError] = useState(null);

    const loadMaterials = useCallback(async (autoSelect = false) => {
        if (currentNotebook?.id && !currentNotebook.isDraft && !draftMode) {
            try {
                setLoadError(null);
                const loadedMaterials = await getMaterials(currentNotebook.id);
                const formatted = loadedMaterials.map(m => ({
                    id: m.id,
                    filename: m.filename,
                    title: m.title,
                    status: m.status,
                    chunkCount: m.chunk_count,
                    source_type: m.source_type,
                }));

                setMaterials(formatted);
                if (formatted.length > 0 && !currentMaterial) {
                    setCurrentMaterial(formatted[0]);
                }
                // Auto-select all completed materials on initial notebook load
                // so the chat input is ready without requiring manual checkbox clicks.
                // Uses additive semantics so manual deselections of OTHER sources are kept.
                if (autoSelect) {
                    const completedIds = formatted
                        .filter(m => m.status === 'completed')
                        .map(m => m.id);
                    if (completedIds.length > 0) {
                        setSelectedSources(prev => new Set([...prev, ...completedIds]));
                    }
                }
            } catch (error) {
                console.error('Failed to load materials:', error);
                setLoadError('Failed to load sources. Click to retry.');
            }
        }
    }, [currentNotebook?.id, currentNotebook?.isDraft, draftMode, setMaterials, currentMaterial, setCurrentMaterial, setSelectedSources]);

    // Initial load when notebook changes — auto-select all completed sources
    // so the chat send button is immediately enabled.
    // (AppContext already calls deselectAllSources() on notebook change, so
    //  we don't need to do it again here.)
    useEffect(() => {
        loadMaterials(true);
    }, [currentNotebook?.id, loadMaterials]);

    // WebSocket: real-time material processing updates
    const handleWsMessage = useCallback((msg) => {
        if (msg.type === 'material_update' && msg.material_id) {
            setMaterials(prev => prev.map(m =>
                m.id === msg.material_id
                    ? {
                        ...m,
                        status: msg.status,
                        ...(msg.title ? { title: msg.title } : {}),
                        ...(msg.error ? { error: msg.error } : {}),
                      }
                    : m
            ));
            // Reload full material list when a material completes to get chunk_count etc.
            if (msg.status === 'completed' || msg.status === 'failed') {
                loadMaterials();
                // Auto-add newly completed material to selection so the user
                // can start chatting immediately after upload without any
                // manual interaction. This only ADDs — never removes — so
                // existing manual source selections are preserved.
                if (msg.status === 'completed') {
                    setSelectedSources(prev => new Set([...prev, msg.material_id]));
                }
            }
        }
    }, [setMaterials, loadMaterials, setSelectedSources]);

    useMaterialUpdates(user?.id || null, handleWsMessage);

    // Fallback polling for pending/processing materials (in case WS drops)
    // Pass autoSelect=true so that if the WebSocket missed a "completed" event the
    // polling path still enables the send button by populating selectedSources.
    useEffect(() => {
        const hasProcessingMaterials = materials.some(m => m.status && !['completed', 'failed'].includes(m.status));
        if (!hasProcessingMaterials) return;

        const interval = setInterval(() => {
            loadMaterials(true); // autoSelect=true — ensures completed materials are selected even when WS misses an event
        }, 8000); // Relaxed interval — WebSocket handles most updates

        return () => clearInterval(interval);
    }, [materials, loadMaterials]);

    const handleMouseMove = useCallback((e) => {
        if (isResizing) {
            const newWidth = e.clientX;
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

    const handleFileUpload = async (files) => {
        if (!files || files.length === 0) return;
        setLoadingState('upload', true);

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
                result = await uploadBatch(files, currentNotebook?.id);
            }

            if (result.materials) {
                result.materials.forEach(m => {
                    if (m.status !== 'error') {
                        addMaterial({
                            id: m.material_id,
                            filename: m.filename,
                            chunkCount: m.chunk_count,
                            status: m.status,
                        });
                    }
                });
            }
        } catch (error) {
            console.error('Batch upload failed:', error);
            alert('Upload failed: ' + error.message);
        } finally {
            setLoadingState('upload', false);
        }
    };

    const handleSearchSubmit = async (e) => {
        if (e.key !== 'Enter' || !searchQuery.trim()) return;

        setIsSearching(true);
        setShowSearchDialog(true);
        setSearchResults([]);
        setSearchError(null);

        try {
            // Priority: explicit selectedFileType > query "filetype:X"
            let fileType = selectedFileType;
            let cleanQuery = searchQuery.trim();

            const filetypeMatch = cleanQuery.match(/filetype:(\w+)/i);
            if (filetypeMatch) {
                if (!fileType) {
                    fileType = filetypeMatch[1];
                }
                // Always strip it to avoid duplication in the final string
                cleanQuery = cleanQuery.replace(/filetype:\w+/ig, '').trim();
            }

            const results = await webSearch(cleanQuery, fileType);
            setSearchResults(results);
        } catch (error) {
            console.error('Search failed:', error);
            setSearchError(error.message || 'Failed to search the web');
        } finally {
            setIsSearching(false);
        }
    };

    const handleAddWebSources = async (selectedResults) => {
        if (!selectedResults || selectedResults.length === 0) return;

        setLoadingState('upload', true);
        try {
            let currentNbId = currentNotebook?.isDraft ? null : currentNotebook?.id;
            let newlyCreatedNotebook = null;

            for (const resObj of selectedResults) {
                const autoCreate = !currentNbId;
                const res = await uploadUrl(
                    resObj.link,
                    currentNbId,
                    autoCreate,
                    'auto',
                    resObj.title
                );

                if (res.notebook && !newlyCreatedNotebook) {
                    newlyCreatedNotebook = res.notebook;
                    currentNbId = res.notebook.id;
                    setCurrentNotebook(res.notebook);
                    setDraftMode(false);
                }

                addMaterial({
                    id: res.material_id,
                    filename: res.filename,
                    title: resObj.title, // Add title to materials state
                    status: res.status,
                    source_type: res.source_type || 'url'
                });
            }

            if (newlyCreatedNotebook) {
                navigate(`/notebook/${newlyCreatedNotebook.id}`, { replace: true });
            }
        } catch (error) {
            console.error('Failed to add web sources:', error);
            alert('Failed to add some sources');
        } finally {
            setLoadingState('upload', false);
            loadMaterials();
        }
    };

    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true);
        } else if (e.type === 'dragleave') {
            setDragActive(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleFileUpload(Array.from(e.dataTransfer.files));
        }
    };

    const handleSourceClick = (source) => {
        setCurrentMaterial(source);
    };

    const handleCheckboxToggle = (source) => {
        toggleSourceSelection(source.id);
    };

    const handleSeeText = async (source) => {
        setModalFilename(source.title || source.filename);
        setModalText('');
        setModalLoading(true);
        setShowTextModal(true);

        try {
            const response = await getMaterialText(source.id);
            setModalText(response.text);
        } catch (error) {
            console.error('Failed to fetch text:', error);
            setModalText('Error: Failed to load material text.');
        } finally {
            setModalLoading(false);
        }
    };

    const handleRemoveSource = async (source) => {
        try {
            await deleteMaterial(source.id);
            const next = materials.filter(m => m.id !== source.id);
            setMaterials(next);
            if (currentMaterial?.id === source.id) {
                setCurrentMaterial(next.length > 0 ? next[0] : null);
            }
        } catch (error) {
            console.error('Failed to remove source:', error);
            alert('Failed to remove source: ' + error.message);
        }
    };

    const handleRenameSource = async (source, newName) => {
        try {
            const isUrlOrYoutube = (source.source_type || source.sourceType) === 'url' || (source.source_type || source.sourceType) === 'youtube';
            const payload = isUrlOrYoutube ? { title: newName } : { filename: newName };
            await updateMaterial(source.id, payload);
            const updates = isUrlOrYoutube ? { title: newName } : { filename: newName };
            setMaterials(prev => prev.map(m => m.id === source.id ? { ...m, ...updates } : m));
            if (currentMaterial?.id === source.id) {
                setCurrentMaterial(prev => prev ? { ...prev, ...updates } : null);
            }
        } catch (error) {
            console.error('Failed to rename source:', error);
            alert('Failed to rename source: ' + error.message);
        }
    };

    return (
        <>
            <aside
                className="h-full overflow-hidden flex flex-col relative border-r border-[#3A3F4B] bg-[#1C1E26] text-gray-200"
                style={{ width: `${width}px`, minWidth: `${minWidth}px` }}
            >
                {/* Header */}
                <div className="panel-header py-4 px-4 border-b border-[#3A3F4B]">
                    <div className="flex justify-between items-center w-full">
                        <span className="text-white font-semibold text-[15px]">Sources</span>
                        <button className="text-gray-400 hover:text-white transition-colors">
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            </svg>
                        </button>
                    </div>
                </div>

                {/* Add Source Button & Search Block */}
                <div className="p-4 border-b border-[#2A2D35] space-y-5">
                    <button
                        className="w-full py-2.5 px-4 rounded-full border border-[#4A4E58] hover:bg-white/5 transition-colors flex items-center justify-center gap-2 text-[14px] text-[#E5E7EB] font-medium"
                        onClick={() => setShowUploadDialog(true)}
                        disabled={loading.upload}
                    >
                        {loading.upload ? (
                            <div className="loading-spinner w-4 h-4" />
                        ) : (
                            <span className="text-[16px] leading-none mb-0.5">+</span>
                        )}
                        Add sources
                    </button>

                    {/* Unique Premium Search Box */}
                    <div className="p-3 bg-gradient-to-b from-[#2A2D35] to-[#1C1E26] border border-[#3A3F4B]/80 rounded-[18px] space-y-3 shadow-[0_4px_20px_rgba(0,0,0,0.2)] relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/5 rounded-full blur-2xl pointer-events-none transform translate-x-10 -translate-y-10"></div>

                        {/* Search Input */}
                        <div className="flex items-center gap-2.5 px-3 py-2 bg-[#1C1E26]/80 rounded-xl border border-[#3A3F4B]/50 focus-within:border-blue-500/50 focus-within:ring-1 focus-within:ring-blue-500/20 transition-all relative z-10">
                            <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                            </svg>
                            <input
                                type="text"
                                placeholder="Search the web for sources..."
                                className="bg-transparent text-[13px] w-full outline-none text-gray-200 placeholder:text-gray-500 font-medium"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                onKeyDown={handleSearchSubmit}
                            />
                        </div>

                        {/* Filters and Actions Row */}
                        <div className="flex items-center justify-between relative z-10">
                            <div className="flex flex-col relative w-[160px]">
                                <div className="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none">
                                    <svg className="w-3 h-3 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                </div>
                                <select
                                    value={selectedFileType || ''}
                                    onChange={(e) => setSelectedFileType(e.target.value || null)}
                                    className="block w-full pl-7 pr-6 py-1.5 text-[11.5px] font-medium text-gray-300 bg-[#22242C] border border-[#3A3F4B]/60 rounded-lg appearance-none focus:outline-none focus:border-blue-500/50 hover:bg-[#2A2D35] transition-colors cursor-pointer truncate"
                                    style={{ WebkitAppearance: 'none', MozAppearance: 'none' }}
                                >
                                    {ALL_FILE_TYPES.map(ft => (
                                        <option key={ft.id} value={ft.id} className="bg-[#1C1E26] text-gray-200">
                                            {ft.label}
                                        </option>
                                    ))}
                                </select>
                                <div className="absolute inset-y-0 right-0 pr-2 flex items-center pointer-events-none">
                                    <svg className="w-3 h-3 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                    </svg>
                                </div>
                            </div>

                            <button
                                onClick={() => handleSearchSubmit({ key: 'Enter' })}
                                disabled={!searchQuery.trim()}
                                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-900/20 transition-all font-semibold text-[12px] disabled:opacity-50 disabled:cursor-not-allowed group"
                            >
                                <svg className="w-3.5 h-3.5 group-hover:rotate-12 transition-transform" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                    <circle cx="12" cy="12" r="10" strokeWidth="2" />
                                    <path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" strokeWidth="2" />
                                </svg>
                                Web
                            </button>
                        </div>
                    </div>
                </div>

                {/* Sources List Header */}
                <div className="px-5 pt-8 pb-4 flex justify-between items-center bg-transparent">
                    <span className="text-[14px] font-medium text-[#7D8590]">Select all sources</span>
                    <button
                        onClick={() => selectedSources.size === materials.length && materials.length > 0 ? deselectAllSources() : selectAllSources()}
                        className={`flex items-center justify-center w-4 h-4 rounded-[4px] border transition-colors ${selectedSources.size === materials.length && materials.length > 0 ? 'bg-transparent border-white text-white' : selectedSources.size > 0 ? 'bg-transparent border-gray-400 text-gray-400' : 'border-[#4A4E58] bg-transparent hover:border-gray-400'}`}
                        title={selectedSources.size === materials.length && materials.length > 0 ? 'Deselect all' : 'Select all'}
                    >
                        {selectedSources.size === materials.length && materials.length > 0 ? (
                            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                            </svg>
                        ) : selectedSources.size > 0 ? (
                            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14" />
                            </svg>
                        ) : null}
                    </button>
                </div>



                {/* Sources List */}
                <div
                    className={`flex-1 overflow-y-auto transition-colors ${dragActive ? 'bg-accent/5' : ''}`}
                    onDragEnter={handleDrag}
                    onDragLeave={handleDrag}
                    onDragOver={handleDrag}
                    onDrop={handleDrop}
                >
                    {/* Load error banner */}
                    {loadError && (
                        <button
                            onClick={() => { setLoadError(null); loadMaterials(); }}
                            className="w-full px-4 py-2 text-xs text-red-400 bg-red-500/10 hover:bg-red-500/15 transition-colors flex items-center gap-2"
                        >
                            <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M12 3l9.66 16.59a1 1 0 01-.87 1.41H3.21a1 1 0 01-.87-1.41L12 3z" />
                            </svg>
                            {loadError}
                        </button>
                    )}
                    {materials.length > 0 ? (
                        <div className="p-2">
                            <div className="space-y-0.5">
                                {materials.map((source) => (
                                    <SourceItem
                                        key={source.id}
                                        source={source}
                                        checked={selectedSources.has(source.id)}
                                        active={currentMaterial?.id === source.id}
                                        anySelected={selectedSources.size > 0}
                                        onClick={handleSourceClick}
                                        onToggle={handleCheckboxToggle}
                                        onSeeText={handleSeeText}
                                        onRename={handleRenameSource}
                                        onRemove={handleRemoveSource}
                                    />
                                ))}
                            </div>
                        </div>
                    ) : (
                        <div className="h-full p-4">
                            <div className={`dropzone h-full ${dragActive ? 'dropzone-active' : ''}`}>
                                <div className="empty-state-icon">
                                    <svg className="w-8 h-8 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                                    </svg>
                                </div>
                                <p className="empty-state-title">Add sources</p>
                                <p className="empty-state-description mt-1">
                                    Upload PDFs, docs, or text files to get started
                                </p>
                            </div>
                        </div>
                    )}
                </div>

                {/* Resize Handle */}
                <div
                    className={`absolute top-0 right-0 w-1.5 h-full cursor-col-resize transition-colors group ${isResizing ? 'bg-accent/50' : 'hover:bg-accent/30'}`}
                    onMouseDown={() => setIsResizing(true)}
                >
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-1 h-8 rounded-full bg-text-muted/20 opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
            </aside>

            {/* Material Text Modal */}
            {showTextModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 sm:p-6" onClick={() => setShowTextModal(false)}>
                    <div
                        className="bg-[#1C1E26] border border-[#3A3F4B] rounded-2xl shadow-2xl w-full max-w-5xl h-[85vh] flex flex-col overflow-hidden relative"
                        onClick={e => e.stopPropagation()}
                    >
                        {/* Glow effect */}
                        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-3/4 h-32 bg-blue-500/10 rounded-full blur-[60px] pointer-events-none"></div>

                        <div className="p-4 sm:p-5 border-b border-[#3A3F4B] flex items-center justify-between bg-[#1C1E26]/80 backdrop-blur-xl z-10">
                            <div className="flex items-center gap-3 min-w-0">
                                <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400">
                                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                </div>
                                <div className="min-w-0">
                                    <h3 className="text-[15px] font-semibold text-white truncate">{modalFilename}</h3>
                                    <p className="text-[13px] text-gray-400 flex items-center gap-1.5 mt-0.5">
                                        <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                                        Document Preview
                                    </p>
                                </div>
                            </div>
                            <button
                                onClick={() => setShowTextModal(false)}
                                className="p-2 mr-1 rounded-lg text-gray-400 hover:text-white hover:bg-[#2A2D35] transition-colors focus:outline-none"
                            >
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>

                        <div className="flex-1 overflow-y-auto bg-[#1C1E26] relative z-10 p-5 sm:p-8 custom-scrollbar">
                            {modalLoading ? (
                                <div className="flex flex-col items-center justify-center h-full gap-5">
                                    <div className="relative">
                                        <div className="loading-spinner w-12 h-12 text-blue-500" />
                                        <div className="absolute inset-0 bg-blue-500/20 blur-xl rounded-full"></div>
                                    </div>
                                    <p className="text-[14px] text-gray-400 font-medium tracking-wide animate-pulse">Analyzing document content...</p>
                                </div>
                            ) : (
                                <div className="max-w-4xl mx-auto markdown-content rounded-xl">
                                    <MarkdownRenderer content={modalText || '*No text content available for this source.*'} />
                                </div>
                            )}
                        </div>

                        <div className="p-4 border-t border-[#3A3F4B] bg-[#1C1E26]/95 backdrop-blur-xl flex justify-end z-10 rounded-b-2xl">
                            <button
                                onClick={() => setShowTextModal(false)}
                                className="px-5 py-2 rounded-lg text-sm font-medium text-gray-300 hover:text-white hover:bg-[#2A2D35] transition-colors focus:outline-none"
                            >
                                Close Preview
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Upload Dialog */}
            <UploadDialog
                isOpen={showUploadDialog}
                onClose={() => setShowUploadDialog(false)}
                currentNotebook={currentNotebook}
                draftMode={draftMode}
                onMaterialAdded={addMaterial}
                setCurrentNotebook={setCurrentNotebook}
                setDraftMode={setDraftMode}
            />

            <WebSearchDialog
                isOpen={showSearchDialog}
                onClose={() => setShowSearchDialog(false)}
                results={searchResults}
                isSearching={isSearching}
                error={searchError}
                query={searchQuery}
                onAddSelected={handleAddWebSources}
            />
        </>
    );
}
