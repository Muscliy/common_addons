import { useEffect } from "@odoo/owl";

/** Keep the final visible data column at the inline end, after Odoo's utility columns. */
export function useStickyEndColumn(renderer) {
    function update() {
        const table = renderer.tableRef.el;
        if (!table?.tHead) {
            return;
        }
        for (const cell of table.querySelectorAll(".cwc_sticky_end_cell")) {
            cell.classList.remove("cwc_sticky_end_cell", "cwc_sticky_end_edge");
            cell.style.removeProperty("--cwc-sticky-end-offset");
        }
        const view = table.closest(".o_list_view");
        if (!view?.classList.contains("cwc_sticky_end") || !renderer.columns.length) {
            return;
        }
        const lastColumn = renderer.columns.at(-1);
        if (renderer.isColumnFrozen(lastColumn)) {
            return;
        }
        const headers = [...table.tHead.rows[0].cells];
        const lastDataIndex = (renderer.hasSelectors ? 1 : 0) + renderer.columns.length - 1;
        const widths = headers.map((header) => header.getBoundingClientRect().width);
        const endWidth = widths.slice(lastDataIndex).reduce((sum, width) => sum + width, 0);
        const startWidth = headers.reduce(
            (sum, header, index) =>
                sum +
                (index < lastDataIndex && header.classList.contains("cwc_frozen_cell")
                    ? widths[index]
                    : 0),
            0,
        );
        if (endWidth > table.parentElement.clientWidth - startWidth - 80) {
            return;
        }
        const offsets = widths.map((_, index) =>
            widths.slice(index + 1).reduce((sum, width) => sum + width, 0),
        );
        for (const row of table.querySelectorAll(
            "thead tr, tbody tr.o_data_row, tbody tr.o_group_header, tfoot tr",
        )) {
            if (row.closest("table") !== table) {
                continue;
            }
            let index = 0;
            for (const cell of row.cells) {
                const span = cell.colSpan || 1;
                if (span === 1 && index >= lastDataIndex && index < headers.length) {
                    cell.classList.add("cwc_sticky_end_cell");
                    cell.classList.toggle("cwc_sticky_end_edge", index === lastDataIndex);
                    cell.style.setProperty("--cwc-sticky-end-offset", `${offsets[index]}px`);
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
        observer.observe(renderer.tableRef.el.parentElement);
        return () => observer.disconnect();
    });
    return { update };
}
