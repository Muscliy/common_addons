import React, { useState } from 'react';

const status = { pending: '待审批', waiting: '等待前级', approved: '已通过', rejected: '已拒绝', cancelled: '已取消', cancel: '已取消' };

export function ApprovalPanel({ approval, busy, decide }) {
    const [comment, setComment] = useState('');
    return <section className="wf-task">
        <h2>{approval.name}</h2>
        <ol className="wf-log">{approval.reviews.map(review => <li key={review.id}>
            <strong>第 {review.sequence} 级 · {status[review.state]}</strong>
            <div>{review.reviewers.join('、')}</div>
            {review.actor && <div>{review.actor}</div>}{review.comment && <p>{review.comment}</p>}
        </li>)}</ol>
        {approval.can_review && <>
            <textarea className="form-control" aria-label="审批意见" maxLength={4000} placeholder="审批意见（拒绝时必填）"
                disabled={busy} value={comment} onChange={e => setComment(e.target.value)} />
            <div className="d-flex gap-2 mt-2">
                <button className="btn btn-primary" disabled={busy} onClick={() => decide(approval.id, approval.review_id, 'approve', comment)}>通过</button>
                <button className="btn btn-outline-danger" disabled={busy || !comment.trim()} onClick={() => decide(approval.id, approval.review_id, 'reject', comment)}>拒绝</button>
            </div>
        </>}
    </section>;
}
