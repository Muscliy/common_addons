# ARCH: custom_branding

- **Source location**: `common_addons/custom_branding/` in the `common_addons` Git submodule. Odoo module names, asset URLs, model names, XML IDs and database tables remain unchanged; the host project must include `common_addons` in `addons_path`.
## 1. Overview

- **Technical Name**: `custom_branding`
- **Core Purpose**: 将地址、国家选择和工作日历调整为中国本地化体验。
- **Dependencies**: `hr`, `resource`, `mail`

## 2. Model Extensions & Schema

### Inherited Models

- `res.partner`:
  - **Fields Added**: `abt_full_address`（非存储、可编辑计算字段）、`abt_address_original`（最近输入原文）、`abt_address_district`（非存储计算区县）、`abt_address_hint`（计算提示）。
  - **Overridden Methods**: `default_get` 在未指定上下文默认值时将 `country_id` 设为中国；新建联系人语言默认 `zh_CN`，显式 `default_lang`、手工选择及父联系人语言仍按原生规则处理，不批量改已有联系人。
- `hr.employee`:
  - **Fields Added**: None.
  - **Overridden Methods**: `default_get` 在未指定上下文默认值时将 `private_country_id` 设为中国。
- `res.bank`:
  - **Fields Added**: None.
  - **Overridden Methods**: `default_get` 在未指定上下文默认值时将 `country` 设为中国。
- `res.country`:
  - **Fields Added**: None.
  - **Overridden Methods**: `name_search` 在空搜索词时将中国置顶；保留调用方 domain 和 limit，输入搜索词时完全使用原生排序。
- `resource.calendar`:
  - **Fields Added**: `flexible_hours` (`Boolean`), `full_time_required_hours` (`Float`)。
  - **Overridden Methods**: None.
- `resource.calendar.attendance`:
  - **Fields Added**: None.
  - **Overridden Methods**: 新增 `_localize_standard_attendance_names`，将预定义英文标准班次/分段名替换为中文。

### Custom Models

- `abt.address.parser`：无表 AbstractModel，公共离线地址解析服务，所有使用方共用本模块的区划字典及解析逻辑。

## 3. Business Logic & Data Flow

1. 新建联系人、员工或银行记录时，若目标字段被请求、原生默认值为空且 context 未显式提供 `default_<field>`，使用 `base.cn` 作为默认国家。
2. 国家下拉在无关键词时先执行原生搜索；若中国记录仍符合传入 domain，则将其移到第一项并遵守限制条数。
3. 安装/升级数据调用考勤本地化方法，仅精确匹配预定义的英文名称、星期和时段组合；其他自定义考勤名称不变。
4. 联系人头部（公司及个人）与子地址弹窗统一使用“完整地址”输入框；输入失焦通过 onchange 回填，ORM create/write 通过 inverse 使用同一服务，导入/API 与页面行为一致。
5. `abt.address.parser.parse(address)` 返回 original/province/city/district/street/status，不修改业务数据；`partner_values(address)` 将结果适配到联系人原生字段。其他地址模型调用 `parse` 自行映射，禁止复制解析逻辑。
6. 优先匹配已知省市区最长且唯一的前缀；可由唯一城市/区县补全省份。直辖市不重复拼接，重名区县不推测。区县保留在原生 `street` 中，标准地址打印不会丢区县；`abt_address_district` 是辅助结构化信息。
7. 原有分段地址即时合成到完整地址框，无批量迁移、不改旧地址值。只有主动修改完整地址时才替换旧分段信息并保存输入原文；清空会清空分段字段，国家保留。手工展开修改原生字段时完整地址重新计算；与原生字段合成值相同的输入跳过解析，避免 onchange/inverse 循环覆盖人工修正及输入原文。

8. 安装/升级时启用简体中文语言，避免默认选项无效。主表单的税务识别码、网站、语言、标签采用两列，完整地址在其下方独占一行；通过移动原生节点保留控件属性和其他模块扩展。

## 4. Integration & External APIs

无新增控制器、AI API、外部请求或 Python 依赖。区划字典固定打包在 `data/address/`，来源、版本与许可见 `SOURCE.md` 和 `LICENSE`。使用公共服务时不传收件人或电话，仅传地址。

## 5. Gotchas & Constraints

- 显式 context 默认国家优先于中国默认值，不能覆盖业务调用方的选择。
- `name_search` 只有空搜索词才重排；domain 排除中国或 limit 为 1 等情况仍保持有效结果和条数。
- 考勤翻译不是通用字符串替换，必须同时满足标准名称、`dayofweek` 与 `day_period`，以免改写客户自定义班次。
- 联系人地址布局集中在 `custom_branding.view_partner_address_form_cn_global`（仅完整地址，识别提示隐藏；原生分段字段放在默认折叠的修改区域），并通过 `base.cn.address_view_id` 挂到中国国家记录上；Odoo 的 `_view_get_address` 会用该视图替换联系人主表单、地址页签内嵌表单和地址弹窗中的 `o_address_format` 块，只需维护一份布局。
- 该机制取当前公司国家的 `address_view_id`，公司国家不是中国时不生效；不要再单独继承 `base.view_partner_form` 的地址块，运行时会被地址视图整体替换，且嵌套 div 会被 `address_format` 的字段重排打散。
- 本模块依赖 `hr`、`resource`、`mail`，安装时不会自动安装 `contacts`；`res.partner` 及其视图来自 `base`，未安装 Contacts 应用时地址定制同样生效。

- 区划资料为 2023-06-30 快照，覆盖大陆省市区；新区划和港澳台完整区划不保证识别。匹配不完整时保留未匹配文本及提示，允许展开修改，不猜测邮编或把道路中的地名当城市。未知地址保留在 `street`，不调用外部服务兜底。
- 试用范围仅 `res.partner` 地址布局；员工家庭地址及银行地址保持原有输入方式。公司国家不是中国时沿用原生地址布局。
- `contact_address` 及 Odoo 原生报表格式不改写。历史地址仅合成显示，不写回区县；区县根据当前原生地址计算，手工修正不会残留旧区县。原文为最近一次完整地址输入快照，原生字段更新不会伪造新的输入原文。
