import { Component, onWillStart, useSubEnv } from "@odoo/owl";
import { makeContext } from "@web/core/context";
import { _t } from "@web/core/l10n/translation";
import { useBus, useService } from "@web/core/utils/hooks";
import { CogMenu } from "@web/search/cog_menu/cog_menu";
import { Layout } from "@web/search/layout";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { SearchModel } from "@web/search/search_model";
import { WithSearch } from "@web/search/with_search/with_search";
import { getDefaultConfig } from "@web/views/view";

const escapeAttribute = (value) => String(value).replaceAll("&", "&amp;")
    .replaceAll('"', "&quot;").replaceAll("<", "&lt;");

const contextKey = (key) => `dashboard_${key}`;

function itemKey(item) {
    return item.fieldName || item.name?.split("__")[0];
}

class DashboardSearchModel extends SearchModel {
    get domainEvalContext() {
        const companyId = this.context[contextKey("company_id")]?.[0];
        return {
            ...super.domainEvalContext,
            dashboard_annual: this.context.dashboard_view_mode?.[0] === "annual",
            dashboard_department_companies: companyId ? [companyId] : this.globalContext.dashboard_company_ids || [],
        };
    }

    replaceChoice(key, annual = false) {
        this.query = this.query.filter((entry) => {
            const previousKey = itemKey(this.searchItems[entry.searchItemId]);
            return previousKey !== key
                && !(key === contextKey("company_id") && previousKey === contextKey("department_id"))
                && !(annual && previousKey === contextKey("month"));
        });
    }

    toggleSearchItem(id) {
        const item = this.searchItems[id];
        const key = itemKey(item);
        if (key?.startsWith("dashboard_") && !this.query.some((entry) => entry.searchItemId === id)) {
            const annual = key === contextKey("view_mode")
                && makeContext([item.context]).dashboard_view_mode?.[0] === "annual";
            this.replaceChoice(key, annual);
        }
        return super.toggleSearchItem(id);
    }

    addAutoCompletionValues(id, autocompleteValue) {
        const key = itemKey(this.searchItems[id]);
        if (key?.startsWith("dashboard_")) {
            if (!Number.isInteger(autocompleteValue.value)) return;
            this.replaceChoice(key);
        }
        return super.addAutoCompletionValues(id, autocompleteValue);
    }
}

export class DashboardControlPanel extends Component {
    static template = "custom_web_components.DashboardControlPanel";
    static components = { WithSearch };
    static props = ["title", "model", "action?", "actionState?", "search?", "onSearch?", "hideSearchBar?", "slots"];

    setup() {
        const config = { ...getDefaultConfig(), ...this.env.config, actionId: this.props.action?.id };
        config.setDisplayName(this.props.title);
        useSubEnv({ config });
        if (!this.props.search) return;
        const orm = useService("orm");
        this.SearchModel = DashboardSearchModel;
        this.fields = {};
        this.context = {};
        const filters = [];
        const fields = [];
        for (const { key, label, choices, value, hideAnnual } of this.props.search.groups || []) {
            const fieldName = contextKey(key);
            filters.push(choices.map(({ id, name }, index) => {
                const filterName = `${fieldName}__${index}`;
                if (!label && id === value) this.context[`search_default_${filterName}`] = 1;
                const expression = JSON.stringify({ [fieldName]: [id] });
                const invisible = hideAnnual ? ' invisible="dashboard_annual"' : "";
                return `<filter name="${filterName}" string="${escapeAttribute(name)}" context="${escapeAttribute(expression)}"${invisible}/>`;
            }).join(""));
            if (label && choices.length) {
                this.fields[fieldName] = {
                    name: fieldName, string: label, type: "selection", searchable: true,
                    selection: choices.map(({ id, name }) => [id, name]),
                };
                if (choices.some(({ id }) => id === value)) {
                    this.context[`search_default_${fieldName}`] = value;
                }
                fields.push(this.searchField(fieldName));
            }
        }
        const organization = this.props.search.organization;
        if (organization) {
            const departmentField = contextKey("department_id");
            this.fields[departmentField] = {
                name: departmentField, type: "many2one", relation: "hr.department",
                string: organization.departmentLabel, searchable: true,
            };
            this.context.dashboard_company_ids = organization.companyIds;
            if (organization.departmentId) {
                this.context[`search_default_${departmentField}`] = organization.departmentId;
            }
            fields.push(this.searchField(departmentField, "[('company_id', 'in', dashboard_department_companies)]"));
        }
        this.arch = `<search>${[fields.join(""), ...filters].filter(Boolean).join("<separator/>")}</search>`;
        this.irFilters = [];
        onWillStart(async () => {
            if (this.props.action?.id && !this.props.hideSearchBar) {
                this.irFilters = await orm.call("ir.filters", "get_filters", [this.props.model, this.props.action.id]);
            }
        });
    }

    searchField(name, domain = "[]") {
        return `<field name="${name}" operator="=" domain="${domain}" filter_domain="[]" context="{'${name}': self}"/>`;
    }
}

export function organizationSearch(data, options, departmentLabel = _t("主职部门")) {
    const choices = data?.companies || [];
    return {
        groups: [{
            key: "company_id", label: _t("公司"), choices,
            value: options.company_id || (choices.length === 1 ? choices[0].id : 0),
        }],
        organization: { departmentLabel, companyIds: choices.map(({ id }) => id), departmentId: options.department_id },
    };
}

export class DashboardLayout extends Component {
    static template = "custom_web_components.DashboardLayout";
    static components = { Layout, SearchBar, CogMenu };
    static props = ["model", "onSearch?", "hideSearchBar?", "slots"];

    setup() {
        if (this.env.searchModel && this.props.onSearch) {
            const update = () => this.props.onSearch(this.env.searchModel.context);
            useBus(this.env.searchModel, "update", update);
            onWillStart(update);
        }
    }
}
DashboardControlPanel.components.DashboardLayout = DashboardLayout;
