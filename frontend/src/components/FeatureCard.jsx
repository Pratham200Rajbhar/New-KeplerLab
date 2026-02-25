export default function FeatureCard({ icon, title, description, onClick, loading, disabled, onCancel }) {
    return (
        <button
            onClick={loading ? undefined : onClick}
            disabled={!loading && disabled}
            className="feature-card w-full text-left disabled:opacity-50 disabled:cursor-not-allowed group"
        >
            <div className="feature-card-icon">
                {loading ? (
                    <div className="loading-spinner w-5 h-5" />
                ) : (
                    icon
                )}
            </div>
            <div className="flex-1 min-w-0">
                <h4 className={`text-sm font-medium transition-colors ${loading ? 'text-text-secondary' : 'text-text-primary group-hover:text-accent'}`}>{title}</h4>
                <p className="text-xs text-text-muted truncate group-hover:text-text-secondary transition-colors">
                    {loading ? 'Generating…' : description}
                </p>
            </div>
            {loading && onCancel ? (
                <button
                    onClick={(e) => { e.stopPropagation(); onCancel(); }}
                    className="flex-shrink-0 p-1.5 rounded-lg bg-red-500/15 text-red-400 hover:bg-red-500/30 transition-colors"
                    title="Cancel"
                >
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                        <rect x="6" y="6" width="12" height="12" rx="2" />
                    </svg>
                </button>
            ) : (
                <svg className="w-4 h-4 text-text-muted flex-shrink-0 group-hover:text-text-secondary group-hover:translate-x-0.5 transition-all duration-200" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
            )}
        </button>
    );
}
