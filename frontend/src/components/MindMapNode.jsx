import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';

const depthColors = {
    0: 'var(--surface-overlay)',
    1: 'var(--surface-raised)',
    2: 'var(--surface-100)',
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

    const bgColor = depthColors[depth] || 'var(--surface-50)';
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
                    border: `1px solid ${isHighlighted ? 'var(--accent-light)' : 'var(--border-strong)'}`,
                    borderRadius: '6px',
                    padding: '8px 12px',
                    color: 'var(--text-primary)',
                    fontSize: '13px',
                    fontWeight: 500,
                    cursor: 'pointer',
                    opacity: hasHighlights && !isHighlighted ? 0.3 : 1,
                    boxShadow: isHighlighted ? '0 0 0 2px var(--accent-light)' : 'none',
                    transition: 'border-color 0.2s, opacity 0.2s, box-shadow 0.2s',
                    maxWidth: '200px',
                    wordBreak: 'break-word',
                }}
                onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = 'var(--accent-light)';
                }}
                onMouseLeave={(e) => {
                    if (!isHighlighted) {
                        e.currentTarget.style.borderColor = 'var(--border-strong)';
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
                        background: 'var(--surface-overlay)',
                        borderRadius: '4px',
                        border: 'none',
                        color: 'var(--text-primary)',
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
