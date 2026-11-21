# 公共 Web 组件（OCB 19）

`custom_web_components` 是长期维护的 UI 基础模块。第一阶段提供标准 List View 的用户布局，以及仅本地开放的 Component Playground。无需新增生产依赖，不修改 Odoo/OCA Core。

## 安装与启动

模块仅依赖 `web`，`auto_install=True`：新库初始化安装 Web 时自动安装；`scripts/deploy.sh init` 的显式初始化列表也包含它。模块不是 application，不增加生产应用入口。现有数据库不会因普通重启就自动安装新模块，需要执行一次安装。

在已确认的本地开发数据库执行：

```sh
sh scripts/start-local.sh local -i custom_web_components --stop-after-init --no-http
sh scripts/start-local.sh local
```

后续更新用 `-u custom_web_components`。修改 Python/环境变量后重启进程，修改资产后刷新页面。服务器安装/升级沿用部署命令行流程；此变更不会自动操作现有远端库。

## 本地 Playground

进入：**开发工具 → Component Playground → List View**，普通内部用户可用，不要求打开 Odoo debug 模式。首次打开生成当前用户独享的 40 条 DEMO 订单，支持 15 条/页、编辑、排序、分组、many2one、selection、monetary 和可选字段。

主题色目录位于 **开发工具 → 主题**。页面按主题语义、品牌与动作、语义文字、中性色阶、基础色谱、界面基础和提示组件分组，展示当前浏览器实际加载的颜色值；点击任意色块可复制 HEX/RGBA。色板只读，不修改主题或业务数据。

组件目录位于 **开发工具 → 组件**。页面像组件参考手册一样按基础、布局、导航、数据录入、数据展示、反馈分为 6 类，逐项展示 39 种组件的中文名、英文名、用途、实时示例和可复制代码；顶部支持中英文及用途关键词搜索。“指标进度”用中性底轨、实际值填充和目标值竖线表达进度，实际值可越过目标线，并支持系统成功/警告/危险三种语义色；标签页、分页、下拉菜单、开关、普通进度、通知与确认弹窗也可直接交互。目录复用当前 Odoo/Bootstrap 资产，不新增第三方依赖，也不读写业务数据。

仅以下三个进程变量同时满足条件时开放：

| 标记 | 允许值 | 来源 |
| --- | --- | --- |
| `YABO_RUNTIME` | `local` | 本地启动器固定设置；部署入口固定为 `server` |
| `YABO_DATABASE_MODE` | `local` | 本地启动器写入解析后的实际模式，命令行优先于环境变量 |
| `YABO_ENV` | `local` 或 `test` | 沿用根 `.env` / 终端变量；本地启动默认 `test` |

缺失、未知、staging、production 或 remote 模式全部关闭。项目当前环境枚举是 local/test/production，没有独立 development/staging 值，未引入第二套环境体系。手动启动测试进程时需要显式设置以上三个变量；推荐使用统一启动器。判断不依赖 hostname、IP 或浏览器 context/system parameter。

生产保护：

- 服务端过滤开发工具整棵菜单，不把开发进程的判断存到数据库。
- Demo action 和打开/初始化方法检查环境和内部用户组。
- Demo 模型的 `check_access`、`get_views`、`get_view` 在服务端拒绝访问；直接 RPC、导出、分组、读写和删除也受保护，包括 sudo 读取数据。
- 没有专用 HTTP Demo 路由；沿用标准 dataset/action RPC 的登录鉴权，再执行模型保护。
- manifest 不含 `demo` 数据；安装、升级和服务器运行不会自动产生 DEMO 订单。开发代码/视图元数据随模块交付，但业务数据与页面在非本地环境不可使用。
- 本地进程连接 remote 模式时同样关闭，避免向远端业务库添加演示数据。

## 使用列表布局

1. 点击表格最右侧的 **列设置** 图标，所有布局操作集中在这里。
2. 菜单列出当前视图的全部可用字段列，包括默认隐藏列；不列出 `column_invisible` 或权限过滤的列、按钮组。
3. 拖动行左侧 `⠿` 调整顺序，也可聚焦手柄后按 Alt + 上/下方向键。拖到行的上半部/下半部时，插入线分别标出行前/行后的位置，松手后表格同步更新；隐藏列同样可以排序。
4. 勾选 **显示** 控制普通数据列，不要求字段声明 optional。至少保留 2 个不同字段；只有 1 个可用字段的列表保留该字段。只剩最低数量时，已选项禁用，隐藏项仍可重新显示。系统隐藏列、权限裁剪与结构列不开放此控制。
5. 点击 **图钉** 固定在左侧，再点取消。固定列集中在菜单上方，以细分隔线区分，各组内可排序；跨组请使用图钉。隐藏列不参与固定，再显示时恢复其固定状态。
6. 列宽仍在表格中拖动原生列边缘调整。
7. 点击菜单底部 **保存布局**，一起保存 sequence/width/visible/frozen。保存失败保留修改，可重试；未保存的变化仅在当前页面。
8. 刷新、重新登录或在另一台电脑登录后按当前用户、实际 view ID 恢复；表单明细还按关系字段路径隔离。
9. 点击 **恢复默认**，删除当前作用域配置，恢复 XML 顺序、宽度、初始显隐（仍满足最低字段数量），并取消所有固定。

编辑中的记录需要先保存或取消，之后才能调整顺序/显隐/固定或保存/重置布局；列宽仍可调整。保存布局不保存业务记录。
原生列表及继承原生 Renderer 的专用列表统一启用本组件，字段渲染仍走原生机制，普通字段和 optional 字段的显隐由用户/view 数据库偏好控制，不再读取同一浏览器可能由另一用户留下的 localStorage。旧的 sequence/width 配置保持有效；首次使用且没有 visible 配置时采用 XML 初始显隐；用户保存后按个人选择恢复。旧配置或视图/权限变化导致可见列不足时，从当前允许的字段中补足最低数量。无真实 view ID 或偏好加载失败时保留原生 optional 菜单。

固定列使用实测宽度计算 sticky 偏移，表头、数据行和汇总行一致；选框及行拖动 handle 随固定列一起固定。固定区域太宽时暂时允许全部列滚动，菜单显示提示，窗口变宽后自动恢复。打印不使用固定样式。

若某个列表需要固定最右侧的数据列，可在视图根节点添加 `class="cwc_sticky_end"`。它适用于字段列和按钮列，会给 Odoo 自带的列设置/打开表单等末尾辅助列留出位置；固定区域在窄屏容不下时会暂时随表格滚动。此开关是视图默认行为，不写入个人列布局偏好；若末尾字段已被用户固定在左侧，个人设置优先。

配置优先级：用户 width → XML width → Odoo 字段/widget 默认宽度约束与浏览器内容测量。明确指定的宽度以 CSS 像素记录；表格超宽时横向滚动，不强行压缩已保存列宽。没有明确宽度时沿用 Odoo 导出的 `FIELD_WIDTHS` / `listViewWidth` 定义。

XML 示例（本模块支持正整数或 px，不支持百分比默认宽度）：

```xml
<list editable="bottom" class="cwc_sticky_end">
    <field name="name" width="160px"/>
    <field name="partner_id" width="220px"/>
    <field name="amount" width="150px"/>
    <field name="note" width="360px" optional="show"/>
</list>
```

## 配置模型及权限

`web.component.preference` → PostgreSQL `abt_web_component_preference`。

| 字段 | 作用 |
| --- | --- |
| `user_id` | 配置所有者，普通用户只能操作自己 |
| `component_type` | 如 list、dialog、form；不把模型限定为列表 |
| `view_id` | 可选视图 FK；list 类型指定真实 list 视图；list_nested 指定父视图 |
| `model` | 列表模型；list 与视图模型一致，list_nested 与关系字段路径的目标模型一致 |
| `key` | 同一组件内部的实例/用途，默认 default；明细使用 x2many:字段路径 |
| `config` | JSON 配置 |
| `scope` | 自动生成的完整作用域，与 user_id 组成唯一约束，包含无 view 的通用组件 |

```json
{"name": {"sequence": 0, "width": 160, "visible": true, "frozen": false}}
```

list 与 list_nested 使用相同的 sequence/width/visible/frozen 校验；visible 影响普通数据列及 optional 列，至少保留 2 个可用字段（可用字段不足 2 个时全部保留），frozen 仅影响可唯一识别、可移动的字段列。未知/已删除字段不参与渲染。配置最大 64 KiB，width 10–4000，sequence 0–10000。服务端 owner 规则和 CRUD 检查阻止指定他人 user_id 或转移所有权；门户/公共用户无 ACL。

JSON 空对象在 Odoo 18 Json 字段中归一为空值，读取 API 统一返回 `{}`。同一页面的保存/重置请求按 scope 串行，数据库唯一约束防止重复记录；多浏览器编辑采用最后成功保存的完整配置，无实时跨标签同步。极少数同时首次创建的唯一约束冲突会提示保存失败，可重试，不会串用其他用户配置。

验证用户隔离：用户 A 调整并保存，退出后用内部用户 B 打开同一视图，B 应看到 XML 默认值；B 保存另一套布局后重新登录 A，A 保留原布局。两个用户各自打开 Playground 后仅看到自己的 40 条数据。更换 view ID 则有独立配置，即使 model 相同。

## 前端扩展与目录

- `models/`：通用持久化模型，后续组件复用。
- `security/`：ACL 与所有者隔离。
- `static/src/services/`：注册 `component_preference`，统一 ORM load/save/reset 与请求串行化。
- `static/src/utils/`：纯布局运算，不依赖 DOM。
- `static/src/indicator_progress/`：正式可复用的指标进度 Owl 组件。
- `static/src/list_view/`：Controller、Renderer、宽度 hook、OWL 模板和样式。
- `static/src/component_catalog/`：本地开发组件参考 client action、39 项目录元数据、实时交互示例与响应式布局。
- `static/src/theme_palette/`：本地开发主题色板 client action、颜色令牌目录与运行时 computed style 读取。
- `dev/playground/`：开发专用模型、环境保护、视图、菜单及按需数据生成；与正式组件分目录。
- `tests/`、`static/tests/`：Odoo TransactionCase/HttpCase 与 HOOT。

通过 Odoo `patch` 扩展原生 `ListRenderer` 的共享行为，并以 extension 模式扩展 `web.ListRenderer` 模板；不修改 Odoo 核心、不替换标准列表注册入口，也不覆盖业务 Controller、SearchModel 或 Renderer 子类。员工 `hr_employee_list`、指标管理 `indicator_management_list`、指标记录及原生 one2many/many2many 明细均继承布局能力。`custom_web_list` 注册名及 `ComponentListController` / `ComponentListRenderer` 导出保留兼容已有引用，无需逐页接入。

Renderer 根据实际 `env.config.viewId/viewType` 构造作用域。顶层列表继续使用 `list/model/viewId/default`，原有保存配置无需迁移。明细使用 `list_nested/明细模型/父视图ID/x2many:关系字段路径`；逐层明细组合路径，相同子模型在不同明细字段中不会串用配置。服务端验证关系字段链及最终模型。未保存记录的临时 ID 不参与作用域。

没有实际视图 ID 的临时列表、手写 HTML 表格、透视表和电子表格不具备该列表持久化入口；自定义组件如完全替换了原生菜单模板或未调用原生 setup，仍需保留相应原生扩展点。宽度和固定样式只作用于列表自身的表格，列顺序仍由 OWL 渲染，不移动 th/td。

新增 Form/Dialog/Widget/Field/OWL Component：在 `static/src/` 下建立对应功能目录，通过标准 registry 注册，按需增加 `components/`；调用 `component_preference` 并选用独立 component_type/key。将资产显式加入 manifest。Playground 示例集中加到 `dev/playground/`，所有新 Demo 模型/动作必须复用相同服务端保护；新表使用 `abt_` 前缀。不要把 demo 数据放进正式 manifest 的 data/demo 自动加载。

## 验证与升级

本模块数据库/浏览器回归（使用独立测试数据库和端口）：

```sh
./.venv/bin/python odoo-bin -d <独立测试库> --db_host=/tmp --db_user=<本地PG用户> \
  --addons-path=addons,custom_addons,common_addons --data-dir=.local/cwc-test-data \
  -i web --without-demo=all --test-enable --test-tags /custom_web_components \
  --stop-after-init --http-port=8097 --max-cron-threads=0
```

已有测试库使用 `-u custom_web_components`。HttpCase 自行临时设置本地标记，测试事务回滚；Chrome 测试覆盖跨浏览器会话保存/恢复/重置，HOOT 覆盖布局与原生列表能力。手动运行 HOOT：`/web/tests?tag=cwc`。

OCB 19 后续升级重点复核：

1. `ListController.setup`、`env.config.viewId` 和 `listView` registry 描述：确保拿到解析后的实际视图 ID。
2. `ListRenderer.getActiveColumns`、`allColumns`、column.id/name、optional/property 和分组渲染约定。
3. `useMagicColumnWidths` 的 `useMagicColumnWidths=false` 开关、`onStartResize`、window 停止事件、RTL 与 sort suppression；本模块关闭原生瞬时宽度布局 effect，复用其拖动交互，使用自己的持久化宽度 hook。
4. `FIELD_WIDTHS` / widget `listViewWidth` 与表头、selector、action 列结构。
5. `web.ListRenderer` 的 Dropdown/optionalFieldGroups 模板 XPath、computeOptionalActiveFields/displayOptionalFields/toggleOptionalField、`.o_resize` 及原生交互 selector。
6. sticky 的表头/分组/汇总 colspan、选择框和 handle 位置，RTL、ResizeObserver 及主题背景变量。
7. 服务端 `check_access` / `get_view(s)`、动作 `_get_action_dict` 和菜单 `_visible_menu_ids` 入口。

统一扩展依赖原生 setup、列渲染与菜单模板，升级时必须回归以上覆盖点和专用列表业务行为。
