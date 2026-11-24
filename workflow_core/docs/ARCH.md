# ARCH: workflow_core

## 1. Overview

通用流程设计与执行模块，依赖 web、mail、hr。业务模型和流程引擎的详细入口见模块 README。

## 2. Model Extensions & Schema

模板及版本保存流程定义与冻结图；实例、任务、令牌及日志保存执行状态。当前界面调整无数据库变更。

## 3. Business Logic & Data Flow

`WorkflowAction` / `WorkflowMonitorAction` 通过原生 action service 打开，调用 get_canvas / get_monitor 加载数据；React 桥接仅负责画布。

## 4. Integration & External APIs

画布和办理页面使用 `web.ControlPanel`；标题经 `env.config.setDisplayName` 更新，状态使用 control-panel-status-indicator 槽，业务按钮使用 control-panel-navigation-additional 槽。已有 action breadcrumbs 原样保留；直接链接没有上层时，在子环境补充 openParent 入口，不修改 action service 的控制器栈。公共返回按钮由 custom_web_components 的全局扩展提供。

## 5. Gotchas & Constraints

- `useSetupAction.beforeLeave` 保留离开未保存画布的确认，包括公共返回按钮与面包屑导航。
- 控制栏沿用 Odoo 尺寸、布局和响应式行为；不手写替代标题栏，不修改核心库。
- React 桥接挂载、更新、销毁及保存/发布行为与控制栏布局独立。
