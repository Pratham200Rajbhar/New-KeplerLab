import { useState, useEffect } from 'react';
import { usePodcast } from '../../context/PodcastContext';
import { useApp } from '../../context/AppContext';
import VoicePicker from './VoicePicker';
import { getLanguages } from '../../api/podcast';

const MODES = [
  { id: 'overview', label: 'Overview', desc: 'A broad tour of all uploaded material' },
  { id: 'deep-dive', label: 'Deep Dive', desc: 'In-depth analysis of key concepts' },
  { id: 'debate', label: 'Debate', desc: 'Two hosts take opposing perspectives' },
  { id: 'q-and-a', label: 'Q & A', desc: 'Interview-style question and answer' },
];

export default function PodcastModeSelector() {
  const { create, startGeneration, setPhase, error, loading } = usePodcast();
  const { selectedSources } = useApp();

  const [mode, setMode] = useState('overview');
  const [topic, setTopic] = useState('');
  const [language, setLanguage] = useState('en');
  const [hostVoice, setHostVoice] = useState('');
  const [guestVoice, setGuestVoice] = useState('');
  const [languages, setLanguages] = useState([]);
  const [showVoices, setShowVoices] = useState(false);

  useEffect(() => {
    getLanguages().then(setLanguages).catch(() => {});
  }, []);

  const handleGenerate = async () => {
    try {
      const session = await create({ mode, topic, language, hostVoice, guestVoice });
      if (session?.id) {
        await startGeneration(session.id);
      }
    } catch {
      // error is set in context
    }
  };

  const hasSources = selectedSources.size > 0;

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Back button */}
      <button
        onClick={() => setPhase('library')}
        className="flex items-center gap-1.5 text-sm text-text-muted hover:text-text-primary transition-colors"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Back
      </button>

      <div>
        <h3 className="text-sm font-semibold text-text-primary mb-1">New Podcast</h3>
        <p className="text-xs text-text-muted">
          {hasSources
            ? `Using ${selectedSources.size} selected source${selectedSources.size > 1 ? 's' : ''}`
            : 'Select sources in the sidebar first'}
        </p>
      </div>

      {/* Mode selector */}
      <div>
        <label className="text-xs font-medium text-text-secondary mb-2 block">Style</label>
        <div className="grid grid-cols-2 gap-2">
          {MODES.map(m => (
            <button
              key={m.id}
              onClick={() => setMode(m.id)}
              className={`text-left p-2.5 rounded-lg border transition-all ${
                mode === m.id
                  ? 'border-accent bg-accent/10 text-text-primary'
                  : 'border-border hover:border-text-muted text-text-secondary'
              }`}
            >
              <span className="text-xs font-medium block">{m.label}</span>
              <span className="text-[10px] text-text-muted block mt-0.5">{m.desc}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Topic (optional) */}
      <div>
        <label className="text-xs font-medium text-text-secondary mb-1.5 block">
          Focus Topic <span className="text-text-muted">(optional)</span>
        </label>
        <input
          type="text"
          value={topic}
          onChange={e => setTopic(e.target.value)}
          placeholder="e.g. Chapter 3: Neural Networks"
          className="w-full px-3 py-2 text-sm rounded-lg bg-surface border border-border text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent"
        />
      </div>

      {/* Language */}
      <div>
        <label className="text-xs font-medium text-text-secondary mb-1.5 block">Language</label>
        <select
          value={language}
          onChange={e => setLanguage(e.target.value)}
          className="w-full px-3 py-2 text-sm rounded-lg bg-surface border border-border text-text-primary focus:outline-none focus:ring-1 focus:ring-accent"
        >
          {languages.length > 0 ? (
            languages.map(l => (
              <option key={l.code} value={l.code}>{l.name}</option>
            ))
          ) : (
            <>
              <option value="en">English</option>
              <option value="hi">Hindi</option>
              <option value="es">Spanish</option>
              <option value="fr">French</option>
              <option value="de">German</option>
              <option value="ja">Japanese</option>
              <option value="zh">Chinese</option>
              <option value="pt">Portuguese</option>
              <option value="ar">Arabic</option>
              <option value="gu">Gujarati</option>
            </>
          )}
        </select>
      </div>

      {/* Voice Picker Toggle */}
      <div>
        <button
          onClick={() => setShowVoices(!showVoices)}
          className="flex items-center gap-2 text-xs text-accent hover:text-accent-light transition-colors"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d={showVoices ? "M19 9l-7 7-7-7" : "M9 5l7 7-7 7"} />
          </svg>
          {showVoices ? 'Hide voice options' : 'Choose voices'}
        </button>

        {showVoices && (
          <div className="mt-3 space-y-3 animate-fade-in">
            <VoicePicker
              label="Host Voice"
              language={language}
              value={hostVoice}
              onChange={setHostVoice}
            />
            <VoicePicker
              label="Guest Voice"
              language={language}
              value={guestVoice}
              onChange={setGuestVoice}
            />
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="p-2.5 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">
          {error}
        </div>
      )}

      {/* Generate button */}
      <button
        onClick={handleGenerate}
        disabled={!hasSources || loading}
        className="w-full py-2.5 rounded-lg bg-accent hover:bg-accent-light text-white text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        {loading ? (
          <>
            <div className="loading-spinner w-4 h-4" />
            Creating...
          </>
        ) : (
          <>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Generate Podcast
          </>
        )}
      </button>
    </div>
  );
}
