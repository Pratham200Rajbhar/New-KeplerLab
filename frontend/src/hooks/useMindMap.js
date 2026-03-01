import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { getMindMap, generateMindMap } from '../api/mindmap';

export default function useMindMap({ notebookId, selectedSources, onGenerated }) {
    const [status, setStatus] = useState('idle'); // idle | checking | generating | ready | error
    const [mapData, setMapData] = useState(null);
    const [isCanvasOpen, setIsCanvasOpen] = useState(false);
    const [errorMessage, setErrorMessage] = useState(null);

    // Stabilize the selectedSources array reference so useEffect doesn't
    // fire on every render when the parent creates a new array instance.
    const sourcesKey = useMemo(
        () => (selectedSources ? [...selectedSources].sort().join(',') : ''),
        [selectedSources]
    );
    const stableSources = useMemo(
        () => selectedSources || [],
        // eslint-disable-next-line react-hooks/exhaustive-deps
        [sourcesKey]
    );

    const sortedIds = (ids) => [...ids].sort().join(',');

    const checkAndGenerate = useCallback(async () => {
        if (!notebookId || stableSources.length === 0) {
            setStatus('idle');
            return;
        }

        setStatus('checking');
        setErrorMessage(null);

        try {
            const response = await getMindMap(notebookId);

            // Check if saved map matches current sources
            const savedIds = sortedIds(response.material_ids || []);
            const currentIds = sortedIds(stableSources);

            if (savedIds === currentIds) {
                setMapData(response);
                setStatus('ready');
                return;
            }
            // Stale — fall through to regenerate
        } catch (err) {
            // 404 or "not found" means no saved map — fall through to generate
            const msg = (err.message || '').toLowerCase();
            if (!msg.includes('404') && !msg.includes('not found')) {
                // Unexpected error
                setStatus('error');
                setErrorMessage(err.message || 'Failed to check saved mind map');
                return;
            }
        }

        // Generate new mind map
        setStatus('generating');
        try {
            const response = await generateMindMap({
                notebookId,
                materialIds: stableSources,
            });
            setMapData(response);
            setStatus('ready');
            onGenerated?.(response);
        } catch (err) {
            setStatus('error');
            setErrorMessage(err.message || 'Failed to generate mind map');
        }
    }, [notebookId, stableSources, onGenerated]);

    useEffect(() => {
        checkAndGenerate();
    }, [checkAndGenerate]);

    const regenerate = useCallback(async () => {
        if (!notebookId || stableSources.length === 0) return;

        setStatus('generating');
        setErrorMessage(null);

        try {
            const response = await generateMindMap({
                notebookId,
                materialIds: stableSources,
            });
            setMapData(response);
            setStatus('ready');
            onGenerated?.(response);
        } catch (err) {
            setStatus('error');
            setErrorMessage(err.message || 'Failed to regenerate mind map');
        }
    }, [notebookId, stableSources, onGenerated]);

    const openCanvas = useCallback(() => {
        setIsCanvasOpen(true);
    }, []);

    const closeCanvas = useCallback(() => {
        setIsCanvasOpen(false);
    }, []);

    return {
        status,
        mapData,
        isCanvasOpen,
        errorMessage,
        regenerate,
        openCanvas,
        closeCanvas,
    };
}
