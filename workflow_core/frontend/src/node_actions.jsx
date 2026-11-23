import React, { useLayoutEffect, useRef } from 'react';
import { backgrounds } from './graph.js';

export function BackgroundSelect({ id, value, disabled, onChange }) {
    return <select id={id} className="form-select" value={value || ''} disabled={disabled}
        onChange={event => onChange(event.target.value)}>
        {Object.entries(backgrounds).map(([color, label]) => <option key={color} value={color}>{label}</option>)}
    </select>;
}

export function NodeActions({ anchor, node, onClose, onEdit, onColor, onRemove }) {
    const menu = useRef(null);
    const { x, y, trigger, fromButton } = anchor;
    useLayoutEffect(() => {
        const element = menu.current;
        const canvas = element.parentElement;
        const place = () => {
            element.style.left = Math.max(0, Math.min(x, canvas.clientWidth - element.offsetWidth)) + 'px';
            element.style.top = Math.max(0, Math.min(y, canvas.clientHeight - element.offsetHeight)) + 'px';
        };
        place();
        element.querySelector('button').focus();
        const resize = new ResizeObserver(place);
        resize.observe(canvas);
        const outside = event => {
            if (!element.contains(event.target) && !(fromButton && trigger.contains(event.target))) onClose();
        };
        const escape = event => {
            if (event.key === 'Escape') {
                onClose();
                trigger?.focus();
            }
        };
        document.addEventListener('pointerdown', outside);
        document.addEventListener('keydown', escape);
        return () => {
            resize.disconnect();
            document.removeEventListener('pointerdown', outside);
            document.removeEventListener('keydown', escape);
        };
    }, [x, y, trigger, fromButton, onClose]);

    return <div ref={menu} className="wf-node-actions rounded border shadow p-2" role="dialog" aria-label="节点操作">
        <button type="button" className="btn btn-light text-start" onClick={onEdit}>编辑属性</button>
        <div id="wf-node-swatch-label">背景色</div>
        <div className="wf-node-swatches" role="group" aria-labelledby="wf-node-swatch-label">
            {Object.entries(backgrounds).map(([color, label]) =>
                <button key={color} type="button" className={color ? `wf-node-swatch wf-color-${color}` : 'wf-node-swatch'}
                    aria-label={label} title={label} aria-pressed={color === (node.data.background_color || '')}
                    onClick={() => onColor(color)}>
                    {!color && <i className="fa fa-undo" aria-hidden="true" />}
                </button>
            )}
        </div>
        <button type="button" className="btn btn-outline-danger text-start" onClick={onRemove}>删除节点</button>
    </div>;
}
