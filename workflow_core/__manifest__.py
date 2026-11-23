{
    "name": "通用工作流",
    "summary": "可视化流程设计、版本发布、人工待办与执行监控",
    "version": "19.0.1.3.0",
    "category": "Productivity/Workflow",
    "license": "LGPL-3",
    "depends": ["web", "mail"],
    "data": [
        "security/groups.xml",
        "security/ir.model.access.csv",
        "security/rules.xml",
        "views/definition_views.xml",
        "views/runtime_views.xml",
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_backend": ["workflow_core/static/src/action/*"],
        "workflow_core.canvas": [
            "workflow_core/static/lib/workflow_canvas.js",
            "workflow_core/static/lib/workflow_canvas.css",
        ],
        "web.assets_unit_tests": ["workflow_core/static/tests/*.test.js"],
    },
    "application": True,
    "installable": True,
}
