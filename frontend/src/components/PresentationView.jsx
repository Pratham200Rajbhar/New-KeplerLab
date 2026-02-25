import { useState, useRef, useEffect, useCallback } from 'react';
import { apiConfig, getAccessToken } from '../api/config';
import { jsPDF } from 'jspdf';
import Modal from './Modal';

// ─── Authenticated Image Fetcher ──────────────────────────────────────────────

function useSlideImages(slides) {
    const [blobUrls, setBlobUrls] = useState(new Map());
    const [errors, setErrors] = useState(new Set());
    const fetchingRef = useRef(new Set());
    const blobUrlsRef = useRef(blobUrls);

    // Keep ref in sync with state
    useEffect(() => {
        blobUrlsRef.current = blobUrls;
    }, [blobUrls]);

    const fetchImage = useCallback(async (slide) => {
        if (!slide?.url) return;
        const key = String(slide.slide_number);
        // Use ref to avoid stale closure — no dependency on blobUrls
        if (blobUrlsRef.current.has(key) || fetchingRef.current.has(key)) return;

        fetchingRef.current.add(key);
        try {
            const token = getAccessToken();
            if (!token) return;
            const res = await fetch(`${apiConfig.baseUrl}${slide.url}`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!res.ok) throw new Error(`${res.status}`);
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            setBlobUrls(prev => new Map(prev).set(key, url));
        } catch {
            setErrors(prev => new Set([...prev, slide.slide_number]));
        } finally {
            fetchingRef.current.delete(key);
        }
    }, []); // stable — no deps needed thanks to refs

    const getUrl = useCallback((slide) => {
        if (!slide) return null;
        return blobUrls.get(String(slide.slide_number)) || null;
    }, [blobUrls]);

    // Cleanup on unmount — use ref to get latest blob URLs
    useEffect(() => () => {
        blobUrlsRef.current.forEach(url => URL.revokeObjectURL(url));
    }, []);

    return { fetchImage, getUrl, errors };
}

// ─── Main Presentation Viewer ─────────────────────────────────────────────────

export default function InlinePresentationView({ data, onRegenerate, loading }) {
    const [current, setCurrent] = useState(1);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [showOverview, setShowOverview] = useState(false);
    const [showDownload, setShowDownload] = useState(false);
    const [slideDirection, setSlideDirection] = useState(''); // 'left' | 'right'
    const [animating, setAnimating] = useState(false);
    const containerRef = useRef(null);
    const downloadRef = useRef(null);

    const title = data?.title || 'Presentation';
    const slideCount = data?.slide_count || 0;
    const theme = data?.theme || '';
    const slides = data?.slides || [];

    const { fetchImage, getUrl, errors } = useSlideImages(slides);

    // Preload current + neighbors
    useEffect(() => {
        if (!slides.length) return;
        const toLoad = slides.slice(Math.max(0, current - 2), Math.min(slides.length, current + 3));
        toLoad.forEach(fetchImage);
    }, [slides, current, fetchImage]);

    // Preload all thumbnails
    useEffect(() => {
        slides.forEach(fetchImage);
    }, [slides, fetchImage]);

    const navigateTo = useCallback((num, dir = '') => {
        if (num < 1 || num > slideCount || animating) return;
        setSlideDirection(dir);
        setCurrent(num);
        setAnimating(true);
        // tiny lock to prevent accidental double-clicks during CSS entrance
        setTimeout(() => setAnimating(false), 250);
    }, [slideCount, animating]);

    const next = useCallback(() => navigateTo(current + 1, 'left'), [current, navigateTo]);
    const prev = useCallback(() => navigateTo(current - 1, 'right'), [current, navigateTo]);

    // Keyboard nav
    useEffect(() => {
        const handler = (e) => {
            if (showOverview) return;
            switch (e.key) {
                case 'ArrowRight': case ' ': e.preventDefault(); next(); break;
                case 'ArrowLeft': e.preventDefault(); prev(); break;
                case 'Home': e.preventDefault(); navigateTo(1); break;
                case 'End': e.preventDefault(); navigateTo(slideCount); break;
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

    // Close dropdown when clicking outside
    useEffect(() => {
        const handler = (e) => {
            if (downloadRef.current && !downloadRef.current.contains(e.target)) {
                setShowDownload(false);
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, []);

    // Fullscreen sync
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

    // ── Download Handlers ──────────────────────────────────────────────────────

    const handleDownloadHTML = useCallback(() => {
        if (!data?.html) return;
        const blob = new Blob([data.html], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${title.replace(/\s+/g, '_')}.html`;
        a.click();
        URL.revokeObjectURL(url);
        setShowDownload(false);
    }, [data?.html, title]);

    const handleDownloadPDF = useCallback(async () => {
        if (!slides.length) return;
        setShowDownload(false);

        // Build PDF using jsPDF — 16:9 landscape
        const doc = new jsPDF({ orientation: 'landscape', unit: 'px', format: [960, 540] });

        for (let i = 0; i < slides.length; i++) {
            const slide = slides[i];
            let url = getUrl(slide);

            // Ensure the slide is fetched
            if (!url) {
                await fetchImage(slide);
                // wait a tick
                await new Promise(r => setTimeout(r, 200));
                url = getUrl(slide);
            }

            if (url) {
                if (i > 0) doc.addPage([960, 540], 'landscape');
                doc.addImage(url, 'PNG', 0, 0, 960, 540);
            }
        }

        doc.save(`${title.replace(/\s+/g, '_')}.pdf`);
    }, [slides, getUrl, fetchImage, title]);

    const handleDownloadPNG = useCallback(() => {
        const slide = slides[current - 1];
        const url = getUrl(slide);
        if (!url) return;
        const a = document.createElement('a');
        a.href = url;
        a.download = `${title.replace(/\s+/g, '_')}_slide${current}.png`;
        a.click();
        setShowDownload(false);
    }, [slides, current, getUrl, title]);


    // ── Slide image for current ────────────────────────────────────────────────
    const currentSlide = slides[current - 1];
    const currentUrl = getUrl(currentSlide);
    const hasError = errors.has(current);

    if (!slides.length) {
        return (
            <div className="pv-empty">
                <svg width="48" height="48" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
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
                .pv-stage {
                    flex: 1;
                    display: flex;
                    position: relative;
                    background: #000;
                    padding: 0;
                    margin: 0;
                    overflow: hidden;
                }
                .pv-fullscreen .pv-stage {
                    padding: 0;
                }
                .pv-slide-wrapper {
                    flex: 1;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    position: relative;
                    width: 100%;
                    height: 100%;
                    margin: 0;
                    padding: 0;
                }
                .pv-fullscreen .pv-slide-wrapper {
                    max-width: none;
                }
                .pv-slide-container {
                    position: relative;
                    width: 100%;
                    height: 100%;
                    overflow: hidden;
                    background: #000;
                }
                .pv-fullscreen .pv-slide-container {
                    border-radius: 0;
                    box-shadow: none;
                }
                .pv-slide-img {
                    width: 100%;
                    height: 100%;
                    object-fit: contain;
                    display: block;
                }
                @keyframes slideFromLeft {
                    from { opacity: 0; transform: translateX(-40px); }
                    to   { opacity: 1; transform: translateX(0); }
                }
                @keyframes slideFromRight {
                    from { opacity: 0; transform: translateX(40px); }
                    to   { opacity: 1; transform: translateX(0); }
                }
                .pv-slide-enter-left  { animation: slideFromLeft 0.25s cubic-bezier(0.2, 0.8, 0.2, 1) forwards; }
                .pv-slide-enter-right { animation: slideFromRight 0.25s cubic-bezier(0.2, 0.8, 0.2, 1) forwards; }
                .pv-slide-placeholder {
                    width: 100%;
                    height: 100%;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    gap: 16px;
                    background: linear-gradient(135deg, #1e2235 0%, #0e1020 100%);
                    color: rgba(255,255,255,0.5);
                    font-size: 14px;
                }
                .pv-footer {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 12px 20px;
                    background: rgba(26,29,46,0.6);
                    border-top: 1px solid rgba(255,255,255,0.06);
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
                    transition: all 0.2s ease;
                    border: 1px solid transparent;
                }
                .pv-nav-btn:hover:not(:disabled) {
                    background: rgba(255,255,255,0.1);
                    color: #fff;
                    transform: translateY(-1px);
                }
                .pv-nav-btn:disabled {
                    opacity: 0.3;
                    cursor: not-allowed;
                }
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
                    transition: all 0.2s cubic-bezier(0.2, 0.8, 0.2, 1);
                    z-index: 10;
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
                    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
                }
                .pv-overview-item:hover { border-color: rgba(99,102,241,0.5); transform: translateY(-3px); }
                .pv-overview-item.active { border-color: #6366f1; box-shadow: 0 0 0 2px rgba(99,102,241,0.4); }
                .pv-overview-item img { width: 100%; aspect-ratio: 16/9; object-fit: cover; display: block; }
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
                    box-shadow: 0 2px 4px rgba(0,0,0,0.5);
                }
                .pv-download-wrap { position: relative; }
                .pv-dropdown {
                    position: absolute;
                    bottom: calc(100% + 12px);
                    right: 0;
                    background: #1e2235;
                    border: 1px solid rgba(255,255,255,0.1);
                    border-radius: 12px;
                    padding: 8px;
                    min-width: 200px;
                    box-shadow: 0 24px 60px rgba(0,0,0,0.6);
                    z-index: 50;
                    animation: dropUp 0.2s cubic-bezier(0.2, 0.8, 0.2, 1);
                }
                @keyframes dropUp {
                    from { opacity: 0; transform: translateY(10px) scale(0.95); }
                    to   { opacity: 1; transform: translateY(0) scale(1); }
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
                    transition: all 0.15s ease;
                    background: transparent;
                    border: none;
                    text-align: left;
                }
                .pv-dropdown-item:hover { background: rgba(99,102,241,0.2); color: #fff; }
                .pv-dropdown-item-icon {
                    width: 32px;
                    height: 32px;
                    border-radius: 8px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    flex-shrink: 0;
                }
                .pv-dropdown-divider {
                    height: 1px;
                    background: rgba(255,255,255,0.06);
                    margin: 6px 0;
                }
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
                <div className="pv-header">
                    <div style={{ flex: 1, minWidth: 0 }}>
                        <div className="pv-header-title" title={title}>{title}</div>
                        <div className="pv-header-meta">
                            {slideCount} slides{theme ? ` · ${theme}` : ''}
                        </div>
                    </div>
                    {onRegenerate && (
                        <div className="pv-header-actions">
                            <button className="pv-nav-btn" onClick={onRegenerate} style={{ padding: '6px 12px', background: 'rgba(99,102,241,0.1)', color: '#a5b4fc', borderColor: 'rgba(99,102,241,0.2)' }}>
                                <RegenerateIcon /> <span style={{ fontSize: 12 }}>Regenerate</span>
                            </button>
                        </div>
                    )}
                </div>

                <div className="pv-stage">
                    {showOverview && (
                        <div className="pv-overview">
                            <div className="pv-overview-header">
                                <span className="pv-overview-title">{title} — {slideCount} slides</span>
                                <button className="pv-icon-btn" onClick={() => setShowOverview(false)} title="Close overview">
                                    <CloseIcon />
                                </button>
                            </div>
                            <div className="pv-overview-grid" style={{ gridTemplateColumns: `repeat(${Math.min(4, Math.ceil(Math.sqrt(slideCount)))}, 1fr)` }}>
                                {slides.map((slide, i) => {
                                    const n = i + 1;
                                    const url = getUrl(slide);
                                    return (
                                        <button key={n} className={`pv-overview-item${n === current ? ' active' : ''}`} onClick={() => { setCurrent(n); setShowOverview(false); }}>
                                            {url ? (
                                                <img src={url} alt={`Slide ${n}`} draggable={false} />
                                            ) : (
                                                <div style={{ width: '100%', aspectRatio: '16/9', background: 'rgba(255,255,255,0.04)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                                    <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)' }}>Loading…</span>
                                                </div>
                                            )}
                                            <div className="pv-overview-num">{n}</div>
                                        </button>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    <div className="pv-slide-wrapper">
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

                        <div className={`pv-slide-container${slideDirection === 'left' ? ' pv-slide-enter-left' : slideDirection === 'right' ? ' pv-slide-enter-right' : ''}`} key={current}>
                            {currentUrl && !hasError ? (
                                <img src={currentUrl} alt={`Slide ${current}`} className="pv-slide-img" draggable={false} />
                            ) : (
                                <div className="pv-slide-placeholder">
                                    {!hasError ? (
                                        <>
                                            <div className="pv-spinner" />
                                            <p>Loading slide…</p>
                                        </>
                                    ) : (
                                        <>
                                            <ImageOffIcon />
                                            <p>Slide {current} unavailable</p>
                                        </>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                <div className="pv-footer">
                    <div style={{ display: 'flex', alignItems: 'center', flex: 1 }}>
                        <span className="pv-counter">Slide {current} of {slideCount}</span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, flex: 1 }}>
                        <button className="pv-nav-btn" onClick={prev} disabled={current <= 1}>
                            <ChevronLeft size={16} /> Prev
                        </button>
                        <button className="pv-nav-btn" onClick={next} disabled={current >= slideCount}>
                            Next <ChevronRight size={16} />
                        </button>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 8, flex: 1 }}>
                        <button className={`pv-icon-btn${showOverview ? ' active' : ''}`} onClick={() => setShowOverview(v => !v)} title="Slide overview">
                            <GridIcon />
                        </button>

                        <div ref={downloadRef} className="pv-download-wrap">
                            <button className="pv-icon-btn" onClick={() => setShowDownload(v => !v)} title="Download" style={showDownload ? { background: 'rgba(99,102,241,0.2)', color: '#a5b4fc', borderColor: 'rgba(99,102,241,0.4)' } : {}}>
                                <DownloadIcon />
                            </button>

                            {showDownload && (
                                <div className="pv-dropdown">
                                    <button className="pv-dropdown-item" onClick={handleDownloadHTML}>
                                        <div className="pv-dropdown-item-icon" style={{ background: 'rgba(249,115,22,0.15)' }}><HtmlIcon /></div>
                                        <div><div className="pv-dropdown-label">HTML</div><div className="pv-dropdown-sub">Interactive file</div></div>
                                    </button>
                                    <div className="pv-dropdown-divider" />
                                    <button className="pv-dropdown-item" onClick={handleDownloadPDF}>
                                        <div className="pv-dropdown-item-icon" style={{ background: 'rgba(239,68,68,0.15)' }}><PdfIcon /></div>
                                        <div><div className="pv-dropdown-label">PDF</div><div className="pv-dropdown-sub">All slides</div></div>
                                    </button>
                                    <div className="pv-dropdown-divider" />
                                    <button className="pv-dropdown-item" onClick={handleDownloadPNG} disabled={!currentUrl}>
                                        <div className="pv-dropdown-item-icon" style={{ background: 'rgba(16,185,129,0.15)' }}><PngIcon /></div>
                                        <div><div className="pv-dropdown-label">PNG</div><div className="pv-dropdown-sub">Current slide</div></div>
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
