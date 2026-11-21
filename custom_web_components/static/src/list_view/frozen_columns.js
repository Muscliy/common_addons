import { useEffect } from "@odoo/owl";

/** Apply sticky presentation to existing cells; OWL remains the sole owner of column order. */
export function useFrozenColumns(renderer) {
    function update() {
        const table = renderer.tableRef.el;
        if (!table?.tHead) {
            return;
        }
        const headers = [...table.tHead.rows[0].cells];
        const hasFrozen = renderer.columns.some((column) => renderer.isColumnFrozen(column));
        const pinned = renderer.columns.map(
            (column) =>
                hasFrozen && (column.widget === "handle" || renderer.isColumnFrozen(column)),
        );
        if (renderer.hasSelectors) {
            pinned.unshift(hasFrozen);
        }
        const widths = headers.map((header) => header.getBoundingClientRect().width);
        let offset = 0;
        const offsets = widths.map((width, index) => {
            const start = offset;
            if (pinned[index]) {
                offset += width;
            }
            return start;
        });
        // A small viewport must remain navigable even when saved frozen widths no longer fit.
        const overflow = hasFrozen && offset > table.parentElement.clientWidth - 80;
        table.classList.toggle("cwc_has_frozen", hasFrozen && !overflow);
        if (renderer.layout.freezeOverflow !== overflow) {
            renderer.layout.freezeOverflow = overflow;
        }
        const last = pinned.lastIndexOf(true);
        for (const row of table.querySelectorAll(
            "thead tr, tbody tr.o_data_row, tbody tr.o_group_header, tfoot tr",
        )) {
            if (row.closest("table") !== table) {
                continue;
            }
            let index = 0;
            for (const cell of row.cells) {
                const span = cell.colSpan || 1;
                // Never make a group label spanning scrolling columns sticky: it would cover its aggregates.
                const sticky =
                    !overflow &&
                    pinned.slice(index, index + span).length === span &&
                    pinned.slice(index, index + span).every(Boolean);
                cell.classList.toggle("cwc_frozen_cell", sticky);
                cell.classList.toggle("cwc_frozen_edge", sticky && index + span - 1 === last);
                if (sticky) {
                    cell.style.setProperty("--cwc-frozen-offset", `${offsets[index]}px`);
                } else {
                    cell.style.removeProperty("--cwc-frozen-offset");
                }
                index += span;
            }
        }
    }
    useEffect(() => {
        update();
        const observer = new ResizeObserver(update);
        for (const header of renderer.tableRef.el.tHead?.rows[0].cells || []) {
            observer.observe(header);
        }
        // OWL disconnects this observer both before the next effect and on unmount.
        return () => observer.disconnect();
    });
    return { update };
}
