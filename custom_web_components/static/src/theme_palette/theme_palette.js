import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { normalizeCSSColor } from "@web/core/utils/colors";
import { useService } from "@web/core/utils/hooks";

const probe = (id, name, cssName, probeClass, property = "backgroundColor") => ({
    id,
    name,
    cssName,
    probeClass,
    property,
});

const variable = (id, name, cssName) => ({
    id,
    name,
    cssName,
    variable: `--cwc-theme-${id}`,
});

export const THEME_COLOR_GROUPS = [
    {
        id: "theme",
        name: "主题语义色",
        description: "Bootstrap 与 Odoo 组件共用的背景语义，是按钮、徽标和状态的基础色。",
        tokens: [
            probe("theme-primary", "主题", ".bg-primary", "bg-primary"),
            probe("theme-secondary", "次要", ".bg-secondary", "bg-secondary"),
            probe("theme-success", "成功", ".bg-success", "bg-success"),
            probe("theme-info", "信息", ".bg-info", "bg-info"),
            probe("theme-warning", "警告", ".bg-warning", "bg-warning"),
            probe("theme-danger", "危险", ".bg-danger", "bg-danger"),
            probe("theme-light", "浅色", ".bg-light", "bg-light"),
            probe("theme-dark", "深色", ".bg-dark", "bg-dark"),
        ],
    },
    {
        id: "brand",
        name: "品牌与动作",
        description: "Odoo 品牌、链接、动作和收藏等全局令牌。",
        tokens: [
            variable("brand-primary", "品牌主色", "$o-brand-primary"),
            variable("brand-odoo", "Odoo 品牌色", "$o-brand-odoo"),
            variable("action", "动作色", "$o-action"),
            variable("brand-secondary", "品牌次色", "$o-brand-secondary"),
            variable("brand-lightsecondary", "品牌浅次色", "$o-brand-lightsecondary"),
            variable("link", "链接色", "$o-main-link-color"),
            variable("favourite", "收藏色", "$o-main-favorite-color"),
        ],
    },
    {
        id: "text",
        name: "语义文字",
        description: "已经过可读性调整的文字工具类，数值可能与同名背景色不同。",
        tokens: [
            probe("text-primary", "主题文字", ".text-primary", "text-primary", "color"),
            probe("text-secondary", "次要文字", ".text-secondary", "text-secondary", "color"),
            probe("text-success", "成功文字", ".text-success", "text-success", "color"),
            probe("text-info", "信息文字", ".text-info", "text-info", "color"),
            probe("text-warning", "警告文字", ".text-warning", "text-warning", "color"),
            probe("text-danger", "危险文字", ".text-danger", "text-danger", "color"),
            probe("text-light", "浅色文字", ".text-light", "text-light", "color"),
            probe("text-dark", "深色文字", ".text-dark", "text-dark", "color"),
            probe("text-action", "动作文字", ".text-action", "text-action", "color"),
            probe("text-favourite", "收藏文字", ".text-favourite", "text-favourite", "color"),
        ],
    },
    {
        id: "neutral",
        name: "中性色阶",
        description: "从页面底色到正文深色的完整灰阶，可用于层级、边框和禁用状态。",
        tokens: [
            probe("neutral-white", "白色", ".bg-white", "bg-white"),
            ...[100, 200, 300, 400, 500, 600, 700, 800, 900].map((step) =>
                probe(`neutral-${step}`, `灰 ${step}`, `.bg-${step}`, `bg-${step}`),
            ),
            probe("neutral-black", "黑色", ".bg-black", "bg-black"),
        ],
    },
    {
        id: "spectrum",
        name: "基础色谱",
        description: "Bootstrap 基础色，适合图表、分类和需要稳定区分度的辅助视觉。",
        tokens: [
            variable("blue", "蓝", "$blue"),
            variable("indigo", "靛蓝", "$indigo"),
            variable("purple", "紫", "$purple"),
            variable("pink", "粉", "$pink"),
            variable("red", "红", "$red"),
            variable("orange", "橙", "$orange"),
            variable("yellow", "黄", "$yellow"),
            variable("green", "绿", "$green"),
            variable("teal", "青绿", "$teal"),
            variable("cyan", "青", "$cyan"),
        ],
    },
    {
        id: "interface",
        name: "界面基础",
        description: "页面表面、正文、边界、选中和输入状态使用的底层颜色。",
        tokens: [
            variable("view-background", "视图背景", "$o-view-background-color"),
            variable("main-text", "正文", "$o-main-text-color"),
            variable("muted", "弱化文字", "$o-main-color-muted"),
            variable("heading", "标题", "$o-main-headings-color"),
            variable("border", "默认边框", "$border-color"),
            variable("active-background", "选中背景", "$o-component-active-bg"),
            variable("active-border", "选中边框", "$o-component-active-border"),
            variable("required-border", "必填边框", "$o-input-border-required"),
            variable("invalid-background", "无效输入背景", "$o-input-invalid-bg"),
            variable("form-secondary", "表单辅助", "$o-form-lightsecondary"),
            variable("shadow", "阴影基色", "$o-shadow-color"),
        ],
    },
    {
        id: "alerts",
        name: "提示组件实际色",
        description: "从当前渲染的 Alert 组件读取文字、背景和边框，可发现主题的组件级覆盖。",
        tokens: [
            ...["success", "info", "warning", "danger"].flatMap((type) => [
                probe(
                    `alert-${type}-text`,
                    `${type} · 文字`,
                    `.alert-${type} color`,
                    `alert alert-${type}`,
                    "color",
                ),
                probe(
                    `alert-${type}-background`,
                    `${type} · 背景`,
                    `.alert-${type} background`,
                    `alert alert-${type}`,
                ),
                probe(
                    `alert-${type}-border`,
                    `${type} · 边框`,
                    `.alert-${type} border`,
                    `alert alert-${type}`,
                    "borderTopColor",
                ),
            ]),
        ],
    },
];

export const THEME_COLOR_COUNT = THEME_COLOR_GROUPS.reduce(
    (count, group) => count + group.tokens.length,
    0,
);

export class ThemePalette extends Component {
    static template = "custom_web_components.ThemePalette";
    static props = ["*"];

    setup() {
        this.groups = THEME_COLOR_GROUPS;
        this.totalColors = THEME_COLOR_COUNT;
        this.paletteRoot = useRef("paletteRoot");
        this.colors = useState({});
        this.notification = useService("notification");
        onMounted(() => this.readColors());
    }

    readColors() {
        const root = this.paletteRoot.el;
        const rootStyle = getComputedStyle(root);
        for (const group of this.groups) {
            for (const token of group.tokens) {
                let value;
                if (token.variable) {
                    value = rootStyle.getPropertyValue(token.variable).trim();
                } else {
                    const element = root.querySelector(`[data-color-probe="${token.id}"]`);
                    value = getComputedStyle(element)[token.property];
                }
                this.colors[token.id] = normalizeCSSColor(value);
            }
        }
    }

    swatchStyle(token) {
        const color = this.colors[token.id];
        return color ? `background-color: ${color}` : "";
    }

    copyLabel(token) {
        return `复制 ${token.name} ${this.colors[token.id] || "颜色值"}`;
    }

    async copyColor(token) {
        const color = this.colors[token.id];
        if (!color) {
            return;
        }
        try {
            await browser.navigator.clipboard.writeText(color);
            this.notification.add(`已复制 ${token.name}：${color}`, {
                type: "success",
            });
        } catch {
            this.notification.add("无法复制颜色，请检查浏览器剪贴板权限。", {
                type: "warning",
            });
        }
    }
}

registry.category("actions").add("custom_web_components.theme_palette", ThemePalette);
