# ARCH: workflow_project

## 1. Overview

为 workflow_core 扩展项目任务节点和 project.task 业务关联；模块及接口明细见 README。

## 2. Model Extensions & Schema

扩展流程定义的业务模型白名单、流程版本节点选项和实例联动；项目关联数据由 workflow.project.link 管理。

## 3. Business Logic & Data Flow

项目任务创建、状态同步和负责人授权沿用原生 Project 权限，适配器不授予项目管理权限。

## 4. Integration & External APIs

`WorkflowVersion._node_options` 复用 `definition_id._can_manage()`，使指定流程管理员能够配置本流程的项目节点。可选项目和负责人仍使用原有项目访问规则及 eligibility 校验。

## 5. Gotchas & Constraints

指定流程管理员不等于 Project 管理员，也不自动取得其他流程、其他公司的数据或发布权限。
