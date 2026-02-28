import { useState, useEffect } from 'react';
import Modal from '../Modal';
import VoicePicker from './VoicePicker';
import { getLanguages } from '../../api/podcast';

const DEFAULT_LANGUAGES = [
  { code: 'en', name: 'English' },
  { code: 'hi', name: 'Hindi' },
  { code: 'es', name: 'Spanish' },
  { code: 'fr', name: 'French' },
  { code: 'de', name: 'German' },
  { code: 'ja', name: 'Japanese' },
  { code: 'zh', name: 'Chinese' },
  { code: 'pt', name: 'Portuguese' },
  { code: 'ar', name: 'Arabic' },
  { code: 'gu', name: 'Gujarati' },
];

/**
 * Simplified Podcast configuration dialog.
 * Shows: What to cover, Language, Host Voice, Guest Voice, Generate button.
 */
export default function PodcastConfigDialog({ onGenerate, onCancel, loading }) {
  const [scope, setScope] = useState('full');
  const [topic, setTopic] = useState('');
  const [language, setLanguage] = useState('en');
  const [hostVoice, setHostVoice] = useState('');
  const [guestVoice, setGuestVoice] = useState('');
  const [languages, setLanguages] = useState([]);

  useEffect(() => {
    getLanguages()
      .then(data => {
        if (Array.isArray(data)) setLanguages(data);
        else if (data && Array.isArray(data.languages)) setLanguages(data.languages);
        else setLanguages([]);
      })
      .catch(() => setLanguages([]));
  }, []);

  const availableLanguages = languages.length > 0 ? languages : DEFAULT_LANGUAGES;

  const handleSubmit = (e) => {
    e.preventDefault();
    onGenerate({
      mode: 'overview',
      topic: scope === 'topic' ? topic.trim() : '',
      language,
      hostVoice: hostVoice || undefined,
      guestVoice: guestVoice || undefined,
    });
  };

  const modalIcon = (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
    </svg>
  );

  return (
    <Modal
      isOpen={true}
      onClose={onCancel}
      title="New AI Podcast"
      icon={modalIcon}
      maxWidth="max-w-lg"
      showClose={!loading}
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        {/* What to Cover */}
        <div className="form-group">
          <label className="form-label">What to cover</label>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setScope('full')}
              disabled={loading}
              className={`flex items-center gap-3 p-3 rounded-xl border-2 transition-all text-left ${
                scope === 'full'
                  ? 'border-accent bg-accent/8'
                  : 'border-border hover:border-text-muted/40'
              }`}
            >
              <div className={`p-2 rounded-lg ${scope === 'full' ? 'bg-accent/15 text-accent' : 'bg-surface-overlay text-text-muted'}`}>
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
              </div>
              <div>
                <span className={`text-sm font-medium block ${scope === 'full' ? 'text-text-primary' : 'text-text-secondary'}`}>
                  Full Resource
                </span>
                <span className="text-[11px] text-text-muted">Cover all material</span>
              </div>
            </button>
            <button
              type="button"
              onClick={() => setScope('topic')}
              disabled={loading}
              className={`flex items-center gap-3 p-3 rounded-xl border-2 transition-all text-left ${
                scope === 'topic'
                  ? 'border-accent bg-accent/8'
                  : 'border-border hover:border-text-muted/40'
              }`}
            >
              <div className={`p-2 rounded-lg ${scope === 'topic' ? 'bg-accent/15 text-accent' : 'bg-surface-overlay text-text-muted'}`}>
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <div>
                <span className={`text-sm font-medium block ${scope === 'topic' ? 'text-text-primary' : 'text-text-secondary'}`}>
                  Specific Topic
                </span>
                <span className="text-[11px] text-text-muted">Focus on one area</span>
              </div>
            </button>
          </div>
        </div>

        {/* Topic Input */}
        {scope === 'topic' && (
          <div className="form-group animate-fade-in">
            <label className="form-label">Topic</label>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. Chapter 3, Neural Networks, etc."
              className="input"
              disabled={loading}
              autoFocus
            />
          </div>
        )}

        {/* Language */}
        <div className="form-group">
          <label className="form-label">Language</label>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="input"
            disabled={loading}
          >
            {availableLanguages.map((l) => (
              <option key={l.code || l} value={l.code || l}>
                {l.name || l}
              </option>
            ))}
          </select>
        </div>

        {/* Voice Selection */}
        <div className="form-group">
          <label className="form-label">Podcast Voices</label>
          <div className="space-y-3 p-3 rounded-xl bg-surface-overlay/50 border border-border">
            <VoicePicker
              label="Host Voice"
              language={language}
              value={hostVoice}
              onChange={setHostVoice}
            />
            <div className="border-t border-border" />
            <VoicePicker
              label="Guest Voice"
              language={language}
              value={guestVoice}
              onChange={setGuestVoice}
            />
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 pt-2">
          <button
            type="button"
            className="btn-secondary flex-1"
            onClick={onCancel}
            disabled={loading}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="btn-primary flex-1"
            disabled={loading || (scope === 'topic' && !topic.trim())}
          >
            {loading ? (
              <>
                <div className="loading-spinner w-4 h-4 mr-2" />
                Generating…
              </>
            ) : (
              <>
                <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Generate Podcast
              </>
            )}
          </button>
        </div>
      </form>
    </Modal>
  );
}
