/**
 * FileViewerPage — renders a public file URL in-browser without forcing download.
 *
 * Route: /view?url=<encoded-https-url>
 *
 * Strategy by extension:
 *   .pdf                          → iframe → backend proxy (Content-Disposition: inline)
 *   .docx .doc .xlsx .xls .pptx
 *   .ppt .odt .ods .odp          → MS Office Online Viewer iframe
 *   .txt .csv .md .rtf            → backend proxy (renders as plain text)
 *   other                         → download fallback card
 *
 * Security:
 *   - The URL is validated on the backend (/api/file-viewer/info) before any render
 *     (HTTPS-only, no private IPs).
 *   - The raw destination URL is never used as a redirect target.
 */

import { useEffect, useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const FILE_VIEWER_BASE = `${API_BASE}/api/v1`;

const OFFICE_EXTS = new Set(['.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt', '.odt', '.ods', '.odp']);
const PDF_EXTS   = new Set(['.pdf']);
const TEXT_EXTS  = new Set(['.txt', '.csv', '.md', '.rtf']);

function getExtension(url) {
    try {
        const path = new URL(url).pathname.toLowerCase();
        const dot = path.lastIndexOf('.');
        return dot !== -1 ? path.slice(dot) : '';
    } catch {
        return '';
    }
}

function getFilename(url) {
    try {
        const path = new URL(url).pathname;
        return path.split('/').filter(Boolean).pop() || 'file';
    } catch {
        return 'file';
    }
}

function getDomain(url) {
    try { return new URL(url).hostname.replace(/^www\./, ''); }
    catch { return url; }
}

// ── Sub-components ────────────────────────────────────────────────────────────

function TopBar({ filename, domain, fileUrl, onBack }) {
    return (
        <div className="h-12 flex-shrink-0 flex items-center gap-3 px-4 bg-[#191B21] border-b border-[#2A2D35] z-10">
            <button
                onClick={onBack}
                className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-white transition-colors group"
                title="Back"
            >
                <svg className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                <span className="hidden sm:inline">Back</span>
            </button>

            <div className="w-px h-5 bg-[#2A2D35]" />

            {/* Favicon + domain */}
            <img
                src={`https://www.google.com/s2/favicons?sz=32&domain=${domain}`}
                alt=""
                className="w-4 h-4 rounded-sm flex-shrink-0"
                onError={(e) => { e.target.style.display = 'none'; }}
            />
            <span className="text-xs text-gray-500 font-medium uppercase tracking-wide hidden sm:block">{domain}</span>

            <div className="w-px h-5 bg-[#2A2D35] hidden sm:block" />

            {/* Filename */}
            <span className="text-sm text-gray-200 truncate flex-1 min-w-0">{decodeURIComponent(filename)}</span>

            {/* Action buttons */}
            <div className="flex items-center gap-1.5 flex-shrink-0">
                <a
                    href={fileUrl}
                    download
                    className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs text-gray-400 hover:text-white hover:bg-[#2A2D35] transition-colors"
                    title="Download original"
                >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    <span className="hidden sm:inline">Download</span>
                </a>
                <a
                    href={fileUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs text-gray-400 hover:text-white hover:bg-[#2A2D35] transition-colors"
                    title="Open original URL"
                >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                    <span className="hidden sm:inline">Open Original</span>
                </a>
            </div>
        </div>
    );
}

function LoadingSpinner({ message = 'Loading…' }) {
    return (
        <div className="flex-1 flex flex-col items-center justify-center gap-4 text-gray-400">
            <div className="w-10 h-10 border-2 border-gray-600 border-t-blue-400 rounded-full animate-spin" />
            <p className="text-sm">{message}</p>
        </div>
    );
}

function ErrorCard({ message, fileUrl }) {
    return (
        <div className="flex-1 flex flex-col items-center justify-center gap-4 p-8">
            <div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
                <svg className="w-8 h-8 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
            </div>
            <div className="text-center max-w-sm">
                <h3 className="text-white font-semibold mb-1">Cannot display file</h3>
                <p className="text-sm text-gray-400">{message}</p>
            </div>
            {fileUrl && (
                <a
                    href={fileUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    download
                    className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#2A2D35] hover:bg-[#3A3F4B] text-gray-200 text-sm transition-colors"
                >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    Download file instead
                </a>
            )}
        </div>
    );
}

function OtherFileCard({ fileUrl, filename, ext }) {
    return (
        <div className="flex-1 flex flex-col items-center justify-center gap-5 p-8">
            <div className="w-20 h-20 rounded-2xl bg-[#2A2D35] border border-[#3A3F4B] flex items-center justify-center">
                <svg className="w-10 h-10 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
            </div>
            <div className="text-center">
                <h3 className="text-white font-semibold mb-1">{decodeURIComponent(filename)}</h3>
                <p className="text-sm text-gray-400">
                    {ext ? `${ext.slice(1).toUpperCase()} file` : 'File'} — cannot be previewed in the browser.
                </p>
            </div>
            <div className="flex gap-2">
                <a
                    href={fileUrl}
                    download
                    className="flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors"
                >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    Download
                </a>
                <a
                    href={fileUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#2A2D35] hover:bg-[#3A3F4B] text-gray-200 text-sm transition-colors"
                >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                    Open URL
                </a>
            </div>
        </div>
    );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function FileViewerPage() {
    const [searchParams] = useSearchParams();
    const rawUrl = searchParams.get('url') || '';

    const [state, setState] = useState('loading'); // loading | validating | ready | error
    const [errorMsg, setErrorMsg] = useState('');
    const [viewerInfo, setViewerInfo] = useState(null); // from /api/file-viewer/info
    const [iframeLoaded, setIframeLoaded] = useState(false);

    const handleBack = () => {
        if (window.history.length > 1) {
            window.history.back();
        } else {
            window.location.href = '/';
        }
    };

    const validateAndLoad = useCallback(async () => {
        if (!rawUrl) {
            setState('error');
            setErrorMsg('No file URL was provided. Add ?url=<encoded-url> to the address bar.');
            return;
        }

        // Quick client-side sanity check before hitting the API
        if (!rawUrl.startsWith('https://')) {
            setState('error');
            setErrorMsg('Only HTTPS file URLs are supported.');
            return;
        }

        setState('validating');
        try {
            const res = await fetch(`${FILE_VIEWER_BASE}/file-viewer/info?url=${encodeURIComponent(rawUrl)}`, {
                credentials: 'omit',
            });
            if (!res.ok) {
                const body = await res.json().catch(() => ({}));
                throw new Error(body.detail || `Server returned ${res.status}`);
            }
            const info = await res.json();
            setViewerInfo(info);
            setState('ready');
        } catch (err) {
            setState('error');
            setErrorMsg(err.message || 'Failed to validate the file URL.');
        }
    }, [rawUrl]);

    useEffect(() => { validateAndLoad(); }, [validateAndLoad]);

    // ── Derived display values ──────────────────────────────────────────────
    const ext      = viewerInfo?.ext      ?? getExtension(rawUrl);
    const filename = viewerInfo?.filename ?? getFilename(rawUrl);
    const domain   = getDomain(rawUrl);

    // The URL we embed in the iframe
    const proxyUrl   = `${FILE_VIEWER_BASE}/file-viewer/proxy?url=${encodeURIComponent(rawUrl)}`;
    const officeUrl  = viewerInfo?.office_viewer_url ?? '';

    // ── Render ──────────────────────────────────────────────────────────────
    return (
        <div className="h-screen flex flex-col bg-[#0F1117] text-white overflow-hidden">
            <TopBar
                filename={filename}
                domain={domain}
                fileUrl={rawUrl}
                onBack={handleBack}
            />

            {/* Body */}
            <div className="flex-1 flex overflow-hidden">
                {state === 'loading' || state === 'validating' ? (
                    <LoadingSpinner message={state === 'validating' ? 'Validating URL…' : 'Loading…'} />

                ) : state === 'error' ? (
                    <ErrorCard message={errorMsg} fileUrl={rawUrl} />

                ) : viewerInfo?.kind === 'pdf' ? (
                    // ── PDF via backend proxy ───────────────────────────────
                    <div className="flex-1 relative flex flex-col">
                        {!iframeLoaded && (
                            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-gray-400 bg-[#0F1117] z-10">
                                <div className="w-10 h-10 border-2 border-gray-600 border-t-red-400 rounded-full animate-spin" />
                                <p className="text-sm">Loading PDF…</p>
                            </div>
                        )}
                        <iframe
                            src={proxyUrl}
                            title={filename}
                            className="flex-1 w-full h-full border-0"
                            onLoad={() => setIframeLoaded(true)}
                            onError={() => { setState('error'); setErrorMsg('Failed to load PDF. The file may be unavailable or require authentication.'); }}
                            sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
                        />
                    </div>

                ) : viewerInfo?.kind === 'office' ? (
                    // ── Office files via MS Office Online Viewer ────────────
                    <div className="flex-1 relative flex flex-col">
                        {!iframeLoaded && (
                            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-gray-400 bg-[#0F1117] z-10">
                                <div className="w-10 h-10 border-2 border-gray-600 border-t-blue-400 rounded-full animate-spin" />
                                <p className="text-sm">Opening in Office Viewer…</p>
                                <p className="text-xs text-gray-600">The file must be publicly accessible on the internet.</p>
                            </div>
                        )}
                        <div className="flex-shrink-0 flex items-center gap-2 px-4 py-2 bg-[#1C1E26] border-b border-[#2A2D35] text-xs text-gray-500">
                            <svg className="w-4 h-4 text-blue-400" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M21.393 6.143A1 1 0 0020.5 5.5h-5V4a1 1 0 00-1-1H5a1 1 0 00-1 1v16a1 1 0 001 1h10a1 1 0 001-1v-1.5h4.5a1 1 0 00.98-.804l1.5-10a1 1 0 00-.587-1.053zM14 19H6V5h7v1.5a1 1 0 001 1h4.375l-1.2 8H15a1 1 0 00-1 1V19z" />
                            </svg>
                            Powered by Microsoft Office Online Viewer — file must be publicly accessible
                        </div>
                        <iframe
                            src={officeUrl}
                            title={filename}
                            className="flex-1 w-full h-full border-0"
                            onLoad={() => setIframeLoaded(true)}
                            frameBorder="0"
                            allowFullScreen
                        />
                    </div>

                ) : viewerInfo?.kind === 'text' ? (
                    // ── Plain text via backend proxy ────────────────────────
                    <div className="flex-1 relative flex flex-col">
                        {!iframeLoaded && (
                            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-gray-400 bg-[#0F1117] z-10">
                                <div className="w-10 h-10 border-2 border-gray-600 border-t-green-400 rounded-full animate-spin" />
                                <p className="text-sm">Loading file…</p>
                            </div>
                        )}
                        <iframe
                            src={proxyUrl}
                            title={filename}
                            className="flex-1 w-full h-full border-0"
                            onLoad={() => setIframeLoaded(true)}
                            sandbox="allow-scripts allow-same-origin"
                        />
                    </div>

                ) : (
                    // ── Unsupported / other ─────────────────────────────────
                    <OtherFileCard fileUrl={rawUrl} filename={filename} ext={ext} />
                )}
            </div>
        </div>
    );
}
