# ARCH: workflow_core

## 1. Overview

通用流程设计与执行模块，依赖 web、mail、hr。业务模型和流程引擎的详细入口见模块 README。

## 2. Model Extensions & Schema

模板及版本保存流程定义与冻结图；实例、任务、令牌及日志保存执行状态。

模板基本信息包括 name、description、icon、application_menu_id、category_id、manager_id。`icon` 使用原生 Image 字段（上限 256×256）及附件访问控制；未上传时显示模块自带 SVG。`application_menu_id` 关联现有应用根菜单，不依赖具体费用或财务模块；看板默认按模块分组。`workflow.category` 使用 `abt_workflow_category` 表，类别属于一个应用模块；同一模块下名称唯一，引用中的类别不能跨模块移动。模板切换模块会清空不匹配的类别，RPC 同样校验类别所属模块。

`manager_id` 必填，默认当前维护人，可选择本公司有效内部用户。部门与公司字段及其发起范围规则保持原样。旧模板没有模块/类别时保留空值；升级脚本为旧模板保留有效内部创建人为管理员，否则使用系统管理员。类别及基本信息不修改版本快照或已运行实例。

## 3. Business Logic & Data Flow

`WorkflowAction` / `WorkflowMonitorAction` 通过原生 action service 打开，调用 get_canvas / get_monitor 加载数据；React 桥接仅负责画布。

指定管理员自动获得基础 `group_user` 访问角色，不授予全局设计、发布或执行权限。定义模型的全局维护记录规则和 `_check_manage` 同时约束指定管理员；普通内部用户仅能维护自己的流程基本信息、获取负责人、保存画布和创建新版本。全局工作流管理员保留管理能力。调整管理员后旧管理员立即失去维护权；基础访问角色保留，但不再具备该流程写权限。新建模板仍由既有设计人员负责，发布/恢复版本仍要求发布角色；版本/节点/边直接 CRUD 的内部写保护不变。门户、停用及无所属公司权限的用户不能被指定。

## 4. Integration & External APIs

画布和办理页面使用 `web.ControlPanel`；标题经 `env.config.setDisplayName` 更新，状态使用 control-panel-status-indicator 槽，业务按钮使用 control-panel-navigation-additional 槽。已有 action breadcrumbs 原样保留；直接链接没有上层时，在子环境补充 openParent 入口，不修改 action service 的控制器栈。公共返回按钮由 custom_web_components 的全局扩展提供。

## 5. Gotchas & Constraints

- `useSetupAction.beforeLeave` 保留离开未保存画布的确认，包括公共返回按钮与面包屑导航。
- 控制栏沿用 Odoo 尺寸、布局和响应式行为；不手写替代标题栏，不修改核心库。
- React 桥接挂载、更新、销毁及保存/发布行为与控制栏布局独立。
