# 通用工作流核心

面向 OCB 19 的可视化流程核心。模块名 `workflow_core`，模型名 `workflow.*`，自研表及关系表以 `abt_workflow_` 开头。仅依赖 `web`、`mail`，无需 OCA Tier Validation 或 Project。

当前闭环：创建模板 → 拖拽节点/配置/连线 → 保存 → 校验 → 发布 → 选择业务记录（可选）→ 启动 → 办理人工任务 → 顺序/条件推进 → 监控及历史。

## 安装与构建

主项目已有 common_addons 加载路径。仅在明确选定的本地测试库执行，例如在主项目根目录：

```sh
YABO_RUNTIME=local YABO_ENV=test DYLD_LIBRARY_PATH=/opt/homebrew/opt/expat/lib .venv/bin/python odoo-bin \
  -d YOUR_ISOLATED_TEST_DB --db_user=YOUR_LOCAL_PG_USER \
  --addons-path=addons,common_addons -i workflow_core \
  --without-demo=all --stop-after-init --no-http --max-cron-threads=0
```

`DYLD_LIBRARY_PATH` 是本项目 macOS 开发环境的 expat 设置；Linux 不需要。数据库用户、连接和附件目录按实际测试环境指定。不要使用 remote 启动模式安装或测试。

浏览器产物已随模块提供，服务器运行无需 Node 或 CDN。修改 React 源码时，在 `workflow_core/frontend/` 执行：

```sh
npm ci --ignore-scripts
npm run build
npm test
```

Node >=20；开发测试默认使用已安装的 Chrome，可通过 `PLAYWRIGHT_CHANNEL` 选择其他已安装渠道。React/ReactDOM 19.3.1、React Flow 13.0.2、esbuild 0.28.2 和测试工具使用精确版本与 lockfile。React Flow 13 使用 Changeset API，不能复制旧版 applyNodeChanges 用法。

## 使用

1. 在用户设置中分配工作流角色。系统设置管理员继承工作流管理员权限。
2. 打开“工作流管理 → 流程模板”，创建模板。业务模型留空可用于不关联单据的流程；当前注册的业务模型为联系人。
3. 打开画布，点击或拖入开始、人工任务、条件分支、结束节点；“插入示例”提供三节点人工任务流程。
4. 从节点右侧连接点拖到另一节点左侧连接点，点击节点设置名称/负责人。负责人留为“流程发起人”时由发起人办理。
5. 选择条件节点的出线，配置字段、比较方式、类型值及 AND/OR；其中一条设为默认出口。条件按画布保存的连线顺序选择首条满足条件的出口，未满足则走默认出口。
6. 保存并校验后发布。草稿允许未连完；发布拒绝缺少开始/结束、循环、孤立节点、悬空连线和无效条件。已发布版本只读；通过模板表单“新建版本”编辑副本。
7. 在当前有效的发布版本画布点击“启动流程”。关联业务时使用 Odoo 原生选择窗口，不能输入任意模型或执行代码。
8. 负责人从“我的待办”进入流程，在右侧填写意见并完成任务。状态、节点时间和日志由后端返回；“查看业务单据”重新检查原单据权限。
9. 模板的“允许启动的用户组”为空时允许工作流执行人员启动；配置后还需属于至少一个指定组。可归档模板停止新实例，已有实例继续按原版本执行。
10. 发起人或工作流管理员可在实例表单取消流程，未完成任务被取消，历史保留。

窄屏使用“节点库/属性”切换面板，画布仍可平移缩放。按钮和节点库支持键盘操作；选中元素可用 Delete 删除。离开未保存画布会确认，保存/发布期间禁止继续编辑以防覆盖在途修改。

## 职责与文件边界

| 位置 | 职责 |
| --- | --- |
| models/definition.py | 模板、公司/业务模型、有效版本、版本复制和启动入口 |
| models/version.py | 草稿保存、revision 冲突、图读写、校验与发布 |
| models/graph.py | 节点/连线关系及发布后的写保护 |
| models/runtime.py | 实例、节点执行、追加日志、只读监控、取消 |
| models/task.py | 负责人授权、办理意见、任务完成与推进事务 |
| services/access.py | 原用户权限、业务记录范围、事务行锁 |
| services/graph_validation.py / rules.py | 有限图结构和有类型的安全条件规则 |
| services/engine.py | 顺序/条件激活与人工待办创建 |
| static/src/action/ | OWL Client Action、原生 RPC/对话框、生命周期、主题变量 |
| frontend/src/ | React 画布、节点注册映射、属性/条件编辑、纯图序列化 |
| tests/ / frontend/tests/ / static/tests/ | Odoo 行为/权限/并发、真实画布交互、OWL 桥接测试 |

手写源文件保持300行以内；生成的 JS/CSS、lockfile 和第三方许可证属于生成产物。

## 事务和权限契约

- 保存草稿、发布、启动、办理、取消各自使用 savepoint；失败时整步回滚。任务完成和下一节点/任务创建同事务，不提前 commit。
- 锁顺序为 definition → version，以及 instance → task。Odoo 的 PostgreSQL REPEATABLE READ 下，通过不改变字段值的行 UPDATE 建立 MVCC 冲突；竞争请求由 Odoo 的 RPC 事务重试机制重新读取，避免“等到锁但仍看不到刚创建实例”的旧快照。
- 请求幂等键按模板+发起人唯一，节点激活按实例+节点唯一，人工任务按激活唯一。已完成任务的重复请求返回成功，不重复推进、不覆盖原意见。
- 运行记录仅允许已授权的私有引擎路径提权创建/更新，不能通过 RPC create/write、context 标记或伪造 readonly 字段推进。执行日志只能追加，运行历史不可删除。
- 设计与发布角色独立；审批角色由可选适配器引入。多公司规则为全局限制，参与人规则与查看人员规则在其范围内生效。管理员也不能代替任务负责人办理。
- 每次启动、监控、办理和打开业务单据均以原调用者检查原单据访问权限；任务分配还检查候选人的公司、有效性和单据可读性。
- 设计人员具有 ir.model 只读元数据权限以配置模型。执行人员访问模型技术名只在受控元数据上提权，原业务记录不提权。
- 条件仅支持已授权标量字段（文本/布尔/数字/选择）和有限操作符，不支持关系链、Python、JS、safe_eval 或 server action。

## 公共接口

均为认证 Odoo ORM RPC，参数中的记录集合应为单条；权限由服务端校验。

| 模型/方法 | 输入及结果 |
| --- | --- |
| workflow.definition.action_designer / action_new_version | 返回画布 client action；后者需要设计权限 |
| workflow.version.get_canvas / get_assignees | 返回标准图、revision、状态/权限/字段元数据；候选人员最多500人 |
| workflow.version.save_graph(graph, revision) | 原子替换草稿节点和连线，返回新 revision；冲突要求刷新 |
| workflow.version.action_validate / action_publish(revision) | 图校验；发布冻结版本并切换模板当前版本 |
| workflow.definition.action_start(res_id=0, request_key='') | 启动并返回实例监控 action；重试应复用 request_key |
| workflow.task.action_complete(comment='') | 当前负责人办理，重复请求不重复推进 |
| workflow.instance.get_monitor / action_business_record / action_cancel | 监控快照、打开单据、取消 |

所有模型表使用显式 `_table`；版本、节点和连线都是可查询关系，JSON 仅承载位置、viewport、经过校验的条件及节点配置。

## 可选节点扩展

适配器通过 `workflow.node.kind` 的 selection_add 注册类型，实现 `_validate_config(kind, config, version)`、`_waits_for_input()` 和 `_activate_input(...)`。节点配置必须在保存和发布时通过服务端校验；核心类型拒绝额外配置。版本的 `_node_types()` 与 `_node_options()` 返回当前已安装类型及其设计元数据；图校验按实际注册类型检查，不接受客户端自报类型。

核心画布提供审批节点配置/监控组件，只有安装 [workflow_tier_validation](../workflow_tier_validation/README.md) 后才显示审批节点入口；核心后端没有 OCA 导入或依赖。监控中的审批操作由适配器 RPC 处理，携带固定 review ID。未安装适配器时保留原图格式及行为。

## 当前边界

- 核心支持单条执行路径；拒绝循环和并行类型。审批已由可选适配器交付；Project 关联、并行汇合、退回/撤回、领取/转交、超时、自动动作、失败恢复、版本回退、撤销/重做及复制粘贴属于后续交付，不提供虚假的可用按钮。
- 版本发布后保持不可变，运行实例不随新版本切换。MVP 每节点最多激活一次；阶段四的循环/并行需引入独立 token、fork scope 和 activation 标识后再扩展唯一约束。
- 核心允许联系人作为基础业务示例；其他业务模型由后续适配器注册并扩展界面候选范围，不直接改业务 state。
- 当前失败操作回滚并向用户报错；还没有持久异常状态、自动补偿或恢复队列，不将回滚称为故障恢复。

## 验证

从主项目根目录，在隔离库执行：

```sh
.venv/bin/python -m ruff check common_addons/workflow_core
.venv/bin/python -m ruff format --check common_addons/workflow_core
YABO_RUNTIME=local YABO_ENV=test DYLD_LIBRARY_PATH=/opt/homebrew/opt/expat/lib .venv/bin/python odoo-bin \
  -d YOUR_ISOLATED_TEST_DB --db_user=YOUR_LOCAL_PG_USER \
  --addons-path=addons,common_addons -u workflow_core --without-demo=all \
  --test-enable --test-tags=/workflow_core --stop-after-init --no-http \
  --http-port=8096 --gevent-port=8097 --max-cron-threads=0
```

`-u` 要求模块已经安装；首次使用 `-i`。HttpCase 为浏览器测试自动启动本机 HTTP。并发测试使用真正独立连接和短暂提交的专属记录，finally 精确清理；仅在隔离库运行。日志中预期的 serialization 错误由事务重试处理，测试最终结果以 tests.result 为准。

已安装项目主题时，CLI 运行 HOOT 也应带 `YABO_RUNTIME=local YABO_ENV=test`（与本地启动器相同）；测试框架读取模块依赖需要本地应用管理入口。未设置时，主题的服务器应用管理保护会阻止该框架请求；不应为测试修改部署保护。

第三方许可证见 `static/lib/THIRD_PARTY_LICENSES.txt`。react-compiler-runtime 1.0.0 的 npm 包缺少其声明的仓库根许可证，构建使用 `frontend/licenses/react-compiler-runtime.LICENSE` 补齐，来源为 [React 官方 MIT LICENSE](https://github.com/facebook/react/blob/main/LICENSE)。
