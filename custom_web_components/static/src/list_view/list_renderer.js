import { onWillStart, useExternalListener, useState, useSubEnv } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { listPreferenceScope } from "./preference_scope";
import { ListRenderer } from "@web/views/list/list_renderer";
import {
    frozenFirst,
    movableNames,
    moveColumn,
    orderedColumns,
} from "@custom_web_components/utils/list_layout";
import { usePreferenceWidths } from "./column_widths";
import { columnVisibility } from "./column_visibility";
import { useFrozenColumns } from "./frozen_columns";
import { useStickyEndColumn } from "./sticky_end";

// Patch the shared base so registered views, specialized subclasses and X2Many all opt in.
// Keep each view's controller, renderer overrides and template inheritance intact.
patch(ListRenderer, { useMagicColumnWidths: false });
patch(ListRenderer.prototype, {
    setup() {
        this.columnDrag = useState({ source: null, target: null, placement: null });
        useExternalListener(window, "dragend", () => this.clearColumnDrag());
        useExternalListener(window, "drop", () => this.clearColumnDrag());
        useExternalListener(window, "keydown", (event) => {
            if (event.key === "Escape") {
                this.clearColumnDrag();
            }
        });
        this.layout = useState({
            config: {},
            dirty: false,
            busy: false,
            loaded: false,
            freezeOverflow: false,
        });
        super.setup();
        this.preferences = useService("component_preference");
        this.scope = listPreferenceScope(this);
        useSubEnv({
            componentListPath: {
                viewId: this.env.config.viewId,
                path: this.scope?.type === "list_nested" ? this.scope.key.slice(7) : "",
            },
        });
        this.preferenceWidths = usePreferenceWidths(this);
        this.frozenColumns = useFrozenColumns(this);
        this.stickyEndColumn = useStickyEndColumn(this);
        onWillStart(async () => {
            if (this.scope?.viewId) {
                try {
                    this.layout.config = await this.preferences.load(this.scope);
                    this.layout.loaded = true;
                } catch {
                    this.notificationService.add(
                        _t("Could not load list layout. Reload to retry."),
                        { type: "warning" },
                    );
                }
            }
        });
    },

    get canPersonalize() {
        return this.layout.loaded && !this.layout.busy && !this.props.list.editedRecord;
    },

    getActiveColumns(list) {
        const active = super.getActiveColumns(list);
        const ordered = this.orderedLayoutColumns;
        const activeIds = new Set(active.map((column) => column.id));
        const { available, visible } = this.columnVisibility;
        return ordered.filter(
            (column) =>
                activeIds.has(column.id) &&
                (!this.layout.loaded || !available.has(column.name) || visible.has(column.name)),
        );
    },

    get orderedLayoutColumns() {
        return frozenFirst(orderedColumns(this.allColumns, this.layout.config), this.layout.config);
    },

    get settingsColumns() {
        return this.orderedLayoutColumns.filter(
            (column) =>
                column.type === "field" &&
                !this.evalColumnInvisible(column.column_invisible) &&
                !(this.props.list.isGrouped && column.widget === "handle"),
        );
    },

    get displayOptionalFields() {
        return (
            (this.layout.loaded && this.settingsColumns.length > 0) || super.displayOptionalFields
        );
    },

    computeOptionalActiveFields() {
        if (!this.layout.loaded) {
            return super.computeOptionalActiveFields();
        }
        // Use user/view preferences and XML defaults, never another login's browser storage.
        return Object.fromEntries(
            this.allColumns
                .filter((column) => column.optional)
                .map((column) => [
                    column.name,
                    this.columnVisibility.available.has(column.name)
                        ? this.columnVisibility.visible.has(column.name)
                        : column.optional === "show",
                ]),
        );
    },

    isColumnVisible(column) {
        if (this.layout.loaded && this.columnVisibility.available.has(column.name)) {
            return this.columnVisibility.visible.has(column.name);
        }
        return !column.optional || this.optionalActiveFields[column.name];
    },

    get columnVisibility() {
        return columnVisibility(
            this.allColumns.filter((column) => !this.evalColumnInvisible(column.column_invisible)),
            this.layout.config,
        );
    },

    canToggleColumn(column) {
        const { available, visible, minimum } = this.columnVisibility;
        return (
            this.canPersonalize &&
            available.has(column.name) &&
            (!visible.has(column.name) || visible.size > minimum)
        );
    },

    columnVisibilityTitle(column) {
        if (!this.columnVisibility.available.has(column.name)) {
            return "此列由系统控制";
        }
        if (
            this.isColumnVisible(column) &&
            this.columnVisibility.visible.size <= this.columnVisibility.minimum
        ) {
            return `至少保留 ${this.columnVisibility.minimum} 个字段`;
        }
        return "显示此列";
    },

    async toggleOptionalField(name) {
        if (!this.layout.loaded) {
            return super.toggleOptionalField(name);
        }
        const column = this.settingsColumns.find((candidate) => candidate.name === name);
        if (column && this.canToggleColumn(column)) {
            this.updateColumn(name, { visible: !this.isColumnVisible(column) });
        }
    },

    updateColumn(name, changes) {
        this.layout.config = {
            ...this.layout.config,
            [name]: { ...this.layout.config[name], ...changes },
        };
        this.layout.dirty = true;
    },

    isColumnFrozen(column) {
        return (
            movableNames(this.allColumns).has(column.name) &&
            this.layout.config[column.name]?.frozen === true
        );
    },

    toggleColumnFrozen(column) {
        if (this.canMoveColumn(column) && this.isColumnVisible(column)) {
            this.updateColumn(column.name, { frozen: !this.isColumnFrozen(column) });
        }
    },

    canMoveColumn(column) {
        return this.canPersonalize && movableNames(this.allColumns).has(column.name);
    },

    onColumnDragStart(event, column) {
        if (!this.canMoveColumn(column)) {
            event.preventDefault();
            return;
        }
        this.clearColumnDrag();
        this.columnDrag.source = column.name;
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", column.name);
    },

    clearColumnDrag() {
        Object.assign(this.columnDrag, {
            source: null,
            target: null,
            placement: null,
        });
    },

    onColumnMenuStateChanged(state) {
        if (!state.isOpen) {
            this.clearColumnDrag();
        }
    },

    onColumnDragOver(event, column) {
        const source = this.settingsColumns.find((item) => item.name === this.columnDrag.source);
        const allowed =
            source &&
            source.name !== column.name &&
            this.canMoveColumn(source) &&
            this.canMoveColumn(column) &&
            this.isColumnFrozen(source) === this.isColumnFrozen(column);
        if (!allowed) {
            this.columnDrag.target = null;
            this.columnDrag.placement = null;
            if (event.dataTransfer) {
                event.dataTransfer.dropEffect = "none";
            }
            return;
        }
        event.preventDefault();
        const bounds = event.currentTarget.getBoundingClientRect();
        this.columnDrag.target = column.name;
        this.columnDrag.placement =
            event.clientY < bounds.top + bounds.height / 2 ? "before" : "after";
        if (event.dataTransfer) {
            event.dataTransfer.dropEffect = "move";
        }
    },

    onColumnDragLeave(event) {
        if (!event.currentTarget.contains(event.relatedTarget)) {
            this.columnDrag.target = null;
            this.columnDrag.placement = null;
        }
    },

    onColumnDrop(event, column) {
        event.preventDefault();
        this.onColumnDragOver(event, column);
        if (this.columnDrag.target) {
            this.changeColumnOrder(this.columnDrag.source, column.name, this.columnDrag.placement);
        }
        this.clearColumnDrag();
    },

    onColumnMoveKey(event, column) {
        if (
            !event.altKey ||
            !["ArrowUp", "ArrowDown"].includes(event.key) ||
            !this.canMoveColumn(column)
        ) {
            return;
        }
        event.preventDefault();
        event.stopPropagation();
        const direction = event.key === "ArrowDown" ? 1 : -1;
        const index = this.settingsColumns.findIndex((candidate) => candidate.id === column.id);
        const target = this.settingsColumns[index + direction];
        if (target && this.canMoveColumn(target)) {
            this.changeColumnOrder(column.name, target.name);
        }
    },

    changeColumnOrder(source, target, placement = null) {
        if (!this.canPersonalize || source === target) {
            return;
        }
        if (!!this.layout.config[source]?.frozen !== !!this.layout.config[target]?.frozen) {
            this.notificationService.add(
                _t("Reorder within the same group. Use the pin button to change groups."),
                { type: "info" },
            );
            return;
        }
        const config = moveColumn(
            this.orderedLayoutColumns,
            this.layout.config,
            source,
            target,
            placement,
        );
        if (config !== this.layout.config) {
            this.layout.config = config;
            this.layout.dirty = true;
        }
    },

    async saveLayout() {
        if (!this.canPersonalize || !this.layout.dirty) {
            return;
        }
        this.layout.busy = true;
        try {
            const { available, visible } = this.columnVisibility;
            for (const name of available) {
                this.layout.config[name] = {
                    ...this.layout.config[name],
                    visible: visible.has(name),
                };
            }
            await this.preferences.save(this.scope, JSON.parse(JSON.stringify(this.layout.config)));
            this.layout.dirty = false;
            this.notificationService.add(_t("List layout saved."), {
                type: "success",
            });
        } catch {
            this.notificationService.add(
                _t("Could not save list layout. Your changes are still available; retry saving."),
                { type: "danger" },
            );
        } finally {
            this.layout.busy = false;
        }
    },

    async resetLayout() {
        if (!this.canPersonalize) {
            return;
        }
        this.layout.busy = true;
        try {
            await this.preferences.reset(this.scope);
            this.layout.config = {};
            this.layout.dirty = false;
            this.preferenceWidths.reset();
        } catch {
            this.notificationService.add(_t("Could not reset list layout. Please retry."), {
                type: "danger",
            });
        } finally {
            this.layout.busy = false;
        }
    },
});

// Compatibility export for views that explicitly imported the shared renderer.
export { ListRenderer as ComponentListRenderer };
