import React from 'react';

export function approvalDirectory(saved = {}, options = {}) {
    const entries = items => Object.fromEntries((items || []).map(item => [item.id, item.name]));
    return {
        user: { ...saved.user, ...entries(options.users) },
        group: { ...saved.group, ...entries(options.groups) },
        field: { ...saved.field, ...Object.fromEntries(Object.entries(options.fields || {}).map(([key, info]) => [key, info.string])) },
    };
}

export function nodeReviewers(node, directory, approval) {
    if (approval) {
        return approval.reviews.flatMap(review => review.reviewers.length
            ? [{ label: review.reviewers.join('、'), person: true }] : []);
    }
    return (node.data.config?.levels || []).flatMap(({ kind, ref }) => {
        const name = directory[kind]?.[ref];
        if (!name) return [];
        if (kind === 'user') return [{ label: name, person: true }];
        return [{ label: kind === 'group' ? `组 · ${name}` : `按 ${name}` }];
    });
}

export function NodeReviewers({ reviewers }) {
    return <div className="wf-node-reviewers" role="group" aria-label="审批人"
        title={reviewers.map(item => item.label).join(' → ')}>
        {reviewers.map(({ label, person }, index) => <React.Fragment key={index}>
            {index > 0 && ' → '}
            <span className={person ? 'wf-node-reviewer-name' : undefined}>{label}</span>
        </React.Fragment>)}
    </div>;
}
