import { createContext, useContext, useState, useCallback, useEffect, useMemo, useRef } from 'react';

const AppContext = createContext(null);

export function AppProvider({ children }) {
    // Notebook state
    const [currentNotebook, setCurrentNotebook] = useState(null);
    const [draftMode, setDraftMode] = useState(false);

    // Current material state
    const [currentMaterial, setCurrentMaterial] = useState(null);
    const [materials, setMaterials] = useState([]);
    const [selectedSources, setSelectedSources] = useState(new Set());

    // Toggle a single source selection
    const toggleSourceSelection = useCallback((id) => {
        setSelectedSources(prev => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    }, []);

    // Select / deselect all
    const selectAllSources = useCallback(() => {
        setSelectedSources(new Set(materials.map(m => m.id)));
    }, [materials]);

    const deselectAllSources = useCallback(() => {
        setSelectedSources(new Set());
    }, []);

    // Chat state
    const [sessionId, setSessionId] = useState(null);
    const [messages, setMessages] = useState([]);

    // Generated content
    const [flashcards, setFlashcards] = useState(null);
    const [quiz, setQuiz] = useState(null);
    const [notes, setNotes] = useState([]);

    // UI state
    const [loading, setLoading] = useState({});
    const [error, setError] = useState(null);
    const [activePanel, setActivePanel] = useState('chat');

    // Set loading state for a specific key
    const setLoadingState = useCallback((key, value) => {
        setLoading(prev => ({ ...prev, [key]: value }));
    }, []);

    // Add a message to chat
    const addMessage = useCallback((role, content, citations = null) => {
        const message = {
            id: `${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
            role,
            content,
            citations: citations || null,
            timestamp: new Date(),
        };
        setMessages(prev => [...prev, message]);
        return message;
    }, []);

    // Clear context when switching between notebooks (not on initial load)
    const prevNotebookRef = useRef(undefined);
    useEffect(() => {
        const prevId = prevNotebookRef.current;
        const currId = currentNotebook?.id;
        prevNotebookRef.current = currId;

        // Skip the initial mount (prevId === undefined) — ChatPanel will load
        // messages from the API. Only clear when actively switching notebooks.
        if (prevId !== undefined && currId && prevId !== currId) {
            deselectAllSources();
            setCurrentMaterial(null);
            setMaterials([]);
            setMessages([]);
            setSessionId(null);
            setFlashcards(null);
            setQuiz(null);
            setNotes([]);
            setError(null);
        }
    }, [currentNotebook?.id, deselectAllSources]);

    // Clear chat
    const clearMessages = useCallback(() => {
        setMessages([]);
        setSessionId(null);
    }, []);

    // Add material
    const addMaterial = useCallback((material) => {
        setMaterials(prev => [...prev, material]);
        if (!currentMaterial) {
            setCurrentMaterial(material);
        }
    }, [currentMaterial]);

    // Add note
    const addNote = useCallback((content, source = null) => {
        const note = {
            id: `${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
            content,
            source,
            timestamp: new Date(),
        };
        setNotes(prev => [...prev, note]);
        return note;
    }, []);

    const value = useMemo(() => ({
        // Notebook
        currentNotebook,
        setCurrentNotebook,
        draftMode,
        setDraftMode,

        // Material
        currentMaterial,
        setCurrentMaterial,
        materials,
        setMaterials,
        addMaterial,
        selectedSources,
        setSelectedSources,
        toggleSourceSelection,
        selectAllSources,
        deselectAllSources,

        // Chat
        sessionId,
        setSessionId,
        messages,
        setMessages,
        addMessage,
        clearMessages,

        // Generated content
        flashcards,
        setFlashcards,
        quiz,
        setQuiz,
        notes,
        setNotes,
        addNote,

        // UI
        loading,
        setLoadingState,
        error,
        setError,
        activePanel,
        setActivePanel,
    }), [
        currentNotebook, draftMode, currentMaterial, materials, selectedSources,
        sessionId, messages, flashcards, quiz, notes, loading, error, activePanel,
        setCurrentNotebook, setDraftMode, setCurrentMaterial, setMaterials,
        addMaterial, setSelectedSources, toggleSourceSelection, selectAllSources,
        deselectAllSources, setSessionId, setMessages, addMessage, clearMessages,
        setFlashcards, setQuiz, setNotes, addNote, setLoadingState, setError,
        setActivePanel,
    ]);

    return (
        <AppContext.Provider value={value}>
            {children}
        </AppContext.Provider>
    );
}

export function useApp() {
    const context = useContext(AppContext);
    if (!context) {
        throw new Error('useApp must be used within an AppProvider');
    }
    return context;
}
