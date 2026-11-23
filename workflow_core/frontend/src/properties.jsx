import React, { useState } from 'react';
import { RuleEditor } from './rule_editor.jsx';
import { labels, states } from './graph.js';
import { ApprovalEditor } from './approval_editor.jsx';
import { ApprovalPanel } from './approval_panel.jsx';
import { ProjectEditor } from './project_editor.jsx';
import { ProjectPanel } from './project_panel.jsx';

const events = { started: '流程启动', node_completed: '节点完成', waiting: '等待办理',
    task_completed: '任务完成', completed: '流程完成', cancelled: '流程取消',
    approval_requested: '发起审批', approval_approved: '审批通过', approval_rejected: '审批拒绝',
    parallel_split: '并行分支启动', join_waiting: '等待分支汇合', parallel_joined: '分支已汇合', project_task_linked: '关联项目任务', project_task_completed: '项目任务完成', project_task_cancelled: '项目任务取消' };

export function Properties({ node, edge, nodes, canvas, assignees, updateNode, updateEdge, remove, complete, decide, decideProject, openProject, busy }) {
    const [comment, setComment] = useState('');
    const editable = canvas.can_edit;
    return <aside className="wf-properties" aria-label="属性面板">
        {node ? <>
            <h2>{labels[node.type]}</h2>
            <label className="form-label" htmlFor="wf-node-name">节点名称</label>
            <input id="wf-node-name" className="form-control" value={node.data.label} disabled={!editable}
                maxLength={120} onChange={(e) => updateNode({ label: e.target.value })} />
            {node.type === 'task' && <>
                <label className="form-label" htmlFor="wf-assignee">负责人</label>
                <select id="wf-assignee" className="form-select" value={node.data.assignee_id || 0} disabled={!editable}
                    onChange={(e) => updateNode({ assignee_id: Number(e.target.value) })}>
                    <option value={0}>流程发起人</option>
                    {assignees.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
                </select>
            </>}
            {node.type === 'approval' && !canvas.instance_id && canvas.node_options?.approval && <ApprovalEditor config={node.data.config} disabled={!editable}
                options={canvas.node_options?.approval} change={config => updateNode({ config })} />}
            {node.type === 'project_task' && !canvas.instance_id && canvas.node_options?.project_task && <ProjectEditor
                config={node.data.config} options={canvas.node_options.project_task} disabled={!editable} change={config => updateNode({ config })} />}
            {node.type === 'fork' && <>
                <label className="form-label mt-3" htmlFor="wf-join">汇合节点</label>
                <select id="wf-join" className="form-select" disabled={!editable} value={node.data.config?.join || ''}
                    onChange={e => updateNode({ config: { join: e.target.value } })}>
                    <option value="">请选择</option>
                    {nodes.filter(n => n.type === 'join').map(n => <option key={n.id} value={n.id}>{n.data.label}</option>)}
                </select>
            </>}
            {node.data.state && <p className="mt-3">{node.type === 'join' && node.data.state === 'waiting' ? '等待分支' : states[node.data.state]}</p>}
            {node.data.execution && <dl>
                <dt>开始时间</dt><dd>{node.data.execution.started_at}</dd>
                <dt>完成时间</dt><dd>{node.data.execution.finished_at || '—'}</dd>
            </dl>}
        </> : edge ? <>
            <h2>连线</h2>
            <p>{nodes.find((n) => n.id === edge.source)?.data.label} → {nodes.find((n) => n.id === edge.target)?.data.label}</p>
            {nodes.find((n) => n.id === edge.source)?.type === 'condition' && <>
                <label className="form-check"><input className="form-check-input" type="checkbox"
                    checked={!!edge.data?.default} disabled={!editable}
                    onChange={(e) => updateEdge({ default: e.target.checked, rule: {} })} />默认出口</label>
                {!edge.data?.default && <RuleEditor rule={edge.data?.rule || {}} fields={canvas.fields}
                    disabled={!editable} change={(rule) => updateEdge({ rule })} />}
            </>}
        </> : <p className="text-muted">选择节点或连线</p>}
        {editable && (node || edge) && <button className="btn btn-outline-danger mt-3" onClick={remove}>删除{node ? '节点' : '连线'}</button>}
        {canvas.instance_id && <section className="wf-tasks">
            {(canvas.approvals || []).map(approval => <ApprovalPanel key={`${approval.id}:${approval.review_id}`}
                approval={approval} busy={busy} decide={decide} />)}
            {(canvas.project_tasks || []).map(task => <ProjectPanel key={task.id} task={task} busy={busy} decide={decideProject} open={openProject} />)}
            <h2>任务</h2>
            {(canvas.tasks || []).map((task) => <div className="wf-task" key={task.id}>
                <strong>{task.name}</strong><div>{task.assignee} · {task.state === 'pending' ? '待办理' : states[task.state]}</div>
                {task.can_complete && <>
                    <textarea className="form-control mt-2" aria-label="办理意见" maxLength={4000} placeholder="办理意见" value={comment}
                        onChange={(e) => setComment(e.target.value)} />
                    <button className="btn btn-primary mt-2" disabled={busy} onClick={() => complete(task.id, comment)}>完成任务</button>
                </>}
            </div>)}
            <h2>执行记录</h2>
            <ol className="wf-log">{(canvas.logs || []).map((log) => <li key={log.id}>
                <strong>{events[log.event] || '执行记录'}{log.node && ` · ${log.node}`}</strong>
                <span>{log.actor} · {log.at}</span>{log.comment && <p>{log.comment}</p>}
            </li>)}</ol>
        </section>}
    </aside>;
}
