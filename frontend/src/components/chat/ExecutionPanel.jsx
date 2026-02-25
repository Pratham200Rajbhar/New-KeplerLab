import { useState, useRef, useEffect } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { executeCode } from '../../api/chat';

/**
 * ExecutionPanel — shows generated Python code + Run button + streaming terminal.
 *
 * Props:
 *   code        — Python code string to display
 *   notebookId  — for execution API call
 *   initialOutput — optional pre-populated stdout (from agent run)
 *   initialExitCode — optional exit code from agent run
 */
export default function ExecutionPanel({ code, notebookId, initialOutput = '', initialExitCode = null }) {
    const [collapsed, setCollapsed] = useState(false);
    const [running, setRunning] = useState(false);
    const [output, setOutput] = useState(initialOutput);
    const [exitCode, setExitCode] = useState(initialExitCode);
    const terminalRef = useRef(null);

    useEffect(() => {
        if (terminalRef.current) {
            terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
        }
    }, [output]);

    const handleRun = async () => {
        if (running) return;
        setRunning(true);
        setOutput('');
        setExitCode(null);

        try {
            const response = await executeCode(code, notebookId);
            if (!response.body) throw new Error('No response body');

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const parts = buffer.split('\n\n');
                buffer = parts.pop();

                for (const part of parts) {
                    const lines = part.split('\n');
                    let eventName = '';
                    let dataStr = '';
                    for (const line of lines) {
                        if (line.startsWith('event: ')) eventName = line.slice(7).trim();
                        else if (line.startsWith('data: ')) dataStr = line.slice(6).trim();
                    }
                    if (!eventName || !dataStr) continue;
                    try {
                        const payload = JSON.parse(dataStr);
                        if (eventName === 'stdout') {
                            setOutput((prev) => prev + payload.line + '\n');
                        } else if (eventName === 'result') {
                            setExitCode(payload.exit_code ?? 0);
                            if (payload.stderr) {
                                setOutput((prev) => prev + '\n[stderr]\n' + payload.stderr);
                            }
                        } else if (eventName === 'error') {
                            setOutput((prev) => prev + '\n⚠ Error: ' + (payload.error || 'Unknown'));
                            setExitCode(-1);
                        }
                    } catch { /* skip malformed */ }
                }
            }
        } catch (err) {
            setOutput((prev) => prev + '\n⚠ ' + err.message);
            setExitCode(-1);
        } finally {
            setRunning(false);
        }
    };

    return (
        <div className="execution-panel">
            {/* Code block header */}
            <div className="execution-header">
                <div className="execution-header-left">
                    <span className="execution-icon">📝</span>
                    <span className="execution-title">Generated Script</span>
                    <span className="execution-lang">python</span>
                </div>
                <div className="execution-header-right">
                    <button
                        className="execution-collapse-btn"
                        onClick={() => setCollapsed((v) => !v)}
                        title={collapsed ? 'Expand' : 'Collapse'}
                    >
                        {collapsed ? '▶ Expand' : '▼ Collapse'}
                    </button>
                </div>
            </div>

            {/* Code viewer */}
            {!collapsed && (
                <div className="execution-code">
                    <SyntaxHighlighter
                        language="python"
                        style={oneDark}
                        customStyle={{ margin: 0, borderRadius: '0 0 8px 8px', fontSize: '13px', maxHeight: '300px' }}
                    >
                        {code}
                    </SyntaxHighlighter>
                </div>
            )}

            {/* Action bar */}
            <div className="execution-actions">
                <button
                    className={`execution-run-btn ${running ? 'execution-run-btn--running' : ''}`}
                    onClick={handleRun}
                    disabled={running}
                >
                    {running ? (
                        <>
                            <span className="execution-spinner" />
                            Running...
                        </>
                    ) : '▶ Run Script'}
                </button>
                {exitCode !== null && (
                    <span className={`execution-exit-badge ${exitCode === 0 ? 'exit-ok' : 'exit-err'}`}>
                        Exit: {exitCode}
                    </span>
                )}
            </div>

            {/* Terminal output */}
            {(output || running) && (
                <div className="terminal-box" ref={terminalRef}>
                    <div className="terminal-header">
                        <span className="terminal-icon">📟</span>
                        <span>Terminal Output</span>
                        {running && <span className="terminal-running-dot" />}
                    </div>
                    <pre className="terminal-content">{output || 'Running...'}</pre>
                </div>
            )}
        </div>
    );
}
