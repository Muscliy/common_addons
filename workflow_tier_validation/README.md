# 工作流分级审批（阶段三）

`workflow_tier_validation` 为 `workflow_core` 增加审批节点。依赖 `base_tier_validation`，使用 `external_addons/tier-validation` 中固定提交的 OCA Git submodule；不复制或修改上游源码，不依赖 board、forward 或 server_action。模块采用 AGPL-3。

## 安装与使用

在主项目根目录，对指定的隔离本地库执行：

```sh
YABO_RUNTIME=local YABO_ENV=test DYLD_LIBRARY_PATH=/opt/homebrew/opt/expat/lib .venv/bin/python odoo-bin \
  -d YOUR_ISOLATED_TEST_DB --db_user=YOUR_LOCAL_PG_USER \
  --addons-path=addons,common_addons,external_addons/tier-validation \
  -i workflow_tier_validation --without-demo=all --stop-after-init --no-http --max-cron-threads=0
```

数据库连接、data-dir 按本地环境指定。`DYLD_LIBRARY_PATH` 仅用于本项目 macOS 环境。服务器使用核心自带浏览器构建产物，无需额外 Node 服务。

1. 为审批人员分配“流程审批人员”角色；该角色不授予设计、发布或人工任务办理权限。工作流管理员包含审批角色，但仍不能代替候选人审批。
2. 设计人员在画布添加“审批”节点，配置1至20级，每级选择人员、用户组任一人或业务字段，可调整顺序。
3. 动态字段只允许当前业务模型上可访问的 `res.users` / `res.groups` many2one、many2many 字段，不支持关系链。实际候选人需有效、具有审批角色、属于流程公司并能读取业务单据。
4. 保存并发布。节点激活时冻结每级候选人，随后修改用户组成员或业务字段不会改变在途候选人；账户停用、公司权限或业务读取权限撤销仍会阻止操作。
5. 当前审批人从“工作流管理 → 我的审批”打开流程，在右侧通过或填写意见后拒绝。每次只办理当前一级，同一人连续两级也需要分别确认。
6. 所有级次通过才推进后继节点。任一级拒绝即结束当前实例，保留意见、审批人与全部级次历史；发起人或管理员取消也保留历史。

一组中的多人采用任意一人通过。多级必须依次全部通过；这不是多人同时会签、并行分支或审批转交。审批列表及 OCA 原生 bus 待审批计数可用；当前未配置邮件、活动或超时提醒。

## 模型与数据流

- 新模型 `workflow.approval` 继承 OCA `tier.validation` 和核心运行记录基类；表 `abt_workflow_approval`，按 `node_instance_id` 唯一，实例/公司由节点激活关联。
- 节点、节点激活与实例扩展 `approval` / `rejected` 类型或状态；核心节点 `config` 存储经校验的级次。核心独立安装时仍只有原有四种节点。
- OCA `tier.definition` 和 `tier.review` 增加 `workflow_approval_id`；定义上的候选人关系表为 `abt_workflow_tier_candidate_rel`，OCA 原有模型和表不改名。
- 每次节点激活创建独立审批单及独立定义快照，再通过原生 `request_validation` 创建 reviews。即使同一流程有多个审批节点，也不会共享级次或审批状态。
- 用户组和动态字段在激活时解析为确定的用户集合；快照采用 individual 类型并由适配器返回完整冻结候选集合，不依赖之后可修改的 OCA 全局定义或用户组成员。
- 通过/拒绝调用原生 `_validate_tier` / `_rejected_tier`，刷新顺序状态及原生计数，再同步节点/实例和执行日志。最后一级通过及后继任务创建处于同一 savepoint，失败整步回滚。

## 文件职责

| 位置 | 职责 |
| --- | --- |
| models/approval.py | 审批单、只读权限及原生入口保护 |
| models/decision.py | 固定级次审批、幂等、加锁及结果同步 |
| models/definition.py / review.py / wizard.py | 工作流所属 OCA 数据和评论向导的写入/读取保护 |
| models/node.py / integration.py | 节点扩展、设计元数据、监控、审批 RPC、取消联动 |
| services/configuration.py | 配置、人员资格、业务权限与动态字段解析 |
| services/snapshot.py / scope.py | 激活快照及 Python 事务能力令牌 |
| security/ / views/ | 角色、全局记录规则及我的审批入口 |
| tests/ | 顺序/拒绝/回滚、ORM/RPC安全、浏览器与真实双连接竞争 |

## 接口与安全契约

`workflow.instance.action_review(approval_id, review_id, decision, comment='')` 为画布入口；验证审批单属于当前实例后调用 `workflow.approval.action_decide(decision, comment='', review_id=0)`。decision 仅为 `approve` / `reject`，拒绝意见必填、意见最多4000字。调用必须携带不可变的 review ID，缺少时拒绝；重试同一个已由本人处理、结果相同的 review 返回成功，不覆盖意见或误批下一级。

- 锁顺序为 instance → approval，通过核心 MVCC 行更新锁交由 Odoo 对序列化冲突重试整个事务。不同候选人竞争同一级只有一个结果。
- 每次操作重新检查公司、参与人、当前级次、候选人资格及原业务记录权限。管理员没有替他人通过的特权。
- 审批单只读；工作流所属 review/definition 的 create、write、unlink、copy、关联修改和评论向导均由服务端保护。客户端 context 中的 sudo、skip 等标记不授予能力。
- 私有写入使用 Python ContextVar，绑定数据库、当前游标和节点激活，不能由 JSON RPC context 伪造。普通非工作流 OCA 单据保留原生行为。
- 多公司/参与人采用全局规则与原规则取交集；原单据读取约束同时覆盖直接 read、缓存命中及 export_data。审批意见和候选人不能通过直接读取关联 tier 记录绕过业务权限。
- 快照不可编辑/删除，审批历史不可重置。已有审批节点或拒绝状态时阻止卸载适配器，以免丢失冻结版本及审计；没有自动删除历史的卸载路径。

## 验证

从主项目根目录，安装后执行（仅限隔离库）：

```sh
.venv/bin/ruff check common_addons/workflow_core common_addons/workflow_tier_validation
.venv/bin/ruff format --check common_addons/workflow_core common_addons/workflow_tier_validation
YABO_RUNTIME=local YABO_ENV=test DYLD_LIBRARY_PATH=/opt/homebrew/opt/expat/lib .venv/bin/python odoo-bin \
  -d YOUR_ISOLATED_TEST_DB --db_user=YOUR_LOCAL_PG_USER \
  --addons-path=addons,common_addons,external_addons/tier-validation \
  -u base_tier_validation,workflow_core,workflow_tier_validation --without-demo=all \
  --test-enable --test-tags=/base_tier_validation,/workflow_core,/workflow_tier_validation \
  --stop-after-init --no-http --http-port=8096 --gevent-port=8097 --max-cron-threads=0
```

并发测试使用独立连接提交专属测试数据，并在 finally 精确清理；预期 serialization 日志不等于测试失败。浏览器测试覆盖实际两用户依次通过及 RPC 状态写入、伪造意见向导拒绝。核心前端测试在 `workflow_core/frontend/` 执行 `npm test`。完整交付证据见 [实施方案](../docs/workflow-platform-plan.md)。
