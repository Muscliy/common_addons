import React from 'react';

export function ApprovalEditor({ config = {}, options = {}, disabled, change }) {
    const levels = config.levels || [];
    const update = (index, value) => change({ levels: levels.map((level, i) => i === index ? value : level) });
    return <section className="wf-approval-editor">
        <h2 className="mt-3">审批级次</h2>
        {levels.map((level, index) => {
            const choices = level.kind === 'user' ? options.users || [] : level.kind === 'group' ? options.groups || [] :
                Object.entries(options.fields || {}).map(([id, field]) => ({ id, name: field.string }));
            return <fieldset key={index} className="wf-task" disabled={disabled}>
                <legend className="fs-6">第 {index + 1} 级</legend>
                <select className="form-select mb-2" aria-label={`第${index + 1}级审批方式`} value={level.kind}
                    onChange={e => update(index, { kind: e.target.value, ref: e.target.value === 'field' ? '' : 0 })}>
                    <option value="user">指定人员</option><option value="group">用户组任一人</option><option value="field">业务字段</option>
                </select>
                <select className="form-select" aria-label={`第${index + 1}级审批人`} value={level.ref}
                    onChange={e => update(index, { ...level, ref: level.kind === 'field' ? e.target.value : Number(e.target.value) })}>
                    <option value={level.kind === 'field' ? '' : 0}>请选择</option>
                    {choices.map(choice => <option value={choice.id} key={choice.id}>{choice.name}</option>)}
                </select>
                {!disabled && <div className="d-flex gap-2 mt-2">
                    <button className="btn btn-secondary" disabled={index === 0} aria-label={`上移第${index + 1}级`} onClick={() => {
                        const next = [...levels]; [next[index - 1], next[index]] = [next[index], next[index - 1]]; change({ levels: next });
                    }}>上移</button>
                    <button className="btn btn-outline-danger" onClick={() => change({ levels: levels.filter((_, i) => i !== index) })}>移除</button>
                </div>}
            </fieldset>;
        })}
        {!disabled && levels.length < 20 && <button className="btn btn-secondary" onClick={() => change({ levels: [...levels, { kind: 'user', ref: 0 }] })}>添加级次</button>}
    </section>;
}
