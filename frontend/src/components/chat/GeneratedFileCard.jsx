import { useState, memo } from 'react';
import Modal from '../Modal';

/**
 * GeneratedFileCard — displays a generated file with download/preview actions.
 *
 * Props:
 *   filename    — name of the file
 *   downloadUrl — relative URL to download the file
 *   size        — file size in bytes
 *   fileType    — type string (spreadsheet, document, image, etc.)
 */

const FILE_STYLES = {
    spreadsheet: { icon: '📊', border: 'border-green-500/30', bg: 'bg-green-500/5' },
    document: { icon: '📝', border: 'border-blue-500/30', bg: 'bg-blue-500/5' },
    image: { icon: '🖼️', border: 'border-purple-500/30', bg: 'bg-purple-500/5' },
    data: { icon: '🗃️', border: 'border-gray-500/30', bg: 'bg-gray-500/5' },
    web: { icon: '🌐', border: 'border-cyan-500/30', bg: 'bg-cyan-500/5' },
    text: { icon: '📄', border: 'border-gray-500/30', bg: 'bg-gray-500/5' },
    file: { icon: '📁', border: 'border-gray-500/30', bg: 'bg-gray-500/5' },
};

// Override based on extension
function getStyleFromFilename(filename, fileType) {
    const ext = filename.split('.').pop()?.toLowerCase();
    if (ext === 'pdf') return { icon: '📕', border: 'border-red-500/30', bg: 'bg-red-500/5' };
    if (ext === 'csv') return { icon: '🗃️', border: 'border-gray-500/30', bg: 'bg-gray-500/5' };
    return FILE_STYLES[fileType] || FILE_STYLES.file;
}

function formatSize(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function isPreviewable(filename) {
    const ext = filename.split('.').pop()?.toLowerCase();
    return ['png', 'jpg', 'jpeg', 'svg', 'gif', 'webp'].includes(ext);
}

export default memo(function GeneratedFileCard({ filename, downloadUrl, size, fileType }) {
    const [showPreview, setShowPreview] = useState(false);
    const [downloading, setDownloading] = useState(false);
    const style = getStyleFromFilename(filename, fileType);

    const handleDownload = async () => {
        setDownloading(true);
        try {
            // Get file token first
            const { apiFetch } = await import('../../api/config');
            const tokenRes = await apiFetch('/auth/file-token');
            const { token } = await tokenRes.json();

            const url = `${downloadUrl}?token=${token}`;

            // Trigger browser download
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        } catch (err) {
            console.error('Download failed:', err);
        } finally {
            setDownloading(false);
        }
    };

    const handlePreview = () => {
        setShowPreview(true);
    };

    return (
        <>
            <div
                className={`inline-flex items-center gap-3 px-3 py-2.5 rounded-xl border ${style.border} ${style.bg} hover:shadow-sm transition-all max-w-xs`}
            >
                {/* File icon */}
                <span className="text-xl flex-shrink-0">{style.icon}</span>

                {/* File info */}
                <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-text-primary truncate" title={filename}>
                        {filename}
                    </p>
                    <p className="text-xs text-text-muted">{formatSize(size)}</p>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1 flex-shrink-0">
                    {isPreviewable(filename) && (
                        <button
                            onClick={handlePreview}
                            className="p-1.5 rounded-lg hover:bg-white/10 text-text-muted hover:text-text-primary transition-colors"
                            title="Preview"
                        >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                            </svg>
                        </button>
                    )}
                    <button
                        onClick={handleDownload}
                        disabled={downloading}
                        className="p-1.5 rounded-lg hover:bg-white/10 text-accent hover:text-accent-dark transition-colors disabled:opacity-50"
                        title="Download"
                    >
                        {downloading ? (
                            <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                        ) : (
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                            </svg>
                        )}
                    </button>
                </div>
            </div>

            {/* Image Preview Modal */}
            {showPreview && (
                <Modal
                    isOpen={showPreview}
                    onClose={() => setShowPreview(false)}
                    title={filename}
                    maxWidth="max-w-3xl"
                >
                    <div className="flex items-center justify-center p-4">
                        <img
                            src={downloadUrl}
                            alt={filename}
                            className="max-w-full max-h-[70vh] rounded-lg object-contain"
                        />
                    </div>
                </Modal>
            )}
        </>
    );
});
