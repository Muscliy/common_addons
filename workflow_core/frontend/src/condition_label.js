export const operators = {
    eq: { name: '等于', symbol: '=' },
    ne: { name: '不等于', symbol: '≠' },
    gt: { name: '大于', symbol: '>' },
    ge: { name: '大于等于', symbol: '≥' },
    lt: { name: '小于', symbol: '<' },
    le: { name: '小于等于', symbol: '≤' },
};

const numbers = new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 20 });

function displayValue(value, field) {
    if (typeof value === 'number') return numbers.format(value);
    if (typeof value === 'boolean') return value ? '是' : '否';
    const selected = Array.isArray(field?.selection) && field.selection.find(([key]) => key === value);
    if (selected) return selected[1];
    return value === '' ? '空值' : `“${value}”`;
}

function describe(rule, fields, nested = false, depth = 0) {
    if (!rule || depth > 8) return '';
    const children = rule.all || rule.any;
    if (Array.isArray(children) && children.length === 1) {
        return describe(children[0], fields, nested, depth + 1);
    }
    if (Array.isArray(children) && children.length > 1 && children.length <= 20) {
        const terms = children.map(child => describe(child, fields, true, depth + 1));
        if (terms.some(term => !term)) return '';
        const text = terms.join(rule.any ? ' 或 ' : ' 且 ');
        return nested ? `（${text}）` : text;
    }
    if (typeof rule.field !== 'string' || !rule.field || !Object.hasOwn(operators, rule.op)
        || !['number', 'boolean', 'string'].includes(typeof rule.value)) {
        return '';
    }
    const field = fields?.[rule.field];
    const comparison = [operators[rule.op].symbol, displayValue(rule.value, field)].join(' ');
    return nested ? `${field?.string || rule.field} ${comparison}` : comparison;
}

export function conditionLabel(edgeData, fields) {
    if (edgeData?.default) return '默认';
    if (!edgeData?.rule || !Object.keys(edgeData.rule).length) return '';
    return describe(edgeData.rule, fields) || '条件待完善';
}
