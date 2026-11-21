import { Component, useRef, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { IndicatorProgress } from "@custom_web_components/indicator_progress/indicator_progress";

const entry = (id, name, englishName, description, snippet, keywords = "") => ({
    id,
    name,
    englishName,
    description,
    snippet,
    keywords,
});

export const COMPONENT_GROUPS = [
    {
        id: "foundation",
        name: "基础",
        icon: "fa-cube",
        description: "组成界面的最小视觉元素。",
        components: [
            entry(
                "button",
                "按钮",
                "Button",
                "触发主要、次要或危险操作。",
                '<button class="btn btn-primary">主要操作</button>',
                "action primary secondary danger",
            ),
            entry(
                "icon",
                "图标",
                "Icon",
                "用紧凑的视觉符号辅助识别操作。",
                '<i class="fa fa-search" aria-hidden="true"/>',
                "font awesome symbol",
            ),
            entry(
                "typography",
                "排版",
                "Typography",
                "建立标题、正文与辅助信息的阅读层级。",
                '<h4>标题</h4><p class="text-muted">辅助说明</p>',
                "heading text muted",
            ),
            entry(
                "link",
                "链接",
                "Link",
                "跳转到另一位置或打开关联资源。",
                '<a href="#">查看详细资料</a>',
                "anchor navigation",
            ),
            entry(
                "divider",
                "分割线",
                "Divider",
                "分隔相邻但语义不同的内容区域。",
                '<hr class="my-3"/>',
                "separator rule",
            ),
        ],
    },
    {
        id: "layout",
        name: "布局",
        icon: "fa-columns",
        description: "组织内容的空间、网格与响应式规则。",
        components: [
            entry(
                "grid",
                "栅格",
                "Grid",
                "按十二列体系组织响应式页面。",
                '<div class="row"><div class="col-4">4</div><div class="col-8">8</div></div>',
                "columns row responsive",
            ),
            entry(
                "stack",
                "堆叠",
                "Stack",
                "沿单一方向排列一组关联元素。",
                '<div class="d-flex flex-column gap-2">...</div>',
                "flex vertical horizontal",
            ),
            entry(
                "spacing",
                "间距",
                "Spacing",
                "使用统一的内外边距建立节奏。",
                '<div class="p-3 mb-2">...</div>',
                "padding margin gap",
            ),
            entry(
                "responsive",
                "响应式",
                "Responsive",
                "根据可用宽度改变内容结构。",
                '<div class="d-grid d-md-flex gap-2">...</div>',
                "breakpoint mobile desktop",
            ),
        ],
    },
    {
        id: "navigation",
        name: "导航",
        icon: "fa-compass",
        description: "帮助用户定位、切换和推进流程。",
        components: [
            entry(
                "breadcrumb",
                "面包屑",
                "Breadcrumb",
                "展示当前页面在信息层级中的位置。",
                '<nav><ol class="breadcrumb">...</ol></nav>',
                "path hierarchy",
            ),
            entry(
                "tabs",
                "标签页",
                "Tabs",
                "在同一上下文中切换并列内容。",
                '<ul class="nav nav-tabs">...</ul>',
                "sections switch",
            ),
            entry(
                "pagination",
                "分页",
                "Pagination",
                "在分段数据集合之间移动。",
                '<ul class="pagination">...</ul>',
                "pager pages",
            ),
            entry(
                "dropdown",
                "下拉菜单",
                "Dropdown",
                "在有限空间内收纳一组操作。",
                '<Dropdown><button>更多</button><t t-set-slot="content">...</t></Dropdown>',
                "menu actions overlay",
            ),
            entry(
                "steps",
                "步骤条",
                "Steps",
                "表达线性流程的当前位置与完成状态。",
                '<ol class="o_cwc_steps">...</ol>',
                "wizard progress process",
            ),
        ],
    },
    {
        id: "data-entry",
        name: "数据录入",
        icon: "fa-keyboard-o",
        description: "收集、选择和校验用户输入。",
        components: [
            entry(
                "input",
                "输入框",
                "Input",
                "录入简短的单行文本。",
                '<input class="form-control" placeholder="请输入"/>',
                "text field",
            ),
            entry(
                "textarea",
                "文本域",
                "Textarea",
                "录入较长的多行内容。",
                '<textarea class="form-control" rows="3"/>',
                "multiline",
            ),
            entry(
                "select",
                "选择器",
                "Select",
                "从预定义选项中选择一项。",
                '<select class="form-select"><option>选项</option></select>',
                "option picker",
            ),
            entry(
                "checkbox",
                "复选框",
                "Checkbox",
                "独立开启或关闭多个选项。",
                '<input class="form-check-input" type="checkbox"/>',
                "multiple choice",
            ),
            entry(
                "radio",
                "单选框",
                "Radio",
                "从互斥选项中选择一项。",
                '<input class="form-check-input" type="radio"/>',
                "single choice",
            ),
            entry(
                "switch",
                "开关",
                "Switch",
                "即时切换一个布尔状态。",
                '<button role="switch" aria-checked="true">...</button>',
                "toggle boolean",
            ),
            entry(
                "input-group",
                "组合输入",
                "Input Group",
                "为输入框附加前缀、后缀或动作。",
                '<div class="input-group"><span class="input-group-text">¥</span><input class="form-control"/></div>',
                "prefix suffix",
            ),
            entry(
                "range",
                "滑块",
                "Range",
                "在连续区间中选择近似值。",
                '<input class="form-range" type="range"/>',
                "slider number",
            ),
            entry(
                "date",
                "日期",
                "Date Input",
                "通过浏览器日期控件录入日期。",
                '<input class="form-control" type="date"/>',
                "calendar time",
            ),
            entry(
                "upload",
                "文件上传",
                "File Input",
                "从本地设备选择一个或多个文件。",
                '<input class="form-control" type="file"/>',
                "attachment file",
            ),
        ],
    },
    {
        id: "data-display",
        name: "数据展示",
        icon: "fa-table",
        description: "以可扫描的形式呈现状态和业务数据。",
        components: [
            entry(
                "badge",
                "徽标",
                "Badge",
                "用紧凑数字或短词强调状态。",
                '<span class="badge text-bg-success">已完成</span>',
                "count state",
            ),
            entry(
                "tag",
                "标签",
                "Tag",
                "标注分类、属性或可移除的筛选条件。",
                '<span class="o_cwc_tag">企业客户</span>',
                "label category chip",
            ),
            entry(
                "avatar",
                "头像",
                "Avatar",
                "表示用户、团队或对象身份。",
                '<span class="o_cwc_avatar">陈</span>',
                "person identity initials",
            ),
            entry(
                "card",
                "卡片",
                "Card",
                "将标题、内容和操作组合为独立区域。",
                '<div class="card"><div class="card-body">...</div></div>',
                "panel container",
            ),
            entry(
                "table",
                "表格",
                "Table",
                "按行列对齐展示结构化数据。",
                '<table class="table"><thead>...</thead><tbody>...</tbody></table>',
                "rows columns list view",
            ),
            entry(
                "list",
                "列表",
                "List",
                "按垂直顺序展示同类条目。",
                '<div class="list-group"><div class="list-group-item">...</div></div>',
                "items collection",
            ),
            entry(
                "empty",
                "空状态",
                "Empty State",
                "解释无数据状态并提供下一步。",
                '<div class="o_cwc_empty_state">暂无数据</div>',
                "blank no data",
            ),
            entry(
                "progress",
                "进度条",
                "Progress",
                "反馈任务完成比例。",
                '<div class="progress"><div class="progress-bar" style="width: 68%"/></div>',
                "percent loading",
            ),
            entry(
                "indicator-progress",
                "指标进度",
                "Indicator Progress",
                "用带底色的轨道对比实际值与目标竖线，允许实际值越过目标。",
                `<IndicatorProgress actual="120" target="100" tone="'success'" actualText="'实际 120次'" targetText="'目标 100次'" ariaLabel="'年度达成率：120%'"/>`,
                "kpi target actual success warning danger attainment 目标 实际 达成率",
            ),
        ],
    },
    {
        id: "feedback",
        name: "反馈",
        icon: "fa-bell-o",
        description: "回应操作结果、系统状态与等待过程。",
        components: [
            entry(
                "alert",
                "警告提示",
                "Alert",
                "在内容流中持续说明重要状态。",
                '<div class="alert alert-warning">请检查待确认信息。</div>',
                "warning success info danger",
            ),
            entry(
                "notification",
                "消息通知",
                "Notification",
                "短暂反馈操作结果，不中断当前任务。",
                "notification.add('保存成功', { type: 'success' })",
                "toast success warning danger",
            ),
            entry(
                "dialog",
                "对话框",
                "Dialog",
                "要求用户确认或集中处理一项任务。",
                "dialog.add(ConfirmationDialog, { title: '确认操作', body: '...' })",
                "modal confirmation",
            ),
            entry(
                "spinner",
                "加载指示",
                "Spinner",
                "表示耗时未知的进行中状态。",
                '<span class="spinner-border" role="status"/>',
                "loading wait",
            ),
            entry(
                "skeleton",
                "骨架屏",
                "Skeleton",
                "在内容结构已知时提供加载占位。",
                '<div class="o_cwc_skeleton">...</div>',
                "placeholder loading",
            ),
            entry(
                "status",
                "状态点",
                "Status",
                "用颜色与文字联合表达运行状态。",
                '<span class="o_cwc_status"><i/>运行中</span>',
                "online offline health",
            ),
        ],
    },
];

export const COMPONENT_COUNT = COMPONENT_GROUPS.reduce(
    (count, group) => count + group.components.length,
    0,
);

export class ComponentCatalog extends Component {
    static template = "custom_web_components.ComponentCatalog";
    static components = { Dropdown, DropdownItem, IndicatorProgress };
    static props = ["*"];

    setup() {
        this.groups = COMPONENT_GROUPS;
        this.totalComponents = COMPONENT_COUNT;
        this.catalogRoot = useRef("catalogRoot");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.state = useState({
            query: "",
            activeCategory: COMPONENT_GROUPS[0].id,
            activeTab: "overview",
            page: 2,
            switchOn: true,
            progress: 68,
            dropdownChoice: "尚未选择",
        });
    }

    get visibleGroups() {
        const query = this.state.query.trim().toLocaleLowerCase();
        if (!query) {
            return this.groups;
        }
        return this.groups
            .map((group) => ({
                ...group,
                components: group.components.filter((component) =>
                    [
                        component.name,
                        component.englishName,
                        component.description,
                        component.keywords,
                    ]
                        .join(" ")
                        .toLocaleLowerCase()
                        .includes(query),
                ),
            }))
            .filter((group) => group.components.length);
    }

    get visibleCount() {
        return this.visibleGroups.reduce((count, group) => count + group.components.length, 0);
    }

    onSearch(event) {
        this.state.query = event.target.value;
    }

    clearSearch() {
        this.state.query = "";
    }

    scrollToCategory(categoryId) {
        this.state.activeCategory = categoryId;
        this.catalogRoot.el
            .querySelector(`[data-category="${categoryId}"]`)
            ?.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    setActiveTab(tab) {
        this.state.activeTab = tab;
    }

    setPage(page) {
        this.state.page = page;
    }

    toggleSwitch() {
        this.state.switchOn = !this.state.switchOn;
    }

    adjustProgress(delta) {
        this.state.progress = Math.max(0, Math.min(100, this.state.progress + delta));
    }

    chooseDropdown(label) {
        this.state.dropdownChoice = label;
    }

    showNotification(type) {
        const messages = {
            success: "组件配置已保存。",
            warning: "还有 2 项内容需要确认。",
            danger: "操作失败，请稍后重试。",
        };
        this.notification.add(messages[type], { type });
    }

    openDialog() {
        this.dialog.add(ConfirmationDialog, {
            title: "确认提交",
            body: "这是一条标准确认对话框示例，不会修改任何业务数据。",
            confirmLabel: "确认",
            cancelLabel: "取消",
            cancel: () => {},
        });
    }

    async copySnippet(component) {
        try {
            await browser.navigator.clipboard.writeText(component.snippet);
            this.notification.add(`已复制 ${component.name} 示例`, { type: "success" });
        } catch {
            this.notification.add("无法复制代码，请检查浏览器剪贴板权限。", {
                type: "warning",
            });
        }
    }
}

registry.category("actions").add("custom_web_components.component_catalog", ComponentCatalog);
