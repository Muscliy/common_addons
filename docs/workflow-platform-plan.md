# 通用工作流平台实施方案

日期：2026-11-23。阶段一调研与依赖准备已完成；阶段二 `workflow_core` 已实现，实际范围和验证见第10节及模块 README。下文保留总体设计，阶段三至五的模型和功能仍为待实施内容，不能视为已经可用。

## 1. 已确认的模块和命名

```text
yabo_platform/
├── external_addons/tier-validation/   # OCA 上游 Git submodule，19.0
└── common_addons/                     # 自有公共模块 Git submodule
    ├── workflow_core/                 # 定义、设计器、执行、待办、监控
    ├── workflow_tier_validation/      # 可选 OCA 审批适配
    └── workflow_project/              # 可选 project.task 适配
```

模型名采用 `workflow.*`；自研持久模型显式指定 `_table = 'abt_workflow_…'`，新建的 Many2many 关系表同样使用该前缀。OCA 上游模型和数据表不改名。未来的通用采购、销售、生产适配也放 common_addons；雅博专用流程规则另放 custom_addons。

用户已经确认三个自研模块的名称、职责与目录，并授权开始实施。现有公共模块分别承担主题、中文本地化、UI 组件和图表，没有可复用的流程定义或执行引擎，故需要独立工作流模块。核心仅依赖 web/mail，不依赖 OCA、Project、Purchase 或 MRP。

## 2. 实际项目检查

| 检查项 | 实际证据与结论 |
| --- | --- |
| OCB 版本 | `odoo/release.py` 为 19.0；`.venv/bin/python odoo-bin --version` 输出 Odoo Server 19.0 |
| Python / Node | 本机 Python 3.12.14、Node 20.8.1；仓库 Ruff 目标 py310，实际 Odoo 最低版本以 release.py 为准 |
| 自有模块 | common_addons 是独立 Git 子模块；custom_addons 为业务模块；两处未发现 workflow/abt_flow 或 React Flow 实现 |
| 原生前端入口 | `custom_web_components/static/src/theme_palette/theme_palette.js` 使用 action registry；可复用原生 Client Action、ORM/notification/action 服务 |
| 三方画布生命周期参考 | `custom_web_echarts/static/src/echart/echart.js` 已有 loadBundle、mount、ResizeObserver、unmount/dispose 范式；仅参考生命周期，不用图表组件代替流程图 |
| Project | `addons/project/models/project_task.py` 存在，支持 user_ids、多公司等；是否在业务库安装未查询，不把源码存在等同于已安装 |
| Mail | `addons/mail/models/mail_activity_mixin.py:activity_schedule`、mail.activity、mail.thread 可复用，但活动不作为执行状态的唯一来源 |
| Bus | `addons/bus/models/bus.py:_sendone` 存在；先请求后刷新，确有需要再加实时通知，Bus 消息不作为流程推进依据 |
| 访问控制/锁 | `odoo/orm/models.py:check_access`、`try_lock_for_update` 存在；后者 SKIP LOCKED，拿不到锁时必须报忙/重试，不能认为处理成功 |
| 开发配置 | `config/database-modes.json` 驱动 local/remote，remote 指向部署数据；测试使用独立本地库，未连接业务库 |
| 部署配置 | `deploy/entrypoint.py` 显式枚举 addons_path；Docker 复制 external_addons，.dockerignore 未排除 tier-validation |
| 设计规范 | 已读 DESIGN.md，部分文案仍写 Odoo 18；以实际 OCB 19 接口及现有主题源码为准，不改全局颜色 |

查阅项目及上级 AGENTS、README、requirements.txt、pyproject.toml、setup.cfg、ruff.toml、全局 common/python 规范。用户需求明确不要求维护 ARCH.md；本次以本方案记录稳定技术决策，未为新模块生成 ARCH.md。后续修改现有模块仍参考其必要架构上下文。

## 3. 能力归属

| 来源 | 可复用能力 | 自研边界 |
| --- | --- | --- |
| Odoo | ORM、事务、ACL、记录规则、ir.model/fields、公司、mail.thread/activity、cron、assets、Client Action | 不把 ORM/活动当作流程编排引擎；动态业务访问每次校验实际记录权限 |
| OCA Tier Validation | 指定人/组/字段候选人、多级/顺序审批、通过/拒绝、意见、提醒 | 不负责图遍历、并行汇合、回退、版本、异常恢复；还需加固 workflow 所属审批记录的写权限 |
| React Flow | 拖拽、连线、自定义节点、缩放、小地图、只读执行图 | 不负责审批权限、真实执行状态、幂等或持久化；撤销/重做、属性表单、安全规则 UI 需自行实现 |
| workflow_core | 图校验、结构化条件、版本、节点激活、任务、运行日志、权限和推进 | 不导入业务模块或执行配置中的 Python/JS；业务动作使用服务端注册表 |
| 自研适配器 | 审批、Project、后续业务模块映射 | 用业务方法操作原记录，不能写 state 冒充业务动作 |

## 4. OCA 基线与接入设计

上游 [OCA/tier-validation](https://github.com/OCA/tier-validation/tree/19.0)，固定提交 [b6e4e43](https://github.com/OCA/tier-validation/commit/b6e4e43e43f9d47d77c5eb4f79802286eb642087)。完整源码核验保存在资料仓的 `调研/调研笔记/14_OCA审批框架技术核验.md`，包含固定提交的 manifest、模型和测试链接。

| 模块 | 版本/上游状态 | 选择 |
| --- | --- | --- |
| base_tier_validation | 19.0.1.8.0，Mature，依赖 mail | 阶段三使用 |
| base_tier_validation_board | 19.0.1.0.1，Beta，额外依赖 spreadsheet_dashboard | 非核心依赖，统一待办自行提供 |
| base_tier_validation_forward | 19.0.1.2.2，Alpha | 阶段四单独验证后使用 |
| base_tier_validation_server_action | 19.0.1.1.0，Beta | 不依赖：sudo().run() 与本需求的动作白名单冲突 |

四者 manifest 均 AGPL-3。核心可选 LGPL-3，OCA 适配器采用 AGPL-3，并保留上游版权与许可证；组合分发按相应许可证履行义务。MIT 前端不会改变后端的许可义务。

每次审批节点激活生成独立 `workflow.approval`，继承 `tier.validation` 并关联 node.instance，避免把整个 instance 混入 tier.validation 导致多个审批节点共享 reviews。发布审批配置必须冻结，激活时产生隔离的 tier.definition 快照，不能让后续编辑全局审批定义改变在途审批。

单条 review 的多候选人是任意一人通过；多条 review 全部通过才整体通过。会签/或签应显式定义参与人和满足策略。restart_validation 会删除旧 reviews，不能代替工作流的不可覆盖历史。

基础 tier.review 的内部用户 ACL 允许 CRUD，write 中未见 reviewer 级状态保护。这是源码层发现，未做攻击复现；阶段三必须保护 workflow 所属 review 的 create/write/unlink、definition、model/res_id、评论向导，以及受关联业务权限限制的读访问，覆盖直接 RPC 绕过。不得使用可伪造的 context 标记作为唯一授权条件，不通过新增限制规则与上游宽松规则做 OR 来声称收紧权限。

## 5. React Flow 与 OWL 集成方案

截至核验，npm 官方元数据为 `@xyflow/react@13.0.2`（MIT，React/ReactDOM >=18，Node >=20），`react/react-dom@19.3.1`（MIT）。上游主分支与 npm 当前版本已核对；实施时锁定经过测试的精确版本和 lockfile，不依赖 latest。

新增 React、ReactDOM、React Flow 的必要性：满足已指定的节点编辑器；替代方案是重写 OWL 节点画布，维护成本明显更高且偏离需求。影响：新增隔离的浏览器包、构建链和供应链维护，需实测压缩体积和加载时长。构建工具仅开发依赖；第一版不引入 ELK.js、独立前端网站、外部服务或 CDN。

方案：Odoo Client Action 管页头、原生服务、权限与导航；OWL 提供固定尺寸的画布 DOM 容器。模块内前端源码打包为隔离 IIFE，使用 loadBundle 按需加载，不把裸 npm import/JSX 直接交给 Odoo 的资产转换器。React 通过 `createRoot()` 管理该容器内部 DOM；OWL 不再 patch 同一子树。卸载时 root.unmount、清理观察器/事件和未完成请求的回调，异步加载完成时检查当前挂载是否仍有效。

桥接边界为 `mount(element, props) → {update(props), destroy()}`；React 调用保存/校验/发布等回调，由 OWL 的 orm 服务执行 RPC，传输纯数据，不暴露 env 或任意 Python 操作。后端返回 canonical graph、revision 和权限；保存使用 revision 冲突检查，禁止静默覆盖他人修改。设计器和监控分别使用 edit/read-only mode，后端仍拦截已发布版本写入。

默认三栏：节点库、画布、属性面板；顶部原生按钮。沿用字体和 `$o-brand-primary`、`$o-main-text-color`、`$border-color` 等变量，通过模块根 CSS 变量传给 React Flow。只读、加载、失败、空态和未保存状态独立呈现；窄屏面板折叠而非挤压画布，需390px真实截图验证。节点库只呈现后端已实现且当前可用的类型，不能给未实现的并行/审批节点假入口。

参考：[React createRoot/unmount](https://react.dev/reference/react-dom/client/createRoot)、[React Flow 包声明](https://github.com/xyflow/xyflow/blob/main/packages/react/package.json)、[主题](https://reactflow.dev/learn/customization/theming)、[测试](https://reactflow.dev/learn/advanced-use/testing)。撤销、复制等 Pro 示例不直接假设可无条件复制，按开源 API 自行实现。

## 6. 数据模型（待实施）

| 模型 | 显式表名 | 关键关系/字段 |
| --- | --- | --- |
| workflow.definition | abt_workflow_definition | name、code、company_id、model_id、允许启动组、当前 published_version_id |
| workflow.version | abt_workflow_version | definition_id、number、state、revision、published_by/date、布局 viewport；定义+版本唯一 |
| workflow.node | abt_workflow_node | version_id、key、type、name、position、类型配置；版本+key唯一 |
| workflow.edge | abt_workflow_edge | version_id、key、source/target节点、顺序、规则、默认分支；节点必须同一版本 |
| workflow.instance | abt_workflow_instance | 冻结 version_id、company_id、业务 model/res_id、发起人、state、request_key；请求键唯一 |
| workflow.node.instance | abt_workflow_node_instance | instance_id、node_id、activation序号、state、开始/结束、失败摘要；每次再激活新建 |
| workflow.task | abt_workflow_task | node_instance_id、候选/负责人、领取/完成状态、期限、意见、完成者；激活+任务键唯一 |
| workflow.execution.log | abt_workflow_execution_log | instance/node_instance、actor、事件、前后状态、时间、意见；普通RPC不能改删 |
| workflow.token | abt_workflow_token | 阶段四：分支作用域、fork activation、来源edge、迭代、到达状态，不能仅按node计数汇合 |
| workflow.action.execution | abt_workflow_action_execution | 阶段四：action key、唯一执行键、状态、重试、结果；外部副作用需幂等契约/outbox |
| workflow.approval | abt_workflow_approval | 仅审批适配器：node_instance_id、tier.validation 聚合、冻结审批配置 |

JSON 仅存布局及经 schema 校验的节点配置/条件；实例、任务、节点执行、关联关系、权限和审计均可查询。核心所有跨模型关系检查公司和版本，ondelete restrict 保留历史。Project 适配器在 task 增加可选 project_task_id，不把 project.task 当通用待办。

## 7. 执行语义与安全契约

发布：锁定 definition/version，校验一个开始、可达结束、孤立节点、类型/连线基数、规则字段与权限、所有路径可结束。MVP 拒绝所有环、并行和未实现类型。发布后 version/node/edge 的 create/write/unlink 都受保护；回退通过切换有效版本，不重写历史版本。运行实例始终指向启动版本。

启动：检查执行角色、流程允许组、当前有效发布版本、流程公司、业务记录 read 及适配器要求的 write 权限，显式校验模型白名单，拒绝任意 res_model RPC。业务引用不允许仅以超级用户存在性检查替代原用户权限。每个公开方法校验参数类型、记录数量和状态，不信任按钮显隐。

推进：事务内按实例→节点→任务顺序加锁，再读取当前状态。任务完成和后继激活同事务，唯一键防重复任务；重复完成返回已有结果或明确已处理，不重复日志/推进。公开 create/write 不允许伪造运行状态、负责人、版本或日志；引擎的特权写入限定在已完成原用户权限校验的私有方法内。

条件采用有限 JSON schema（字段、运算符、类型值、AND/OR），不执行 eval/safe_eval 或任意服务端代码。先限制到标量字段，不支持任意关系链；读取字段遵循字段组权限。条件分支确定顺序并且恰好一个默认出口，不能同时选多个出口；缺字段/类型错误报错，不能默认为通过。

MVP 人工任务采用明确定义的负责人或当前发起人，候选组/领取在后续独立验收。业务记录无权访问后不能继续办任务或导出监控中的敏感字段。全局公司隔离规则与角色规则分别设置，不误用多个 group rule 的并集。角色为管理员/设计/发布/执行/审批/查看；菜单权限不能代替 ACL 和方法权限。

异常：受控失败在 savepoint 内回滚本步业务动作，再在外层保存失败节点及简洁异常日志；不得吞掉异常后标记成功。恢复按 activation/action key 幂等重试。数据库序列化冲突让 Odoo 重试整个事务，不能局部继续使用已失效缓存。取消保留节点与日志，不删除已办记录。

阶段四并行必须按 fork activation 生成令牌及 join scope，支持循环时增加迭代标识；超时 cron 按幂等键记录提醒，取消/撤回和补偿策略单独定义。外部动作不承诺分布式 exactly-once，采用事务 outbox 和接收方幂等键。

## 8. 开发顺序和验收门槛

1. **阶段一（已完成）**：核实环境/OCA/React 方案，Git 子模块、加载路径与测试、架构和风险结论；完成本地 commit。
2. **阶段二**：只实现 workflow_core 完整闭环：创建→画布拖拽/属性/连线→保存/刷新→校验/发布→启动→人工任务/顺序/条件→监控/日志；版本不可变、多公司/角色和重复提交必须同阶段完成。先以独立本地库安装核心，证明不需要 OCA/Project。
3. **阶段三**：实现 workflow_tier_validation、双级审批/拒绝/评论/同步，直接 RPC 和向导加固、动态候选人、并发和重复回调；上游全套测试 + 适配器回归。
4. **阶段四**：逐项提供并行/汇合、会签/或签、受控退回/撤回、领取/转交、超时、白名单动作及故障恢复；每项先定义执行语义再显示节点入口。
5. **阶段五**：workflow_project 关联/创建 Project 任务及状态映射；按原生方法进行操作，验证多负责人、任务取消和双向同步幂等。采购、模具示例用显式 demo/test 数据，不修改业务库。

每阶段完成代码、适用测试、差异检查和本地 commit；未获授权不推送/合并/部署，不操作生产数据。

测试分层：Odoo TransactionCase 覆盖图校验、ORM/RPC 伪造、权限/公司、条件、冻结与幂等；两个独立数据库连接覆盖并发完成和唯一启动；React 的真实浏览器组件测试覆盖拖拽/连线/属性/布局恢复/只读模式/卸载；HOOT 覆盖 OWL 桥接和错误态；HttpCase/tour 覆盖端到端闭环。安装后再 -u 验证已有流程实例保留；前端构建、主题覆盖、桌面/390px、键盘焦点均需真实页面验证。不能以静态检查代替行为测试。

## 9. 阶段一实际验证

- 分支：主仓库与 common_addons 均为 `feat/configurable-workflow`；原有未跟踪 CLAUDE.md 未改动、不纳入提交。
- OCA 以 Git submodule 放 external_addons，固定上述提交；源码未修改。common_addons 尚未创建工作流模块。
- `.venv/bin/python -m unittest deploy.test_config scripts.tests.test_start_development`：27 项通过，包括新增路径在 local/remote 和部署入口中的可见性。测试使用虚拟配置，不建立远程数据库连接。
- Ruff 检查两个测试文件通过；deploy/entrypoint.py 存在基线已有的 PLC0415（迁移模式延迟导入），用 HEAD 原文件与当前文件分别经 Ruff JSON 比较，确认告警集合相同、无新增问题；未更改无关迁移导入逻辑。
- 独立本地库 `codex_workflow_20261123_phase1` 执行 OCA 安装/测试：83 项 Odoo 测试，0 failed/0 errors；其中原生 HttpCase 审批组件浏览器测试通过 5 项/14 断言。Odoo tests.stats 的 93 为内部统计口径，报告采用 tests.result 的 83，浏览器5项包含在 HttpCase 中，不相加成88。
- OCA 测试命令：`DYLD_LIBRARY_PATH=/opt/homebrew/opt/expat/lib .venv/bin/python odoo-bin -d codex_workflow_20261123_phase1 --db_user=leehu --addons-path=addons,common_addons,external_addons/tier-validation -i base_tier_validation --without-demo=all --test-enable --test-tags=/base_tier_validation --stop-after-init --no-http --max-cron-threads=0 --data-dir=.local/workflow-phase1-data --logfile=.local/workflow-phase1-oca.log`。测试框架会为 HttpCase 自动启用 HTTP；该日志包含 HOOT 成功信号。
- 后续重复 -i 检查已安装模块返回0项测试，不作为额外通过证据。唯一完整测试证据为上述首次安装日志。
- 上游模块说明在 docutils 渲染时有 RST 缩进警告；安装、资产预编译、测试退出码均成功，未修改上游说明来隐藏告警。
- 本阶段未运行 Docker 构建，未安装 board/forward/server_action，未验证自研工作流功能、OCA 直接RPC加固或 React/OWL 实际挂载；这些均为后续阶段门槛。

## 10. 阶段二实现与验证

实现位于 [workflow_core](../workflow_core/README.md)。实际持久模型为 definition、version、node、edge、instance、node.instance、task、execution.log；审批、token 和自动动作执行模型尚未创建。模块仅依赖 web/mail，全部新表及两张显式关系表均采用 `abt_workflow_` 前缀。

已实现四类节点、三栏 React Flow 画布及 OWL 生命周期桥接、布局/viewport 保存、revision 冲突保护、类型化 AND/OR 条件编辑、图校验、发布冻结与新版本、启动/顺序/条件流转、人工待办及已办、只读执行图/节点时间/意见历史、关联业务入口、归档/取消、角色分离、公司/参与人/启动组/负责人权限。其他业务模型适配、审批、并行、故障恢复等后续功能在模块 README 明确列出，不显示未实现的节点入口。

源文件按模型、权限/校验/引擎、OWL、React 节点/画布/属性/条件编辑以及测试拆分，最大手写源文件251行。所有状态变更在同一事务完成，不在引擎中提前 commit；通过独立连接测试实际发现并修复了 REPEATABLE READ 下只锁不写仍可读取旧快照的问题。现在通过不改变审计字段值的 UPDATE 产生序列化冲突，再由 Odoo 重试整个 RPC 事务。

实际验证（均在独立本地测试库，无业务库或远端操作）：

- `.venv/bin/python -m ruff check common_addons/workflow_core` 与 `ruff format --check` 通过。项目现有 COM812 与 formatter 的兼容提示仍存在，未关闭规则；最终两项检查均通过。
- 最终 Odoo 命令沿用第9节测试模式，数据库为 `codex_workflow_20261123_phase2`、模块为 `-u workflow_core --test-tags=/workflow_core`，增加 `YABO_RUNTIME=local YABO_ENV=test`、HTTP 8096/gevent 8097。最终日志 `.local/workflow-phase2-delivery-tests.log`：25项测试、0失败/0错误。
- 其中一个 HttpCase 完成实际设计→保存→校验→发布→启动→办理→监控；另一个运行3项 HOOT、11断言，覆盖桥接单次挂载/更新/销毁、失败重试、异步加载时销毁后不继续 RPC。HOOT 项包含在 HttpCase 中，不与25重复累计。
- `npm test -- --reporter=line`：3项 Playwright 测试通过，覆盖真实拖拽/属性/连线/序列化重挂载、只读保护与销毁、键盘新增与删除。
- 双连接并发启动及办理通过：相同请求键只有一个实例、一个任务、一次完成事件。故意制造的 PostgreSQL serialization 错误属于重试测试预期；不能据日志字面 ERROR 误判为最终测试错误，也不能把失败调用视为成功推进。
- 同一办理中后继负责人失效导致失败，验证已完成标记、意见、日志和新节点全部回滚，恢复负责人后可重新办理。
- 最终代码在全新 `codex_workflow_20261123_clean` 空库用 `-i workflow_core` 安装成功；该库未安装 OCA/Project。日志 `.local/workflow-phase2-clean-install.log`。
- 已保存发布版本、草稿布局、运行实例、待办及历史后执行模块升级，逐项检查仍保留原版本/任务ID、状态、节点坐标和4条历史。另在测试库安装项目原主题，再次完成全部25项回归，主题源码未修改。
- `npm run build` 可复现，输出 SHA-256 与构建前一致；JS 486,777字节、gzip 158,794字节，CSS 与完整第三方许可证独立提供。npm 安装审计报告0漏洞；不代表未来版本或所有漏洞均已排除。
- 桌面/390px及实际主题覆盖检查通过：原生菜单打开已保存的条件流程、保存返回新 revision、只读监控不可保存，页面无未捕获 JS 异常。390px 下 document.scrollWidth=390，无横向溢出；选中描边随 `--wf-brand` 从实际主题蓝切到测试色后恢复。实际检查了设计器桌面/窄屏、监控截图，证据为 `.local/workflow-phase2-visuals/{designer-desktop.png,designer-mobile.png,monitor-desktop.png,verification.json}`。

主仓库只更新公共模块提交指针和 Docker context 排除规则，避免把 node_modules、Playwright 输出带入镜像。未构建 Docker 镜像、未推送、未部署；不能据本地验证宣称生产已安装。
