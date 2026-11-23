from odoo import api, fields, models
from odoo.exceptions import ValidationError


class WorkflowToken(models.Model):
    _name = "workflow.token"
    _inherit = "workflow.runtime.record"
    _description = "流程执行令牌"
    _table = "abt_workflow_token"
    _order = "id"

    instance_id = fields.Many2one(
        "workflow.instance",
        required=True,
        ondelete="restrict",
        index=True,
    )
    company_id = fields.Many2one(
        related="instance_id.company_id",
        store=True,
        index=True,
    )
    key = fields.Char(required=True)
    node_id = fields.Many2one("workflow.node", required=True, ondelete="restrict")
    parent_id = fields.Many2one("workflow.token", ondelete="restrict", index=True)
    fork_activation_id = fields.Many2one(
        "workflow.node.instance",
        ondelete="restrict",
        index=True,
    )
    branch_edge_id = fields.Many2one("workflow.edge", ondelete="restrict")
    state = fields.Selection(
        [
            ("active", "执行中"),
            ("waiting", "等待中"),
            ("joined", "已汇合"),
            ("done", "已结束"),
            ("cancelled", "已取消"),
        ],
        required=True,
        default="active",
        index=True,
    )
    _key_unique = models.Constraint("UNIQUE(instance_id, key)", "执行令牌已存在。")

    @api.constrains(
        "instance_id",
        "node_id",
        "parent_id",
        "fork_activation_id",
        "branch_edge_id",
    )
    def _check_scope(self):
        for token in self:
            if token.node_id.version_id != token.instance_id.version_id:
                raise ValidationError(self.env._("令牌节点必须属于实例的冻结版本。"))
            if not token.parent_id:
                if (
                    token.fork_activation_id
                    or token.branch_edge_id
                    or token.key != "root"
                ):
                    raise ValidationError(self.env._("根令牌不能关联并行分支。"))
                continue
            fork = token.fork_activation_id
            if (
                token.parent_id.instance_id != token.instance_id
                or not fork
                or fork.instance_id != token.instance_id
                or fork.token_id != token.parent_id
                or fork.node_id.kind != "fork"
                or token.branch_edge_id.source_id != fork.node_id
            ):
                raise ValidationError(self.env._("令牌、分支与分支激活范围不匹配。"))
