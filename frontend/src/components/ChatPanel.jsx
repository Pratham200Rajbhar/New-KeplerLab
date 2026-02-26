import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { streamChat, getChatHistory, streamResearch, getSuggestions, getChatSessions, createChatSession, deleteChatSession } from '../api/chat';
import ChatMessage from './ChatMessage';
import { MarkdownRenderer, sanitizeStreamingMarkdown } from './ChatMessage';
import SuggestionDropdown from './chat/SuggestionDropdown';
import ResearchProgress from './chat/ResearchProgress';
import AgentThinkingBar from './chat/AgentThinkingBar';
import AgentActionBlock from './chat/AgentActionBlock';
import Modal from './Modal';

const QUICK_ACTIONS = [
    { id: 'summarize', label: 'Summarize', icon: '📝' },
    { id: 'explain', label: 'Explain this', icon: '💡' },
    { id: 'keypoints', label: 'Key points', icon: '🎯' },
    { id: 'studyguide', label: 'Study guide', icon: '📚' },
];

const RESEARCH_STEPS_TEMPLATE = [
    { label: 'Planning queries', status: 'pending' },
    { label: 'Searching sources', status: 'pending' },
    { label: 'Extracting content', status: 'pending' },
    { label: 'Clustering themes', status: 'pending' },
    { label: 'Writing report', status: 'pending' },
];

/** Parse SSE stream from a Response into a structured object. */
async function readSSEStream(response, callbacks = {}) {
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
            let dataLines = [];
            for (const line of lines) {
                if (line.startsWith('event: ')) eventName = line.slice(7).trim();
                else if (line.startsWith('data: ')) dataLines.push(line.slice(6));
                else if (line.startsWith('data:')) dataLines.push(line.slice(5));
            }
            const dataStr = dataLines.join('\n').trim();
            if (!eventName || !dataStr) continue;
            try {
                const payload = JSON.parse(dataStr);
                callbacks[eventName]?.(payload);
            } catch { /* skip malformed */ }
        }
    }
}

export default function ChatPanel() {
    const {
        currentMaterial,
        currentNotebook,
        messages,
        setMessages,
        addMessage,
        loading,
        setLoadingState,
        draftMode,
        selectedSources,
        materials,
    } = useApp();

    const effectiveIds = useMemo(() => Array.from(selectedSources).filter(id => {
        const mat = materials.find(m => m.id === id);
        return mat && mat.status === 'completed';
    }), [selectedSources, materials]);
    const hasSource = effectiveIds.length > 0;
    // True when the user has selected sources but they are still being processed
    const isSourceProcessing = !hasSource && selectedSources.size > 0;

    const [inputValue, setInputValue] = useState('');
    const [streamingContent, setStreamingContent] = useState('');
    const [agentStepLabel, setAgentStepLabel] = useState('');

    // Agent thinking state
    const [isThinking, setIsThinking] = useState(false);
    const [thinkingStep, setThinkingStep] = useState('');
    const [stepLog, setStepLog] = useState([]);
    const [currentStepNum, setCurrentStepNum] = useState(0);
    const [pendingFiles, setPendingFiles] = useState([]);
    const [isRepair, setIsRepair] = useState(false);
    const [repairCount, setRepairCount] = useState(0);

    const [isFetchingSuggestions, setIsFetchingSuggestions] = useState(false);
    const [showSuggestions, setShowSuggestions] = useState(false);
    const [suggestions, setSuggestions] = useState([]);

    // Toast for user-visible error feedback
    const [toastMsg, setToastMsg] = useState(null);
    const showToast = useCallback((msg) => {
        setToastMsg(msg);
        setTimeout(() => setToastMsg(null), 4000);
    }, []);

    // Live streaming step log (shown before commit)
    const [liveStepLog, setLiveStepLog] = useState([]);

    // Sessions state
    const [sessions, setSessions] = useState([]);
    const [searchParams, setSearchParams] = useSearchParams();
    const currentSessionId = searchParams.get('session') || null;
    const setCurrentSessionId = useCallback((id) => {
        setSearchParams(prev => {
            const next = new URLSearchParams(prev);
            if (id) { next.set('session', id); } else { next.delete('session'); }
            return next;
        }, { replace: true });
    }, [setSearchParams]);
    const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);
    const [historySearchTerm, setHistorySearchTerm] = useState('');

    // Research state
    const [researchMode, setResearchMode] = useState(false);
    const [researchSteps, setResearchSteps] = useState([]);
    const [researchQuery, setResearchQuery] = useState('');

    const messagesEndRef = useRef(null);
    const textareaRef = useRef(null);
    const isChattingRef = useRef(false);
    const abortControllerRef = useRef(null);

    // Abort any in-flight stream on unmount
    useEffect(() => {
        return () => {
            abortControllerRef.current?.abort();
        };
    }, []);

    useEffect(() => {
        isChattingRef.current = loading.chat || researchMode;
    }, [loading.chat, researchMode]);

    // Load initial sessions on notebook change
    useEffect(() => {
        const loadHistory = async () => {
            if (currentNotebook?.id && !currentNotebook.isDraft && !draftMode) {
                try {
                    const sessionsData = await getChatSessions(currentNotebook.id);
                    const newSessions = sessionsData.sessions || [];
                    setSessions(newSessions);

                    // Validate URL session param, fallback to first session if stale or missing
                    const urlSession = searchParams.get('session');
                    const isValid = urlSession && newSessions.some(s => s.id === urlSession);
                    if (!isValid && newSessions.length > 0) {
                        setCurrentSessionId(newSessions[0].id);
                    } else if (!isValid) {
                        setCurrentSessionId(null);
                    }
                } catch (error) {
                    console.error('Failed to load initial sessions:', error);
                }
            } else {
                setSessions([]);
                // Don't clear session ID from URL when notebook simply isn't loaded yet.
                // The session param in the URL should survive so that when the notebook
                // finishes loading we can restore the exact session the user was viewing.
            }
        };
        loadHistory();
    }, [currentNotebook?.id, draftMode]); // eslint-disable-line react-hooks/exhaustive-deps

    // Load messages when currentSessionId or notebook changes
    useEffect(() => {
        let cancelled = false;

        const loadMessages = async (attempt = 0) => {
            if (currentNotebook?.id && !currentNotebook.isDraft && !draftMode) {
                try {
                    const history = await getChatHistory(currentNotebook.id, currentSessionId);
                    // Prevent overwriting the optimistic UI if we are in the middle of sending a message
                    if (cancelled || isChattingRef.current) return;

                    if (history && history.length > 0) {
                        const loadedMessages = history.map(msg => ({
                            id: msg.id,
                            role: msg.role,
                            content: msg.content,
                            timestamp: new Date(msg.created_at),
                            blocks: msg.blocks || [],
                            agentMeta: msg.agent_meta || null,
                        }));
                        setMessages(loadedMessages);
                    } else {
                        setMessages([]);
                    }
                } catch (error) {
                    console.error('Failed to load chat history:', error);
                    // Retry once after a short delay (handles token refresh race)
                    if (attempt < 1 && !cancelled) {
                        setTimeout(() => { if (!cancelled) loadMessages(attempt + 1); }, 800);
                        return;
                    }
                    if (!isChattingRef.current && !cancelled) setMessages([]);
                }
            } else if (!currentNotebook?.id) {
                // No notebook loaded yet — don't clear; wait for notebook to arrive.
            } else {
                setMessages([]);
            }
        };
        loadMessages();

        return () => { cancelled = true; };
    }, [currentNotebook?.id, currentSessionId, draftMode, setMessages]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, streamingContent]);

    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
        }
    }, [inputValue]);

    useEffect(() => {
        setShowSuggestions(false);
        setSuggestions([]);
    }, [inputValue]);

    const handleCreateSession = async () => {
        if (!currentNotebook?.id) return;
        try {
            const res = await createChatSession(currentNotebook.id, "New Chat");
            if (res.session_id) {
                setCurrentSessionId(res.session_id);
                setMessages([]);
                const sessionsData = await getChatSessions(currentNotebook.id);
                setSessions(sessionsData.sessions || []);
            }
        } catch (e) {
            console.error("Failed to create session", e);
            showToast('Failed to create chat session');
        }
    };

    const handleDeleteSession = async (e, sessionId) => {
        e.stopPropagation();
        try {
            await deleteChatSession(sessionId);
            const sessionsData = await getChatSessions(currentNotebook?.id);
            const newSessions = sessionsData.sessions || [];
            setSessions(newSessions);
            if (currentSessionId === sessionId) {
                setCurrentSessionId(newSessions.length > 0 ? newSessions[0].id : null);
            }
        } catch (err) {
            console.error("Failed to delete", err);
            showToast('Failed to delete session');
        }
    };

    const handleSelectSession = (sessionId) => {
        setCurrentSessionId(sessionId);
        setIsHistoryModalOpen(false);
    };

    const handleCreateChatClick = () => {
        handleCreateSession();
        setIsHistoryModalOpen(false);
    };

    const handleStop = useCallback(() => {
        abortControllerRef.current?.abort();
    }, []);

    const handleSend = async (message = inputValue) => {
        if (!message.trim() || !hasSource || !currentNotebook?.id || currentNotebook.isDraft) return;

        const userMessage = message.trim();
        setInputValue('');
        addMessage('user', userMessage);
        setLoadingState('chat', true);
        setStreamingContent('');
        setAgentStepLabel('');
        setIsThinking(true);
        setThinkingStep('');
        setStepLog([]);
        setLiveStepLog([]);
        setCurrentStepNum(0);
        setPendingFiles([]);
        setIsRepair(false);
        setRepairCount(0);

        const ac = new AbortController();
        abortControllerRef.current = ac;

        let accumulated = '';
        let agentMeta = null;
        let messageBlocks = [];
        let committedMsgId = null;
        let localStepLog = [];
        let localPendingFiles = [];

        try {
            let sessionIdToUse = currentSessionId;
            if (!sessionIdToUse) {
                const title = userMessage.slice(0, 30) + (userMessage.length > 30 ? '...' : '');
                const res = await createChatSession(currentNotebook.id, title);
                sessionIdToUse = res.session_id;
                setCurrentSessionId(sessionIdToUse);
                const sessionsData = await getChatSessions(currentNotebook.id);
                setSessions(sessionsData.sessions || []);
            }

            const response = await streamChat(
                null,
                userMessage,
                currentNotebook.id,
                effectiveIds,
                sessionIdToUse,
                ac.signal
            );

            await readSSEStream(response, {
                token: (payload) => {
                    accumulated += payload.content || '';
                    setStreamingContent(accumulated);
                },
                step: (payload) => {
                    const TOOL_STEP_LABELS = {
                        rag_tool:       'Searching materials…',
                        research_tool:  'Researching online…',
                        python_tool:    'Running Python…',
                        data_profiler:  'Profiling dataset…',
                        quiz_tool:      'Generating quiz…',
                        flashcard_tool: 'Creating flashcards…',
                        ppt_tool:       'Building slides…',
                        file_generator: 'Generating file…',
                    };
                    const raw = payload.tool || payload.label || '';
                    const label = TOOL_STEP_LABELS[raw] || payload.label || raw || 'Thinking…';
                    setAgentStepLabel(label);
                    setThinkingStep(label);
                    setCurrentStepNum(prev => prev + 1);
                    // Add a "running" entry to the live step log
                    setLiveStepLog(prev => {
                        // Update last entry if it was running, or add a new running entry
                        const updated = prev.map(s => s.status === 'running' ? { ...s, status: 'success' } : s);
                        return [...updated, { tool: raw, label: TOOL_STEP_LABELS[raw] || raw, status: 'running' }];
                    });
                },
                step_done: (payload) => {
                    const stepEntry = payload.step || { tool: payload.tool, status: payload.status };
                    localStepLog.push(stepEntry);
                    setStepLog(prev => [...prev, stepEntry]);
                    // Update liveStepLog: replace the last running entry with the completed step,
                    // and merge any live stdout/code that arrived during streaming
                    setLiveStepLog(prev => {
                        const lastRunningIdx = prev.findLastIndex(s => s.status === 'running');
                        if (lastRunningIdx === -1) {
                            return [...prev, stepEntry];
                        }
                        const updated = [...prev];
                        // Merge: keep live stdout/code if step_done didn't include them
                        const liveStep = updated[lastRunningIdx];
                        updated[lastRunningIdx] = {
                            ...stepEntry,
                            code: stepEntry.code || liveStep.code || '',
                            stdout: stepEntry.stdout || liveStep.stdout || '',
                        };
                        return updated;
                    });
                    // Also update localStepLog with code from live step
                    setLiveStepLog(prev => {
                        const last = prev[prev.length - 1];
                        if (last && last.code && localStepLog.length > 0) {
                            localStepLog[localStepLog.length - 1].code = last.code;
                        }
                        if (last && last.stdout && localStepLog.length > 0 && !localStepLog[localStepLog.length - 1].stdout) {
                            localStepLog[localStepLog.length - 1].stdout = last.stdout;
                        }
                        return prev;
                    });
                },
                code_written: (payload) => {
                    // Update liveStepLog: inject code into the running step immediately
                    setLiveStepLog(prev => {
                        if (prev.length === 0) return prev;
                        const updated = [...prev];
                        // Find the last running or most recent step
                        const runningIdx = updated.findLastIndex(s => s.status === 'running');
                        const targetIdx = runningIdx !== -1 ? runningIdx : updated.length - 1;
                        updated[targetIdx] = { ...updated[targetIdx], code: payload.code };
                        return updated;
                    });
                },
                code_generating: (_payload) => {
                    // Code is being generated by LLM — update the thinking step
                    setThinkingStep('Generating code…');
                    setLiveStepLog(prev => {
                        if (prev.length === 0) return prev;
                        const updated = [...prev];
                        const runningIdx = updated.findLastIndex(s => s.status === 'running');
                        if (runningIdx !== -1) {
                            updated[runningIdx] = { ...updated[runningIdx], label: 'Generating code…' };
                        }
                        return updated;
                    });
                },
                code_stdout: (payload) => {
                    // Live stdout line from python execution — append to running step
                    const line = payload.line || '';
                    setLiveStepLog(prev => {
                        if (prev.length === 0) return prev;
                        const updated = [...prev];
                        const runningIdx = updated.findLastIndex(s => s.status === 'running');
                        const targetIdx = runningIdx !== -1 ? runningIdx : updated.length - 1;
                        const existing = updated[targetIdx].stdout || '';
                        updated[targetIdx] = {
                            ...updated[targetIdx],
                            stdout: existing ? existing + '\n' + line : line,
                            label: 'Running Python…',
                        };
                        return updated;
                    });
                },
                stdout: (_payload) => {
                    // Batch stdout arrives with step_done — also update the live log
                    const output = _payload.output || '';
                    if (output) {
                        setLiveStepLog(prev => {
                            if (prev.length === 0) return prev;
                            const updated = [...prev];
                            // Find the step that just completed
                            const lastIdx = updated.length - 1;
                            if (!updated[lastIdx].stdout) {
                                updated[lastIdx] = { ...updated[lastIdx], stdout: output };
                            }
                            return updated;
                        });
                    }
                },
                repair_attempt: (payload) => {
                    const count = payload.attempt || 1;
                    setIsRepair(true);
                    setRepairCount(count);
                    setThinkingStep(`Fixing error — attempt ${count}`);
                },
                repair_success: (payload) => {
                    setIsRepair(false);
                    setThinkingStep('Fix applied, re-running…');
                },
                file_ready: (payload) => {
                    localPendingFiles.push(payload);
                    setPendingFiles(prev => [...prev, payload]);
                },
                meta: (payload) => {
                    agentMeta = payload;
                },
                blocks: (payload) => {
                    messageBlocks = payload.blocks || [];
                },
                done: (payload) => {
                    const finalContent = accumulated || (agentMeta && agentMeta.response) || '';
                    const elapsedTime = payload.elapsed || 0;
                    if (finalContent) {
                        // Add message with full metadata including step_log and generated_files
                        const newMsg = {
                            id: `ai-${Date.now()}`,
                            role: 'assistant',
                            content: finalContent,
                            agentMeta: {
                                ...(agentMeta || {}),
                                step_log: localStepLog.length > 0 ? localStepLog : (agentMeta?.step_log || []),
                                generated_files: localPendingFiles.length > 0 ? localPendingFiles : (agentMeta?.generated_files || []),
                                total_time: elapsedTime,
                            },
                            blocks: messageBlocks,
                        };
                        setMessages(prev => [...prev, newMsg]);
                        committedMsgId = newMsg.id;
                    }
                    setStreamingContent('');
                    setIsThinking(false);
                    setLiveStepLog([]);
                    accumulated = '';
                },
                error: (payload) => {
                    addMessage('assistant', `I encountered an error: ${payload.error || 'Streaming error'}`);
                    setStreamingContent('');
                    setIsThinking(false);
                    setLiveStepLog([]);
                    accumulated = '';
                },
            });

            // Flush any remaining content that wasn't committed via done event
            if (accumulated && !committedMsgId) {
                setMessages(prev => [...prev, {
                    id: `ai-${Date.now()}`,
                    role: 'assistant',
                    content: accumulated,
                    agentMeta,
                    blocks: messageBlocks,
                }]);
                setStreamingContent('');
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                // User stopped generation — commit any partial content
                if (accumulated && !committedMsgId) {
                    setMessages(prev => [...prev, {
                        id: `ai-${Date.now()}`,
                        role: 'assistant',
                        content: accumulated,
                        agentMeta,
                        blocks: messageBlocks,
                    }]);
                }
            } else {
                addMessage('assistant', `I encountered an error: ${error.message}`);
            }
            setStreamingContent('');
            setLiveStepLog([]);
        } finally {
            setLoadingState('chat', false);
            setAgentStepLabel('');
            setIsThinking(false);
            setIsRepair(false);
            setRepairCount(0);
            abortControllerRef.current = null;
        }
    };

    const handleResearch = async () => {
        const query = inputValue.trim();
        if (!query || !hasSource || !currentNotebook?.id || loading.chat) return;

        setInputValue('');
        addMessage('user', query);
        setLoadingState('chat', true);
        setResearchMode(true);
        setResearchQuery(query);
        setResearchSteps(RESEARCH_STEPS_TEMPLATE.map(s => ({ ...s })));

        const stepMap = {
            'research_planner': 0,
            'search_executor': 1,
            'content_extractor': 2,
            'theme_clusterer': 3,
            'synthesis_engine': 4,
        };

        const ac = new AbortController();
        abortControllerRef.current = ac;

        let accumulated = '';
        let agentMeta = null;

        const advanceStep = (toolName) => {
            const idx = stepMap[toolName] ?? -1;
            if (idx < 0) return;
            setResearchSteps(prev => prev.map((s, i) => ({
                ...s,
                status: i < idx ? 'done' : i === idx ? 'active' : s.status,
            })));
        };

        try {
            const response = await streamResearch(
                query,
                currentNotebook.id,
                effectiveIds,
                ac.signal,
            );

            await readSSEStream(response, {
                step: (payload) => advanceStep(payload.tool || ''),
                token: (payload) => {
                    accumulated += payload.content || '';
                },
                meta: (payload) => {
                    agentMeta = payload;
                    // Mark all steps done
                    setResearchSteps(prev => prev.map(s => ({ ...s, status: 'done' })));
                },
                done: () => {
                    setResearchMode(false);
                    if (accumulated) {
                        setMessages(prev => [...prev, {
                            id: `ai-research-${Date.now()}`,
                            role: 'assistant',
                            content: accumulated,
                            agentMeta,
                            blocks: [],
                        }]);
                    }
                },
                error: (payload) => {
                    setResearchMode(false);
                    addMessage('assistant', `Research failed: ${payload.error || 'Unknown error'}`);
                },
            });
        } catch (err) {
            setResearchMode(false);
            if (err.name === 'AbortError') {
                // User stopped — commit partial report if any
                if (accumulated) {
                    setMessages(prev => [...prev, {
                        id: `ai-research-${Date.now()}`,
                        role: 'assistant',
                        content: accumulated,
                        agentMeta,
                        blocks: [],
                    }]);
                }
            } else {
                addMessage('assistant', `Research failed: ${err.message}`);
            }
        } finally {
            setLoadingState('chat', false);
            setResearchMode(false); // ensure research mode is always cleared on exit
            abortControllerRef.current = null;
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleQuickAction = (action) => {
        const prompts = {
            summarize: 'Summarize the main points from this document',
            explain: 'Explain the key concepts in simple terms',
            keypoints: 'What are the most important takeaways?',
            studyguide: 'Create a study guide from this content',
        };
        handleSend(prompts[action.id] || action.label);
    };

    const handleGetSuggestions = async () => {
        if (!inputValue.trim() || !hasSource || !currentNotebook?.id) return;
        setIsFetchingSuggestions(true);
        setShowSuggestions(true);
        try {
            const data = await getSuggestions(inputValue, currentNotebook.id);
            setSuggestions(data?.suggestions || []);
        } catch (err) {
            console.error(err);
            setSuggestions([]);
        } finally {
            setIsFetchingSuggestions(false);
        }
    };

    const handleSuggestionSelect = (suggestion) => {
        setShowSuggestions(false);
        setSuggestions([]);
        setInputValue(suggestion);
        handleSend(suggestion);
    };

    const isLoading = loading.chat;
    const showTypingIndicator = isLoading && !streamingContent && !researchMode && liveStepLog.length === 0;

    // Search and Grouping Logic for Chat History
    const filteredSessions = useMemo(() => sessions.filter(s => {
        const searchTerm = historySearchTerm.toLowerCase();
        const matchesTitle = (s.title || 'New Conversation').toLowerCase().includes(searchTerm);
        const matchesContent = s.messages_text ? s.messages_text.toLowerCase().includes(searchTerm) : false;
        return matchesTitle || matchesContent;
    }), [sessions, historySearchTerm]);

    const groupedSessions = useMemo(() => {
        const groups = {
            today: [],
            yesterday: [],
            previous7Days: [],
            older: []
        };

        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);
        const sevenDaysAgo = new Date(today);
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

        filteredSessions.forEach(session => {
            const sessionDate = new Date(session.createdAt || Date.now());
            if (sessionDate >= today) {
                groups.today.push(session);
            } else if (sessionDate >= yesterday) {
                groups.yesterday.push(session);
            } else if (sessionDate >= sevenDaysAgo) {
                groups.previous7Days.push(session);
            } else {
                groups.older.push(session);
            }
        });

        return groups;
    }, [filteredSessions]);

    const renderHistoryGroup = (title, items) => {
        if (items.length === 0) return null;
        return (
            <div className="mb-6 last:mb-0">
                <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3 px-2">
                    {title}
                </h3>
                <div className="space-y-2">
                    {items.map(s => (
                        <div
                            key={s.id}
                            onClick={() => handleSelectSession(s.id)}
                            className={`group relative p-3 rounded-xl transition-all cursor-pointer flex items-center justify-between ${currentSessionId === s.id
                                ? 'bg-accent/5 shadow-sm'
                                : 'bg-surface hover:bg-surface-raised hover:shadow-sm'
                                }`}
                        >
                            <div className="flex items-center gap-4 min-w-0 pr-4">
                                <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 transition-colors ${currentSessionId === s.id ? 'bg-accent/10 text-accent' : 'bg-surface-overlay text-text-muted group-hover:text-accent group-hover:bg-accent/5'
                                    }`}>
                                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                                    </svg>
                                </div>
                                <div className="flex flex-col min-w-0">
                                    <h4 className={`font-medium text-[15px] truncate transition-colors ${currentSessionId === s.id ? 'text-accent' : 'text-text-primary group-hover:text-accent'
                                        }`}>
                                        {s.title || 'New Conversation'}
                                    </h4>
                                    <div className="flex items-center text-[11px] text-text-muted mt-0.5">
                                        {new Date(s.createdAt || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    </div>
                                </div>
                            </div>

                            <button
                                onClick={(e) => handleDeleteSession(e, s.id)}
                                className="opacity-0 group-hover:opacity-100 text-text-muted hover:text-status-error transition-all p-2 rounded-lg hover:bg-red-500/10 flex-shrink-0"
                                title="Delete Chat"
                            >
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                            </button>
                        </div>
                    ))}
                </div>
            </div>
        );
    };

    return (
        <main className="flex-1 bg-surface-50 flex flex-col overflow-hidden relative">
            {/* History Modal */}
            <Modal
                isOpen={isHistoryModalOpen}
                onClose={() => setIsHistoryModalOpen(false)}
                title="Chat History"
                maxWidth="max-w-4xl"
                icon={
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                }
            >
                <div className="flex flex-col md:flex-row h-[70vh] gap-6 -mx-2">
                    {/* Left Sidebar */}
                    <div className="w-full md:w-72 flex flex-col gap-5 flex-shrink-0 pr-6 pl-2">
                        <button
                            onClick={handleCreateChatClick}
                            className="w-full py-3.5 px-4 rounded-xl bg-accent hover:bg-accent-dark text-white font-medium flex items-center justify-center gap-2.5 transition-all shadow-md hover:shadow-lg transform active:scale-[0.98]"
                        >
                            <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
                            </svg>
                            New Conversation
                        </button>

                        <div className="relative group">
                            <svg className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-text-muted group-focus-within:text-accent transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                            </svg>
                            <input
                                type="text"
                                placeholder="Search conversations..."
                                value={historySearchTerm}
                                onChange={(e) => setHistorySearchTerm(e.target.value)}
                                className="w-full pl-10 pr-4 py-2.5 bg-surface-overlay border border-border rounded-xl text-sm focus:outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 transition-all text-text-primary placeholder:text-text-muted"
                            />
                            {historySearchTerm && (
                                <button
                                    onClick={() => setHistorySearchTerm('')}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary transition-colors"
                                >
                                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                    </svg>
                                </button>
                            )}
                        </div>

                        <div className="mt-auto p-4 rounded-xl bg-surface-overlay">
                            <h3 className="text-xs font-bold text-text-muted uppercase tracking-wider mb-3">Overview</h3>
                            <div className="flex items-center justify-between text-sm">
                                <div className="flex items-center gap-2 text-text-secondary">
                                    <svg className="w-4 h-4 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                                    </svg>
                                    Total Chats
                                </div>
                                <span className="font-semibold text-text-primary px-2 py-0.5 rounded-md bg-white dark:bg-black/20 shadow-sm border border-border/50">
                                    {sessions.length}
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Right Content Area */}
                    <div className="flex-1 overflow-y-auto pr-3 flex flex-col">
                        {sessions.length === 0 ? (
                            <div className="flex flex-col items-center justify-center h-full text-center">
                                <div className="w-16 h-16 rounded-2xl bg-accent-subtle text-accent flex items-center justify-center mb-4 shadow-sm">
                                    <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                                    </svg>
                                </div>
                                <h3 className="text-lg text-text-primary font-semibold">No Conversations Yet</h3>
                                <p className="text-sm text-text-secondary mt-2 max-w-sm">
                                    Start a new conversation to begin exploring topics or chatting with your documents.
                                </p>
                            </div>
                        ) : filteredSessions.length === 0 ? (
                            <div className="flex flex-col items-center justify-center h-full text-center">
                                <div className="w-12 h-12 rounded-full bg-surface-overlay text-text-muted flex items-center justify-center mb-3">
                                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                    </svg>
                                </div>
                                <h3 className="text-text-primary font-medium">No results found</h3>
                                <p className="text-sm text-text-muted mt-1">Try adjusting your search term.</p>
                            </div>
                        ) : (
                            <div className="flex flex-col">
                                {renderHistoryGroup("Today", groupedSessions.today)}
                                {renderHistoryGroup("Yesterday", groupedSessions.yesterday)}
                                {renderHistoryGroup("Previous 7 Days", groupedSessions.previous7Days)}
                                {renderHistoryGroup("Older", groupedSessions.older)}
                            </div>
                        )}
                    </div>
                </div>
            </Modal>

            {/* Header */}
            <div className="panel-header border-b border-border bg-surface flex justify-between items-center px-4 py-2.5 shrink-0 gap-3">
                {/* Left — title + session name */}
                <div className="flex items-center gap-2.5 min-w-0">
                    <span className="font-semibold text-text-primary text-sm">Chat</span>
                    {sessions.find(s => s.id === currentSessionId)?.title && (
                        <span className="text-xs text-text-muted bg-surface-overlay px-2 py-0.5 rounded-full truncate max-w-[140px]">
                            {sessions.find(s => s.id === currentSessionId)?.title}
                        </span>
                    )}
                </div>

                {/* Right — source badge + buttons */}
                <div className="flex items-center gap-1.5 flex-shrink-0">
                    {/* Source pill */}
                    {hasSource && (
                        <div className="hidden sm:flex items-center gap-1.5 text-xs px-2 py-1 rounded-full bg-status-success/10 text-status-success border border-status-success/20">
                            <span className="w-1.5 h-1.5 rounded-full bg-status-success" />
                            {selectedSources.size > 1 ? `${selectedSources.size} sources` : '1 source'}
                        </div>
                    )}
                    {/* Processing pill — shown when selected source is still indexing */}
                    {isSourceProcessing && (
                        <div className="hidden sm:flex items-center gap-1.5 text-xs px-2 py-1 rounded-full bg-accent/10 text-accent border border-accent/20 animate-pulse">
                            <span className="w-1.5 h-1.5 rounded-full bg-accent" />
                            Indexing…
                        </div>
                    )}
                    <button
                        onClick={() => setIsHistoryModalOpen(true)}
                        className="btn-secondary py-1.5 px-2.5 flex items-center gap-1.5 text-xs"
                        title="Chat history"
                    >
                        <svg className="w-3.5 h-3.5 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        History
                    </button>
                    <button
                        onClick={handleCreateChatClick}
                        className="btn-icon p-1.5 rounded-lg hover:bg-surface-overlay text-text-muted transition-all"
                        title="New Chat"
                    >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                        </svg>
                    </button>
                </div>
            </div>

            {/* Chat Content */}
            <div className="flex-1 overflow-y-auto">
                {messages.length === 0 && !researchMode ? (
                    <div className="flex flex-col items-center justify-center h-full px-6 py-12">
                        <div className="max-w-lg text-center">
                            {hasSource ? (
                                <>
                                    {/* Active source indicator */}
                                    <div className="inline-flex items-center gap-2 px-3 py-1.5 glass rounded-full mb-6">
                                        <div className="w-2 h-2 bg-status-success rounded-full animate-pulse" />
                                        <span className="text-sm text-text-secondary">
                                            {selectedSources.size > 1
                                                ? <><span className="text-text-primary font-medium">{selectedSources.size} sources</span> selected</>
                                                : <>Ready to explore <span className="text-text-primary font-medium">{materials.find(m => selectedSources.has(m.id))?.filename}</span></>}
                                        </span>
                                    </div>

                                    {/* Removed AI Agent Mode badge */}

                                    <h2 className="text-2xl font-semibold text-text-primary mb-3">
                                        What would you like to know?
                                    </h2>
                                    <p className="text-text-secondary mb-8">
                                        Ask questions, run code, research topics — all inline.
                                    </p>

                                    {/* Quick Actions */}
                                    <div className="flex flex-wrap justify-center gap-2">
                                        {QUICK_ACTIONS.map((action) => (
                                            <button
                                                key={action.id}
                                                className="quick-action-chip"
                                                onClick={() => handleQuickAction(action)}
                                            >
                                                <span>{action.icon}</span>
                                                <span>{action.label}</span>
                                            </button>
                                        ))}
                                    </div>
                                </>
                            ) : isSourceProcessing ? (
                                <>
                                    <div className="w-16 h-16 rounded-2xl glass flex items-center justify-center mx-auto mb-6">
                                        <svg className="w-8 h-8 text-accent animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                        </svg>
                                    </div>
                                    <h2 className="text-2xl font-semibold text-text-primary mb-3">Processing your source…</h2>
                                    <p className="text-text-secondary">
                                        Hold tight while we index your file. Chat will unlock automatically when it's ready.
                                    </p>
                                </>
                            ) : (
                                <>
                                    <div className="w-16 h-16 rounded-2xl glass flex items-center justify-center mx-auto mb-6">
                                        <svg className="w-8 h-8 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                                        </svg>
                                    </div>
                                    <h2 className="text-2xl font-semibold text-text-primary mb-3">Welcome to KeplerLab</h2>
                                    <p className="text-text-secondary">
                                        Add sources to start exploring with AI-powered research assistance
                                    </p>
                                </>
                            )}
                        </div>
                    </div>
                ) : (
                    <div className="max-w-4xl w-full mx-auto px-4 py-8 sm:px-6 md:px-8">
                        {messages.map((msg, idx) => (
                            <ChatMessage
                                key={msg.id}
                                message={msg}
                                notebookId={currentNotebook?.id}
                            />
                        ))}

                        {/* Research progress (live) */}
                        {researchMode && (
                            <div className="message flex w-full justify-start message-ai">
                                <div className="message-content w-full">
                                    <ResearchProgress steps={researchSteps} query={researchQuery} />
                                </div>
                            </div>
                        )}

                        {/* Live streaming bubble */}
                        {(streamingContent || (isThinking && liveStepLog.length > 0)) && (
                            <div className="chat-msg chat-msg-ai group py-5">
                                <div className="flex gap-3 w-full">
                                    <div className="ai-avatar flex-shrink-0 mt-0.5 streaming-pulse">
                                        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                                            <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                                        </svg>
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        {liveStepLog.length > 0 && (
                                            <AgentActionBlock
                                                stepLog={liveStepLog}
                                                toolsUsed={[]}
                                                totalTime={0}
                                                isStreaming={true}
                                            />
                                        )}
                                        {streamingContent && (
                                            <div className="markdown-content">
                                                <MarkdownRenderer content={sanitizeStreamingMarkdown(streamingContent)} />
                                                <span className="streaming-cursor" />
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Typing indicator with agent step label */}
                        {showTypingIndicator && (
                            <div className="chat-msg chat-msg-ai py-5 animate-fade-in">
                                <div className="flex gap-3 w-full">
                                    <div className="ai-avatar flex-shrink-0 mt-0.5 streaming-pulse">
                                        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                                            <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                                        </svg>
                                    </div>
                                    <div className="flex items-center gap-2 py-1">
                                        <div className="typing-indicator">
                                            <span /><span /><span />
                                        </div>
                                        {agentStepLabel && (
                                            <span className="text-xs text-text-muted">{agentStepLabel}</span>
                                        )}
                                    </div>
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>
                )}
            </div>

            {/* Input Area */}
            <div className="p-4 sm:p-6 flex justify-center w-full z-10 sticky bottom-0 bg-gradient-to-t from-surface-100 via-surface-100 to-transparent pt-12">
                <div className="max-w-4xl w-full relative">
                    {/* Agent Thinking Bar — live step progress */}
                    {isThinking && (
                        <AgentThinkingBar
                            isActive={isThinking}
                            currentStep={thinkingStep}
                            stepNumber={currentStepNum}
                            totalSteps={0}
                            isRepair={isRepair}
                            repairCount={repairCount}
                        />
                    )}

                    {/* Suggestion Dropdown */}
                    {hasSource && currentNotebook?.id && !currentNotebook.isDraft && showSuggestions && (
                        <SuggestionDropdown
                            suggestions={suggestions}
                            loading={isFetchingSuggestions}
                            onSelect={handleSuggestionSelect}
                            onClose={() => setShowSuggestions(false)}
                        />
                    )}

                    {/* Removed AI Agent Mode label */}

                    <div className="chat-input-container rounded-2xl shadow-elevated bg-surface-raised border border-border focus-within:ring-2 ring-accent/20 transition-all transform-gpu hover:shadow-lg">
                        <textarea
                            ref={textareaRef}
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder={hasSource
                                ? (isLoading ? 'AI is thinking…' : selectedSources.size > 1 ? `Ask about ${selectedSources.size} sources…` : 'Ask anything about your source…')
                                : isSourceProcessing ? 'Processing source, please wait…' : 'Select a source to start…'}
                            disabled={!hasSource || isLoading}
                            className="flex-1 bg-transparent text-[15px] sm:text-base text-text-primary placeholder-text-muted resize-none outline-none min-h-[48px] max-h-[200px] py-3.5 px-4 leading-relaxed"
                            rows={1}
                        />
                        <div className="flex items-end pb-2.5 pr-2.5 gap-1">
                            {/* ✨ Suggest button */}
                            {inputValue.trim().length > 0 && (
                                <button
                                    onClick={handleGetSuggestions}
                                    disabled={!hasSource || isLoading || isFetchingSuggestions}
                                    className="btn-icon text-accent hover:bg-accent/10 disabled:opacity-30 rounded-[10px] w-9 h-9 flex items-center justify-center transition-all"
                                    title="Get prompt suggestions"
                                >
                                    {isFetchingSuggestions ? (
                                        <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                                    ) : (
                                        "✨"
                                    )}
                                </button>
                            )}

                            {/* 🔬 Research button */}
                            {!isLoading && (
                            <button
                                onClick={handleResearch}
                                disabled={!inputValue.trim() || !hasSource || isLoading}
                                className="btn-icon text-text-muted disabled:opacity-30 rounded-[10px] w-9 h-9 flex items-center justify-center transition-all research-btn"
                                title="Deep Research — searches the web and synthesizes a report"
                            >
                                🔬
                            </button>
                            )}

                            {/* Stop / Send button */}
                            {isLoading ? (
                                <button
                                    onClick={handleStop}
                                    className="btn-icon bg-red-500/20 text-red-400 hover:bg-red-500/30 rounded-[10px] w-9 h-9 flex items-center justify-center transition-all ml-1"
                                    title="Stop generation"
                                >
                                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                                        <rect x="6" y="6" width="12" height="12" rx="2" />
                                    </svg>
                                </button>
                            ) : (
                            <button
                                onClick={() => handleSend()}
                                disabled={!inputValue.trim() || !hasSource || isLoading || !currentNotebook?.id || !!currentNotebook?.isDraft}
                                className="btn-icon bg-accent text-white disabled:opacity-40 disabled:bg-surface-overlay disabled:text-text-muted rounded-[10px] w-9 h-9 flex items-center justify-center transition-all ml-1"
                            >
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                                </svg>
                            </button>
                            )}
                        </div>
                    </div>
                    {/* Footer hint */}
                    <div className="flex items-center justify-center gap-3 mt-2">
                        <p className="text-xs text-text-muted">
                            <kbd className="px-1.5 py-0.5 rounded bg-surface-overlay border border-border/50 font-mono text-[10px]">Enter</kbd> send
                            &nbsp;·&nbsp;
                            <kbd className="px-1.5 py-0.5 rounded bg-surface-overlay border border-border/50 font-mono text-[10px]">⇧ Enter</kbd> new line
                            &nbsp;·&nbsp; 🔬 deep research
                        </p>
                        {inputValue.length > 0 && (
                            <span className={`text-xs tabular-nums ${ inputValue.length > 1800 ? 'text-status-error' : 'text-text-muted' }`}>
                                {inputValue.length}
                            </span>
                        )}
                    </div>
                </div>
            </div>

            {/* Toast notification */}
            {toastMsg && (
                <div className="fixed bottom-4 right-4 z-50 bg-surface-raised text-text-primary px-4 py-2 rounded-lg shadow-lg border border-border text-sm animate-fade-in">
                    {toastMsg}
                </div>
            )}
        </main>
    );
}
