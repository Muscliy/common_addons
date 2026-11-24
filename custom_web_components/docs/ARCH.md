# ARCH: custom_web_components

- **Source location**: `common_addons/custom_web_components/` in the `common_addons` Git submodule. Odoo module names, asset URLs, model names, XML IDs and database tables remain unchanged; the host project must include `common_addons` in `addons_path`.
## 1. Overview

- **Technical Name**: `custom_web_components`
- **Core Purpose**: 长期维护的 Odoo Web/UI 公共组件；提供用户列表布局、可复用指标进度和本地 Playground。
- **Dependencies**: `web`；`auto_install=True`，无循环依赖，无新增生产依赖。
- **Entry Points**: registry `list` / `custom_web_list`、service `component_preference`；开发工具 → 组件、开发工具 → Component Playground → List View、开发工具 → 主题。
- **Boundary**: 通用能力在 models/static；开发模型/环境保护/菜单在 dev/playground。

## 2. Model Extensions & Schema

### web.component.preference

- Table: `abt_web_component_preference`。
- Fields: user_id (res.users, required, cascade), component_type (Char), view_id (ir.ui.view, optional/cascade), model (Char), key (Char/default), config (Json), scope (computed/precomputed/stored Char)。
- Unique: `(user_id, scope)`；scope 是 `[component_type, view_id or 0, model, key]` 的确定性 JSON，避免 PostgreSQL NULL unique 语义导致无 view 的重复配置。
- Constraints: 合法作用域 token、已知 model、list 的 view/model 匹配且必须为真实 list view；list_nested 必须指定父视图，key 为 x2many:字段路径，关系链终点必须与列表 model 一致、64 KiB JSON 上限；list/list_nested 字段仅允许 sequence/width/visible/frozen，整数/boolean 与范围校验。
- Ownership: base.group_user ACL + 无分组全局 owner rule；create/write 显式禁止普通用户伪造/转移 user_id；不通过 sudo 读写偏好。scope 禁止调用方赋值（包括 context default 注入）。
- Metadata: 仅验证 ir.ui.view 的 model/type 时 sudo，因为内部用户无该模型直接读取权限；不返回视图元数据。
- Empty config: Odoo Json 将空对象归一为空值，API 返回 `{}`；reset 删除记录。

### web.component.playground.order

- Table: `abt_web_component_playground_order`。
- Fields: name, user_id, partner_id, order_date, salesperson_id, state, currency_id, amount, note；标准审计字段。
- No sale dependency, no customer/company creation, no mail, no scheduled jobs。
- Internal-user ACL + owner rule；OCB 19 的 `_check_access`、`_search`、`read`、`export_data` 及公开 `check_access` 入口都额外验证本地环境，覆盖管理员环境绕过一般 ACL 的路径。get_views/get_view 同样验证。
- 首次打开为当前用户生成 40 条 DEMO 订单，默认用自己的 partner、user、公司币种；正常安装/升级不创建记录。

### Inherited framework models

- ir.ui.menu._visible_menu_ids: 在 core 缓存结果之外按当前进程环境过滤开发工具子树，不改变数据库菜单 active/groups。
- ir.actions.act_window._get_action_dict: 对 res_model 为 `web.component.playground.*` 的动作检查环境和内部用户；只有模型名判断使用 sudo，权限检查使用原用户。
- ir.actions.client._get_action_dict: 对 tag 为 `custom_web_components.component_catalog` / `custom_web_components.theme_palette` 的组件目录与主题色板动作执行相同环境与内部用户检查。

## 3. Business Logic & Data Flow

1. 初始化仅安装 web 也自动安装模块；Docker scripts/deploy.sh init 列表显式包含模块。已有库需一次 -i。
2. 通过 Odoo patch 扩展原生 ListRenderer 及 extension 模式扩展 web.ListRenderer 模板，保留业务专用 Controller/Renderer/SearchModel 和标准 registry。Renderer 从 env.config.viewId/viewType 构造顶层 list 作用域；明细根据 nestedKeyOptionalFieldsData 和祖先 Renderer 的 componentListPath 构造 list_nested/model/父视图/x2many:字段路径，通过 useSubEnv 传递关系路径。原有 list/model/viewId/default 配置保持兼容。
3. Renderer onWillStart 调用 preference service load；加载失败保持默认渲染并提示，禁用持久化入口，避免覆盖未知保存配置。
4. getActiveColumns 先调用原生 optional/column_invisible/group 过滤，再应用普通字段的个人显隐，根据完整 allColumns 的 sequence 和 frozen 分区返回排序后的活动列；OWL 同步渲染表头/行/汇总，不移动 DOM 节点。
5. 右侧原生 Dropdown 内展示所有可用字段列，HTML drag/drop 只接受本 Renderer 菜单启动的具名列拖动；Alt+上下方向键等价。固定/普通列组内排序，跨组用图钉。编辑中禁用顺序/显隐/固定/保存/重置，表头不再注入控制按钮。菜单不显示重复标题/说明/分组文字，固定与普通区域用细线分隔。columnDrag 保存 source/target/placement；行中心划分 before/after，提示线与 drop 共用坐标判定。拖动时仅更新提示，松手后按目标移除源列后的实际索引插入，避免向下拖动差一位。非法/外部拖动无提示，离开目标、Escape、dragend、drop、关闭菜单均清理提示；动画遵循 prefers-reduced-motion。
6. 宽度 hook 关闭 ListRenderer 原生瞬时宽度 effect，复用其 onStartResize 手势和 FIELD_WIDTHS/listViewWidth 默认约束。显式 user/XML 像素值优先；未知宽度通过浏览器测量并按原生类型范围约束。ResizeObserver 重算内容区，保持显式宽度。
7. 拖动/缩放/显隐/固定仅改变本地 config 和 dirty 状态；菜单保存按钮提交完整 config。失败保留修改并通知；reset 清空配置，恢复 XML 顺序/宽度/optional 显隐并取消固定。
8. columnVisibility 在已通过权限/column_invisible 过滤的普通字段中应用 config.visible，未配置字段使用 XML 初始显隐。普通字段与 optional 字段都可个性化，handle/动态 property 等结构列不参与计数；相同字段重复出现只计一次。最少保留 min(2, 可用字段数) 个字段；旧配置或视图/权限变化不足时按原始字段顺序补足。只剩最低数量时禁止取消选中，事件处理同样校验；保存时固化实际可见字段。computeOptionalActiveFields 将该结果交给原生 optional 过滤，不读取跨用户 localStorage。无 view ID/加载失败回退原生菜单和显隐。
9. frozenFirst 只分区可唯一识别的字段槽位，OWL 控制顺序。useFrozenColumns 用实际表头宽度累计 sticky 偏移；只给完整覆盖固定区的 colspan 单元格应用样式；选择框/handle 一并固定。ResizeObserver 追踪 resize，区域超过容器宽减 80px 时暂停固定并提示，打印无 sticky。
10. 列表视图根节点的 `cwc_sticky_end` 类启用末尾数据列固定。`useStickyEndColumn` 依据 OWL 当前列顺序和表头实测宽度，为末尾列与其后的原生辅助列计算右侧偏移；跨列的分组单元格不固定。固定区域与左侧用户固定列合计宽度在容器内不足时暂停；末尾字段已由用户固定在左侧时保留个人选择。打印仍无 sticky。
11. service 按 scope 串行保存/重置，不缓存读取，避免跨挂载组件的旧缓存；普通 ORM 用 env.uid 建立 owner domain。
12. Playground 的菜单 server action 调用 open_playground，先检查原用户和环境再按需 seed，再通过标准 _for_xml_id 返回受保护 window action。仅此固定动作的安全元数据使用 sudo 读取，兼容项目主题在 core 读取前检查动作字段；Demo 数据操作始终保留原用户。
13. 主题色板 client action 在浏览器挂载后读取当前编译资产中的 SCSS 令牌、标准颜色工具类与 Alert 组件计算样式，标准化为 HEX/RGBA 展示；点击色块仅复制已渲染的颜色值，不读写数据库。
14. 组件目录 client action 由静态元数据生成分类、搜索和代码片段，当前覆盖基础、布局、导航、数据录入、数据展示、反馈 6 类 39 种组件；示例复用已加载的 Odoo/Bootstrap 样式及 Dropdown、ConfirmationDialog、notification service，不加载外部资源，不读写业务数据。
15. `IndicatorProgress` 是正式公共 Owl 组件，输入 actual、target、tone、ariaLabel 及可选 actualText/targetText；组件用 Odoo SCSS 主题变量生成胶囊形全圆角中性底轨和目标文本，实际填充继承底轨圆角，目标刻度采用 7×19px 的深色边框、浅色背景与双层阴影，以 actual/target 中较大值作为比例尺上限，因此实际值超过目标时填充越过目标线并延伸到轨道末端。tone 只接受 success、warning、danger 并通过系统语义色工具类着色；阈值判断和显示文本格式化由调用方负责。

## 4. Integration & External APIs

### ORM methods (internal authenticated users)

- get_preference(component_type, model, view_id=False, key='default') → JSON object。
- save_preference(component_type, model, view_id=False, key='default', config=None) → True。
- reset_preference(component_type, model, view_id=False, key='default') → True。
- web.component.playground.order.open_playground() → window action；受环境保护。
- client action `custom_web_components.component_catalog` → 可检索的组件类型目录与实时示例；受相同本地开发环境保护。
- client action `custom_web_components.theme_palette` → 当前主题颜色目录；受相同本地开发环境保护。
- 不新增 HTTP 路由。标准 dataset RPC / action 路由及现有 Odoo ACL 继续生效。

### Process configuration

- `TYH_RUNTIME=local` AND `TYH_DATABASE_MODE=local` AND `TYH_ENV in {local,test}` 才开放 Playground。
- scripts/start_development.py 写入解析后的 mode，避免 CLI remote 被旧环境 local 误判；部署入口已有强制 server 标记。
- 未知/缺失/staging/production/remote 均关闭；不依赖 host/IP/debug/context/system parameter。

### Assets and tests

- web.assets_backend: services/utils/list_view、indicator_progress、component_catalog、theme_palette 与 form 的 JS + OWL XML + SCSS。
- web.assets_unit_tests: static/tests/*.test.js，tag cwc。
- tests/: TransactionCase 验证权限/配置/环境矩阵；HttpCase Chrome 验证真实跨会话持久化并执行 HOOT。
- 无外部 API、Token 或新增运行时依赖。

## 5. Gotchas & Constraints

- 统一采用 Odoo patch 扩展原生 ListRenderer.prototype 和静态宽度策略，模板使用 extension。专用 js_class、x2many 及 Renderer 子类通过原生继承链接入，保留业务覆盖方法；不替换标准 list registry。保留 custom_web_list 和 ComponentListController/Renderer 兼容导出。此设计替代旧版仅注册标准 list 子类的局部接入方式，以满足全系统原生列表覆盖。
- 没有实际数据库 view ID 的 ad-hoc 列表无保存入口；手写 HTML 表格、透视表不属于 ListRenderer。自定义组件须调用原生 setup 并保留原生菜单模板扩展点。明细按父视图与完整关系字段路径隔离，路径超过 key 的 128 字符限制时不提供保存入口；不以记录临时 ID 作为布局作用域。
- 重复同名字段、row handle、按钮组、widget 和动态 properties 保持槽位；这类字段不开放移动和固定；普通重复字段共享显隐配置，handle/动态 property 等结构列保持系统显隐。
- `cwc_sticky_end` 是独立的视图默认行为，可固定末尾按钮组或字段，不改变个人偏好 JSON；对继承原生 Renderer 的列表生效。
- 首次使用沿用 XML 初始显隐，保存后普通字段及 optional 字段均由用户/view 偏好控制，并保证最低字段数量。系统隐藏字段和权限裁剪优先，旧浏览器 localStorage 不迁移。该策略自 19.0.1.5.1 起替代“非 optional 必须显示”的旧限制。
- 宽度支持正整数或 px；不支持百分比。显式宽度小于内容时截断/换行，超出容器则横向滚动；不保证原生自适应算法的逐像素结果。
- JSON 是整份用户布局；跨浏览器最后成功写入为准，无实时同步。唯一约束防止并发首次保存产生重复记录，冲突时显示保存失败，用户可重试。
- 修改环境标记需重启对应进程并刷新浏览器。视图/动作元数据会随模块安装在所有环境，但数据访问与入口始终受后端保护；生产不生成演示数据。
- 组件目录是开发参考页而不是独立组件库：其中 Button/Form/Table 等复用 Bootstrap/Odoo 公共样式，Tag/Steps/Skeleton 等是目录内展示的组合模式；若业务代码需要复用组合模式，应先提取到独立 static/src 功能目录并补充 API 测试。
- 色板展示的是当前页面实际加载的颜色：SCSS 令牌通过色板局部 CSS variables 暴露，工具类及 Alert 颜色通过隐藏探针读取 computed style，因此安装其他主题后数值会随资产变化；它不是可编辑的主题配置页。
- 升级核对 env.config.viewId、getActiveColumns/allColumns、FIELD_WIDTHS/listViewWidth、useMagicColumnWidths 关闭开关与 onStartResize 停止事件、ListRenderer Dropdown/optionalFieldGroups 模板 XPath、computeOptionalActiveFields/displayOptionalFields、表头/分组/汇总 colspan 与 sticky 主题变量，以及后端 access/action/menu 方法。
- 新组件使用独立 component_type/key 与对应 static/src 子目录；新增 Demo 必须复用同一后端环境检查并更新本文件。详见 ../README.md。

### Dashboard control panel and stylesheet

- `DashboardControlPanel` wraps Odoo `Layout`, `WithSearch`, `SearchBar` and `CogMenu` for client actions. Each card or list body stays in its own dashboard. Exclusive company, department and period filters pass context to the page’s existing data loaders. Department autocomplete uses the selected company or all currently available companies. Dashboard pages with their own period controls can set `hideSearchBar` to keep the control panel and cog menu without displaying the search bar or loading saved filters.

- static/src/dashboard/dashboard.scss 在 web.assets_backend 中注册；提供 o_cwc_dashboard 根变量、o_cwc_dashboard_header 页头、o_cwc_dashboard_title 标题和 o_cwc_dashboard_metric KPI容器，无JS状态、数据访问或新表。
- 消费者为 custom_hr_workbench 和 custom_hr_indicator：消费者仅处理栅格、业务控件及图表，不能覆盖共享尺寸为另一套视觉。局部 --dashboard-metric-accent 可设置指标语义色。品牌来自Odoo主题变量；中性色集中维护。
- 修改共享规则须同步 DESIGN.md，编译/主题覆盖测试及两页桌面、390px浏览器比较，保持原有业务流程。

### Shared form unit label

- static/src/form/unit_label.scss 在 web.assets_backend 中注册；提供 o_goal_label_unit（数值后的“（单位）”强调色标记）和 o_goal_unit_row（值 + 单位行），无 JS 状态、数据访问或新表。
- 标记内不能出现块级包装：Odoo 字段渲染为 div.o_field_widget > div.o_many2one > a，任一层为 block 都会让括号、单位分成三行，并让 flex 行把标记压到 1 个字符宽。共享规则把包装层和 o_many2one 都收敛为 inline，并禁止标记收缩。
- o_goal_unit_row 把数值输入框限制为 12rem（最小 6rem），使单位紧跟输入框，而不是被推到整行末端；消费者为 custom_hr_indicator 的指标模板、部门/员工指标和“创建下级指标”向导表单，以及 yabo_strategy 的目标与战术表单。custom_hr_indicator 不再依赖 yabo_strategy 的私有样式。
- 修改时同步 DESIGN.md，并在真实表单的桌面与窄屏宽度检查单位不换行、不溢出、输入框仍可读写。
