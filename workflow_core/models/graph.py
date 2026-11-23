from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.workflow_core.services.access import require_internal_write
from odoo.addons.workflow_core.services.engine import create_task
from odoo.addons.workflow_core.services.graph_validation import (
    HANDLE_POSITIONS,
    NODE_BACKGROUNDS,
    NODE_TYPES,
)


class WorkflowGraphElement(models.AbstractModel):
    _name = "workflow.graph.element"
    _description = "流程图元素写保护"

    def _check_draft(self) -> None:
        if any(record.version_id.state != "draft" for record in self):
            raise UserError(self.env._("已发布流程的节点和连线不可修改。"))

    @api.model_create_multi
    def create(self, vals_list):
        require_internal_write(self)
        versions = self.env["workflow.version"].browse(
            {v["version_id"] for v in vals_list},
        )
        if any(version.state != "draft" for version in versions):
            raise UserError(self.env._("不能向已发布版本添加元素。"))
        return super().create(vals_list)

    def write(self, vals):
        require_internal_write(self)
        self._check_draft()
        if "version_id" in vals:
            raise UserError(self.env._("不能移动元素所属版本。"))
        return super().write(vals)

    def unlink(self):
        require_internal_write(self)
        self._check_draft()
        return super().unlink()


class WorkflowNode(models.Model):
    _name = "workflow.node"
    _inherit = "workflow.graph.element"
    _description = "流程节点"
    _table = "abt_workflow_node"
    _order = "id"

    version_id = fields.Many2one(
        "workflow.version",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        related="version_id.company_id",
        store=True,
        index=True,
    )
    key = fields.Char(required=True)
    name = fields.Char(required=True)
    kind = fields.Selection(NODE_TYPES, required=True)
    position = fields.Json(required=True)
    config = fields.Json(default=dict)
    background_color = fields.Selection(NODE_BACKGROUNDS, string="节点背景色")
    assignee_id = fields.Many2one("res.users", string="负责人", ondelete="restrict")
    _key_unique = models.Constraint(
        "UNIQUE(version_id, key)",
        "同一版本节点标识必须唯一。",
    )

    def _canvas_data(self) -> dict:
        result = {
            "id": self.key,
            "type": self.kind,
            "position": self.position,
            "data": {"label": self.name, "assignee_id": self.assignee_id.id or 0},
        }
        if self.config:
            result["data"]["config"] = self.config
        if self.background_color:
            result["data"]["background_color"] = self.background_color
        return result

    def _validate_config(self, kind: str, config: dict, version) -> None:
        if kind == "fork":
            if (
                set(config) != {"join"}
                or not isinstance(config["join"], str)
                or not config["join"]
            ):
                raise ValidationError(self.env._("请选择并行分支的汇合节点。"))
        elif config:
            raise ValidationError(self.env._("此节点类型不接受额外配置。"))

    def _waits_for_input(self) -> bool:
        return self.kind == "task"

    def _activate_input(self, instance, activation, record, actor_id: int) -> None:
        create_task(instance, activation, record)


class WorkflowEdge(models.Model):
    _name = "workflow.edge"
    _inherit = "workflow.graph.element"
    _description = "流程连线"
    _table = "abt_workflow_edge"
    _order = "sequence, id"

    version_id = fields.Many2one(
        "workflow.version",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        related="version_id.company_id",
        store=True,
        index=True,
    )
    key = fields.Char(required=True)
    sequence = fields.Integer()
    source_id = fields.Many2one("workflow.node", required=True, ondelete="restrict")
    target_id = fields.Many2one("workflow.node", required=True, ondelete="restrict")
    source_handle = fields.Selection(HANDLE_POSITIONS, string="出线连接点")
    target_handle = fields.Selection(HANDLE_POSITIONS, string="入线连接点")
    is_default = fields.Boolean()
    rule = fields.Json(default=dict)
    _key_unique = models.Constraint(
        "UNIQUE(version_id, key)",
        "同一版本连线标识必须唯一。",
    )

    @api.constrains("version_id", "source_id", "target_id")
    def _check_versions(self):
        for edge in self:
            if (
                edge.source_id.version_id != edge.version_id
                or edge.target_id.version_id != edge.version_id
            ):
                raise ValidationError(self.env._("连线两端必须属于同一流程版本。"))

    def _canvas_data(self) -> dict:
        result = {
            "id": self.key,
            "source": self.source_id.key,
            "target": self.target_id.key,
            "data": {"default": self.is_default, "rule": self.rule or {}},
        }
        if self.source_handle:
            result["sourceHandle"] = self.source_handle
        if self.target_handle:
            result["targetHandle"] = self.target_handle
        return result
