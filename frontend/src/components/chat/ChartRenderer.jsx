import { useState, useRef } from 'react';

/**
 * ChartRenderer — renders inline base64 PNG charts with Download + Expand.
 *
 * Props:
 *   base64Chart  — base64-encoded PNG string (no prefix)
 *   explanation  — AI-generated insight text
 *   title        — optional chart title
 */
export default function ChartRenderer({ base64Chart, explanation, title = 'Chart' }) {
    const [expanded, setExpanded] = useState(false);
    const imgRef = useRef(null);

    if (!base64Chart) return null;

    const src = base64Chart.startsWith('data:')
        ? base64Chart
        : `data:image/png;base64,${base64Chart}`;

    const handleDownload = () => {
        const a = document.createElement('a');
        a.href = src;
        a.download = `${title.replace(/\s+/g, '_')}.png`;
        a.click();
    };

    return (
        <>
            <div className="chart-renderer">
                <div className="chart-header">
                    <span className="chart-icon">📊</span>
                    <span className="chart-title">{title}</span>
                </div>

                <div className="chart-image-wrapper">
                    <img
                        ref={imgRef}
                        src={src}
                        alt={title}
                        className="chart-image"
                        onClick={() => setExpanded(true)}
                    />
                </div>

                <div className="chart-actions">
                    <button className="chart-btn" onClick={handleDownload} title="Download PNG">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                        Download
                    </button>
                    <button className="chart-btn" onClick={() => setExpanded(true)} title="Expand">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                        </svg>
                        Expand
                    </button>
                </div>

                {explanation && (
                    <div className="chart-insight">
                        <span className="chart-insight-icon">💡</span>
                        <div className="chart-insight-text">
                            <strong>Insight:</strong> {explanation}
                        </div>
                    </div>
                )}
            </div>

            {/* Full-size modal */}
            {expanded && (
                <div className="chart-modal-backdrop" onClick={() => setExpanded(false)}>
                    <div className="chart-modal" onClick={(e) => e.stopPropagation()}>
                        <button className="chart-modal-close" onClick={() => setExpanded(false)}>✕</button>
                        <img src={src} alt={title} className="chart-modal-image" />
                        {explanation && (
                            <div className="chart-modal-insight">
                                <strong>💡 Insight:</strong> {explanation}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </>
    );
}
