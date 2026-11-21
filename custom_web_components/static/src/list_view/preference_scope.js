/** Persist standard lists by view, and relational lists by root view and field path. */
export function listPreferenceScope(renderer) {
    const viewId = renderer.env.config.viewId;
    const model = renderer.props.list.resModel;
    if (!Number.isInteger(viewId) || viewId <= 0 || !model) {
        return null;
    }
    const nested = renderer.props.nestedKeyOptionalFieldsData;
    if (nested) {
        const parent = renderer.env.componentListPath;
        const prefix = parent?.viewId === viewId ? parent.path : "";
        const path = [prefix, nested.field].filter(Boolean).join(".");
        const key = `x2many:${path}`;
        return key.length <= 128 ? { type: "list_nested", model, viewId, key } : null;
    }
    // Hand-built dashboard lists can inherit a form/action env without being its real view.
    // A real list controller sets viewType=list; relational lists are handled above.
    if (renderer.env.config.viewType !== "list") {
        return null;
    }
    return { type: "list", model, viewId };
}
