import { useState } from 'react';
import { usePodcast } from '../../context/PodcastContext';
import { getPodcastExportUrl } from '../../api/podcast';

/**
 * End-of-session export bar / dialog.
 * Supports PDF and JSON export formats.
 */
export default function PodcastExportBar({ onClose }) {
  const { session, exportSession, generateSummary } = usePodcast();
  const [exporting, setExporting] = useState(null); // 'pdf' | 'json' | null
  const [summary, setSummary] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [exportResult, setExportResult] = useState(null);

  const handleExport = async (format) => {
    try {
      setExporting(format);
      const result = await exportSession(format);
      setExportResult(result);
    } catch (err) {
      console.error('Export failed:', err);
    } finally {
      setExporting(null);
    }
  };

  const handleSummary = async () => {
    try {
      setSummaryLoading(true);
      const result = await generateSummary();
      setSummary(result?.summary || result);
    } catch (err) {
      console.error('Summary failed:', err);
    } finally {
      setSummaryLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <div className="bg-surface-raised border border-border rounded-xl shadow-2xl p-5 max-w-sm w-full mx-4"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-sm font-semibold text-text-primary">Export Podcast</h4>
          <button onClick={onClose} className="btn-icon-sm">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Export formats */}
        <div className="space-y-2 mb-4">
          <button
            onClick={() => handleExport('pdf')}
            disabled={!!exporting}
            className="w-full flex items-center gap-3 p-3 rounded-lg border border-border hover:border-accent/30 hover:bg-accent/5 transition-all text-left disabled:opacity-50"
          >
            <div className="w-8 h-8 rounded-lg bg-red-500/10 flex items-center justify-center">
              <svg className="w-4 h-4 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
            </div>
            <div>
              <span className="text-xs font-medium text-text-primary block">PDF Transcript</span>
              <span className="text-[10px] text-text-muted">Full dialogue with chapters & Q&A</span>
            </div>
            {exporting === 'pdf' && <div className="loading-spinner w-4 h-4 ml-auto" />}
          </button>

          <button
            onClick={() => handleExport('json')}
            disabled={!!exporting}
            className="w-full flex items-center gap-3 p-3 rounded-lg border border-border hover:border-accent/30 hover:bg-accent/5 transition-all text-left disabled:opacity-50"
          >
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center">
              <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
            </div>
            <div>
              <span className="text-xs font-medium text-text-primary block">JSON Data</span>
              <span className="text-[10px] text-text-muted">Structured data for further processing</span>
            </div>
            {exporting === 'json' && <div className="loading-spinner w-4 h-4 ml-auto" />}
          </button>
        </div>

        {/* Summary */}
        <div className="border-t border-border pt-3">
          {!summary ? (
            <button
              onClick={handleSummary}
              disabled={summaryLoading}
              className="w-full py-2 rounded-lg border border-border hover:bg-surface-overlay text-text-secondary text-xs font-medium flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
            >
              {summaryLoading ? (
                <><div className="loading-spinner w-3 h-3" /> Generating summary…</>
              ) : (
                <><svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg> Generate Summary</>
              )}
            </button>
          ) : (
            <div className="p-2.5 rounded-lg bg-surface-overlay">
              <p className="text-[10px] font-medium text-text-muted uppercase mb-1">Summary</p>
              <p className="text-xs text-text-secondary leading-relaxed">{summary}</p>
            </div>
          )}
        </div>

        {/* Download link */}
        {exportResult?.filename && (
          <div className="mt-3 p-2 rounded-lg bg-green-500/10 border border-green-500/20 text-center">
            <p className="text-xs text-green-400 mb-1">Export ready!</p>
            <a
              href={getPodcastExportUrl(session.id, exportResult.filename)}
              download
              className="text-xs text-accent hover:text-accent-light underline"
            >
              Download {exportResult.filename}
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
