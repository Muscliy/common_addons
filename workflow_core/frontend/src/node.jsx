import React from 'react';
import { Handle, Position } from '@xyflow/react';
import { labels, states } from './graph.js';

const icons = { start: 'fa-play', end: 'fa-stop', task: 'fa-user', condition: 'fa-code-fork', fork: 'fa-random', join: 'fa-compress', approval: 'fa-check-square-o' };

export function WorkflowNode({ type, data }) {
    return <div className={`wf-node wf-${type} wf-state-${data.state || 'idle'}`}>
        {type !== 'start' && <Handle type="target" position={Position.Left} />}
        <div className="wf-node-kind"><i className={`fa ${icons[type]}`} aria-hidden="true" /> {labels[type]}</div>
        <strong>{data.label}</strong>
        {data.state && <div className="wf-node-state">{type === 'join' && data.state === 'waiting' ? '等待分支' : states[data.state] || data.state}</div>}
        {type !== 'end' && <Handle type="source" position={Position.Right} />}
    </div>;
}

export const nodeTypes = Object.fromEntries(Object.keys(labels).map((key) => [key, WorkflowNode]));
