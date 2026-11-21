{
    'name': '公共 ECharts 组件',
    'summary': '按需加载的 ECharts Owl 组件与只读表单字段控件',
    'description': '供 Odoo 后台按需加载 Apache ECharts 的通用组件。',
    'version': '19.0.1.1.0',
    'category': 'Hidden/Tools',
    'license': 'LGPL-3',
    'depends': ['web'],
    'assets': {
        'web.assets_backend': [
            'custom_web_echarts/static/src/echart/*.js',
            'custom_web_echarts/static/src/echart/*.xml',
            'custom_web_echarts/static/src/echart/*.scss',
        ],
        'custom_web_echarts.echarts_lib': [
            'custom_web_echarts/static/lib/echarts/echarts.min.js',
        ],
        'custom_web_echarts.d3_hierarchy_lib': [
            'custom_web_echarts/static/lib/d3-hierarchy/d3-hierarchy.min.js',
        ],
        'web.assets_unit_tests': [
            'custom_web_echarts/static/tests/*.test.js',
        ],
    },
    'installable': True,
    'application': False,
}
