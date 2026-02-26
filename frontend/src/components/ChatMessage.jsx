import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeRaw from 'rehype-raw';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useState, useRef, useCallback, memo } from 'react';
import AgentStepsPanel from './chat/AgentStepsPanel';
import AgentActionBlock from './chat/AgentActionBlock';
import GeneratedFileCard from './chat/GeneratedFileCard';
import ExecutionPanel from './chat/ExecutionPanel';
import ChartRenderer from './chat/ChartRenderer';
import BlockHoverMenu from './chat/BlockHoverMenu';

// Custom code theme — dark, clean, modern
const customCodeTheme = {
    ...oneDark,
    'pre[class*="language-"]': {
        ...oneDark['pre[class*="language-"]'],
        background: '#1a1b26',
        borderRadius: '0 0 12px 12px',
        margin: 0,
        padding: '16px',
        fontSize: '13px',
        lineHeight: '1.7',
    },
};

// Hoist plugin arrays to module scope so they are referentially stable
const REMARK_PLUGINS = [remarkGfm, remarkMath];
const REHYPE_PLUGINS = [rehypeRaw, rehypeKatex];

/**
 * Sanitize partially-streamed markdown so it doesn't break the renderer.
 * Closes unclosed fenced code blocks and unclosed bold/italic markers.
 */
export function sanitizeStreamingMarkdown(text) {
    if (!text) return '';
    let result = text;

    // Close unclosed fenced code blocks (```)
    const fenceMatches = result.match(/^(`{3,})/gm);
    if (fenceMatches && fenceMatches.length % 2 !== 0) {
        // Odd number of fences — the last one is unclosed
        result += '\n```';
    }

    // Close unclosed tilde fences (~~~)
    const tildeFences = result.match(/^(~{3,})/gm);
    if (tildeFences && tildeFences.length % 2 !== 0) {
        result += '\n~~~';
    }

    return result;
}

function CopyButton({ code }) {
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(code);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch {
            // Fallback for non-HTTPS or denied clipboard permission
            try {
                const textarea = document.createElement('textarea');
                textarea.value = code;
                textarea.style.position = 'fixed';
                textarea.style.opacity = '0';
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                setCopied(true);
                setTimeout(() => setCopied(false), 2000);
            } catch {
                // Silently fail if copy is completely unavailable
            }
        }
    };

    return (
        <button onClick={handleCopy} className="copy-code-btn" title="Copy code">
            {copied ? (
                <svg className="w-4 h-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
            ) : (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
            )}
        </button>
    );
}

/**
 * Markdown renderer component — shared between full messages and block content.
 * Supports: GFM tables, task lists, strikethrough, math (KaTeX), HTML, syntax highlighting.
 */
export function MarkdownRenderer({ content }) {
    // Guard against null/undefined/non-string content
    const safeContent = typeof content === 'string' ? content : String(content || '');

    // Track whether we're inside a <pre> block so the code component can
    // distinguish fenced code blocks from inline `code` spans.
    const isInsidePre = useRef(false);

    // Memoize the `code` component so it captures the ref correctly
    const codeComponent = useCallback(({ className, children, node, ...props }) => {
        const match = /language-(\w+)/.exec(className || '');
        const codeString = String(children).replace(/\n$/, '');
        // Block code: has a language tag, has a className, is multiline, or is a child of <pre>
        const isBlock = isInsidePre.current || Boolean(match) || Boolean(className) || codeString.includes('\n');
        if (isBlock) {
            const language = match ? match[1] : 'text';
            return (
                <div className="md-code-block-wrapper">
                    <div className="md-code-header">
                        <span className="md-code-language">{language}</span>
                        <CopyButton code={codeString} />
                    </div>
                    <SyntaxHighlighter
                        style={customCodeTheme}
                        language={language}
                        PreTag="div"
                        customStyle={{ margin: 0, borderRadius: '0 0 12px 12px', border: '1px solid var(--border)', borderTop: 'none' }}
                    >
                        {codeString}
                    </SyntaxHighlighter>
                </div>
            );
        }
        return <code className="md-inline-code" {...props}>{children}</code>;
    }, []);

    return (
        <ReactMarkdown
            remarkPlugins={REMARK_PLUGINS}
            rehypePlugins={REHYPE_PLUGINS}
            components={{
                h1: ({ children }) => (
                    <h1 className="md-heading md-h1">{children}</h1>
                ),
                h2: ({ children }) => (
                    <h2 className="md-heading md-h2">{children}</h2>
                ),
                h3: ({ children }) => <h3 className="md-heading md-h3">{children}</h3>,
                h4: ({ children }) => <h4 className="md-heading md-h4">{children}</h4>,
                h5: ({ children }) => <h5 className="md-heading md-h5">{children}</h5>,
                h6: ({ children }) => <h6 className="md-heading md-h6">{children}</h6>,
                p: ({ children, node }) => {
                    // Prevent wrapping block-level children (images, divs) in <p> which causes hydration errors
                    const hasBlock = node?.children?.some(c =>
                        c.tagName === 'img' || c.tagName === 'div' || c.tagName === 'pre' || c.tagName === 'table'
                    );
                    if (hasBlock) return <div className="md-paragraph">{children}</div>;
                    return <p className="md-paragraph">{children}</p>;
                },
                ul: ({ children, className }) => {
                    // Support GFM task lists
                    const isTaskList = className?.includes('contains-task-list');
                    return <ul className={`md-list md-ul ${isTaskList ? 'md-task-list' : ''}`}>{children}</ul>;
                },
                ol: ({ children, start }) => <ol className="md-list md-ol" start={start}>{children}</ol>,
                li: ({ children, className }) => {
                    const isTask = className?.includes('task-list-item');
                    return <li className={`md-list-item ${isTask ? 'md-task-item' : ''}`}>{children}</li>;
                },
                input: ({ checked, type, ...props }) => {
                    // GFM task list checkbox
                    if (type === 'checkbox') {
                        return (
                            <input
                                type="checkbox"
                                checked={checked}
                                readOnly
                                className="md-task-checkbox"
                                {...props}
                            />
                        );
                    }
                    return <input type={type} {...props} />;
                },
                code: codeComponent,
                pre: ({ children }) => {
                    // Signal to the code component that we're inside a <pre>
                    isInsidePre.current = true;
                    const result = <>{children}</>;
                    // Reset after rendering (synchronous)
                    isInsidePre.current = false;
                    return result;
                },
                blockquote: ({ children }) => (
                    <blockquote className="md-blockquote">
                        <div className="md-blockquote-content">{children}</div>
                    </blockquote>
                ),
                a: ({ href, children }) => (
                    <a href={href} target="_blank" rel="noopener noreferrer" className="md-link">
                        {children}
                        <svg className="w-3 h-3 inline-block ml-0.5 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                        </svg>
                    </a>
                ),
                table: ({ children }) => (
                    <div className="md-table-wrapper"><table className="md-table">{children}</table></div>
                ),
                thead: ({ children }) => <thead className="md-thead">{children}</thead>,
                tbody: ({ children }) => <tbody className="md-tbody">{children}</tbody>,
                tr: ({ children }) => <tr className="md-tr">{children}</tr>,
                th: ({ children, style }) => <th className="md-th" style={style}>{children}</th>,
                td: ({ children, style }) => <td className="md-td" style={style}>{children}</td>,
                strong: ({ children }) => <strong className="md-strong">{children}</strong>,
                em: ({ children }) => <em className="md-em">{children}</em>,
                del: ({ children }) => <del className="md-del">{children}</del>,
                hr: () => <hr className="md-hr" />,
                img: ({ src, alt }) => (
                    <div className="md-image-wrapper">
                        <img src={src} alt={alt} className="md-image" loading="lazy" />
                        {alt && <span className="md-image-caption">{alt}</span>}
                    </div>
                ),
                // Details/summary for collapsible sections (from HTML in markdown)
                details: ({ children }) => (
                    <details className="md-details">{children}</details>
                ),
                summary: ({ children }) => (
                    <summary className="md-summary">{children}</summary>
                ),
                // Superscript / subscript for footnotes etc
                sup: ({ children }) => <sup className="md-sup">{children}</sup>,
                sub: ({ children }) => <sub className="md-sub">{children}</sub>,
            }}
        >
            {safeContent}
        </ReactMarkdown>
    );
}

// ─── Action bar buttons — ChatGPT / Claude style ────────────────────────────
function ActionButton({ icon, activeIcon, label, onClick, isActive = false }) {
    const [active, setActive] = useState(isActive);
    return (
        <button
            onClick={() => { setActive(!active); onClick?.(!active); }}
            title={label}
            className={`inline-flex items-center justify-center w-7 h-7 rounded-lg transition-all duration-150
                ${active
                    ? 'text-accent bg-accent/10'
                    : 'text-text-muted hover:text-text-secondary hover:bg-surface-overlay'}`}
        >
            {active ? (activeIcon || icon) : icon}
        </button>
    );
}

function CopyActionButton({ content }) {
    const [copied, setCopied] = useState(false);
    return (
        <button
            onClick={async () => {
                await navigator.clipboard.writeText(content);
                setCopied(true);
                setTimeout(() => setCopied(false), 2000);
            }}
            title={copied ? 'Copied!' : 'Copy'}
            className={`inline-flex items-center justify-center w-7 h-7 rounded-lg transition-all duration-150
                ${copied
                    ? 'text-green-500 bg-green-500/10'
                    : 'text-text-muted hover:text-text-secondary hover:bg-surface-overlay'}`}
        >
            {copied ? (
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                </svg>
            ) : (
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
            )}
        </button>
    );
}

/**
 * Try to parse a DATA_ANALYSIS JSON payload from the agent response.
 * Returns { stdout, exit_code, base64_chart, explanation } or null.
 */
function tryParseDataAnalysis(content) {
    if (!content) return null;
    const trimmed = content.trim();
    if (!trimmed.startsWith('{')) return null;
    // Guard: must end with } and not be too complex (multi-source)
    if (!trimmed.endsWith('}')) return null;
    try {
        const parsed = JSON.parse(trimmed);
        if ('stdout' in parsed || 'base64_chart' in parsed || 'explanation' in parsed) {
            return parsed;
        }
    } catch { /**/ }
    return null;
}

/**
 * Convert a research JSON payload {executive_summary, key_findings, sources, ...}
 * into a human-readable markdown string so it renders properly.
 */
function tryParseResearchJSON(content) {
    if (!content) return null;
    const trimmed = content.trim();
    if (!trimmed.startsWith('{')) return null;
    try {
        const p = JSON.parse(trimmed);
        if (!('executive_summary' in p) && !('key_findings' in p) && !('findings' in p)) return null;

        const lines = [];

        if (p.executive_summary) {
            lines.push(`## Summary\n\n${p.executive_summary}`);
        }

        const findings = p.key_findings || p.findings || [];
        if (findings.length) {
            lines.push(`\n## Key Findings\n`);
            findings.forEach(f => lines.push(`- ${typeof f === 'string' ? f : JSON.stringify(f)}`));
        }

        if (p.methodology) lines.push(`\n## Methodology\n\n${p.methodology}`);
        if (p.conclusion)   lines.push(`\n## Conclusion\n\n${p.conclusion}`);
        if (p.limitations)  lines.push(`\n## Limitations\n\n${p.limitations}`);

        const sources = p.sources || p.references || [];
        if (sources.length) {
            lines.push(`\n## Sources\n`);
            sources.forEach((s, i) => {
                const url   = typeof s === 'string' ? s : (s.url || s.link || '');
                const title = typeof s === 'object' ? (s.title || s.name || url) : url;
                lines.push(url ? `${i + 1}. [${title}](${url})` : `${i + 1}. ${title}`);
            });
        }

        return lines.join('\n');
    } catch { /**/ }
    return null;
}

/**
 * Parse multi-tool synthesis responses that look like:
 *   [Source 1 — data_profiler]\n<text>\n\n---\n\n[Source 2 — python_tool]\n{...json...}
 * Returns an array of { tool, raw, json } blocks, or null if this format is not detected.
 */
function tryParseMultiSource(content) {
    if (!content) return null;
    if (!content.includes('[Source ')) return null;
    if (!/\[Source \d+ — [^\]]+\]/.test(content)) return null;

    // Split on --- that appears at the start of a line, not inside JSON/code
    const rawBlocks = content.split(/\n---\n/);
    const blocks = [];

    for (const block of rawBlocks) {
        const trimmed = block.trim();
        if (!trimmed) continue;
        const m = trimmed.match(/^\[Source \d+ — ([^\]]+)\]\n?([\s\S]*)/);
        if (!m) {
            if (trimmed) blocks.push({ tool: null, raw: trimmed, json: null });
            continue;
        }
        const tool = m[1].trim();
        const body = m[2].trim();
        let json = null;
        // Only try JSON parse if body starts with { and ends with }
        if (body.startsWith('{') && body.endsWith('}')) {
            try { json = JSON.parse(body); } catch { /**/ }
        }
        blocks.push({ tool, raw: body, json });
    }

    return blocks.length > 0 ? blocks : null;
}

function extractPythonCode(content) {
    if (!content) return null;
    const match = content.match(/```python\n([\s\S]*?)```/);
    return match ? match[1] : null;
}

// Tool badge metadata — shown below completed AI responses
const TOOL_BADGE = {
    rag_tool:       { icon: '🔍', label: 'RAG Search' },
    research_tool:  { icon: '🌐', label: 'Web Research' },
    python_tool:    { icon: '🐍', label: 'Python' },
    data_profiler:  { icon: '🧠', label: 'Data Profile' },
    quiz_tool:      { icon: '📝', label: 'Quiz' },
    flashcard_tool: { icon: '🃏', label: 'Flashcards' },
    ppt_tool:       { icon: '📊', label: 'Slides' },
    code_repair:    { icon: '🔧', label: 'Code Repair' },
};

export default memo(function ChatMessage({ message, notebookId }) {
    const isUser = message.role === 'user';
    const blocks = message.blocks || [];
    const agentMeta = message.agentMeta || null;
    const stepLog = agentMeta?.step_log || message.stepLog || [];
    const generatedFiles = agentMeta?.generated_files || message.generatedFiles || [];

    // Try to parse special payloads
    const dataAnalysis = !isUser ? tryParseDataAnalysis(message.content) : null;
    const multiSource  = !isUser && !dataAnalysis ? tryParseMultiSource(message.content) : null;
    const researchMarkdown = !isUser && !dataAnalysis && !multiSource ? tryParseResearchJSON(message.content) : null;
    const pythonCode = !isUser && !dataAnalysis && !multiSource && !researchMarkdown ? extractPythonCode(message.content) : null;

    const renderAIContent = () => {
        if (dataAnalysis) {
            return (
                <div className="markdown-content">
                    {dataAnalysis.base64_chart && (
                        <ChartRenderer
                            base64Chart={dataAnalysis.base64_chart}
                            explanation={dataAnalysis.explanation}
                            title="Data Analysis Chart"
                        />
                    )}
                    {!dataAnalysis.base64_chart && dataAnalysis.explanation && (
                        <MarkdownRenderer content={dataAnalysis.explanation} />
                    )}
                    {dataAnalysis.stdout && (
                        <details className="mt-3 group/raw" open={!dataAnalysis.explanation}>
                            <summary className="cursor-pointer text-xs text-text-muted hover:text-text-secondary select-none list-none flex items-center gap-1.5 py-1">
                                <svg className="w-3 h-3 transition-transform group-open/raw:rotate-90" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                </svg>
                                Raw output
                            </summary>
                            <pre className="mt-1.5 text-xs font-mono px-3 py-2.5 rounded-lg bg-surface-overlay border border-border/30 overflow-x-auto whitespace-pre-wrap text-text-secondary">{dataAnalysis.stdout}</pre>
                        </details>
                    )}
                    {message.generatedCode && (
                        <ExecutionPanel
                            code={message.generatedCode}
                           
                            initialOutput={dataAnalysis.stdout || ''}
                            initialExitCode={dataAnalysis.exit_code ?? null}
                        />
                    )}
                </div>
            );
        }

        if (researchMarkdown) {
            return (
                <div className="markdown-content">
                    <MarkdownRenderer content={researchMarkdown} />
                </div>
            );
        }

        if (multiSource) {
            return (
                <div className="space-y-4">
                    {multiSource.map((block, i) => {
                        const meta = block.tool ? TOOL_BADGE[block.tool] : null;
                        const analysis = block.json && ('stdout' in block.json || 'base64_chart' in block.json || 'explanation' in block.json)
                            ? block.json : null;
                        const researchMd = !analysis && block.json ? tryParseResearchJSON(block.raw) : null;

                        return (
                            <div key={i}>
                                {meta && (
                                    <div className="flex items-center gap-1.5 mb-2">
                                        <span className="text-xs text-text-muted font-medium">{meta.icon} {meta.label}</span>
                                    </div>
                                )}
                                {analysis && (
                                    <div className="markdown-content">
                                        {analysis.base64_chart && (
                                            <ChartRenderer base64Chart={analysis.base64_chart} explanation={analysis.explanation} title="Data Analysis Chart" />
                                        )}
                                        {!analysis.base64_chart && analysis.explanation && (
                                            <MarkdownRenderer content={analysis.explanation} />
                                        )}
                                        {analysis.stdout && (
                                            <details className="mt-2 group/raw">
                                                <summary className="cursor-pointer text-xs text-text-muted hover:text-text-secondary select-none list-none flex items-center gap-1.5 py-1">
                                                    <svg className="w-3 h-3 transition-transform group-open/raw:rotate-90" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                                    </svg>
                                                    Raw output
                                                </summary>
                                                <pre className="mt-1 text-xs font-mono px-3 py-2 rounded-lg bg-surface-overlay border border-border/30 overflow-x-auto whitespace-pre-wrap text-text-secondary">{analysis.stdout}</pre>
                                            </details>
                                        )}
                                    </div>
                                )}
                                {researchMd && (
                                    <div className="markdown-content">
                                        <MarkdownRenderer content={researchMd} />
                                    </div>
                                )}
                                {!analysis && !researchMd && (
                                    <div className="markdown-content">
                                        <MarkdownRenderer content={block.raw} />
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            );
        }

        if (blocks.length > 0) {
            return (
                <div className="markdown-content">
                    {blocks.map((block) => (
                        <BlockHoverMenu key={block.id} blockId={block.id}>
                            <MarkdownRenderer content={block.text} />
                        </BlockHoverMenu>
                    ))}
                    {pythonCode && <ExecutionPanel code={pythonCode} />}
                </div>
            );
        }

        return (
            <div className="markdown-content">
                <MarkdownRenderer content={message.content} />
                {pythonCode && <ExecutionPanel code={pythonCode} />}
                {message.chartData?.base64_chart && (
                    <ChartRenderer
                        base64Chart={message.chartData.base64_chart}
                        explanation={message.chartData.explanation}
                        title={message.chartData.title || 'Chart'}
                    />
                )}
            </div>
        );
    };

    // ─────────── User message ───────────
    if (isUser) {
        return (
            <div className="chat-msg chat-msg-user flex justify-end py-3">
                <div className="max-w-[80%] sm:max-w-[70%]">
                    <div className="user-bubble">
                        <p className="whitespace-pre-wrap text-[15px] leading-relaxed">{message.content}</p>
                    </div>
                </div>
            </div>
        );
    }

    // ─────────── AI message ───────────
    return (
        <div className="chat-msg chat-msg-ai group py-5">
            <div className="flex gap-3 w-full">
                {/* Avatar */}
                <div className="ai-avatar flex-shrink-0 mt-0.5">
                    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                    {/* Agent steps — collapsible drawer above content */}
                    {stepLog.length > 0 && (
                        <AgentActionBlock
                            stepLog={stepLog}
                            toolsUsed={agentMeta?.tools_used || []}
                            totalTime={agentMeta?.total_time || 0}
                            isStreaming={false}
                        />
                    )}

                    {/* Main content */}
                    {renderAIContent()}

                    {/* Generated File Cards */}
                    {generatedFiles.length > 0 && (
                        <div className="flex flex-wrap gap-2 mt-3">
                            {generatedFiles.map((file, idx) => (
                                <GeneratedFileCard
                                    key={`${file.filename}-${idx}`}
                                    filename={file.filename}
                                    downloadUrl={file.download_url}
                                    size={file.size}
                                    fileType={file.type}
                                />
                            ))}
                        </div>
                    )}

                    {/* Citations */}
                    {message.citations && message.citations.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mt-3">
                            {message.citations.map((citation, idx) => (
                                <span key={idx} className="citation">
                                    <span className="citation-number">{idx + 1}</span>
                                    <span className="truncate max-w-[100px]">{citation.source || 'Source'}</span>
                                </span>
                            ))}
                        </div>
                    )}

                    {/* Action bar — visible on hover like Claude/ChatGPT */}
                    <div className="ai-action-bar opacity-0 group-hover:opacity-100 transition-opacity duration-150 mt-2 flex items-center gap-0.5">
                        <CopyActionButton content={message.content} />
                        <ActionButton
                            label="Good response"
                            icon={
                                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                                </svg>
                            }
                        />
                        <ActionButton
                            label="Bad response"
                            icon={
                                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
                                </svg>
                            }
                        />
                    </div>

                    {/* Tool badges — concise inline indicators */}
                    {agentMeta?.tools_used?.length > 0 && !stepLog.length && (
                        <div className="flex flex-wrap gap-1.5 mt-2.5">
                            {[...new Set(agentMeta.tools_used)].map(tool => {
                                const b = TOOL_BADGE[tool];
                                if (!b) return null;
                                return (
                                    <span
                                        key={tool}
                                        className="inline-flex items-center gap-1 text-xs text-text-muted px-2 py-0.5 rounded-full bg-surface-overlay/60 border border-border/20"
                                    >
                                        {b.icon} {b.label}
                                    </span>
                                );
                            })}
                        </div>
                    )}

                    {/* Legacy agent steps panel */}
                    {agentMeta && !stepLog.length && <AgentStepsPanel meta={agentMeta} />}
                </div>
            </div>
        </div>
    );
});
