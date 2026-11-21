/** Unique named fields can move; row handles, widgets and duplicate fields stay in their slots. */
export function movableNames(columns) {
    const counts = new Map();
    for (const column of columns) {
        counts.set(column.name, (counts.get(column.name) || 0) + 1);
    }
    return new Set(
        columns
            .filter(
                (column) =>
                    column.type === "field" &&
                    column.widget !== "handle" &&
                    !column.relatedPropertyField &&
                    counts.get(column.name) === 1,
            )
            .map((column) => column.name),
    );
}

export function orderedColumns(columns, config) {
    const movable = movableNames(columns);
    const fields = columns.filter((column) => movable.has(column.name));
    const indexes = new Map(fields.map((column, index) => [column.name, index]));
    const sequence = (column) => config[column.name]?.sequence ?? indexes.get(column.name);
    fields.sort((a, b) => sequence(a) - sequence(b) || indexes.get(a.name) - indexes.get(b.name));
    let index = 0;
    return columns.map((column) => (movable.has(column.name) ? fields[index++] : column));
}

/** Partition movable field slots only; preserve handles, buttons and duplicate fields. */
export function frozenFirst(columns, config) {
    const movable = movableNames(columns);
    const fields = columns.filter((column) => movable.has(column.name));
    const frozen = (column) => config[column.name]?.frozen === true;
    const ordered = [...fields.filter(frozen), ...fields.filter((column) => !frozen(column))];
    let index = 0;
    return columns.map((column) => (movable.has(column.name) ? ordered[index++] : column));
}

export function moveColumn(columns, config, source, target, placement = null) {
    const movable = movableNames(columns);
    if (!movable.has(source) || !movable.has(target) || source === target) {
        return config;
    }
    const names = frozenFirst(orderedColumns(columns, config), config)
        .filter((column) => movable.has(column.name))
        .map((column) => column.name);
    const targetIndex = names.indexOf(target);
    names.splice(names.indexOf(source), 1);
    const insertionIndex = placement
        ? names.indexOf(target) + (placement === "after" ? 1 : 0)
        : targetIndex;
    names.splice(insertionIndex, 0, source);
    return {
        ...config,
        ...Object.fromEntries(names.map((name, sequence) => [name, { ...config[name], sequence }])),
    };
}

export function configuredWidth(column, config) {
    const saved = config[column.name]?.width;
    if (Number.isInteger(saved) && saved >= 10 && saved <= 4000) {
        return saved;
    }
    const xmlWidth = column.attrs?.width;
    if (xmlWidth && /^\d+(?:px)?$/.test(xmlWidth)) {
        return Math.max(10, Math.min(4000, Number.parseInt(xmlWidth, 10)));
    }
    return null;
}
