{
    "name": "工作流项目任务",
    "summary": "创建/关联 Project 任务与原子状态同步",
    "version": "19.0.1.0.3",
    "category": "Productivity/Workflow",
    "license": "LGPL-3",
    "depends": ["workflow_core", "project_todo"],
    "data": [
        "security/ir.model.access.csv",
        "security/rules.xml",
        "views/project_views.xml",
        "views/todo_approval_views.xml",
    ],
    "installable": True,
}
