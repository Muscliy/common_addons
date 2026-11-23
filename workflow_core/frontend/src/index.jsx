import React from 'react';
import { createRoot } from 'react-dom/client';
import { Editor } from './editor.jsx';
import '@xyflow/react/dist/style.css';

export function mount(element, props) {
    const root = createRoot(element);
    const render = (next) => root.render(<Editor key={`${next.canvas.id}:${next.canvas.revision}`} {...next} />);
    render(props);
    return { update: render, destroy: () => root.unmount() };
}
