import { useState, useRef, useEffect } from 'react';
import MiniBlockChat from './MiniBlockChat';

const LANG_OPTIONS = [
    'Hindi', 'Bengali', 'Marathi', 'Telugu', 'Tamil', 'Gujarati', 'Urdu', 'Kannada', 'Odia', 'Malayalam', 'Punjabi',
    'Spanish', 'French', 'German', 'Chinese', 'Arabic', 'Portuguese', 'Japanese'
];

/**
 * BlockHoverMenu — wraps a single AI paragraph block.
 * On hover, shows floating action buttons: ❓ Ask | 🔄 Simplify | 🌍 Translate | 📚 Explain
 *
 * Props:
 *   blockId   — ResponseBlock UUID for API calls
 *   children  — the paragraph content JSX
 */
export default function BlockHoverMenu({ blockId, children }) {
    const [hovered, setHovered] = useState(false);
    const [menuOpen, setMenuOpen] = useState(false);
    const [miniChat, setMiniChat] = useState(null); // {action, lang?} | null
    const [showLangPicker, setShowLangPicker] = useState(false);
    const [langSearch, setLangSearch] = useState('');
    const ref = useRef(null);

    useEffect(() => {
        const handler = (e) => {
            if (ref.current && !ref.current.contains(e.target)) {
                setShowLangPicker(false);
                setHovered(false);
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, []);

    const openAction = (action, lang = '') => {
        setMiniChat({ action, lang });
        setShowLangPicker(false);
        setLangSearch('');
    };

    const close = () => setMiniChat(null);

    return (
        <div
            ref={ref}
            className="block-hover-wrapper"
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => {
                if (!showLangPicker) setHovered(false);
            }}
        >
            <div className="block-hover-content">
                {children}

                {/* Floating action menu */}
                {(hovered || showLangPicker) && !miniChat && blockId && (
                    <div className="block-hover-actions">
                        <button
                            className="block-action-btn"
                            title="Ask a question"
                            onClick={() => openAction('ask')}
                        >
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <span>Ask</span>
                        </button>
                        <button
                            className="block-action-btn"
                            title="Simplify"
                            onClick={() => openAction('simplify')}
                        >
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                            </svg>
                            <span>Simplify</span>
                        </button>
                        <div className="block-hover-lang-wrapper">
                            <button
                                className="block-action-btn"
                                title="Translate"
                                onClick={() => setShowLangPicker((v) => !v)}
                            >
                                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
                                </svg>
                                <span>Translate</span>
                            </button>
                            {showLangPicker && (
                                <div className="lang-picker flex flex-col max-h-[250px] w-40">
                                    <div className="px-2 pb-1 border-b border-[var(--border)]">
                                        <input
                                            type="text"
                                            placeholder="Search language..."
                                            value={langSearch}
                                            onChange={(e) => setLangSearch(e.target.value)}
                                            className="w-full bg-[var(--surface-overlay)] text-[var(--text-primary)] text-xs px-2 py-1.5 rounded focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                                            autoFocus
                                            onClick={(e) => e.stopPropagation()} // Keep picker open on click
                                        />
                                    </div>
                                    <div className="overflow-y-auto overflow-x-hidden flex-1 py-1 custom-scrollbar">
                                        {LANG_OPTIONS.filter(l => l.toLowerCase().includes(langSearch.toLowerCase())).length > 0 ? (
                                            LANG_OPTIONS.filter(l => l.toLowerCase().includes(langSearch.toLowerCase())).map((lang) => (
                                                <button
                                                    key={lang}
                                                    className="lang-picker-item"
                                                    onClick={() => openAction('translate', lang)}
                                                >{lang}</button>
                                            ))
                                        ) : (
                                            <div className="px-3 py-2 text-xs text-[var(--text-muted)] text-center">No results</div>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                        <button
                            className="block-action-btn"
                            title="Explain in depth"
                            onClick={() => openAction('explain')}
                        >
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                            </svg>
                            <span>Explain</span>
                        </button>
                    </div>
                )}
            </div>

            {/* Inline mini-chat */}
            {miniChat && blockId && (
                <MiniBlockChat
                    blockId={blockId}
                    action={miniChat.action}
                    lang={miniChat.lang}
                    onClose={close}
                />
            )}
        </div>
    );
}
