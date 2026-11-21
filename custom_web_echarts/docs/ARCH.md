# ARCH: custom_web_echarts

- **Source location**: `common_addons/custom_web_echarts/` in the `common_addons` Git submodule. Odoo module names, asset URLs, model names, XML IDs and database tables remain unchanged; the host project must include `common_addons` in `addons_path`.
## 1. Overview

- **Technical Name**: `custom_web_echarts`.
- **Core Purpose**: Reusable Apache ECharts rendering for Odoo 18 Owl pages and read-only form fields.
- **Dependencies**: `web`; vendored Apache ECharts 6.1.0 (Apache-2.0). Optional install, no automatic installation.
- **Boundary**: Rendering and chart lifecycle only. Business data, access control, chart selection and option construction belong to each consuming addon.

## 2. Model Extensions & Schema

- No ORM models, database tables, migrations, XML data or HTTP controllers.
- The Char/Text/Json field widget reads an existing model field without writing it.

## 3. Business Logic & Data Flow

1. The small `EChart` Owl wrapper and field widget are registered in `web.assets_backend`. The full browser build is isolated in `custom_web_echarts.echarts_lib`, excluded from the normal backend bundle.
2. On mount, `EChart` calls Odoo `loadBundle()` and checks that `globalThis.echarts` registered. The Odoo asset loader caches a bundle URL, including concurrent chart loads. A failed load displays an error and logs the underlying exception.
3. When a non-null option arrives, the wrapper creates an ECharts instance, replaces its option with `notMerge: true`, and responds to container size changes via `ResizeObserver`. A theme change recreates the instance. Unmount disconnects the observer and disposes the chart.
4. A null option clears the instance and shows an empty message. The form field widget parses JSON strings or accepts objects, rejects arrays/invalid values, and shows an inline error for invalid input.

## 4. Integration & External APIs

- Import `EChart` from `@custom_web_echarts/echart/echart` and supply an ECharts `option` object or `null`; optional props: `height` in pixels, `theme`, `ariaLabel`.
- Use form field `widget="custom_echarts"` on Char, Text or Json; supported XML options: `height`, `theme`, `aria_label`.
- Consuming addons declare `custom_web_echarts` in `depends`. They must enforce their own record permissions before constructing chart data and avoid passing untrusted executable formatters.
- HOOT tag `custom_web_echarts`; no external service, RPC or network CDN is required at runtime.
- Vendored file: `static/lib/echarts/echarts.min.js` from npm `echarts@6.1.0`, SHA-256 `b66b25aeb4df84e33199dc21694014d336d222cbd9deb0e5a7c14bd6aa0d0fd0`; LICENSE and NOTICE are preserved.

## 5. Gotchas & Constraints

- Installing this module does not replace existing Chart.js charts or create a dashboard builder.
- The first chart on a page incurs the vendor bundle download; pages without a chart do not load it. The full browser build is approximately 1.1 MB before HTTP compression; monitor version and security updates separately.
- The field widget is display-only. JSON cannot encode JavaScript callback functions; advanced interactive formatters require a trusted Owl caller.
- The reusable renderer does not claim that every ECharts chart type has suitable business data. A consuming module explicitly chooses types and maps its data accordingly.

### Optional Click Events and D3 Hierarchy Layout

- `EChart` accepts an optional `onClick(event)` prop, registered once per created instance and dispatching to the current prop callback. Normal instance disposal also disposes listeners. Existing consumers need no changes.
- `custom_web_echarts.d3_hierarchy_lib` contains a separate 14,828-byte `d3-hierarchy@3.1.2` UMD build (BSD-3-Clause; zero runtime dependencies). It exposes `globalThis.d3.hierarchy/pack`; only consumers explicitly requesting it load the bundle. Provenance, SHA-256 and LICENSE are preserved with the vendor file.
- ECharts still owns rendering and data authorization remains with the consumer. D3 only computes hierarchy layouts. No network CDN at runtime and no tables/models introduced.
