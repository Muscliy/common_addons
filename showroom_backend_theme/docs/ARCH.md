# ARCH: showroom_backend_theme

- **Source location**: `common_addons/showroom_backend_theme/` in the `common_addons` Git submodule. Odoo module names, asset URLs, model names, XML IDs and database tables remain unchanged; the host project must include `common_addons` in `addons_path`.
## 1. Overview

- **Technical Name**: `showroom_backend_theme`
- **Core Purpose**: 提供 TYJ 白标后台/前台主题，并在服务器运行环境关闭应用管理入口。
- **Dependencies**: `web`, `mail`
- **Semantic Colors**: 增加 `exceed`（超越目标）语义色，默认 `#5F4B8B`；与 Odoo 原生 `success`、`warning` 等状态并列使用。

## 2. Model Extensions & Schema

### Inherited Models

- `ir.ui.menu`:
  - **Fields Added**: None.
  - **Overridden Methods**: `_visible_menu_ids` 在非本地运行时隐藏 `base.menu_management` 及其子菜单。
- `ir.actions.act_window`:
  - **Fields Added**: None.
  - **Overridden Methods**: `_get_action_dict` 在目标模型为应用管理模型时执行运行时访问检查。
- `ir.module.module`:
  - **Fields Added**: None.
  - **Overridden Methods**: `button_install`, `_button_immediate_function`, `_import_zipfile`, `write` 在 HTTP 请求内拒绝安装、升级、卸载或状态切换。
- `res.partner`:
  - **Fields Added**: None.
  - **Overridden Methods**: 新增 `_apply_tyj_branding`，升级时将 OdooBot/root 用户和官方邮件模板中的白标文本迁移为 TYJ 品牌。

### Custom Models

None.

## 3. Business Logic & Data Flow

1. `apps_enabled()` 仅在 `TYH_RUNTIME == "local"` 时返回真；不依赖 `TYH_ENV`、数据库模式或任何请求参数。
2. 非本地运行时，菜单、窗口 action、DataSet RPC 及模块模型写路径共同拦截应用管理模型（`ir.module.*`, `base.module.*`, `base.import.module`）。窗口 action 的目标模型使用 `sudo` 读取，以保持 Odoo 核心对普通内部用户安全加载 action 的既有契约；该提权不改变 action 输出字段或目标业务模型权限。
3. 在安装/升级时，品牌数据与 `_apply_tyj_branding` 更新系统助手、root 用户及 XML 定义邮件模板中的 Odoo 品牌文本；后台和登录页加载主题、导航栏、侧栏与白标前端资产。登录页使用 Odoo 原生登录布局，不依赖 Website。
4. 品牌推广视图保留 `web.brand_promotion_message` 标准调用节点，仅覆盖消息上下文。
5. 登录页停用记录只能引用本模块已经定义的模板视图；不要为不存在的 XML ID 创建只有 `active` 字段的 `ir.ui.view`。OCB 19 会因缺少视图架构而拒绝加载。
5. 后台列表表格保留 Odoo 对宽表计算出的像素宽度，同时使用 `min-width: 100%` 保证列较少的列表铺满渲染容器；宽表仍由列表容器提供横向滚动。
6. `static/src/scss/primary_variables.scss` 在 Odoo 主变量前定义 `$o-exceed` 与 `$exceed`，并合并 `$theme-colors`。`static/src/scss/theme_colors.scss` 在共享 `web._assets_bootstrap` 的 `import_bootstrap.scss` 前加载，补齐强调文字、浅色背景、浅色边框、表格及对应 utility 映射；Odoo/Bootstrap 随后统一生成后台、前台及共享该 Bootstrap bundle 的报表样式。`theme_colors_backend.scss` 使用原生 `button-variant` mixin 补齐 `btn-fill-exceed`；不依赖后台专用的按钮选择器，以兼容移除后台 review 样式的报表 bundle。保留其他语义色映射及原生 hover、focus、active、disabled 和透明度规则。
7. `static/src/scss/showroom_dialog.scss` 同时加载到后台和前台资源。所有 `.modal-footer` 操作区靠右；Odoo 技术弹框中会撑满宽度的 `footer`、表单编辑和查看按钮容器也分别靠右。外层覆盖 Odoo 响应式对齐 utility 的 `!important`，内层覆盖核心 dialog 样式。
8. 后台导航栏和业务侧栏采用白色表面、深色文字及青色选中态。左上角企业标识、顶部 Odoo 原生分区及下拉菜单保持原有结构。侧栏应用名称仍选择应用；有可见子菜单的应用额外显示“…”按钮，按 `menuService.getMenuAsTree()` 展开分组卡片面板。每张卡片宽 200px，面板围绕被点击的按钮垂直居中并在视口边缘内贴边。先按单列渲染并测量整张卡片的高度；超过可用屏幕高度的第一张卡片及后续卡片移入第二列。首次定位和分列完成后才显示面板，并以短淡入过渡呈现，避免从默认位置跳到最终位置。分组内容用原生 `details` 的内容区域过渡；动画结束后重新测量列数和面板位置，避免按中间高度分列。面板以视口高度为上限，不设置内部滚动；分组卡片默认展开，也可通过标题收起。叶子菜单通过 `menuService.selectMenu()` 执行原生 action。切换应用、收起侧栏、点击面板外、按 Escape 或滚动侧栏时关闭面板。窄屏仍使用 Odoo 原生应用菜单。

### Sidebar Bookmarks & History

- 侧栏提供“应用 / 书签 / 记录”三个页签，收起时保留图标切换；应用页继续使用菜单服务与既有分组子菜单。
- `showroom_sidebar_entries` 服务在 `ACTION_MANAGER:UI-UPDATED` 后读取已提交路由与当前控制器标题，保存最近 50 个不同页面；访问相同路由时移到最前。弹窗及尚未保存的新建表单不记录。
- 原生 `cogMenu` 注册“添加到书签”操作，覆盖支持该菜单的列表、看板及表单；收藏同一路由时去重。侧栏条目用 Odoo 生成的相对链接恢复页面，由原生客户端重新检查业务权限。
- 书签和记录各有原生 Dropdown 删除入口，仅移除对应导航条目，不删除业务记录。
- 仅存页面标题和相对路由，使用浏览器 localStorage 的 `tyj.sidebar.entries:<database>:<uid>` 键隔离数据库和用户；刷新保留，不跨浏览器／设备同步。不保存完整 action、用户上下文或业务数据。读取时过滤非后台地址，存储异常通过通知显示，不阻断应用导航。
- 新的前端资源需要模块升级后刷新资源；指向远端数据库时不能未经授权升级。

### Light / Dark Theme

- 右上角原生 `systray` 的太阳／月亮入口提供 Light 和 Dark，当前选项显示勾选状态，支持键盘操作。
- 选择写入 Odoo 原生 `color_scheme` Cookie（一年有效、当前浏览器生效），刷新当前地址后加载对应资源；重复选择当前主题不刷新。默认 Light，仅接受 `light` / `dark`。
- `ir.http.color_scheme()` 扩展保留原生页面资源选择流程。Dark bundle 在所有默认变量前加载 `dark_variables.scss`，原生列表、表单、输入框、下拉菜单和弹窗由同一套深色变量重新编译；公共外壳的 `showroom-color()` 映射和共享看板令牌同时适配，品牌主色保持不变。
- 主题切换会刷新页面；业务模块自行硬编码的颜色仍需逐页适配。前台、登录页和打印资源不加载深色变量。新增资源及 Python 扩展需要升级模块、重启服务；不得未经授权升级远端数据库。

### Exceed Color API

| 类型 | 可用变量 / 类名 |
| --- | --- |
| SCSS | `$o-exceed`、`$exceed`，默认 `#5F4B8B`；`$exceed-text-emphasis`、`$exceed-bg-subtle`、`$exceed-border-subtle` |
| 后台 CSS | `--exceed`、`--exceed-rgb`、`--exceed-text-emphasis`、`--exceed-bg-subtle`、`--exceed-border-subtle` |
| 前台 CSS | 原生 Bootstrap 前缀：`--bs-exceed`、`--bs-exceed-rgb` 及同名派生变量 |
| 文字 / 背景 / 边框 | `text-exceed`、`bg-exceed`、`border-exceed` |
| 强调 / 浅色 | `text-exceed-emphasis`、`bg-exceed-subtle`、`border-exceed-subtle` |
| 链接 / 焦点 | `link-exceed`、`link-underline-exceed`、`focus-ring-exceed` |
| 按钮 | `btn-exceed`、`btn-fill-exceed`、`btn-outline-exceed` |
| 徽标 | `badge text-bg-exceed`（自动使用白色文字），也可在普通元素上使用 `text-bg-exceed` |
| 提示 / 列表 / 表格 | `alert-exceed`、`list-group-item-exceed`、`table-exceed`（搭配对应基础类） |

```xml
<span class="badge text-bg-exceed">超越目标</span>
<div class="bg-exceed-subtle text-exceed border border-exceed-subtle">完成率超过目标</div>
<button type="button" class="btn btn-exceed">查看超越成果</button>
<div class="alert alert-exceed" role="alert">已超越目标</div>
```

SCSS 可直接使用 `color: $o-exceed;`，后台普通 CSS 可使用 `color: var(--exceed);`。默认强调文字为 `#261e38`，浅色背景为 `#dfdbe8`，浅色边框为 `#bfb7d1`；派生色沿用 Bootstrap 的 shade/tint 比例，并随 `$exceed` 覆盖值重新计算。

无数据库依赖的样式回归测试（实际编译 Odoo 后台/前台 Bootstrap 栈和报表样式，覆盖类生成、颜色、可读性、原生状态保留、变量覆盖、Bootstrap 暗色派生变量及报表文字/背景的静态 RGB 兼容）：

```sh
./.venv/bin/python -m unittest discover -s common_addons/showroom_backend_theme/tests -p test_theme_colors.py -v
```

TYJ 助手头像由本模块的 `static/src/img/tyj-assistant.svg` 提供，避免依赖 Odoo 18 `mail` 模块中已移除的文件路径。

## 4. Integration & External APIs

- `AppAccessHome.web_client` 继承原生 Web 客户端路由：非本地环境访问包含 `apps` 的子路径返回 404。
- `AppAccessDataSet.call_kw` 和 `call_button` 继承原生 Dataset 路由：应用管理模型的 RPC 在非本地环境抛出 `AccessError`。
- 路由保留原生 Web 会话/鉴权配置；额外授权由 `TYH_RUNTIME` 服务端环境变量控制。无第三方 API。

## 5. Gotchas & Constraints

- 默认关闭：缺少、为空或大小写不完全等于 `local` 的 `TYH_RUNTIME` 都禁用应用管理。
- 限制只对请求路径生效，保留部署/初始化的受控 CLI 模块安装能力；本地模式也不提升原生用户权限。
- 应用管理拦截必须同时覆盖菜单、action、HTTP 页面、Dataset RPC、按钮、zip 导入和直接 `state` 写入，避免新增旁路。
- `ir.actions.act_window._get_action_dict` 的策略检查不得直接以当前业务用户读取 action 字段；核心方法本身使用 `sudo().read()` 并执行安全字段白名单，主题扩展必须保持相同权限边界。
- 白标 SQL 仅面向 XML 定义的 `mail.template`，规避注册表加载期渲染检查；不要扩展为修改客户/管理员创建的模板。
- 不得整段替换 `web.brand_promotion` 容器或删除标准 `web.brand_promotion_message` 调用，以维持原生白标入口。
- 列表宽度只能设置最小宽度，不要使用强制 `width: 100% !important` 覆盖 Odoo 的列宽计算，否则字段较多时会丢失横向滚动或挤压列内容。
- `exceed` 是样式语义，业务代码须自行决定何时应用；不扩展 Odoo 通知服务的 `type` 枚举或视图的 `decoration-*` 支持列表。
- 保持主题色注册在主变量阶段、派生映射扩展在 Bootstrap 组件和 utility 生成前；不能仅在后台末尾添加 `$theme-colors`，否则根 CSS 变量、按钮、提示框等不会完整生成。后台遵循 Odoo 的无前缀 CSS 变量，前台遵循各自的 `$prefix`。
- 新增 assets 声明后需在目标环境升级 `showroom_backend_theme` 并刷新前端资源。主题本身不写业务数据；本地开发指向远端数据库时，模块升级仍需相应授权。
- 侧栏分组只渲染当前用户从 Odoo 菜单服务获得的可见菜单；叶子 action 沿用服务端权限判断。不要从菜单名称推导路由或复制静态菜单清单。
- 子菜单通过 Owl `useRef` 获取侧栏 DOM 节点以测量位置与高度，不能使用组件实例的 `this.el`（该属性不存在）。即使未超高、仍为单列，也必须在首次渲染测量时完成相对按钮的定位；不要依赖分列状态再次触发渲染。原生 `details` 的首次展开可能不触发 Owl 更新，需在其 `toggle` 事件中重新测量卡片高度。
- OCB 19 移除了 `company` 服务；顶栏公司名和标志从 `@web/core/user` 的 `activeCompany` 读取，并订阅 `ACTIVE_COMPANIES_CHANGED` 刷新。不可再调用 `useService("company")`，否则后台首次渲染就会失败。
