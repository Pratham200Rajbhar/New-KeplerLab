import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { getNotebooks, deleteNotebook, updateNotebook } from '../api/notebooks';

export default function HomePage() {
    const { user, logout } = useAuth();
    const { toggleTheme, isDark } = useTheme();
    const navigate = useNavigate();
    const [notebooks, setNotebooks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showMenu, setShowMenu] = useState(false);
    const [activeMenu, setActiveMenu] = useState(null);
    const [editingNotebook, setEditingNotebook] = useState(null);
    const [editName, setEditName] = useState('');
    const [editDescription, setEditDescription] = useState('');
    const [saving, setSaving] = useState(false);
    const [deletingNotebook, setDeletingNotebook] = useState(null);
    const [toastMsg, setToastMsg] = useState(null);

    const showToast = useCallback((msg) => {
        setToastMsg(msg);
        setTimeout(() => setToastMsg(null), 3000);
    }, []);

    const loadNotebooks = useCallback(async () => {
        try {
            setError(null);
            const data = await getNotebooks();
            setNotebooks(data);
        } catch (err) {
            console.error('Failed to load notebooks:', err);
            setError('Failed to load notebooks. Please try again.');
        }
        setLoading(false);
    }, []);

    useEffect(() => {
        loadNotebooks();
    }, []);

    const handleDelete = async (notebookId, e) => {
        e?.stopPropagation();
        setActiveMenu(null);
        setDeletingNotebook(notebookId);
    };

    const confirmDelete = async () => {
        const notebookId = deletingNotebook;
        setDeletingNotebook(null);
        if (!notebookId) return;

        try {
            await deleteNotebook(notebookId);
            setNotebooks(prev => prev.filter(n => n.id !== notebookId));
        } catch (err) {
            console.error('Failed to delete notebook:', err);
            showToast('Failed to delete notebook. Please try again.');
        }
    };

    const openRenameModal = (notebook, e) => {
        e?.stopPropagation();
        setActiveMenu(null);
        setEditingNotebook(notebook);
        setEditName(notebook.name);
        setEditDescription(notebook.description || '');
    };

    const handleRename = async (e) => {
        e.preventDefault();
        if (!editName.trim()) return;

        setSaving(true);
        try {
            const updated = await updateNotebook(editingNotebook.id, editName.trim(), editDescription.trim() || null);
            setNotebooks(notebooks.map(n => n.id === editingNotebook.id ? updated : n));
            setEditingNotebook(null);
        } catch (err) {
            console.error('Failed to rename notebook:', err);
            showToast('Failed to rename notebook. Please try again.');
        }
        setSaving(false);
    };

    const formatDate = (dateString) => {
        const date = new Date(dateString);
        const now = new Date();
        const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));

        if (diffDays === 0) return 'Today';
        if (diffDays === 1) return 'Yesterday';
        if (diffDays < 7) return `${diffDays} days ago`;
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    };

    const userInitial = user?.username?.charAt(0)?.toUpperCase() || user?.email?.charAt(0)?.toUpperCase() || 'U';

    return (
        <div className="min-h-screen bg-surface">
            <header className="flex items-center justify-between px-6 py-4 border-b border-border">
                <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-xl bg-accent flex items-center justify-center shadow-glow-sm">
                        <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                    </div>
                    <span className="text-base font-semibold text-text-primary">KeplerLab</span>
                </div>

                <div className="flex items-center gap-2">
                    {/* Theme Toggle */}
                    <button
                        onClick={toggleTheme}
                        className="btn-icon"
                        title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
                    >
                        {isDark ? (
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                            </svg>
                        ) : (
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                            </svg>
                        )}
                    </button>

                    <button onClick={() => showToast('Settings coming soon!')} className="btn-ghost text-sm">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                        Settings
                    </button>

                    <div className="relative">
                        <button
                            onClick={() => setShowMenu(!showMenu)}
                            className="w-8 h-8 rounded-xl bg-accent/20 flex items-center justify-center text-accent-light text-sm font-medium hover:bg-accent/30 transition-all"
                        >
                            {userInitial}
                        </button>

                        {showMenu && (
                            <>
                                <div className="fixed inset-0 z-40" onClick={() => setShowMenu(false)} />
                                <div className="absolute right-0 top-full mt-2 w-52 glass rounded-xl shadow-glass overflow-hidden z-50 animate-fade-in">
                                    <div className="px-4 py-3 border-b border-border">
                                        <p className="text-sm font-medium text-text-primary">{user?.username || 'User'}</p>
                                        <p className="text-xs text-text-muted truncate">{user?.email}</p>
                                    </div>
                                    <button
                                        onClick={logout}
                                        className="w-full px-4 py-2.5 text-left text-sm text-text-secondary hover:bg-glass-light flex items-center gap-3 transition-colors"
                                    >
                                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                                        </svg>
                                        Sign out
                                    </button>
                                </div>
                            </>
                        )}
                    </div>
                </div>
            </header>

            <main className="max-w-6xl mx-auto px-6 py-12">
                <h1 className="text-4xl md:text-5xl font-light text-text-primary mb-2">
                    Welcome to KeplerLab
                </h1>
                <p className="text-text-secondary text-lg mb-12">
                    Your AI-powered research assistant
                </p>

                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-sm font-medium text-text-muted uppercase tracking-wider">My Notebooks</h2>
                    <span className="text-xs text-text-muted">{notebooks.length} notebooks</span>
                </div>

                {loading ? (
                    <div className="flex items-center justify-center py-20">
                        <div className="loading-spinner w-8 h-8" />
                    </div>
                ) : error ? (
                    <div className="flex flex-col items-center justify-center py-20 gap-4">
                        <p className="text-text-muted text-sm">{error}</p>
                        <button onClick={loadNotebooks} className="btn-primary text-sm px-4 py-2">
                            Retry
                        </button>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                        {/* Create New Notebook Card */}
                        <button
                            onClick={() => navigate('/notebook/draft')}
                            className="h-48 rounded-2xl border-2 border-dashed border-border hover:border-accent/50 flex flex-col items-center justify-center gap-3 transition-all group hover:bg-accent/5"
                        >
                            <div className="w-12 h-12 rounded-xl bg-accent/20 flex items-center justify-center group-hover:bg-accent/30 group-hover:shadow-glow-sm transition-all">
                                <svg className="w-6 h-6 text-accent-light" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                </svg>
                            </div>
                            <span className="text-text-muted text-sm">Create new notebook</span>
                        </button>

                        {/* Existing Notebooks */}
                        {notebooks.map((notebook) => (
                            <div
                                key={notebook.id}
                                onClick={() => navigate(`/notebook/${notebook.id}`)}
                                className="h-48 rounded-2xl glass cursor-pointer transition-all group relative overflow-hidden hover:shadow-glass hover:border-accent/30 flex flex-col"
                            >
                                {/* Content */}
                                <div className="flex-1 p-4 flex flex-col">
                                    {/* Icon */}
                                    <div className="w-10 h-10 rounded-xl bg-accent/15 flex items-center justify-center mb-auto">
                                        <svg className="w-5 h-5 text-accent-light" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                                        </svg>
                                    </div>

                                    {/* Title & Description */}
                                    <div className="mt-auto">
                                        <h3 className="text-text-primary font-medium text-sm truncate">{notebook.name}</h3>
                                        {notebook.description && (
                                            <p className="text-text-muted text-xs truncate mt-0.5">{notebook.description}</p>
                                        )}
                                        <p className="text-text-muted text-xs mt-2 opacity-60">
                                            {formatDate(notebook.updated_at)}
                                        </p>
                                    </div>
                                </div>

                                {/* Menu Button */}
                                <button
                                    onClick={(e) => { e.stopPropagation(); setActiveMenu(activeMenu === notebook.id ? null : notebook.id); }}
                                    className="absolute top-3 right-3 p-1.5 rounded-lg bg-surface-overlay/80 opacity-0 group-hover:opacity-100 hover:bg-surface-overlay text-text-muted transition-all"
                                >
                                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
                                    </svg>
                                </button>

                                {/* Dropdown Menu */}
                                {activeMenu === notebook.id && (
                                    <>
                                        <div className="fixed inset-0 z-40" onClick={(e) => { e.stopPropagation(); setActiveMenu(null); }} />
                                        <div className="absolute top-10 right-3 w-36 glass-strong rounded-xl shadow-glass overflow-hidden z-50 animate-fade-in">
                                            <button
                                                onClick={(e) => openRenameModal(notebook, e)}
                                                className="w-full px-3 py-2.5 text-left text-sm text-text-secondary hover:bg-glass-light flex items-center gap-2.5 transition-colors"
                                            >
                                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                                </svg>
                                                Rename
                                            </button>
                                            <button
                                                onClick={(e) => handleDelete(notebook.id, e)}
                                                className="w-full px-3 py-2.5 text-left text-sm text-red-400 hover:bg-red-500/10 flex items-center gap-2.5 transition-colors"
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
                )}

                {notebooks.length === 0 && !loading && (
                    <div className="mt-20 text-center">
                        <p className="text-text-muted text-sm mb-4">Get started by creating a new notebook</p>
                        <button onClick={() => navigate('/notebook/draft')} className="btn-primary">
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                            </svg>
                            Create new notebook
                        </button>
                    </div>
                )}
            </main>

            {/* Rename Modal */}
            {editingNotebook && (
                <div className="modal-backdrop" onClick={() => setEditingNotebook(null)}>
                    <div className="modal w-full max-w-md mx-4" onClick={e => e.stopPropagation()}>
                        <div className="modal-header">
                            <h3 className="text-base font-medium text-text-primary">Rename Notebook</h3>
                            <button onClick={() => setEditingNotebook(null)} className="btn-icon-sm">
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>
                        <form onSubmit={handleRename} className="modal-body space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-text-secondary mb-2">
                                    Notebook Name
                                </label>
                                <input
                                    type="text"
                                    value={editName}
                                    onChange={(e) => setEditName(e.target.value)}
                                    placeholder="Notebook name"
                                    className="input w-full"
                                    autoFocus
                                    required
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-text-secondary mb-2">
                                    Description (optional)
                                </label>
                                <textarea
                                    value={editDescription}
                                    onChange={(e) => setEditDescription(e.target.value)}
                                    placeholder="Brief description..."
                                    rows={2}
                                    className="input w-full resize-none"
                                />
                            </div>
                        </form>
                        <div className="modal-footer">
                            <button onClick={() => setEditingNotebook(null)} className="btn-secondary">
                                Cancel
                            </button>
                            <button onClick={handleRename} disabled={saving || !editName.trim()} className="btn-primary">
                                {saving ? 'Saving...' : 'Save'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Delete Confirmation Modal */}
            {deletingNotebook && (
                <div className="modal-backdrop" onClick={() => setDeletingNotebook(null)}>
                    <div className="modal w-full max-w-sm mx-4" onClick={e => e.stopPropagation()}>
                        <div className="modal-body py-6 text-center">
                            <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-red-500/10 flex items-center justify-center">
                                <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                            </div>
                            <h3 className="text-base font-semibold text-text-primary mb-2">Delete notebook?</h3>
                            <p className="text-sm text-text-secondary">This will permanently delete the notebook and all its materials.</p>
                        </div>
                        <div className="modal-footer justify-center gap-3">
                            <button onClick={() => setDeletingNotebook(null)} className="btn-secondary">Cancel</button>
                            <button onClick={confirmDelete} className="px-4 py-2 text-sm rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 font-medium transition-colors">Delete</button>
                        </div>
                    </div>
                </div>
            )}

            {/* Toast notification */}
            {toastMsg && (
                <div className="fixed bottom-4 right-4 z-50 bg-surface-raised text-text-primary px-4 py-2 rounded-lg shadow-lg border border-border text-sm animate-fade-in">
                    {toastMsg}
                </div>
            )}
        </div>
    );
}
