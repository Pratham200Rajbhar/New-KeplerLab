import { useState, useRef, useEffect } from 'react';
import { getBlockFollowup } from '../../api/chat';
import { MarkdownRenderer } from '../ChatMessage';

const LANG_OPTIONS = ['Spanish', 'French', 'German', 'Hindi', 'Chinese', 'Arabic', 'Portuguese', 'Japanese'];

/**
 * MiniBlockChat — inline slide-down mini chat anchored to a response block.
 *
 * Props:
 *   blockId    — ResponseBlock UUID from backend
 *   onClose    — called when dismissed
 *   action     — 'ask' | 'simplify' | 'translate' | 'explain' (default 'ask')
 *   lang       — target language when action='translate'
 */
export default function MiniBlockChat({ blockId, onClose, action = 'ask', lang = '' }) {
    const [question, setQuestion] = useState(
        action === 'simplify' ? 'Simplify this' :
            action === 'explain' ? 'Explain in more depth' :
                action === 'translate' ? `Translate to ${lang}` : ''
    );
    const [response, setResponse] = useState('');
    const [streaming, setStreaming] = useState(false);
    const inputRef = useRef(null);
    const containerRef = useRef(null);

    // Auto-run for non-ask actions
    useEffect(() => {
        if (action !== 'ask') {
            handleSend();
        } else {
            inputRef.current?.focus();
        }
    }, []);

    // Click outside → close
    useEffect(() => {
        const handler = (e) => {
            if (containerRef.current && !containerRef.current.contains(e.target)) {
                onClose?.();
            }
        };
        // Delay to avoid the click that opened it triggering close
        const timer = setTimeout(() => {
            document.addEventListener('mousedown', handler);
        }, 100);
        return () => {
            clearTimeout(timer);
            document.removeEventListener('mousedown', handler);
        };
    }, [onClose]);

    const handleSend = async (text = question) => {
        if (!text.trim() || streaming) return;
        setStreaming(true);
        setResponse('');

        try {
            const res = await getBlockFollowup(blockId, text, action);
            if (!res.body) throw new Error('No response');

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const parts = buffer.split('\n\n');
                buffer = parts.pop();

                for (const part of parts) {
                    const lines = part.split('\n');
                    let evt = '', dat = '';
                    for (const l of lines) {
                        if (l.startsWith('event: ')) evt = l.slice(7).trim();
                        else if (l.startsWith('data: ')) dat = l.slice(6).trim();
                    }
                    if (evt === 'token') {
                        try { setResponse((p) => p + (JSON.parse(dat).content || '')); } catch { /**/ }
                    }
                }
            }
        } catch (err) {
            setResponse('Error: ' + err.message);
        } finally {
            setStreaming(false);
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
        if (e.key === 'Escape') onClose?.();
    };

    return (
        <div ref={containerRef} className="mini-block-chat animate-slide-down">
            <div className="mini-block-chat-header">
                <span className="mini-block-chat-title">
                    {action === 'ask' ? '❓ Ask about this paragraph' :
                        action === 'simplify' ? '🔄 Simplifying...' :
                            action === 'translate' ? `🌍 Translating to ${lang}` :
                                '📚 Explaining in depth'}
                </span>
                <button className="mini-block-close-btn" onClick={onClose}>✕</button>
            </div>

            {action === 'ask' && !response && (
                <div className="mini-block-input-row">
                    <input
                        ref={inputRef}
                        className="mini-block-input"
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Ask something about this paragraph..."
                    />
                    <button
                        className="mini-block-send-btn"
                        onClick={() => handleSend()}
                        disabled={!question.trim() || streaming}
                    >
                        {streaming ? '⏳' : '↑'}
                    </button>
                </div>
            )}

            {(response || streaming) && (
                <div className="mini-block-response">
                    {streaming && !response && (
                        <div className="typing-indicator">
                            <span /><span /><span />
                        </div>
                    )}
                    <div className="mini-block-response-text markdown-content">
                        <MarkdownRenderer content={response} />
                    </div>
                    {!streaming && response && action === 'ask' && (
                        <div className="mini-block-actions-bar">
                            <button className="mini-block-btn" onClick={() => { setResponse(''); setQuestion(''); inputRef.current?.focus(); }}>Ask again</button>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
