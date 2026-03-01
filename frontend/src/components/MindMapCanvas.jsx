import { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import {
    ReactFlow,
    Controls,
    MiniMap,
    Background,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';
import { toPng } from 'html-to-image';
import { useApp } from '../context/AppContext';
import MindMapNode from './MindMapNode';

const nodeTypes = { mindMapNode: MindMapNode };

function buildChildrenMap(nodes) {
    const map = {};
    for (const n of nodes) {
        if (!map[n.id]) map[n.id] = [];
        if (n.parent_id) {
            if (!map[n.parent_id]) map[n.parent_id] = [];
            map[n.parent_id].push(n.id);
        }
    }
    return map;
}

function getDepth(nodeId, nodesById) {
    let depth = 0;
    let current = nodesById[nodeId];
    while (current && current.parent_id) {
        depth++;
        current = nodesById[current.parent_id];
    }
    return depth;
}

function getAllDescendants(nodeId, childrenMap) {
    const result = [];
    const stack = [...(childrenMap[nodeId] || [])];
    while (stack.length > 0) {
        const cid = stack.pop();
        result.push(cid);
        if (childrenMap[cid]) {
            stack.push(...childrenMap[cid]);
        }
    }
    return result;
}

function computeDagreLayout(nodes) {
    const g = new dagre.graphlib.Graph();
    g.setDefaultEdgeLabel(() => ({}));
    g.setGraph({ rankdir: 'LR', nodesep: 60, ranksep: 120 });

    for (const n of nodes) {
        g.setNode(n.id, { width: 160, height: 40 });
    }
    for (const n of nodes) {
        if (n.parent_id) {
            g.setEdge(n.parent_id, n.id);
        }
    }

    dagre.layout(g);

    const positions = {};
    for (const n of nodes) {
        const pos = g.node(n.id);
        if (pos) {
            positions[n.id] = { x: pos.x - 80, y: pos.y - 20 };
        }
    }
    return positions;
}

export default function MindMapCanvas({ mapData, onClose, onRegenerate }) {
    const { setPendingChatMessage } = useApp();

    const [collapsedNodes, setCollapsedNodes] = useState(new Set());
    const [searchQuery, setSearchQuery] = useState('');
    const flowRef = useRef(null);

    const allNodes = mapData?.nodes || [];
    const nodesById = useMemo(() => {
        const m = {};
        for (const n of allNodes) m[n.id] = n;
        return m;
    }, [allNodes]);

    const childrenMap = useMemo(() => buildChildrenMap(allNodes), [allNodes]);

    const positions = useMemo(() => computeDagreLayout(allNodes), [allNodes]);

    const toggleCollapse = useCallback((nodeId) => {
        setCollapsedNodes((prev) => {
            const next = new Set(prev);
            if (next.has(nodeId)) {
                next.delete(nodeId);
            } else {
                next.add(nodeId);
                const descendants = getAllDescendants(nodeId, childrenMap);
                for (const d of descendants) next.add(d);
            }
            return next;
        });
    }, [childrenMap]);

    const onNodeLabelClick = useCallback((nodeId, questionHint, nodeLabel) => {
        setPendingChatMessage({ text: questionHint, source: 'mindmap', nodeLabel });
        onClose();
    }, [setPendingChatMessage, onClose]);

    // Visible nodes: exclude nodes where any ancestor is in collapsedNodes
    const visibleNodes = useMemo(() => {
        return allNodes.filter((n) => {
            // Walk up parent chain — if any ancestor is collapsed, hide this node
            let current = nodesById[n.parent_id];
            while (current) {
                if (collapsedNodes.has(current.id)) return false;
                current = nodesById[current.parent_id];
            }
            return true;
        });
    }, [allNodes, collapsedNodes, nodesById]);

    const visibleNodeIds = useMemo(() => new Set(visibleNodes.map((n) => n.id)), [visibleNodes]);

    // Edges
    const visibleEdges = useMemo(() => {
        return allNodes
            .filter((n) => n.parent_id && visibleNodeIds.has(n.id) && visibleNodeIds.has(n.parent_id))
            .map((n) => ({
                id: `${n.parent_id}-${n.id}`,
                source: n.parent_id,
                target: n.id,
                type: 'smoothstep',
                style: { stroke: '#4a5568' },
            }));
    }, [allNodes, visibleNodeIds]);

    // Search highlighting
    const highlightedIds = useMemo(() => {
        if (!searchQuery.trim()) return new Set();
        const q = searchQuery.toLowerCase();
        return new Set(
            allNodes
                .filter((n) => n.label.toLowerCase().includes(q))
                .map((n) => n.id)
        );
    }, [allNodes, searchQuery]);

    // React Flow nodes
    const rfNodes = useMemo(() => {
        return visibleNodes.map((n) => ({
            id: n.id,
            type: 'mindMapNode',
            position: positions[n.id] || { x: 0, y: 0 },
            data: {
                label: n.label,
                question_hint: n.question_hint,
                has_children: n.has_children,
                collapsedNodes,
                onToggle: toggleCollapse,
                onNodeLabelClick,
                highlightedIds,
                depth: getDepth(n.id, nodesById),
            },
        }));
    }, [visibleNodes, positions, collapsedNodes, toggleCollapse, onNodeLabelClick, highlightedIds, nodesById]);

    const handleExportPng = useCallback(async () => {
        const el = document.querySelector('.react-flow');
        if (!el) return;
        try {
            const dataUrl = await toPng(el, {
                backgroundColor: '#1a202c',
                quality: 1,
            });
            const a = document.createElement('a');
            a.href = dataUrl;
            a.download = `${mapData?.title || 'mindmap'}.png`;
            a.click();
        } catch (err) {
            console.error('Export failed:', err);
        }
    }, [mapData]);

    return (
        <div
            style={{
                position: 'fixed',
                inset: 0,
                zIndex: 50,
                background: '#1a202c',
                display: 'flex',
                flexDirection: 'column',
            }}
        >
            {/* TOOLBAR */}
            <div
                style={{
                    height: '50px',
                    display: 'flex',
                    flexDirection: 'row',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    borderBottom: '1px solid #2d3748',
                    padding: '0 16px',
                    flexShrink: 0,
                }}
            >
                {/* Left: Close */}
                <button
                    onClick={onClose}
                    style={{
                        background: 'none',
                        border: '1px solid #4a5568',
                        color: 'white',
                        padding: '4px 12px',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        fontSize: '13px',
                    }}
                >
                    ✕ Close
                </button>

                {/* Center: Title */}
                <span style={{ color: 'white', fontSize: '14px', fontWeight: 600 }}>
                    {mapData?.title || 'Mind Map'}
                </span>

                {/* Right: Actions */}
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <button
                        onClick={onRegenerate}
                        style={{
                            background: 'none',
                            border: '1px solid #4a5568',
                            color: 'white',
                            padding: '4px 12px',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            fontSize: '13px',
                        }}
                    >
                        🔄 Regen
                    </button>
                    <button
                        onClick={handleExportPng}
                        style={{
                            background: 'none',
                            border: '1px solid #4a5568',
                            color: 'white',
                            padding: '4px 12px',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            fontSize: '13px',
                        }}
                    >
                        📤 Export PNG
                    </button>
                    <div style={{ position: 'relative' }}>
                        <span
                            style={{
                                position: 'absolute',
                                left: '8px',
                                top: '50%',
                                transform: 'translateY(-50%)',
                                fontSize: '13px',
                            }}
                        >
                            🔍
                        </span>
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder="Search nodes..."
                            style={{
                                background: '#2d3748',
                                border: '1px solid #4a5568',
                                color: 'white',
                                padding: '4px 12px 4px 28px',
                                borderRadius: '6px',
                                fontSize: '13px',
                                outline: 'none',
                                width: '160px',
                            }}
                        />
                    </div>
                </div>
            </div>

            {/* React Flow */}
            <div style={{ flex: 1 }} ref={flowRef}>
                <ReactFlow
                    nodes={rfNodes}
                    edges={visibleEdges}
                    nodeTypes={nodeTypes}
                    fitView
                    minZoom={0.1}
                    maxZoom={2}
                    proOptions={{ hideAttribution: true }}
                >
                    <Controls position="bottom-left" />
                    <MiniMap
                        position="bottom-right"
                        nodeColor="#4a5568"
                        maskColor="rgba(0,0,0,0.5)"
                        style={{ background: '#2d3748' }}
                    />
                    <Background variant="dots" color="#4a5568" gap={20} />
                </ReactFlow>
            </div>
        </div>
    );
}
