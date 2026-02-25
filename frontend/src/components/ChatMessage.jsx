import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useState, memo } from 'react';
import AgentStepsPanel from './chat/AgentStepsPanel';
import ExecutionPanel from './chat/ExecutionPanel';
import ChartRenderer from './chat/ChartRenderer';
import BlockHoverMenu from './chat/BlockHoverMenu';

// Custom code theme with enhanced styling
const customCodeTheme = {
    ...oneDark,
    'pre[class*="language-"]': {
        ...oneDark['pre[class*="language-"]'],
        background: 'var(--code-bg, linear-gradient(135deg, #1e1e2e 0%, #252536 100%))',
        borderRadius: '12px',
        border: '1px solid var(--border)',
        margin: '16px 0',
        padding: '16px',
        fontSize: '13px',
    },
};

function CopyButton({ code }) {
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        await navigator.clipboard.writeText(code);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <button onClick={handleCopy} className="copy-code-btn" title="Copy code">
            {copied ? (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
 */
export function MarkdownRenderer({ content, notebookId }) {
    return (
        <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
                h1: ({ children }) => (
                    <h1 className="md-heading md-h1">
                        <span className="md-heading-icon">📌</span>{children}
                    </h1>
                ),
                h2: ({ children }) => (
                    <h2 className="md-heading md-h2">
                        <span className="md-heading-icon">✨</span>{children}
                    </h2>
                ),
                h3: ({ children }) => <h3 className="md-heading md-h3">{children}</h3>,
                h4: ({ children }) => <h4 className="md-heading md-h4">{children}</h4>,
                p: ({ children }) => <p className="md-paragraph">{children}</p>,
                ul: ({ children }) => <ul className="md-list md-ul">{children}</ul>,
                ol: ({ children }) => <ol className="md-list md-ol">{children}</ol>,
                li: ({ children }) => <li className="md-list-item">{children}</li>,
                code: ({ inline, className, children, ...props }) => {
                    const match = /language-(\w+)/.exec(className || '');
                    const codeString = String(children).replace(/\n$/, '');
                    if (!inline && (match || codeString.includes('\n'))) {
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
                                    {...props}
                                >
                                    {codeString}
                                </SyntaxHighlighter>
                            </div>
                        );
                    }
                    return <code className="md-inline-code" {...props}>{children}</code>;
                },
                pre: ({ children }) => <>{children}</>,
                blockquote: ({ children }) => (
                    <blockquote className="md-blockquote">
                        <div className="md-blockquote-icon">💡</div>
                        <div className="md-blockquote-content">{children}</div>
                    </blockquote>
                ),
                a: ({ href, children }) => (
                    <a href={href} target="_blank" rel="noopener noreferrer" className="md-link">
                        {children}
                        <svg className="w-3 h-3 inline-block ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
                th: ({ children }) => <th className="md-th">{children}</th>,
                td: ({ children }) => <td className="md-td">{children}</td>,
                strong: ({ children }) => <strong className="md-strong">{children}</strong>,
                em: ({ children }) => <em className="md-em">{children}</em>,
                del: ({ children }) => <del className="md-del">{children}</del>,
                hr: () => <hr className="md-hr" />,
                img: ({ src, alt }) => (
                    <div className="md-image-wrapper">
                        <img src={src} alt={alt} className="md-image" />
                        {alt && <span className="md-image-caption">{alt}</span>}
                    </div>
                ),
            }}
        >
            {content}
        </ReactMarkdown>
    );
}

/**
 * Try to parse a DATA_ANALYSIS JSON payload from the agent response.
 * Returns { stdout, exit_code, base64_chart, explanation } or null.
 */
function tryParseDataAnalysis(content) {
    if (!content) return null;
    // The python_tool returns a JSON string for DATA_ANALYSIS intent
    const trimmed = content.trim();
    if (!trimmed.startsWith('{')) return null;
    try {
        const parsed = JSON.parse(trimmed);
        if ('stdout' in parsed || 'base64_chart' in parsed || 'explanation' in parsed) {
            return parsed;
        }
    } catch { /**/ }
    return null;
}

/**
 * Extract python code block from markdown-style response.
 * Returns the first ```python ... ``` block content or null.
 */
function extractPythonCode(content) {
    if (!content) return null;
    const match = content.match(/```python\n([\s\S]*?)```/);
    return match ? match[1] : null;
}

export default memo(function ChatMessage({ message, notebookId }) {
    const isUser = message.role === 'user';
    const blocks = message.blocks || [];  // [{id, index, text}]
    const agentMeta = message.agentMeta || null;

    // Try to parse special payloads
    const dataAnalysis = !isUser ? tryParseDataAnalysis(message.content) : null;
    const pythonCode = !isUser && !dataAnalysis ? extractPythonCode(message.content) : null;

    const renderAIContent = () => {
        // DATA_ANALYSIS: JSON payload with chart + explanation
        if (dataAnalysis) {
            return (
                <div className="markdown-content">
                    {/* Show stdout as execution panel if code was present */}
                    {message.generatedCode && (
                        <ExecutionPanel
                            code={message.generatedCode}
                            notebookId={notebookId}
                            initialOutput={dataAnalysis.stdout || ''}
                            initialExitCode={dataAnalysis.exit_code ?? null}
                        />
                    )}
                    {dataAnalysis.base64_chart && (
                        <ChartRenderer
                            base64Chart={dataAnalysis.base64_chart}
                            explanation={dataAnalysis.explanation}
                            title="Data Analysis Chart"
                        />
                    )}
                    {!dataAnalysis.base64_chart && dataAnalysis.explanation && (
                        <div className="chart-insight">
                            <span className="chart-insight-icon">💡</span>
                            <div className="chart-insight-text">{dataAnalysis.explanation}</div>
                        </div>
                    )}
                    {!dataAnalysis.base64_chart && dataAnalysis.stdout && (
                        <div className="terminal-box" style={{ marginTop: '12px' }}>
                            <div className="terminal-header"><span className="terminal-icon">📟</span> Output</div>
                            <pre className="terminal-content">{dataAnalysis.stdout}</pre>
                        </div>
                    )}
                </div>
            );
        }

        // Block-aware rendering (when backend sends block IDs)
        if (blocks.length > 0) {
            return (
                <div className="markdown-content">
                    {blocks.map((block) => (
                        <BlockHoverMenu key={block.id} blockId={block.id}>
                            <MarkdownRenderer content={block.text} notebookId={notebookId} />
                        </BlockHoverMenu>
                    ))}
                    {/* Execution panel for code in the message */}
                    {pythonCode && (
                        <ExecutionPanel
                            code={pythonCode}
                            notebookId={notebookId}
                        />
                    )}
                </div>
            );
        }

        // Default: markdown render with optional code execution panel
        return (
            <div className="markdown-content">
                <MarkdownRenderer content={message.content} notebookId={notebookId} />
                {pythonCode && (
                    <ExecutionPanel code={pythonCode} notebookId={notebookId} />
                )}
                {/* Standalone chart from message chartData */}
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

    return (
        <div className={`message flex w-full ${isUser ? 'justify-end message-user' : 'justify-start message-ai'}`}>
            <div className={`message-content ${isUser ? 'max-w-[80%]' : 'w-full'}`}>
                <div className="message-bubble">
                    {isUser ? (
                        <p className="whitespace-pre-wrap">{message.content}</p>
                    ) : (
                        renderAIContent()
                    )}
                </div>

                {/* Citations */}
                {message.citations && message.citations.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-2">
                        {message.citations.map((citation, idx) => (
                            <span key={idx} className="citation">
                                <span className="citation-number">{idx + 1}</span>
                                <span className="truncate max-w-[100px]">{citation.source || 'Source'}</span>
                            </span>
                        ))}
                    </div>
                )}

                {/* Agent Steps Panel */}
                {!isUser && agentMeta && <AgentStepsPanel meta={agentMeta} />}
            </div>
        </div>
    );
});
