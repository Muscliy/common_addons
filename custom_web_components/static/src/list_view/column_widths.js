import { onMounted, onWillUnmount, useEffect, useExternalListener } from "@odoo/owl";
import { FIELD_WIDTHS } from "@web/views/list/column_width_hook";
import { configuredWidth } from "@custom_web_components/utils/list_layout";

function nativeWidthSpec(column) {
    let width =
        column.type === "field" ? column.field?.listViewWidth : column.widget?.listViewWidth;
    if (typeof width === "function") {
        width = width({
            type: column.fieldType,
            hasLabel: column.hasLabel,
            options: column.options,
        });
    }
    width ||= FIELD_WIDTHS[column.widget || column.fieldType] || [80];
    return Array.isArray(width) ? width : [width, width];
}

/** Native resize gestures, with a separate persistent sizing policy. No cells are moved in the DOM. */
export function usePreferenceWidths(renderer) {
    let naturalWidths = new Map();
    let resizeColumn = null;
    let resizeCleanup = () => {};
    const table = () => renderer.tableRef.el;
    function apply() {
        if (!table() || resizeColumn) {
            return;
        }
        const headers = [...table().querySelectorAll("thead th")];
        const columns = renderer.columns;
        const offset = renderer.hasSelectors ? 1 : 0;
        const missing = columns.some((column) => !naturalWidths.has(column.id));
        if (missing) {
            table().style.tableLayout = "auto";
            table().style.width = "100%";
            headers.forEach((header) => {
                header.style.width = "";
            });
            table().classList.add("o_list_computing_widths");
            columns.forEach((column, index) => {
                const header = headers[index + offset];
                const [min, max] = nativeWidthSpec(column);
                const style = getComputedStyle(header);
                const padding = parseFloat(style.paddingLeft) + parseFloat(style.paddingRight);
                const natural = header.getBoundingClientRect().width - padding;
                naturalWidths.set(
                    column.id,
                    Math.max(min, Math.min(max || Infinity, natural)) + padding,
                );
            });
            table().classList.remove("o_list_computing_widths");
        }
        const widths = headers.map((header) => header.getBoundingClientRect().width);
        if (renderer.hasSelectors) {
            widths[0] = 36;
        }
        columns.forEach((column, index) => {
            widths[index + offset] =
                configuredWidth(column, renderer.layout.config) ?? naturalWidths.get(column.id);
        });
        let tail = offset + columns.length;
        if (renderer.hasOpenFormViewColumn) {
            widths[tail++] = 54;
        }
        if (renderer.hasActionsColumn) {
            widths[tail] = 32;
        }
        table().style.tableLayout = "fixed";
        table().style.width = `${Math.ceil(widths.reduce((sum, width) => sum + width, 0))}px`;
        headers.forEach((header, index) => {
            header.style.width = `${widths[index]}px`;
        });
        renderer.frozenColumns?.update();
        renderer.stickyEndColumn?.update();
    }
    function reset() {
        naturalWidths = new Map();
        if (table()) {
            table().parentElement.style.width = "";
        }
        apply();
    }
    const nativeStart = renderer.columnWidths.onStartResize;
    renderer.columnWidths.onStartResize = (event) => {
        if (renderer.layout.busy || event.button !== 0) {
            return;
        }
        const header = event.target.closest("th");
        resizeColumn = header.dataset.name;
        // The native hook owns pointer movement, RTL, sort suppression and visual feedback.
        nativeStart(event);
        const finish = (stopEvent) => {
            if (stopEvent.type === "pointerdown" && stopEvent.button === 0) {
                return;
            }
            const width = Math.max(
                10,
                Math.min(4000, Math.round(header.getBoundingClientRect().width)),
            );
            renderer.layout.config = {
                ...renderer.layout.config,
                [resizeColumn]: { ...renderer.layout.config[resizeColumn], width },
            };
            renderer.layout.dirty = true;
            resizeColumn = null;
            resizeCleanup();
        };
        const events = ["pointerup", "pointerdown", "keydown"];
        events.forEach((type) => window.addEventListener(type, finish));
        resizeCleanup = () => events.forEach((type) => window.removeEventListener(type, finish));
    };
    useEffect(apply);
    useExternalListener(window, "resize", reset);
    let observer;
    let parentWidth;
    onMounted(() => {
        observer = new ResizeObserver(([entry]) => {
            if (entry.contentRect.width !== parentWidth) {
                parentWidth = entry.contentRect.width;
                reset();
            }
        });
        observer.observe(table().parentElement);
    });
    onWillUnmount(() => {
        if (resizeColumn) {
            // Dispose the native hook's temporary window listeners before removing the table.
            window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
        }
        resizeCleanup();
        observer?.disconnect();
    });
    return { reset };
}
