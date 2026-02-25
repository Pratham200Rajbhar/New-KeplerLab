import { useState } from 'react';

const INTENT_COLORS = {
    QUESTION: 'intent-question',
    DATA_ANALYSIS: 'intent-data',
    RESEARCH: 'intent-research',
    CODE_EXECUTION: 'intent-code',
    CONTENT_GENERATION: 'intent-content',
    UNKNOWN: 'intent-unknown',
    ERROR: 'intent-error',
};

const INTENT_ICONS = {
    QUESTION: '🤔',
    DATA_ANALYSIS: '📊',
    RESEARCH: '🔬',
    CODE_EXECUTION: '⚙️',
    CONTENT_GENERATION: '✨',
    UNKNOWN: '❓',
    ERROR: '⚠️',
};

/**
 * AgentStepsPanel — collapsible metadata panel under each AI message.
 *
 * Props:
 *   meta: { intent, confidence, tools_used, iterations, total_tokens, stopped_reason }
 */
export default function AgentStepsPanel({ meta }) {
    const [expanded, setExpanded] = useState(false);

    if (!meta || !meta.intent) return null;

    const intent = meta.intent || 'UNKNOWN';
    const confidence = Math.round((meta.confidence || 0) * 100);
    const tools = meta.tools_used || [];
    const steps = meta.iterations || 0;
    const tokens = meta.total_tokens || 0;
    const stopped = meta.stopped_reason || 'completed';

    return (
        <div className="agent-steps-panel">
            <button
                className="agent-steps-toggle"
                onClick={() => setExpanded((v) => !v)}
                aria-expanded={expanded}
            >
                <span className="agent-steps-chevron" style={{ transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)' }}>▶</span>
                <span className="agent-steps-title">Agent Steps</span>
                <span className={`intent-badge ${INTENT_COLORS[intent] || 'intent-unknown'}`}>
                    {INTENT_ICONS[intent]} {intent}
                </span>
                <span className="agent-confidence">{confidence}%</span>
            </button>

            {expanded && (
                <div className="agent-steps-body">
                    <div className="agent-step-row">
                        <span className="agent-step-check">✅</span>
                        <span className="agent-step-label">Intent detected:</span>
                        <span className="agent-step-value">{intent} ({confidence}% confidence)</span>
                    </div>
                    {tools.length > 0 && (
                        <div className="agent-step-row">
                            <span className="agent-step-check">✅</span>
                            <span className="agent-step-label">Tools used:</span>
                            <span className="agent-step-value">{tools.join(', ')}</span>
                        </div>
                    )}
                    <div className="agent-step-row">
                        <span className="agent-step-check">✅</span>
                        <span className="agent-step-label">Steps:</span>
                        <span className="agent-step-value">{steps}</span>
                        <span className="agent-step-sep">|</span>
                        <span className="agent-step-label">Tokens:</span>
                        <span className="agent-step-value">{tokens.toLocaleString()}</span>
                    </div>
                    {stopped !== 'completed' && (
                        <div className="agent-step-row">
                            <span className="agent-step-warn">⚠️</span>
                            <span className="agent-step-label">Stopped:</span>
                            <span className="agent-step-value agent-step-warn-text">{stopped}</span>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
