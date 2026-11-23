# 工作流 Project 适配（第五阶段）

`workflow_project` 为 `workflow_core` 增加“项目任务”节点和 `project.task` 业务模型入口。仅依赖核心与 Odoo `project`，无需审批适配器或 OCA；自有代码位于 common_addons，不修改 Project 上游源码。

## 使用

1. 安装 workflow_project。设计/发布人员需要能读取选定项目；发起人及项目负责人同时需要相应的工作流执行和原生 Project 权限。适配器不会自动授予项目管理员权限。
2. 在画布添加“项目任务”，选择“创建项目任务”，指定本公司项目和1至50名负责人。也可将模板业务模型设为“项目任务”，选择“关联当前业务任务”，启动时使用原生记录选择器选任务。
3. 发布后启动，在节点激活时创建或绑定原生 Project 任务并冻结负责人集合。已关联任务的项目、公司、负责人和任务结构不可修改，不能删除；可正常修改名称、说明、优先级及其他普通字段。
4. 负责人从“工作流管理 → 项目待办”打开监控，或在 Project 原生任务表单查看流程状态，并点击“工作流”返回流程。监控支持打开原生任务、完成及取消；取消会先提示整个流程将被取消。
5. 多名负责人中任一人可完成。可从监控办理，也可在原生任务状态控件选择 Done。完成只推进一次，后继失败则两边状态和日志同时回滚。

| 原生 Project 状态/操作 | 流程行为 |
| --- | --- |
| In Progress / Changes Requested / Approved / Waiting | 项目节点保持等待，不因看板阶段折叠或 Approved 自动完成 |
| `1_done` | 关联/激活完成，推进后继或到达并行汇合 |
| `1_canceled` | 当前流程取消，关闭其他未完成工作，保留历史 |
| 流程取消，或并行审批拒绝 | 原生 `write({'state': '1_canceled'})` 取消未完成关联任务；已完成任务保持原状态 |

Odoo 19 原生任务状态控件也是通过 record.update/write 进入状态 inverse；本模块使用这条完整原生路径，不用 SQL 或 sudo 写业务状态。取消/拒绝涉及 Project 任务时，操作者必须有这些任务的原生读取、写入权限；权限失效会让整个操作回滚，不会静默提权取消任务。

## 配置与数据

- 创建：`{"mode":"create","project_id":42,"user_ids":[7,9]}`。
- 关联本次业务记录：`{"mode":"business"}`，要求模板业务模型为 project.task，不把固定任务 ID 写进可复用模板。
- 项目须有效、属于流程公司且非模板；任务须未结束、有效、有项目和合格负责人。当前不支持模板任务、父子任务、依赖或循环任务；也阻止通过其他任务的父子/依赖关系反向改变已绑定任务。
- 新模型 `workflow.project.link` / 表 `abt_workflow_project_link`，按节点激活、Project任务分别唯一；负责人关系表 `abt_workflow_project_user_rel`。每个原生任务只绑定一个节点激活，历史绑定不删除，也不能重新打开已结束的关联任务。
- Project 任务上的“工作流”按钮可见性按用户和公司计算，只有有权访问关联实例及原生任务时可用。未关联任务的创建、状态变化、复制、负责人调整及删除继续采用原生行为；复制已关联任务得到普通未绑定的新任务。
- `workflow.project.link.action_decide(decision, comment='')` 只允许 complete/cancel，意见最多4000字。实际办理人为当前有效负责人；管理员不能替代负责人完成。本人相同结果重试不覆盖原意见，不重复推进。
- 关联模型为只读运行数据，create/write/unlink/copy 受服务端保护；读取/导出同时检查全局公司/参与人、原业务记录和原生任务权限，覆盖缓存命中。

## 原子性与文件职责

| 位置 | 职责 |
| --- | --- |
| models/node.py / integration.py | 节点注册、Project业务模型、设计元数据、监控和取消联动 |
| models/link.py | 关联模型、只读访问、原生入口及对外办理接口 |
| models/project_task.py | 原生状态反向同步、结构保护和表单跳转 |
| services/configuration.py / activation.py | 配置及人员权限校验、以原用户创建/绑定任务 |
| services/synchronization.py | instance → link → Project task 锁、完成/取消、统一事务与幂等 |
| services/scope.py / structure.py | Python事务同步令牌及反向父子/依赖引用保护 |
| security/ / views/ | 公司/参与人规则、Project表单按钮及项目待办 |
| tests/ | 创建/绑定、多负责人、权限/回滚、并发、浏览器、并行及可选审批联动 |

两端状态同步、节点/令牌推进、后继任务和日志处于同一 savepoint，不提前 commit。同步标记采用绑定数据库、游标、关联ID的 ContextVar；客户端 context 无法伪造，也不依赖可伪造的 skip 标记。原生批量状态写入先按统一顺序锁实例/关联/任务，再校验所有实际用户权限；任一项失败整批回滚。

## 安装与验证

在主仓库根目录，仅对隔离本地库执行，按实际环境指定连接和 data-dir：

```sh
YABO_RUNTIME=local YABO_ENV=test DYLD_LIBRARY_PATH=/opt/homebrew/opt/expat/lib .venv/bin/python odoo-bin \
  -d YOUR_ISOLATED_TEST_DB --db_user=YOUR_LOCAL_PG_USER --addons-path=addons,common_addons \
  -i workflow_project --without-demo=all --stop-after-init --no-http --max-cron-threads=0
.venv/bin/ruff check common_addons/workflow_core common_addons/workflow_project
.venv/bin/ruff format --check common_addons/workflow_core common_addons/workflow_project
```

安装后用 `-u workflow_core,workflow_project --test-enable --test-tags=/workflow_core,/workflow_project`，增加独立 HTTP/gevent端口，运行行为和浏览器回归。可选审批联动测试仅在安装 workflow_tier_validation 时执行。并发测试提交独立专属记录并 finally 精确清理，仅限隔离测试库。前端 `npm run build` / `npm test` 在 workflow_core/frontend 执行，服务器无需 Node/CDN。

用户原有业务数据不会自动绑定，不提供生产数据演示脚本；示例仅在测试/本地预览库显式创建。完整验证证据见 [实施方案](../docs/workflow-platform-plan.md)。第四阶段尚未完成的会签、退回、超时等能力不由本适配器补齐。

启用分级审批适配器后，Odoo「待办 → 待审批」使用同一个审批列表。点击当前审批记录打开对应的流程办理页。
