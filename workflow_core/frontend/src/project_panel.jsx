import React, { useState } from 'react';

export function ProjectPanel({ task, busy, decide, open }) {
    const [comment, setComment] = useState('');
    return <section className="wf-task">
        <h2>{task.name}</h2><div>{task.task_name} · {task.task_state}</div><div>{task.assignees.join('、')}</div>
        {task.comment && <p>{task.comment}</p>}
        <button className="btn btn-secondary mt-2" disabled={busy} onClick={() => open(task.id)}>打开项目任务</button>
        {task.can_complete && <>
            <textarea className="form-control mt-2" aria-label="项目任务意见" maxLength={4000} placeholder="办理意见" disabled={busy}
                value={comment} onChange={e => setComment(e.target.value)} />
            <div className="d-flex gap-2 mt-2">
                <button className="btn btn-primary" disabled={busy} onClick={() => decide(task.id, 'complete', comment)}>完成项目任务</button>
                <button className="btn btn-outline-danger" disabled={busy} onClick={() => decide(task.id, 'cancel', comment)}>取消项目任务</button>
            </div>
        </>}
    </section>;
}
