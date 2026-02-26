import { useState, memo, useEffect } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

/**
 * AgentActionBlock — redesigned collapsible step drawer under AI messages.
 *
 * Props:
 *   stepLog     — array of { tool, label, status, time_taken, code, stdout, stderr }
 *   toolsUsed   — array of tool name strings
 *   totalTime   — total execution time in seconds
 *   isStreaming  — whether agent is still running
 */

const TOOL_META = {
    rag_tool:       { icon: '🔍', label: 'Search',      color: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20' },
    research_tool:  { icon: '🌐', label: 'Research',    color: 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20' },
    python_tool:    { icon: '🐍', label: 'Python',      color: 'bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20' },
    quiz_tool:      { icon: '📝', label: 'Quiz',        color: 'bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border-yellow-500/20' },
    flashcard_tool: { icon: '🃏', label: 'Flashcards',  color: 'bg-pink-500/10 text-pink-600 dark:text-pink-400 border-pink-500/20' },
    ppt_tool:       { icon: '📊', label: 'Slides',      color: 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20' },
    data_profiler:  { icon: '🧠', label: 'Profile',     color: 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border-cyan-500/20' },
    file_generator: { icon: '📄', label: 'File',        color: 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-500/20' },
    code_executor:  { icon: '⚙️', label: 'Execute',     color: 'bg-teal-500/10 text-teal-600 dark:text-teal-400 border-teal-500/20' },
};

function getToolMeta(tool) {
    return TOOL_META[tool] || { icon: '⚡', label: tool || 'Tool', color: 'bg-surface-overlay text-text-secondary border-border/40' };
}

function CopyButton({ text }) {
    const [copied, setCopied] = useState(false);
    return (
        <button
            onClick={async () => {
                await navigator.clipboard.writeText(text);
                setCopied(true);
                setTimeout(() => setCopied(false), 2000);
            }}
            className="text-xs px-2 py-0.5 rounded-md bg-surface-overlay hover:bg-surface-raised text-text-muted hover:text-text-primary transition-all"
        >
            {copied ? '✓' : 'Copy'}
        </button>
    );
}

function StepCard({ step, idx, isLiveRunning = false }) {
    const [expanded, setExpanded] = useState(false);
    const meta = getToolMeta(step.tool);
    const hasDetails = step.code || step.stdout || step.stderr;
    const isRunningNow = step.status === 'running';

    // Auto-expand running steps that have live content to show
    useEffect(() => {
        if (isRunningNow && (step.code || step.stdout)) {
            setExpanded(true);
        }
    }, [isRunningNow, step.code, step.stdout]);

    // Auto-scroll stdout container to bottom when new lines arrive
    const stdoutRef = { current: null };

    return (
        <div className={`rounded-xl border overflow-hidden ${isRunningNow ? 'border-accent/40 bg-accent/5' : 'border-border/30 bg-surface-overlay/40'}`}>
            {/* Step row */}
            <button
                onClick={() => (hasDetails || isRunningNow) && setExpanded(v => !v)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 text-left ${(hasDetails || isRunningNow) ? 'hover:bg-surface-raised/60 cursor-pointer' : 'cursor-default'} transition-colors`}
            >
                {/* Step number / spinner */}
                {isRunningNow ? (
                    <span className="w-5 h-5 flex items-center justify-center flex-shrink-0">
                        <span
                            className="w-3.5 h-3.5 rounded-full border-2 border-accent/30 border-t-accent inline-block"
                            style={{ animation: 'spin 0.8s linear infinite' }}
                        />
                    </span>
                ) : (
                    <span className="text-xs text-text-muted tabular-nums w-5 text-right flex-shrink-0">
                        {idx + 1}
                    </span>
                )}

                {/* Tool badge */}
                <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border font-medium flex-shrink-0 ${meta.color}`}>
                    <span>{meta.icon}</span>
                    <span>{meta.label}</span>
                </span>

                {/* Step label */}
                <span className="text-sm text-text-secondary truncate flex-1">
                    {step.label || step.tool}
                </span>

                <div className="flex items-center gap-2 flex-shrink-0">
                    {/* Time */}
                    {step.time_taken != null && (
                        <span className="text-xs tabular-nums text-text-muted">{step.time_taken}s</span>
                    )}
                    {/* Status */}
                    {isRunningNow
                        ? <span className="text-xs text-accent animate-pulse">running</span>
                        : step.status === 'success'
                            ? <span className="text-green-500 text-sm">✓</span>
                            : step.status === 'error'
                                ? <span className="text-red-500 text-sm">✗</span>
                                : null}
                    {/* Expand chevron */}
                    {(hasDetails || isRunningNow) && (
                        <span className={`text-text-muted text-xs transition-transform duration-150 ${expanded ? 'rotate-90' : ''}`}>
                            ▶
                        </span>
                    )}
                </div>
            </button>

            {/* Expanded details — show during running state too for live streaming */}
            {(hasDetails || isRunningNow) && expanded && (
                <div className="px-3 pb-3 space-y-2 border-t border-border/20 pt-2">
                    {step.code && (
                        <div>
                            <div className="flex items-center justify-between mb-1">
                                <span className="text-xs font-medium text-text-muted uppercase tracking-wide">Code</span>
                                <CopyButton text={step.code} />
                            </div>
                            <div className="rounded-lg overflow-hidden max-h-56 overflow-y-auto border border-border/40">
                                <SyntaxHighlighter
                                    language="python"
                                    style={oneDark}
                                    customStyle={{ margin: 0, padding: '10px 12px', fontSize: '11.5px', lineHeight: '1.6', background: '#1a1b26' }}
                                >
                                    {step.code}
                                </SyntaxHighlighter>
                            </div>
                        </div>
                    )}
                    {step.stdout && (
                        <div>
                            <div className="flex items-center gap-2 mb-1">
                                <span className="text-xs font-medium text-text-muted uppercase tracking-wide">Output</span>
                                {isRunningNow && (
                                    <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" title="Live output" />
                                )}
                            </div>
                            <pre
                                ref={el => {
                                    if (el && isRunningNow) el.scrollTop = el.scrollHeight;
                                }}
                                className={`text-xs font-mono p-2.5 rounded-lg bg-surface border border-border/30 max-h-40 overflow-y-auto whitespace-pre-wrap text-text-secondary ${isRunningNow ? 'border-accent/30' : ''}`}
                            >
                                {step.stdout}
                                {isRunningNow && <span className="inline-block w-1.5 h-3.5 bg-accent/60 ml-0.5 animate-pulse" />}
                            </pre>
                        </div>
                    )}
                    {!step.code && !step.stdout && isRunningNow && (
                        <div className="flex items-center gap-2 py-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
                            <span className="text-xs text-text-muted">Waiting for output…</span>
                        </div>
                    )}
                    {step.stderr && (
                        <div>
                            <span className="text-xs font-medium text-red-500 uppercase tracking-wide block mb-1">Error</span>
                            <pre className="text-xs font-mono p-2.5 rounded-lg bg-red-500/5 border border-red-500/20 max-h-40 overflow-y-auto whitespace-pre-wrap text-red-400">
                                {step.stderr}
                            </pre>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export default memo(function AgentActionBlock({ stepLog = [], toolsUsed = [], totalTime = 0, isStreaming = false }) {
    const [isExpanded, setIsExpanded] = useState(isStreaming);

    // Auto-expand when streaming starts and steps arrive
    useEffect(() => {
        if (isStreaming && stepLog.length > 0) {
            setIsExpanded(true);
        }
    }, [isStreaming, stepLog.length]);

    if (!stepLog.length && !toolsUsed.length) return null;

    const uniqueTools = [...new Set(stepLog.map(s => s.tool).concat(toolsUsed))].filter(Boolean);
    const timeStr = totalTime > 0 ? `${totalTime.toFixed(1)}s` : '';

    return (
        <div className="mb-2.5">
            {/* Header row — compact inline pill */}
            <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-surface-overlay/70 hover:bg-surface-overlay border border-border/30 transition-colors text-left"
            >
                {/* Animated dot while streaming */}
                {isStreaming ? (
                    <span className="w-2 h-2 rounded-full bg-accent animate-pulse flex-shrink-0" />
                ) : (
                    <span className={`text-xs text-text-muted transition-transform duration-150 ${isExpanded ? 'rotate-90' : ''}`}>▶</span>
                )}

                {/* Step count */}
                <span className="text-sm text-text-secondary">
                    {isStreaming
                        ? stepLog.length > 0
                            ? `${stepLog.length} step${stepLog.length !== 1 ? 's' : ''}…`
                            : 'Working…'
                        : `${stepLog.length} step${stepLog.length !== 1 ? 's' : ''}`
                    }
                </span>

                {/* Tool pills */}
                {uniqueTools.slice(0, 4).map(tool => {
                    const m = getToolMeta(tool);
                    return (
                        <span key={tool} className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border font-medium ${m.color}`}>
                            {m.icon} {m.label}
                        </span>
                    );
                })}
                {uniqueTools.length > 4 && (
                    <span className="text-xs text-text-muted">+{uniqueTools.length - 4}</span>
                )}

                {/* Time */}
                {timeStr && (
                    <span className="ml-auto text-xs tabular-nums text-text-muted flex-shrink-0">{timeStr}</span>
                )}
            </button>

            {/* Step list */}
            {isExpanded && (
                <div className="mt-1.5 rounded-xl border border-border/30 bg-surface-overlay/50 overflow-hidden divide-y divide-border/20">
                    {stepLog.map((step, idx) => (
                        <StepCard key={idx} step={step} idx={idx} isLiveRunning={isStreaming} />
                    ))}
                </div>
            )}
        </div>
    );
});
