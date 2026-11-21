# 验证记录 — 2026-09-21

使用本机 `.venv`（Python 3.12）、PostgreSQL 18 和 Chrome headless。自动化测试在独立测试库 `cwc_test_20260921` / `cwc_verify_20260921` 中运行。本地模块安装及后续撤回另外记录在下方；没有连接远端数据库。

## Odoo 安装和回归

从空库仅 `-i web --without-demo=all` 初始化，确认 `custom_web_components` 自动安装。
随后在独立验证库加入项目默认的 custom_branding/custom_hr/showroom_backend_theme，验证真实主题组合。

最终回归命令：

```sh
./.venv/bin/python odoo-bin -d cwc_verify_20260921 \
  --db_host=/tmp --db_user=leehu --addons-path=addons,custom_addons,common_addons \
  --data-dir=.local/cwc-validation/verify-data -u custom_web_components \
  --test-enable --test-tags /custom_web_components --stop-after-init \
  --http-port=8097 --max-cron-threads=0 \
  --logfile=.local/cwc-validation/integration-test2.log
```

结果：`0 failed, 0 error(s) of 12 tests`。其中 Chrome 执行 HOOT 6 项，全部通过；另有真实 WebClient 的三次独立浏览器会话验证保存、恢复、重置及再次恢复。

覆盖：

- 当前用户保存/更新/读取/删除，跨用户、view、key、component_type 隔离。
- 直接 ORM CRUD 越权、配置所有者转移、portal、非法类型/范围、作用域注入及过大配置。
- local/server、local/remote、缺省/未知/production/staging 环境矩阵。
- 菜单、动作、Demo ORM 读取/创建/修改/删除/导出/分组、get_view(s) 的关闭。
- server 模式下直接 HTTP dataset RPC 拒绝 Playground，正式 preference API 保持可用。
- Demo 首次打开生成 40 条/用户；重复打开不重复生成；安装不生成数据。
- 真实拖拽列、原生 resize、XML 默认宽度、保存并跨浏览器会话恢复与重置。
- optional 字段开关、排序、分页、many2one、selection、分组、行内编辑、保存失败后重试。
- 独立配置运算保留按钮/行 handle/重复字段槽位，忽略已删除字段。

## 脚本、文档和静态检查

```sh
# 初始化 addons 路径以导入现有 Odoo 相关脚本测试。
./.venv/bin/python -c 'import odoo; odoo.tools.config.parse_config(["--addons-path=addons,custom_addons,common_addons"]); odoo.modules.module.initialize_sys_path(); import unittest; result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover("scripts/tests")); raise SystemExit(not result.wasSuccessful())'
./.venv/bin/python -m unittest deploy.test_config tests.test_custom_addons_arch_docs -v
bash -n scripts/deploy.sh
sh -n scripts/start-local.sh
git diff --check
```

脚本测试 38 项，25 通过、13 项按已有测试定义跳过（依赖指定 Odoo shell 业务库）；配置/架构文档测试 7 项通过。跳过项与本模块无关，未操作业务库补跑。

Ruff 0.16.8 按根 ruff.toml 检查新模块与修改的两个 Python 脚本，全部通过。
ESLint 8 按 addons/web/tooling/_eslintrc.json（包含 Prettier）检查全部新增 JavaScript，全部通过。
格式化/lint 工具仅放在被 Git 忽略的 `.local/cwc-validation` 中，没有新增生产依赖。

## 验证范围

没有部署、推送或合并；现有环境的首次安装方式见 README。
Docker daemon 未运行，未做容器构建验收；已验证部署配置测试、shell 语法，以及同一源码下的默认模块组合。
专用 js_class / x2many 的业务扩展不会自动替换，接入时需要各模块的兼容性回归。

## 固定列撤回

按用户反馈撤回 `1a4fea4c` 引入的固定列功能，恢复模块版本 `18.0.1.0.0`。
保留列顺序、列宽、保存和恢复默认布局。删除固定列按钮、sticky 样式及宽度超限提示。
`frozen` 继续作为配置预留字段，读取旧配置时不会启用固定列，也不会覆盖已保存的 sequence/width。
回归测试增加旧配置包含 `frozen: true` 的场景，验证仍按 sequence 排列、没有固定列按钮或单元格。
本地 `test_odoo_18` 通过更新本模块及重启加载撤回后的代码和资源；不恢复整库、不删除用户偏好。

撤回验证：上述模块回归命令使用日志 `rollback-tests.log`，结果为 12 项零失败；
最终调整断言后单独重跑 `--test-tags /custom_web_components:TestComponentBrowser.test_hoot_components`，
日志 `rollback-hoot.log` 确认 HOOT 6 项、25 个断言全部通过。
Ruff、ESLint、架构文档测试及 `git diff --check` 均通过。


## 统一列设置菜单 — 18.0.1.2.0

将顺序、显隐、固定、保存及恢复默认统一放入原生右侧 Dropdown；不再显示表头拖拽/图钉或表格上方工具栏。
显隐与其他布局一起按用户/view 保存在数据库；缺失 visible 的旧配置采用 XML 默认显隐。
未新增模型、权限或生产依赖，开发环境保护保持原有规则。

使用上方同一独立测试库命令执行 `--test-tags /custom_web_components`，日志
`.local/cwc-validation/settings-final.log`：12 项 Odoo 测试零失败，包含 HOOT 14 项、65 个断言全部通过。
三个独立 Chrome 会话验证菜单拖拽、固定、显隐、列宽、保存、重新登录恢复、实际横向滚动及恢复默认持久化。
补充覆盖没有 optional 字段也有菜单、column_invisible 不出现在菜单、非 optional 不可隐藏、隐藏列固定状态、固定组内排序与跨组阻止、窄窗口、编辑禁用、行 handle/选择框、分组汇总以及偏好加载失败回退原生菜单。
真实主题下截图已检查，位于 `.local/cwc-validation/settings-captures/`，仅包含独立测试库的合成数据。

静态检查：Ruff、ESLint（含 Prettier）、架构文档 unittest、`git diff --check` 全部通过。
本地 `test_odoo_18` 使用统一启动器更新本模块到 `18.0.1.2.0` 并重启；更新前备份，仅更新模块，不恢复整库或删除用户偏好。不操作远端数据库。

## 拖动落点反馈与菜单精简 — 18.0.1.2.1

移除菜单重复标题、说明与分组文字；固定/普通区域仅用细线分隔。
拖动到行的上半部/下半部，分别显示 before/after 插入线和轻微让位动画；实际落点使用同一判定。
修正向下移动时源列移除后的插入索引，保留键盘 Alt+上下逐项移动行为；取消、拖出、外部拖动和跨组拖动有对应清理/拒绝逻辑。

同一独立库回归命令使用 `--test-tags /custom_web_components`，日志
`.local/cwc-validation/drag-feedback-final.log`：12 项 Odoo 测试零失败，HOOT 17 项、89 个断言全部通过。
新增上下方向及首尾精确插入、插入线与实际顺序一致、拖动中不提前改序、离开/Escape/dragend 清理、外部和跨组拖动拒绝测试。
现有跨会话恢复、固定、显隐、列宽及重置回归保持通过。
真实主题下的拖动截图已检查，位于 `.local/cwc-validation/drag-feedback-captures/`，仅使用测试库合成数据。
ESLint、Ruff、架构文档 unittest、`git diff --check` 通过。动画支持系统减少动态效果设置。
本地数据库备份后更新本模块并重启；未修改远端环境及既有用户偏好。

## 原生列表统一布局 — 19.0.1.5.0（2026-11-20）

从标准 list registry 的局部替换改为原生 ListRenderer 共享扩展及模板 extension。
新增专用 Controller/Renderer、无 optional 字段时显示按钮、表单双明细作用域、关系路径与临时列表隔离测试；服务端覆盖明细路径校验、列配置校验及用户隔离。

- 独立库 `cwc_global_regression_20261120` 安装及升级均执行 `--test-enable --test-tags /custom_web_components --stop-after-init --http-port=18099`；最终升级日志 `.local/cwc-global-upgrade-regression.log`：15 项 Odoo 测试零失败，HOOT 31 项、477 个断言通过。覆盖跨会话保存、列宽拖动、显隐、固定、分组、编辑及恢复默认。
- 独立库 `cwc_global_20261120` 安装 `custom_hr/custom_hr_indicator`，真实员工及指标管理 action 验证列设置按钮、排序、列宽拖动、保存、刷新恢复、重新登录恢复、390px 菜单及恢复默认，无浏览器异常。测试库 action 数字 ID 与开发库不同，使用同一 XML action 对应关系。截图在 `.local/cwc-global-captures/`，仅含独立测试数据。
- 指标筛选记忆、生成/分配明细及实际值展示的相关 HOOT 回归：14 项、51 个断言通过，日志 `.local/cwc-global-indicator-hoot.log`。
- 修改的 JS 使用 `addons/web/tooling/_eslintrc.json` 执行 ESLint（含 Prettier）；Python 使用 Ruff；`git diff --check` 通过。
- 本地 `dev-yabo` 使用 `sh scripts/start-local.sh local -u custom_web_components --stop-after-init --no-http` 升级至 `19.0.1.5.0` 并重启。原有 list 偏好作用域不变，无新表或业务数据迁移；未操作远端环境。

覆盖范围为保留原生 setup 和菜单模板扩展点、有实际 view ID 的 Odoo 列表及其明细。手写 HTML 表格、透视表和无视图 ID 的临时列表不提供该持久化入口。

## 个人显隐与最少两个字段 — 19.0.1.5.1（2026-11-20）

首次使用 XML 初始布局；保存后普通字段和 optional 字段均按个人选择展示，不再强制普通字段始终显示。至少保留两个不同的可用数据字段；总共只有一个字段时保留该字段。系统隐藏列、权限裁剪、handle 和动态 property 结构列不计入可选字段数。

- 先通过新增原生列表测试复现普通字段无法隐藏；随后验证隐藏与保存、最后两个字段禁用取消、事件处理拦截、重新显示、旧配置补足、重复字段计数和权限/系统隐藏过滤。
- 独立库升级命令使用 `--test-enable --test-tags /custom_web_components --stop-after-init --http-port=18099`；`.local/cwc-personal-visibility-regression.log`：15 项 Odoo 测试零失败，HOOT 36 项、500 个断言通过。
- 原始指标管理视图未添加 optional 属性，使用独立库中的实际 action 验证全部 15 个数据列可切换；隐藏、保存、刷新恢复、仅保留两个字段及其禁用状态、恢复默认通过，无浏览器异常。截图 `.local/cwc-global-captures/indicator-two-columns.png`。
- ESLint（含 Prettier）、`git diff --check` 通过。无新模型、字段、依赖或用户偏好迁移。
- 更新本地 `dev-yabo` 前备份数据库与 filestore 至 `.local/cwc-personal-visibility-backup/`，只升级公共模块并重启；远端环境未操作。
