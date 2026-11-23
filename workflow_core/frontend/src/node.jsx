import React from 'react';
import { Handle, Position } from '@xyflow/react';
import { backgrounds, labels, states } from './graph.js';

const icons = { start: 'fa-play', end: 'fa-stop', task: 'fa-user', condition: 'fa-code-fork', fork: 'fa-random', join: 'fa-compress', approval: 'fa-check-square-o', project_task: 'fa-tasks' };

export function WorkflowNode({ type, data }) {
    const color = Object.hasOwn(backgrounds, data.background_color) ? data.background_color : '';
    const classes = ['wf-node', `wf-${type}`, `wf-state-${data.state || 'idle'}`];
    if (color) classes.push(`wf-color-${color}`);
    return <div className={classes.join(' ')}>
        {Object.values(Position).map(side =>
            <Handle key={side} id={side} position={side} type={type === 'end' ? 'target' : 'source'}
                className={data.connectedSides?.has(side) ? 'wf-handle-connected' : undefined}
                isConnectableStart={type !== 'end'} isConnectableEnd={type !== 'start'} />
        )}
        {data.openActions && <button type="button" className="wf-node-more btn btn-light nodrag nopan"
            aria-label="节点操作" aria-haspopup="dialog" onClick={data.openActions}>
            <i className="fa fa-ellipsis-h" aria-hidden="true" />
        </button>}
        <div className="wf-node-kind"><i className={`fa ${icons[type]}`} aria-hidden="true" /> {labels[type]}</div>
        <strong title={type === 'condition' ? data.label : undefined}>{data.label}</strong>
        {data.state && <div className="wf-node-state">{type === 'join' && data.state === 'waiting' ? '等待分支' : states[data.state] || data.state}</div>}
    </div>;
}

export const nodeTypes = Object.fromEntries(Object.keys(labels).map((key) => [key, WorkflowNode]));
