{
    "name": "工作流分级审批",
    "summary": "OCA Tier Validation 审批节点与安全适配",
    "version": "19.0.1.1.2",
    "category": "Productivity/Workflow",
    "license": "AGPL-3",
    "depends": ["workflow_core", "base_tier_validation"],
    "data": [
        "security/groups.xml",
        "security/ir.model.access.csv",
        "security/rules.xml",
        "views/approval_views.xml",
    ],
    "installable": True,
}
