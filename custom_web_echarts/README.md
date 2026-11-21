# 公共 ECharts 组件（Odoo 18）

`custom_web_echarts` 是可选的通用前端模块。它提供 Owl 组件 `EChart` 和只读表单字段控件 `custom_echarts`，使用 Apache ECharts 6.1.0；不新增数据库表、服务端接口或业务数据源。需要使用图表的模块在 manifest 的 `depends` 中加入 `custom_web_echarts`。当前 `yabo_strategy` 不依赖此模块；安装它不会自动创建驾驶舱或替换其他图表。

## 按需加载

组件代码进入 `web.assets_backend`；完整 ECharts 浏览器库仅在 `custom_web_echarts.echarts_lib` 中。页面挂载第一个 `EChart` 时调用 Odoo `loadBundle()`，后续图表复用同一资源。未显示图表的后台页面不下载约 1.1 MB 的库文件。模块不自动安装。

Apache ECharts 依 Apache-2.0 许可随模块附带；来源、版本、哈希及许可证见 [vendor 说明](static/lib/echarts/README.md)。引入该生产资源是为了支持现有 Chart.js 以外的 ECharts 图形与选项配置；代价是图表页面的额外下载和后续安全/版本维护。只需要现有基础图表的模块可以继续使用 Odoo 已包含的 Chart.js。

## 在 Owl 页面中使用

```js
import { EChart } from "@custom_web_echarts/echart/echart";

export class MyDashboard extends Component {
    static components = { EChart };
    // 业务模块自行查询、授权并形成 ECharts option 对象。
}
```

```xml
<EChart option="state.chartOption" height="320" ariaLabel="'月度目标与实际'"/>
```

`option` 为 ECharts 原生配置对象或 `null`；`height` 为像素数，默认 300；`theme` 可选。配置对象更新时组件调用 `setOption(..., {notMerge: true})`，容器缩放时调用 `resize()`，卸载时释放实例。`null` 显示“暂无图表数据”。数据读取及权限判断由调用模块负责。

## 在 Odoo 表单中使用

字段控件支持 Char、Text 或 Json 字段，其值为 ECharts 配置对象或 JSON 字符串：

```xml
<field name="chart_option" widget="custom_echarts" readonly="1"
       options="{'height': 320, 'aria_label': '目标与实际'}"/>
```

空值显示“暂无图表数据”，无效 JSON 显示错误信息。字段控件只负责展示，不能在图表上编辑配置；业务模块可用计算字段生成配置，也可用自己的编辑器保存。不要把未经权限过滤的数据或不可信 JavaScript 函数作为图表配置传入。

## 验证

HOOT 测试标签：`custom_web_echarts`；覆盖按需资源请求、实际绘图、配置更新、JSON 解析与无效字段提示。模块可用 `-i custom_web_echarts --stop-after-init` 安装到本地测试数据库，无数据迁移。

新增可选 `onClick` 回调供调用方处理图形点击；组件更新时不重复绑定事件。圆形打包消费者可另行 `loadBundle("custom_web_echarts.d3_hierarchy_lib")`，按需加载 14,828 字节的 `d3-hierarchy@3.1.2`（BSD-3-Clause，无依赖），不下载完整 D3。来源、许可证与哈希见 `static/lib/d3-hierarchy/README.md`。
