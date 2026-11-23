import React from 'react';

export function ProjectEditor({ config = {}, options = {}, disabled, change }) {
    return <section>
        <label className="form-label mt-3" htmlFor="wf-project-mode">项目任务方式</label>
        <select id="wf-project-mode" className="form-select" disabled={disabled} value={config.mode || ''}
            onChange={e => change(e.target.value === 'business' ? { mode: 'business' } : { mode: 'create', project_id: 0, user_ids: [] })}>
            <option value="">请选择</option><option value="create">创建项目任务</option>
            {options.can_link_business && <option value="business">关联当前业务任务</option>}
        </select>
        {config.mode === 'create' && <>
            <label className="form-label mt-3" htmlFor="wf-project">项目</label>
            <select id="wf-project" className="form-select" disabled={disabled} value={config.project_id || 0}
                onChange={e => change({ ...config, project_id: Number(e.target.value) })}>
                <option value={0}>请选择</option>{(options.projects || []).map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
            <label className="form-label mt-3" htmlFor="wf-project-users">项目负责人</label>
            <select id="wf-project-users" className="form-select" multiple disabled={disabled} value={(config.user_ids || []).map(String)}
                onChange={e => change({ ...config, user_ids: [...e.target.selectedOptions].map(o => Number(o.value)) })}>
                {(options.users || []).map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
            </select>
        </>}
    </section>;
}
