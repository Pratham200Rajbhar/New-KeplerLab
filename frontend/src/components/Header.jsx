import { useState, useRef, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useApp } from '../context/AppContext';
import { useTheme } from '../context/ThemeContext';

import { useNavigate } from 'react-router-dom';

export default function Header({ user, onBack }) {
    const navigate = useNavigate();

    const handleBackClick = () => {
        if (onBack) onBack(); // Keep cleanup if provided
        navigate('/');
    };
    const [showMenu, setShowMenu] = useState(false);
    const menuRef = useRef(null);
    const { logout } = useAuth();
    const { currentNotebook } = useApp();
    const { theme, toggleTheme, isDark } = useTheme();

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (menuRef.current && !menuRef.current.contains(event.target)) {
                setShowMenu(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleLogout = async () => {
        setShowMenu(false);
        await logout();
    };

    const userInitial = user?.username?.charAt(0)?.toUpperCase() || user?.email?.charAt(0)?.toUpperCase() || 'U';

    return (
        <header className="h-14 glass flex items-center justify-between px-4 flex-shrink-0 relative z-40">
            {/* Left - Back Button, Logo & Notebook Name */}
            <div className="flex items-center gap-3">
                {/* Back Button */}
                {onBack && (
                    <button
                        onClick={handleBackClick}
                        className="btn-icon"
                        title="Back to notebooks"
                    >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                        </svg>
                    </button>
                )}

                {/* Logo */}
                <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-xl bg-accent flex items-center justify-center shadow-glow-sm">
                        <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                    </div>
                    <span className="text-base font-semibold text-text-primary">KeplerLab</span>
                </div>

                {/* Divider */}
                <div className="w-px h-5 bg-border-light ml-1" />

                {/* Notebook Name */}
                <div className="flex items-center gap-2">
                    <svg className="w-4 h-4 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                    </svg>
                    <h1 className="text-sm text-text-secondary">{currentNotebook?.name || 'Notebook'}</h1>
                </div>
            </div>

            {/* Right - Actions */}
            <div className="flex items-center gap-1">
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

                {/* Share */}
                <button className="btn-ghost text-sm">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
                    </svg>
                    Share
                </button>

                {/* Help */}
                <button className="btn-icon" title="Help">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                </button>

                {/* User Menu */}
                <div className="relative ml-1" ref={menuRef}>
                    <button
                        className="w-8 h-8 rounded-xl bg-accent/20 flex items-center justify-center text-accent-light text-sm font-medium hover:bg-accent/30 transition-all"
                        onClick={() => setShowMenu(!showMenu)}
                    >
                        {userInitial}
                    </button>

                    {showMenu && (
                        <div className="absolute right-0 top-full mt-2 w-56 bg-surface-raised backdrop-blur-xl rounded-2xl border border-border shadow-glass overflow-hidden animate-fade-in z-50">
                            <div className="px-5 py-4 border-b border-border-light bg-surface-overlay">
                                <p className="text-sm font-semibold text-text-primary mb-0.5">{user?.username || 'User'}</p>
                                <p className="text-[11px] text-text-muted truncate">{user?.email || 'user@example.com'}</p>
                            </div>
                            <div className="p-1.5">
                                <button className="w-full px-4 py-2.5 text-left text-sm text-text-secondary hover:bg-surface-overlay hover:text-text-primary rounded-xl flex items-center gap-3 transition-all">
                                    <div className="w-8 h-8 rounded-lg bg-surface-overlay flex items-center justify-center">
                                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924-1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                        </svg>
                                    </div>
                                    <span>Settings</span>
                                </button>
                                <button
                                    onClick={handleLogout}
                                    className="w-full px-4 py-2.5 text-left text-sm text-text-secondary hover:bg-status-error/10 hover:text-status-error rounded-xl flex items-center gap-3 transition-all"
                                >
                                    <div className="w-8 h-8 rounded-lg bg-surface-overlay flex items-center justify-center">
                                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                                        </svg>
                                    </div>
                                    <span>Sign out</span>
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </header>
    );
}
