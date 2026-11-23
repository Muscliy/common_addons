import React, { useCallback, useRef, useState } from 'react';
import { ReactFlow, ReactFlowProvider, Background, Controls, MiniMap, useReactFlow,
    addEdge, ConnectionMode } from '@xyflow/react';
import { nodeTypes } from './node.jsx';
import { Properties } from './properties.jsx';
import { NodeActions } from './node_actions.jsx';
import { connectedSides, defaultHandles, exampleGraph, labels, serialise } from './graph.js';

function Canvas({ canvas, assignees = [], onChange, onReady, onComplete, onDecision, onProjectDecision, onProjectOpen, busy }) {
    const [nodes, setNodes] = useState(canvas.graph.nodes);
    const [edges, setEdges] = useState(canvas.graph.edges);
    const [selection, setSelection] = useState(null);
    const [panel, setPanel] = useState('nodes');
    const [actions, setActions] = useState(null);
    const canvasElement = useRef(null);
    const closeActions = useCallback(() => setActions(null), []);
    const flow = useReactFlow();
    const current = useRef({ nodes, edges, viewport: canvas.graph.viewport });
    const update = (nextNodes, nextEdges) => {
        current.current = { nodes: nextNodes, edges: nextEdges, viewport: flow.getViewport() };
        setNodes(nextNodes); setEdges(nextEdges); onChange();
    };
    const ready = useCallback(() => onReady(() => serialise(
        current.current.nodes, current.current.edges, flow.getViewport())), [onReady, flow]);
    const addNode = (kind, position) => {
        if (!canvas.can_edit) return;
        const node = { id: crypto.randomUUID(), type: kind,
            position: position || flow.screenToFlowPosition({ x: window.innerWidth / 2, y: 240 }),
            data: { label: labels[kind], assignee_id: 0 } };
        update([...nodes, node], edges); setSelection({ kind: 'node', id: node.id }); setPanel('properties');
    };
    const onDrop = (e) => {
        e.preventDefault();
        const kind = e.dataTransfer.getData('application/workflow-node');
        if (canvas.node_types.some(([key]) => key === kind)) addNode(kind, flow.screenToFlowPosition({ x: e.clientX, y: e.clientY }));
    };
    const editNode = id => {
        closeActions();
        setSelection({ kind: 'node', id });
        setPanel('properties');
    };
    const openActions = (event, id, fromButton = false) => {
        if (!canvas.can_edit) return;
        event.preventDefault();
        event.stopPropagation();
        const canvasBox = canvasElement.current.getBoundingClientRect();
        const trigger = event.currentTarget;
        const triggerBox = trigger.getBoundingClientRect();
        setActions(current => fromButton && current?.trigger === trigger ? null : { id, trigger, fromButton,
            x: (fromButton ? triggerBox.left : event.clientX) - canvasBox.left,
            y: (fromButton ? triggerBox.bottom : event.clientY) - canvasBox.top,
        });
    };
    const executions = Object.fromEntries((canvas.executions || []).map((e) => [e.node, e]));
    const displayEdges = edges.map(e => ({ ...defaultHandles, ...e,
        label: e.data?.default ? '默认' : e.data?.rule && Object.keys(e.data.rule).length ? '满足条件' : '' }));
    const connected = connectedSides(displayEdges);
    const displayNodes = nodes.map((node) => ({ ...node, data: { ...node.data,
        state: executions[node.id]?.state, execution: executions[node.id],
        connectedSides: connected.get(node.id),
        openActions: canvas.can_edit && selection?.kind === 'node' && selection.id === node.id
            ? event => openActions(event, node.id, true) : null,
    } }));
    const node = selection?.kind === 'node' ? displayNodes.find((n) => n.id === selection.id) : null;
    const edge = selection?.kind === 'edge' ? edges.find((e) => e.id === selection.id) : null;
    const actionsNode = canvas.can_edit && nodes.find(n => n.id === actions?.id);
    const updateNode = (id, data) => canvas.can_edit && update(nodes.map(n =>
        n.id === id ? { ...n, data: { ...n.data, ...data } } : n), edges);
    const remove = (kind, id) => {
        if (!canvas.can_edit) return;
        const nodeId = kind === 'node' ? id : null;
        const edgeId = kind === 'edge' ? id : null;
        update(nodes.filter(n => n.id !== nodeId), edges.filter(e =>
            e.id !== edgeId && e.source !== nodeId && e.target !== nodeId));
        if (selection?.kind === kind && selection.id === id) setSelection(null);
        closeActions();
    };
    return <div className={`wf-editor wf-panel-${panel}`}>
        <nav className="wf-mobile-tabs" aria-label="编辑面板">
            <button className="btn btn-secondary" aria-pressed={panel === 'nodes'} onClick={() => setPanel(panel === 'nodes' ? 'canvas' : 'nodes')}>节点库</button>
            <button className="btn btn-secondary" aria-pressed={panel === 'properties'} onClick={() => setPanel(panel === 'properties' ? 'canvas' : 'properties')}>属性</button>
        </nav>
        <aside className="wf-library" aria-label="节点库">
            <h2>{canvas.instance_id ? '执行监控' : '节点库'}</h2>
            {canvas.node_types.map(([kind, label]) => <button key={kind} className="btn btn-light wf-palette-node"
                draggable={canvas.can_edit} disabled={!canvas.can_edit} onClick={() => addNode(kind)}
                onDragStart={(e) => e.dataTransfer.setData('application/workflow-node', kind)}>{label}</button>)}
            {canvas.can_edit && nodes.length === 0 && <button className="btn btn-secondary mt-3" onClick={() => {
                const example = exampleGraph(); update(example.nodes, example.edges); flow.fitView();
            }}>插入示例</button>}
        </aside>
        <div className="wf-canvas" ref={canvasElement} onDrop={onDrop} onDragOver={(e) => e.preventDefault()}>
            <ReactFlow nodes={displayNodes} edges={displayEdges}
                nodeTypes={nodeTypes} onInit={ready} defaultViewport={canvas.graph.viewport} connectionMode={ConnectionMode.Loose}
                nodesDraggable={canvas.can_edit} nodesConnectable={canvas.can_edit} edgesReconnectable={false}
                deleteKeyCode={canvas.can_edit && !actionsNode ? ['Backspace', 'Delete'] : null}
                onNodesChange={(changes) => {
                    const next = changes.applyTo(nodes); setNodes(next); current.current.nodes = next;
                    if (canvas.can_edit && changes.toArray().some((c) => ['position', 'remove'].includes(c.type))) {
                        const ids = new Set(next.map((n) => n.id));
                        update(next, edges.filter((e) => ids.has(e.source) && ids.has(e.target)));
                    }
                }}
                onEdgesChange={(changes) => {
                    const next = changes.applyTo(edges); setEdges(next); current.current.edges = next;
                    if (canvas.can_edit && changes.toArray().some((c) => c.type === 'remove')) update(nodes, next);
                }}
                onConnect={(connection) => canvas.can_edit && update(nodes, addEdge({ ...connection,
                    id: crypto.randomUUID(), data: { default: false, rule: {} } }, edges))}
                isValidConnection={({ source, target }) => source !== target &&
                    !edges.some(e => e.source === source && e.target === target)}
                onNodeClick={(_, n) => editNode(n.id)}
                onNodeContextMenu={(event, n) => openActions(event, n.id)}
                onMoveStart={closeActions}
                onEdgeClick={(_, e) => { setSelection({ kind: 'edge', id: e.id }); setPanel('properties'); }}
                onMoveEnd={() => { if (canvas.can_edit) onChange(); }}>
                <Background /><Controls showInteractive={false} /><MiniMap pannable zoomable />
            </ReactFlow>
            {actionsNode && <NodeActions anchor={actions} node={actionsNode} onClose={closeActions}
                onEdit={() => editNode(actionsNode.id)}
                onColor={color => updateNode(actionsNode.id, { background_color: color })}
                onRemove={() => remove('node', actionsNode.id)} />}
        </div>
        <Properties node={node} edge={edge} nodes={nodes} canvas={canvas} assignees={assignees} busy={busy}
            updateNode={data => updateNode(node.id, data)}
            updateEdge={(data) => canvas.can_edit && update(nodes, edges.map((e) => e.id === edge.id ? { ...e, data: { ...e.data, ...data } } : e))}
            remove={() => node ? remove('node', node.id) : remove('edge', edge.id)} complete={onComplete} decide={onDecision} decideProject={onProjectDecision} openProject={onProjectOpen} />
    </div>;
}

export function Editor(props) {
    return <ReactFlowProvider><Canvas {...props} /></ReactFlowProvider>;
}
