import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';

const depthColors = {
    0: '#3d4f6b',
    1: '#2d4a3e',
    2: '#2d3748',
};

function MindMapNode({ data, id }) {
    const {
        label,
        question_hint,
        has_children,
        collapsedNodes,
        onToggle,
        onNodeLabelClick,
        highlightedIds,
        depth,
    } = data;

    const bgColor = depthColors[depth] || '#252d3a';
    const isHighlighted = highlightedIds && highlightedIds.has(id);
    const hasHighlights = highlightedIds && highlightedIds.size > 0;
    const isCollapsed = collapsedNodes && collapsedNodes.has(id);

    return (
        <div style={{ display: 'flex', flexDirection: 'row', alignItems: 'center' }}>
            <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />

            {/* Label area */}
            <div
                onClick={() => onNodeLabelClick(id, question_hint, label)}
                style={{
                    background: bgColor,
                    border: `1px solid ${isHighlighted ? '#68d391' : '#4a5568'}`,
                    borderRadius: '6px',
                    padding: '8px 12px',
                    color: 'white',
                    fontSize: '13px',
                    fontWeight: 500,
                    cursor: 'pointer',
                    opacity: hasHighlights && !isHighlighted ? 0.3 : 1,
                    boxShadow: isHighlighted ? '0 0 0 2px #68d391' : 'none',
                    transition: 'border-color 0.2s, opacity 0.2s, box-shadow 0.2s',
                    maxWidth: '200px',
                    wordBreak: 'break-word',
                }}
                onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = '#68d391';
                }}
                onMouseLeave={(e) => {
                    if (!isHighlighted) {
                        e.currentTarget.style.borderColor = '#4a5568';
                    }
                }}
            >
                {label}
            </div>

            {/* Toggle button */}
            {has_children && (
                <button
                    onClick={(e) => {
                        e.stopPropagation();
                        onToggle(id);
                    }}
                    style={{
                        width: '20px',
                        height: '20px',
                        background: '#4a5568',
                        borderRadius: '4px',
                        border: 'none',
                        color: 'white',
                        fontSize: '11px',
                        marginLeft: '6px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                    }}
                >
                    {isCollapsed ? '>' : '<'}
                </button>
            )}

            <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
        </div>
    );
}

export default memo(MindMapNode);
