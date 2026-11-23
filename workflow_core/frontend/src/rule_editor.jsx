import React from 'react';

const operators = { eq: '等于', ne: '不等于', gt: '大于', ge: '大于等于', lt: '小于', le: '小于等于' };
const numeric = ['integer', 'float', 'monetary'];

function defaultValue(info) {
    if (info?.type === 'boolean') return false;
    return numeric.includes(info?.type) ? 0 : '';
}

function Leaf({ rule, fields, change, disabled }) {
    const info = fields[rule.field];
    const options = numeric.includes(info?.type) ? Object.keys(operators) : ['eq', 'ne'];
    return <div className="wf-rule-leaf">
        <select className="form-select" aria-label="条件字段" disabled={disabled} value={rule.field || ''}
            onChange={(e) => change({ field: e.target.value, op: 'eq', value: defaultValue(fields[e.target.value]) })}>
            <option value="">选择字段</option>
            {Object.entries(fields).map(([name, field]) => <option key={name} value={name}>{field.string}</option>)}
        </select>
        <select className="form-select" aria-label="比较方式" disabled={disabled} value={rule.op || 'eq'}
            onChange={(e) => change({ ...rule, op: e.target.value })}>
            {options.map((op) => <option key={op} value={op}>{operators[op]}</option>)}
        </select>
        {info?.type === 'boolean' ? <select className="form-select" aria-label="比较值" disabled={disabled}
            value={String(rule.value)} onChange={(e) => change({ ...rule, value: e.target.value === 'true' })}>
            <option value="false">否</option><option value="true">是</option>
        </select> : <input className="form-control" aria-label="比较值" disabled={disabled}
            type={numeric.includes(info?.type) ? 'number' : 'text'} value={rule.value ?? ''}
            onChange={(e) => change({ ...rule, value: numeric.includes(info?.type) ? Number(e.target.value) : e.target.value })} />}
    </div>;
}

export function RuleEditor({ rule, fields, change, disabled }) {
    const mode = rule.any ? 'any' : 'all';
    const children = rule[mode] || [rule];
    return <div className="wf-rule-editor">
        <select className="form-select" aria-label="条件组合" disabled={disabled} value={mode}
            onChange={(e) => change({ [e.target.value]: children })}>
            <option value="all">满足全部条件（AND）</option><option value="any">满足任一条件（OR）</option>
        </select>
        {children.map((child, index) => <div key={index} className="wf-rule-row">
            {child.all || child.any ? <RuleEditor rule={child} fields={fields} disabled={disabled}
                change={(value) => change({ [mode]: children.map((c, i) => i === index ? value : c) })} /> :
                <Leaf rule={child} fields={fields} disabled={disabled}
                    change={(value) => change({ [mode]: children.map((c, i) => i === index ? value : c) })} />}
            {!disabled && children.length > 1 && <button className="btn btn-light" aria-label="移除条件"
                onClick={() => change({ [mode]: children.filter((_, i) => i !== index) })}><i className="fa fa-times" /></button>}
        </div>)}
        {!disabled && children.length < 20 && <button className="btn btn-secondary" onClick={() => change({ [mode]: [...children, {}] })}>添加条件</button>}
    </div>;
}
