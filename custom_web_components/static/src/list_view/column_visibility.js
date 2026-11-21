/** Receive only permission-filtered, non-column_invisible columns from the renderer. */
export function columnVisibility(columns, config) {
    const fields = columns.filter(
        (column) =>
            column.type === "field" && column.widget !== "handle" && !column.relatedPropertyField,
    );
    const available = new Set(fields.map((column) => column.name));
    const visible = new Set(
        fields
            .filter(
                (column) =>
                    config[column.name]?.visible ??
                    (!column.optional || column.optional === "show"),
            )
            .map((column) => column.name),
    );
    const minimum = Math.min(2, available.size);
    // Old preferences or a permissions/view change must never leave an unusable empty list.
    for (const column of fields) {
        if (visible.size >= minimum) {
            break;
        }
        visible.add(column.name);
    }
    return { available, visible, minimum };
}
