import { useEffect, useRef, useState, useCallback } from 'react';

/**
 * SuggestionDropdown — appears above the chat input when triggered explicitly.
 *
 * Props:
 *   suggestions — array of suggestion objects
 *   loading     — boolean
 *   onSelect    — callback(suggestion: string)
 *   onClose     — callback
 */
export default function SuggestionDropdown({ suggestions, loading, onSelect, onClose }) {
    const [activeIndex, setActiveIndex] = useState(-1);
    const containerRef = useRef(null);

    // Click outside → close
    useEffect(() => {
        const handler = (e) => {
            if (containerRef.current && !containerRef.current.contains(e.target)) {
                onClose();
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, [onClose]);

    const handleKeyDown = useCallback((e) => {
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            setActiveIndex((i) => Math.min(i + 1, suggestions.length - 1));
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            setActiveIndex((i) => Math.max(i - 1, -1));
        } else if (e.key === 'Enter' && activeIndex >= 0) {
            e.preventDefault();
            if (suggestions[activeIndex]) {
                onSelect(suggestions[activeIndex].suggestion);
            }
        } else if (e.key === 'Escape') {
            onClose();
        }
    }, [suggestions, activeIndex, onClose, onSelect]);

    return (
        <div ref={containerRef} className="suggestion-dropdown" onKeyDown={handleKeyDown} tabIndex={-1}>
            <div className="suggestion-dropdown-header">
                <span className="suggestion-label">✨ Suggestions</span>
                {loading && <div className="suggestion-spinner" />}
            </div>
            <ul className="suggestion-list">
                {!loading && suggestions.length === 0 && (
                    <li className="suggestion-item text-text-muted cursor-default hover:bg-transparent">
                        <span className="suggestion-text">No suggestions found.</span>
                    </li>
                )}
                {suggestions.map((item, idx) => (
                    <li
                        key={idx}
                        className={`suggestion-item ${idx === activeIndex ? 'suggestion-item-active' : ''}`}
                        onMouseEnter={() => setActiveIndex(idx)}
                        onClick={() => onSelect(item.suggestion)}
                    >
                        <span className="suggestion-text">{item.suggestion}</span>
                        <div className="confidence-bar-wrapper">
                            <div
                                className="confidence-bar-fill"
                                style={{ width: `${Math.round((item.confidence || 0) * 100)}%` }}
                            />
                        </div>
                    </li>
                ))}
            </ul>
        </div>
    );
}
