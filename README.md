# Common Addons

雅博平台的公共 Odoo 插件仓库，当前面向 Odoo / OCB 19。

每个插件放在本仓库的独立子目录，包含标准 Odoo `__manifest__.py` 文件。
主项目通过 Git 子模块固定本仓库的提交，并将 `common_addons/` 加入本地及部署环境的 `addons_path`。

拉取主项目后，在主项目根目录执行：

```sh
git submodule update --init --recursive
```

初始化或更新子模块只同步源码，不会自动安装业务插件。

通用工作流平台的已确认模块归属、模型设计、实施顺序和验证记录见
[工作流平台实施方案](docs/workflow-platform-plan.md)。阶段二核心模块的安装、使用及边界见
[workflow_core](workflow_core/README.md)。

## 当前模块

| 模块 | 职责 |
| --- | --- |
| `showroom_backend_theme` | 后台主题、品牌和应用管理入口限制 |
| `custom_branding` | 中国地址解析、默认国家及中文本地化 |
| `custom_web_components` | 公共 UI 组件及列表布局偏好 |
| `custom_web_echarts` | 按需加载的 ECharts 图表组件 |
| `workflow_core` | 可视化工作流模板、版本发布、顺序/条件执行、人工待办及监控 |

主题、本地化、公共 UI 和图表四个既有模块从主项目 `custom_addons/` 迁入，保留原有技术名称、模型、XML ID、资源 URL 和表名。主项目仍按原模块名称声明依赖；不要同时保留两份同名模块源码。`workflow_core` 是在本仓库新建的通用模块。
