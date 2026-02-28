import { useState, useEffect, useRef } from 'react';
import { getVoicesForLanguage, getVoicePreviewUrl } from '../../api/podcast';

/**
 * Voice selector with inline preview playback.
 * Fetches voices per-language and plays a short preview clip.
 */
export default function VoicePicker({ label, language, value, onChange }) {
  const [voices, setVoices] = useState([]);
  const [previewingId, setPreviewingId] = useState(null);
  const audioRef = useRef(new Audio());

  useEffect(() => {
    getVoicesForLanguage(language)
      .then(data => {
        // API may return an array directly or an object like { voices: [...] }
        if (Array.isArray(data)) setVoices(data);
        else if (data && Array.isArray(data.voices)) setVoices(data.voices);
        else setVoices([]);
      })
      .catch(() => setVoices([]));
  }, [language]);

  const handlePreview = (voiceId) => {
    if (previewingId === voiceId) {
      audioRef.current.pause();
      setPreviewingId(null);
      return;
    }
    audioRef.current.src = getVoicePreviewUrl(voiceId, language);
    audioRef.current.play().catch(() => {});
    setPreviewingId(voiceId);
    audioRef.current.onended = () => setPreviewingId(null);
  };

  return (
    <div>
      <label className="text-xs font-medium text-text-secondary mb-1.5 block">{label}</label>
      <div className="space-y-1 max-h-32 overflow-y-auto">
        {voices.length === 0 && (
          <p className="text-[10px] text-text-muted py-1">Loading voices…</p>
        )}
        {voices.map(v => (
          <div
            key={v.id}
            onClick={() => onChange(v.id)}
            className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-all ${
              value === v.id
                ? 'bg-accent/10 border border-accent/30'
                : 'hover:bg-surface-overlay border border-transparent'
            }`}
          >
            <div className="flex-1 min-w-0">
              <span className="text-xs text-text-primary block truncate">{v.name || v.id}</span>
              {v.gender && (
                <span className="text-[9px] text-text-muted capitalize">{v.gender}</span>
              )}
            </div>

            {/* Preview button */}
            <button
              onClick={(e) => { e.stopPropagation(); handlePreview(v.id); }}
              className="p-1 rounded hover:bg-surface-overlay transition-colors flex-shrink-0"
              title="Preview voice"
            >
              {previewingId === v.id ? (
                <svg className="w-3.5 h-3.5 text-accent" fill="currentColor" viewBox="0 0 24 24">
                  <rect x="6" y="4" width="4" height="16" rx="1" />
                  <rect x="14" y="4" width="4" height="16" rx="1" />
                </svg>
              ) : (
                <svg className="w-3.5 h-3.5 text-text-muted" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z" />
                </svg>
              )}
            </button>

            {/* Selection indicator */}
            {value === v.id && (
              <svg className="w-3.5 h-3.5 text-accent flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
              </svg>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
