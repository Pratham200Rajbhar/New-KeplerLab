import { useState, useRef, useEffect, useCallback } from 'react';
import Modal from './Modal';

// Slide dimensions — must match backend SLIDE_WIDTH / SLIDE_HEIGHT
const SLIDE_W = 1920;
const SLIDE_H = 1080;

// ─── Responsive scale hook ────────────────────────────────────────────────────
// Watches a container element and returns the CSS scale factor needed to fit
// a 1920×1080 slide inside it while preserving the 16:9 aspect ratio.

function useSlideScale(containerRef) {
    const [scale, setScale] = useState(1);

    useEffect(() => {
        const el = containerRef.current;
        if (!el) return;

        const update = () => {
            const w = el.clientWidth  || el.offsetWidth  || SLIDE_W;
            const h = el.clientHeight || el.offsetHeight || (w * 9 / 16);
            const scaleW = w / SLIDE_W;
            const scaleH = h / SLIDE_H;
            setScale(Math.min(scaleW, scaleH));
        };

        update();
        const ro = new ResizeObserver(update);
        ro.observe(el);
        return () => ro.disconnect();
    }, [containerRef]);

    return scale;
}

// ─── Single slide rendered inside a scaled iframe ────────────────────────────

function SlideFrame({ slideHtml, label, scale, animClass = '' }) {
    const iframeRef = useRef(null);

    // srcdoc is the cleanest way to embed HTML without a URL.
    // sandbox="allow-same-origin" keeps styles/layout but blocks scripts.
    return (
        <div
            className={`pv-slide-canvas-wrap ${animClass}`}
            style={{
                width:  SLIDE_W * scale,
                height: SLIDE_H * scale,
                position: 'relative',
                overflow: 'hidden',
                borderRadius: scale < 0.9 ? 8 : 0,
                boxShadow: scale < 0.9 ? '0 4px 32px rgba(0,0,0,0.5)' : 'none',
                background: '#000',
            }}
        >
            <iframe
                ref={iframeRef}
                title={label}
                srcDoc={slideHtml}
                sandbox="allow-same-origin"
                scrolling="no"
                style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width:  SLIDE_W,
                    height: SLIDE_H,
                    border: 'none',
                    transformOrigin: 'top left',
                    transform: `scale(${scale})`,
                    display: 'block',
                    background: 'transparent',
                    pointerEvents: 'none',   // let the parent handle all clicks
                }}
            />
        </div>
    );
}

// ─── Thumbnail slide (smaller scale, lighter weight) ─────────────────────────

function SlideThumbnail({ slideHtml, slideNumber, isActive, onClick }) {
    const thumbScale = 200 / SLIDE_W;   // ~200px wide thumbnails
    return (
        <button
            className={`pv-overview-item${isActive ? ' active' : ''}`}
            onClick={onClick}
            title={`Slide ${slideNumber}`}
            style={{ width: 200, height: 200 * (SLIDE_H / SLIDE_W), background: 'transparent', padding: 0, border: 'none' }}
        >
            <div style={{
                width: SLIDE_W * thumbScale,
                height: SLIDE_H * thumbScale,
                overflow: 'hidden',
                position: 'relative',
                pointerEvents: 'none',
            }}>
                <iframe
                    title={`Thumb ${slideNumber}`}
                    srcDoc={slideHtml}
                    sandbox="allow-same-origin"
                    scrolling="no"
                    style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        width: SLIDE_W,
                        height: SLIDE_H,
                        border: 'none',
                        transformOrigin: 'top left',
                        transform: `scale(${thumbScale})`,
                        display: 'block',
                        pointerEvents: 'none',
                    }}
                />
            </div>
            <div className="pv-overview-num">{slideNumber}</div>
        </button>
    );
}

// ─── Main Presentation Viewer ─────────────────────────────────────────────────

export default function InlinePresentationView({ data, onRegenerate, loading }) {
    const [current, setCurrent] = useState(1);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [showOverview, setShowOverview] = useState(false);
    const [showDownload, setShowDownload] = useState(false);
    const [slideDirection, setSlideDirection] = useState('');
    const [animating, setAnimating] = useState(false);
    const containerRef = useRef(null);
    const stageRef = useRef(null);
    const downloadRef = useRef(null);

    const title = data?.title || 'Presentation';
    const slideCount = data?.slide_count || 0;
    const theme = data?.theme || '';
    const slides = data?.slides || [];   // [{slide_number, slide_id, html}]
    const fullHtml = data?.html || '';

    // Calculate scale to fit 1920×1080 into the stage area
    const scale = useSlideScale(stageRef);

    const currentSlide = slides[current - 1];

    const navigateTo = useCallback((num, dir = '') => {
        if (num < 1 || num > slideCount || animating) return;
        setSlideDirection(dir);
        setCurrent(num);
        setAnimating(true);
        setTimeout(() => setAnimating(false), 250);
    }, [slideCount, animating]);

    const next = useCallback(() => navigateTo(current + 1, 'left'),  [current, navigateTo]);
    const prev = useCallback(() => navigateTo(current - 1, 'right'), [current, navigateTo]);

    // Keyboard navigation
    useEffect(() => {
        const handler = (e) => {
            if (showOverview) return;
            switch (e.key) {
                case 'ArrowRight': case ' ': e.preventDefault(); next(); break;
                case 'ArrowLeft':  e.preventDefault(); prev(); break;
                case 'Home':       e.preventDefault(); navigateTo(1); break;
                case 'End':        e.preventDefault(); navigateTo(slideCount); break;
                case 'Escape':
                    if (isFullscreen) document.exitFullscreen();
                    setShowOverview(false);
                    setShowDownload(false);
                    break;
                default: break;
            }
        };
        document.addEventListener('keydown', handler);
        return () => document.removeEventListener('keydown', handler);
    }, [next, prev, navigateTo, slideCount, isFullscreen, showOverview]);

    // Close dropdown on outside click
    useEffect(() => {
        const handler = (e) => {
            if (downloadRef.current && !downloadRef.current.contains(e.target)) {
                setShowDownload(false);
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, []);

    // Fullscreen
    const toggleFullscreen = useCallback(() => {
        if (!document.fullscreenElement) {
            containerRef.current?.requestFullscreen();
        } else {
            document.exitFullscreen();
        }
    }, []);

    useEffect(() => {
        const handler = () => setIsFullscreen(!!document.fullscreenElement);
        document.addEventListener('fullscreenchange', handler);
        return () => document.removeEventListener('fullscreenchange', handler);
    }, []);

    // ── Download handlers ──────────────────────────────────────────────────────

    const handleDownloadHTML = useCallback(() => {
        if (!fullHtml) return;
        const blob = new Blob([fullHtml], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${title.replace(/\s+/g, '_')}.html`;
        a.click();
        URL.revokeObjectURL(url);
        setShowDownload(false);
    }, [fullHtml, title]);

    const handleDownloadSlideHTML = useCallback(() => {
        if (!currentSlide?.html) return;
        const blob = new Blob([currentSlide.html], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${title.replace(/\s+/g, '_')}_slide${current}.html`;
        a.click();
        URL.revokeObjectURL(url);
        setShowDownload(false);
    }, [currentSlide, title, current]);

    const handleOpenFullscreen = useCallback(() => {
        if (!fullHtml) return;
        const blob = new Blob([fullHtml], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        const win = window.open(url, '_blank');
        if (win) {
            // Revoke the URL after the window loads
            win.addEventListener('load', () => URL.revokeObjectURL(url), { once: true });
        }
        setShowDownload(false);
    }, [fullHtml]);

    // ── Empty state ────────────────────────────────────────────────────────────
    if (!slides.length) {
        return (
            <div className="pv-empty">
                <svg width="48" height="48" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                        d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                <p>No presentation data</p>
            </div>
        );
    }

    return (
        <>
            <style>{`
                .pv-root {
                    display: flex;
                    flex-direction: column;
                    background: #0b0d13;
                    border: 1px solid rgba(255,255,255,0.08);
                    border-radius: 12px;
                    overflow: hidden;
                    user-select: none;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.25);
                }
                .pv-root.pv-fullscreen {
                    position: fixed;
                    inset: 0;
                    z-index: 9999;
                    border-radius: 0;
                    border: none;
                }
                .pv-fullscreen .pv-header,
                .pv-fullscreen .pv-footer {
                    display: none;
                }
                .pv-header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 14px 20px;
                    background: rgba(26,29,46,0.5);
                    border-bottom: 1px solid rgba(255,255,255,0.05);
                    flex-shrink: 0;
                }
                .pv-header-title {
                    font-weight: 600;
                    font-size: 15px;
                    color: #f8fafc;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }
                .pv-header-meta {
                    font-size: 12px;
                    color: #94a3b8;
                    margin-top: 3px;
                }
                .pv-header-actions {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    flex-shrink: 0;
                }
                .pv-icon-btn {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    width: 32px;
                    height: 32px;
                    border-radius: 8px;
                    background: rgba(255,255,255,0.05);
                    border: 1px solid transparent;
                    color: #cbd5e1;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }
                .pv-icon-btn:hover {
                    background: rgba(255,255,255,0.1);
                    color: #fff;
                }
                .pv-icon-btn.active {
                    background: rgba(99,102,241,0.2);
                    border-color: rgba(99,102,241,0.4);
                    color: #818cf8;
                }
                /* Stage: fills all remaining space */
                .pv-stage {
                    flex: 1;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: #0b0d13;
                    padding: 16px;
                    overflow: hidden;
                    position: relative;
                    min-height: 0;
                }
                .pv-fullscreen .pv-stage {
                    padding: 0;
                }
                /* Slide wrapper: exact aspect-ratio box for the scale calc */
                .pv-slide-wrapper {
                    flex: 1;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    width: 100%;
                    height: 100%;
                    position: relative;
                    min-height: 0;
                }
                .pv-slide-canvas-wrap {
                    display: block;
                    flex-shrink: 0;
                }
                @keyframes slideFromLeft {
                    from { opacity: 0; transform: translateX(-40px); }
                    to   { opacity: 1; transform: translateX(0); }
                }
                @keyframes slideFromRight {
                    from { opacity: 0; transform: translateX(40px); }
                    to   { opacity: 1; transform: translateX(0); }
                }
                .pv-slide-enter-left  { animation: slideFromLeft  0.22s cubic-bezier(0.2,0.8,0.2,1) forwards; }
                .pv-slide-enter-right { animation: slideFromRight 0.22s cubic-bezier(0.2,0.8,0.2,1) forwards; }
                .pv-hover-arrow {
                    position: absolute;
                    top: 50%;
                    transform: translateY(-50%);
                    width: 48px;
                    height: 48px;
                    border-radius: 24px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: rgba(0,0,0,0.5);
                    backdrop-filter: blur(8px);
                    border: 1px solid rgba(255,255,255,0.1);
                    color: white;
                    cursor: pointer;
                    opacity: 0;
                    z-index: 10;
                    transition: all 0.2s;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                }
                .pv-hover-arrow.left  { left: 16px; }
                .pv-hover-arrow.right { right: 16px; }
                .pv-slide-wrapper:hover .pv-hover-arrow { opacity: 1; }
                .pv-hover-arrow:hover {
                    background: rgba(99,102,241,0.9);
                    border-color: #818cf8;
                    transform: translateY(-50%) scale(1.1);
                }
                .pv-footer {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 12px 20px;
                    background: rgba(26,29,46,0.6);
                    border-top: 1px solid rgba(255,255,255,0.06);
                    flex-shrink: 0;
                }
                .pv-counter {
                    font-size: 13px;
                    font-weight: 600;
                    color: #94a3b8;
                    background: rgba(0,0,0,0.3);
                    border: 1px solid rgba(255,255,255,0.05);
                    padding: 6px 14px;
                    border-radius: 8px;
                    letter-spacing: 0.05em;
                }
                .pv-nav-btn {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding: 8px 16px;
                    border-radius: 8px;
                    background: rgba(255,255,255,0.05);
                    color: #e2e8f0;
                    font-size: 13px;
                    font-weight: 500;
                    cursor: pointer;
                    transition: all 0.2s;
                    border: 1px solid transparent;
                }
                .pv-nav-btn:hover:not(:disabled) {
                    background: rgba(255,255,255,0.1);
                    color: #fff;
                    transform: translateY(-1px);
                }
                .pv-nav-btn:disabled { opacity: 0.3; cursor: not-allowed; }
                /* Overview */
                .pv-overview {
                    position: absolute;
                    inset: 0;
                    background: rgba(3,4,7,0.95);
                    backdrop-filter: blur(10px);
                    z-index: 20;
                    display: flex;
                    flex-direction: column;
                    overflow: hidden;
                    border-radius: inherit;
                }
                .pv-overview-header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 16px 24px;
                    border-bottom: 1px solid rgba(255,255,255,0.06);
                    flex-shrink: 0;
                }
                .pv-overview-title { font-size: 16px; font-weight: 600; color: #f8fafc; }
                .pv-overview-grid {
                    flex: 1;
                    overflow-y: auto;
                    display: grid;
                    gap: 16px;
                    padding: 24px;
                    align-content: start;
                    scrollbar-width: thin;
                    scrollbar-color: rgba(255,255,255,0.1) transparent;
                }
                .pv-overview-item {
                    border-radius: 8px;
                    overflow: hidden;
                    border: 2px solid transparent;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    position: relative;
                    background: rgba(255,255,255,0.04);
                }
                .pv-overview-item:hover { border-color: rgba(99,102,241,0.5); transform: translateY(-3px); }
                .pv-overview-item.active { border-color: #6366f1; box-shadow: 0 0 0 2px rgba(99,102,241,0.4); }
                .pv-overview-num {
                    position: absolute;
                    bottom: 6px;
                    right: 8px;
                    font-size: 11px;
                    font-weight: 700;
                    background: rgba(0,0,0,0.85);
                    color: rgba(255,255,255,0.95);
                    padding: 3px 8px;
                    border-radius: 6px;
                    pointer-events: none;
                }
                /* Download dropdown */
                .pv-download-wrap { position: relative; }
                .pv-dropdown {
                    position: absolute;
                    bottom: calc(100% + 12px);
                    right: 0;
                    background: #1e2235;
                    border: 1px solid rgba(255,255,255,0.1);
                    border-radius: 12px;
                    padding: 8px;
                    min-width: 210px;
                    box-shadow: 0 24px 60px rgba(0,0,0,0.6);
                    z-index: 50;
                    animation: dropUp 0.2s cubic-bezier(0.2,0.8,0.2,1);
                }
                @keyframes dropUp {
                    from { opacity: 0; transform: translateY(10px) scale(0.95); }
                    to   { opacity: 1; transform: translateY(0)    scale(1); }
                }
                .pv-dropdown-item {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    width: 100%;
                    padding: 10px 14px;
                    border-radius: 8px;
                    color: rgba(255,255,255,0.85);
                    font-size: 13px;
                    cursor: pointer;
                    transition: all 0.15s;
                    background: transparent;
                    border: none;
                    text-align: left;
                }
                .pv-dropdown-item:hover { background: rgba(99,102,241,0.2); color: #fff; }
                .pv-dropdown-item-icon {
                    width: 32px; height: 32px;
                    border-radius: 8px;
                    display: flex; align-items: center; justify-content: center;
                    flex-shrink: 0;
                }
                .pv-dropdown-divider { height: 1px; background: rgba(255,255,255,0.06); margin: 6px 0; }
                .pv-dropdown-label { font-weight: 600; }
                .pv-dropdown-sub { font-size: 11px; color: rgba(255,255,255,0.45); }
                .pv-empty {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    gap: 16px;
                    height: 240px;
                    color: rgba(255,255,255,0.4);
                    font-size: 15px;
                    background: rgba(255,255,255,0.02);
                    border-radius: 12px;
                    border: 1px dashed rgba(255,255,255,0.1);
                }
            `}</style>

            <div ref={containerRef} className={`pv-root${isFullscreen ? ' pv-fullscreen' : ''}`}>

                {/* ── Header ── */}
                <div className="pv-header">
                    <div style={{ flex: 1, minWidth: 0 }}>
                        <div className="pv-header-title" title={title}>{title}</div>
                        <div className="pv-header-meta">
                            {slideCount} slides{theme ? ` · ${theme}` : ''}
                        </div>
                    </div>
                    <div className="pv-header-actions">
                        {onRegenerate && (
                            <button
                                className="pv-nav-btn"
                                onClick={onRegenerate}
                                style={{ padding: '6px 12px', background: 'rgba(99,102,241,0.1)', color: '#a5b4fc', borderColor: 'rgba(99,102,241,0.2)' }}
                            >
                                <RegenerateIcon /> <span style={{ fontSize: 12 }}>Regenerate</span>
                            </button>
                        )}
                    </div>
                </div>

                {/* ── Stage ── */}
                <div className="pv-stage">
                    {/* Overview overlay */}
                    {showOverview && (
                        <div className="pv-overview">
                            <div className="pv-overview-header">
                                <span className="pv-overview-title">{title} — {slideCount} slides</span>
                                <button className="pv-icon-btn" onClick={() => setShowOverview(false)} title="Close">
                                    <CloseIcon />
                                </button>
                            </div>
                            <div
                                className="pv-overview-grid"
                                style={{ gridTemplateColumns: `repeat(${Math.min(4, Math.ceil(Math.sqrt(slideCount)))}, 1fr)` }}
                            >
                                {slides.map((slide) => (
                                    <SlideThumbnail
                                        key={slide.slide_number}
                                        slideHtml={slide.html}
                                        slideNumber={slide.slide_number}
                                        isActive={slide.slide_number === current}
                                        onClick={() => { setCurrent(slide.slide_number); setShowOverview(false); }}
                                    />
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Main slide area */}
                    <div className="pv-slide-wrapper" ref={stageRef}>
                        {current > 1 && (
                            <button className="pv-hover-arrow left" onClick={prev} title="Previous">
                                <ChevronLeft size={24} />
                            </button>
                        )}
                        {current < slideCount && (
                            <button className="pv-hover-arrow right" onClick={next} title="Next">
                                <ChevronRight size={24} />
                            </button>
                        )}

                        {currentSlide?.html ? (
                            <SlideFrame
                                key={current}
                                slideHtml={currentSlide.html}
                                label={`Slide ${current} of ${slideCount}`}
                                scale={scale}
                                animClass={
                                    slideDirection === 'left'  ? 'pv-slide-enter-left' :
                                    slideDirection === 'right' ? 'pv-slide-enter-right' : ''
                                }
                            />
                        ) : (
                            <div style={{
                                width: SLIDE_W * scale,
                                height: SLIDE_H * scale,
                                background: 'linear-gradient(135deg,#1e2235,#0e1020)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                color: 'rgba(255,255,255,0.4)',
                                fontSize: 14,
                                borderRadius: 8,
                            }}>
                                Slide {current} unavailable
                            </div>
                        )}
                    </div>
                </div>

                {/* ── Footer ── */}
                <div className="pv-footer">
                    {/* Counter */}
                    <div style={{ display: 'flex', alignItems: 'center', flex: 1 }}>
                        <span className="pv-counter">Slide {current} of {slideCount}</span>
                    </div>

                    {/* Nav buttons */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, flex: 1 }}>
                        <button className="pv-nav-btn" onClick={prev} disabled={current <= 1}>
                            <ChevronLeft size={16} /> Prev
                        </button>
                        <button className="pv-nav-btn" onClick={next} disabled={current >= slideCount}>
                            Next <ChevronRight size={16} />
                        </button>
                    </div>

                    {/* Actions */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 8, flex: 1 }}>
                        <button
                            className={`pv-icon-btn${showOverview ? ' active' : ''}`}
                            onClick={() => setShowOverview(v => !v)}
                            title="Slide overview"
                        >
                            <GridIcon />
                        </button>

                        {/* Open in new tab (full-screen HTML viewer / print-to-PDF) */}
                        <button className="pv-icon-btn" onClick={handleOpenFullscreen} title="Open in new tab (for presentation / print to PDF)">
                            <OpenTabIcon />
                        </button>

                        {/* Download dropdown */}
                        <div ref={downloadRef} className="pv-download-wrap">
                            <button
                                className="pv-icon-btn"
                                onClick={() => setShowDownload(v => !v)}
                                title="Download"
                                style={showDownload ? { background: 'rgba(99,102,241,0.2)', color: '#a5b4fc', borderColor: 'rgba(99,102,241,0.4)' } : {}}
                            >
                                <DownloadIcon />
                            </button>

                            {showDownload && (
                                <div className="pv-dropdown">
                                    <button className="pv-dropdown-item" onClick={handleDownloadHTML}>
                                        <div className="pv-dropdown-item-icon" style={{ background: 'rgba(249,115,22,0.15)' }}>
                                            <HtmlIcon />
                                        </div>
                                        <div>
                                            <div className="pv-dropdown-label">Full Presentation</div>
                                            <div className="pv-dropdown-sub">HTML · all slides</div>
                                        </div>
                                    </button>
                                    <div className="pv-dropdown-divider" />
                                    <button className="pv-dropdown-item" onClick={handleDownloadSlideHTML} disabled={!currentSlide?.html}>
                                        <div className="pv-dropdown-item-icon" style={{ background: 'rgba(16,185,129,0.15)' }}>
                                            <SlideIcon />
                                        </div>
                                        <div>
                                            <div className="pv-dropdown-label">Current Slide</div>
                                            <div className="pv-dropdown-sub">HTML · slide {current}</div>
                                        </div>
                                    </button>
                                </div>
                            )}
                        </div>

                        <button className="pv-icon-btn" onClick={toggleFullscreen} title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}>
                            {isFullscreen ? <ExitFullscreenIcon /> : <FullscreenIcon />}
                        </button>
                    </div>
                </div>
            </div>
        </>
    );
}

// ─── Presentation Config Modal Dialog ────────────────────────────────────────

export function PresentationConfigDialog({ onGenerate, onCancel, loading }) {
    const [maxSlides, setMaxSlides] = useState('');
    const [theme, setTheme] = useState('');
    const [additionalInstructions, setAdditionalInstructions] = useState('');

    const themePresets = [
        { label: '🌑 Dark Modern', value: 'Dark modern theme with gradient backgrounds, deep blues and purples' },
        { label: '☁️ Light Clean', value: 'Light minimalist theme with white backgrounds, soft shadows, and blue accents' },
        { label: '⚡ Neon', value: 'Dark theme with neon glow effects, cyberpunk style, vibrant greens and pinks' },
        { label: '🏢 Corporate', value: 'Professional corporate theme with navy blue and white, clean lines' },
        { label: '🌿 Nature', value: 'Earthy warm theme with greens, browns, and natural tones' },
    ];

    const handleSubmit = (e) => {
        e.preventDefault();
        // If nothing is filled, AI decides everything
        onGenerate({
            maxSlides: maxSlides ? parseInt(maxSlides, 10) : null,
            theme: theme.trim() || null,
            additionalInstructions: additionalInstructions.trim() || null,
        });
    };

    const modalIcon = (
        <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
    );

    return (
        <Modal
            isOpen={true}
            onClose={onCancel}
            title="Presentation Options"
            icon={modalIcon}
            maxWidth="max-w-xl"
            showClose={!loading}
        >
            <p className="text-sm text-text-muted mb-6 leading-relaxed">
                Customize your presentation or leave empty for AI to decide everything automatically.
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
                {/* Slide count */}
                <div className="form-group">
                    <label className="form-label">
                        Number of Slides <span className="form-label-hint">(optional, 3–60)</span>
                    </label>
                    <input
                        type="number"
                        min="3"
                        max="60"
                        value={maxSlides}
                        onChange={e => setMaxSlides(e.target.value)}
                        placeholder="AI decides (typically 8-12 slides)"
                        className="input"
                        disabled={loading}
                    />
                </div>

                {/* Theme */}
                <div className="form-group">
                    <label className="form-label">
                        Visual Theme <span className="form-label-hint">(optional)</span>
                    </label>
                    <div className="chip-group">
                        {themePresets.map(p => (
                            <button
                                key={p.label}
                                type="button"
                                className={`chip${theme === p.value ? ' selected' : ''}`}
                                onClick={() => setTheme(t => t === p.value ? '' : p.value)}
                                disabled={loading}
                            >
                                {p.label}
                            </button>
                        ))}
                    </div>
                    <input
                        type="text"
                        value={theme}
                        onChange={e => setTheme(e.target.value)}
                        placeholder="Or describe your own theme..."
                        className="input"
                        disabled={loading}
                    />
                </div>

                {/* Instructions */}
                <div className="form-group">
                    <label className="form-label">
                        Additional Instructions <span className="form-label-hint">(optional)</span>
                    </label>
                    <textarea
                        value={additionalInstructions}
                        onChange={e => setAdditionalInstructions(e.target.value)}
                        placeholder="e.g. Focus on key statistics, make it executive-level, include comparison tables…"
                        rows={3}
                        className="textarea"
                        disabled={loading}
                    />
                </div>

                {/* Action buttons */}
                <div className="flex flex-col gap-2 pt-2">
                    <button type="submit" className="btn-primary w-full" disabled={loading}>
                        {loading ? (
                            <>
                                <div className="loading-spinner w-4 h-4" />
                                Generating Presentation…
                            </>
                        ) : (
                            <>
                                <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                </svg>
                                Generate Presentation
                            </>
                        )}
                    </button>

                    <button
                        type="button"
                        className="btn-secondary w-full"
                        onClick={onCancel}
                        disabled={loading}
                    >
                        Cancel
                    </button>
                </div>
            </form>
        </Modal>
    );
}

// ─── Icon Components ──────────────────────────────────────────────────────────

const ChevronLeft = ({ size = 20 }) => (
    <svg width={size} height={size} fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" />
    </svg>
);

const ChevronRight = ({ size = 20 }) => (
    <svg width={size} height={size} fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5l7 7-7 7" />
    </svg>
);

const GridIcon = () => (
    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
    </svg>
);

const CloseIcon = () => (
    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
);

const FullscreenIcon = () => (
    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
    </svg>
);

const ExitFullscreenIcon = () => (
    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 9V4.5M9 9H4.5M9 9L3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5m0-4.5l5.25 5.25" />
    </svg>
);

const DownloadIcon = () => (
    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
    </svg>
);

const RegenerateIcon = () => (
    <svg width="15" height="15" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
    </svg>
);

const ImageOffIcon = () => (
    <svg width="32" height="32" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
);

const HtmlIcon = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f97316" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
        <polyline points="16 18 22 12 16 6" /><polyline points="8 6 2 12 8 18" />
    </svg>
);

const PdfIcon = () => (
    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="#ef4444" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" />
        <line x1="9" y1="15" x2="15" y2="15" /><line x1="9" y1="11" x2="15" y2="11" />
    </svg>
);

const PngIcon = () => (
    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="#10b981" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" /><circle cx="8.5" cy="8.5" r="1.5" />
        <polyline points="21 15 16 10 5 21" />
    </svg>
);

const SlideIcon = () => (
    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="#10b981" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
        <rect x="2" y="3" width="20" height="14" rx="2" />
        <line x1="8" y1="21" x2="16" y2="21" />
        <line x1="12" y1="17" x2="12" y2="21" />
    </svg>
);

const OpenTabIcon = () => (
    <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
        <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" />
        <polyline points="15 3 21 3 21 9" />
        <line x1="10" y1="14" x2="21" y2="3" />
    </svg>
);
