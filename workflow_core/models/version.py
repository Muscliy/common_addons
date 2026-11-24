from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

from odoo.addons.workflow_core.services.access import (
    lock_record,
    require_group,
    require_internal_write,
)
from odoo.addons.workflow_core.services.graph_validation import (
    validate_graph,
    validate_payload,
)
from odoo.addons.workflow_core.services.rules import scalar_fields


class WorkflowVersion(models.Model):
    _name = "workflow.version"
    _description = "流程版本"
    _table = "abt_workflow_version"
    _order = "number desc, id desc"
    _rec_name = "display_name"

    definition_id = fields.Many2one(
        "workflow.definition",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        related="definition_id.company_id",
        store=True,
        index=True,
    )
    number = fields.Integer(required=True)
    state = fields.Selection(
        [("draft", "草稿"), ("published", "已发布")],
        default="draft",
        required=True,
    )
    revision = fields.Integer(default=0, required=True)
    viewport = fields.Json(default=lambda self: {"x": 0, "y": 0, "zoom": 1})
    node_ids = fields.One2many("workflow.node", "version_id")
    edge_ids = fields.One2many("workflow.edge", "version_id")
    published_by = fields.Many2one("res.users", readonly=True)
    published_at = fields.Datetime(readonly=True)
    is_current = fields.Boolean(compute="_compute_is_current")
    _number_unique = models.Constraint(
        "UNIQUE(definition_id, number)",
        "流程版本号必须唯一。",
    )

    @api.depends("definition_id.name", "number")
    def _compute_display_name(self):
        for version in self:
            version.display_name = f"{version.definition_id.name} / V{version.number}"

    @api.depends("definition_id.published_version_id")
    def _compute_is_current(self):
        for version in self:
            version.is_current = version.definition_id.published_version_id == version

    def action_restore(self) -> bool:
        self.ensure_one()
        self.check_access("read")
        require_group(self, "group_publisher")
        with self.env.cr.savepoint():
            definition = self.definition_id
            lock_record(definition)
            if self.state != "published":
                raise UserError(self.env._("只能启用已发布版本。"))
            if definition.published_version_id != self:
                self.action_validate()
                definition._set_published_version(self)
        return True

    @api.model_create_multi
    def create(self, vals_list):
        require_internal_write(self)
        if any(vals.get("state", "draft") != "draft" for vals in vals_list):
            raise AccessError(self.env._("新版本必须从草稿开始。"))
        return super().create(vals_list)

    def write(self, vals):
        require_internal_write(self)
        if any(v.state != "draft" for v in self):
            raise UserError(self.env._("已发布版本不可修改, 请创建新版本。"))
        return super().write(vals)

    def unlink(self):
        require_internal_write(self)
        if any(v.state == "published" for v in self):
            raise UserError(self.env._("已发布版本不可删除。"))
        return super().unlink()

    def action_designer(self) -> dict:
        self.ensure_one()
        self.check_access("read")
        return {
            "type": "ir.actions.client",
            "tag": "workflow_core.canvas",
            "name": self.display_name,
            "params": {"version_id": self.id},
        }

    def get_canvas(self) -> dict:
        self.ensure_one()
        self.check_access("read")
        graph = {
            "nodes": [n._canvas_data() for n in self.node_ids],
            "edges": [e._canvas_data() for e in self.edge_ids.sorted("sequence")],
            "viewport": self.viewport,
        }
        model = (
            self.env[self.definition_id.model_id.sudo().model]
            if self.definition_id.model_id
            else None
        )
        condition_fields = scalar_fields(model)
        if model is not None and model._name == "hr.expense":
            if "total_amount" in condition_fields:
                condition_fields["total_amount"]["string"] = self.env._("报销金额")
        return {
            "id": self.id,
            "title": self.display_name,
            "revision": self.revision,
            "state": self.state,
            "graph": graph,
            "node_types": self._node_types(),
            "node_options": self._node_options(),
            "fields": condition_fields,
            "business_model": self.definition_id.model_id.sudo().model or "",
            "can_edit": self.state == "draft"
            and self.definition_id._can_manage(),
            "can_publish": self.state == "draft"
            and self.env.user.has_group("workflow_core.group_publisher"),
            "can_start": self.state == "published"
            and self.definition_id.published_version_id == self
            and self.env.user.has_group("workflow_core.group_executor")
            and self.definition_id._starter_department_allowed(),
            "definition_id": self.definition_id.id,
            "assignees": [
                {"id": u.id, "name": u.name} for u in self.node_ids.assignee_id
            ],
        }

    def get_assignees(self) -> list[dict]:
        self.ensure_one()
        self.check_access("read")
        self.definition_id._check_manage()
        group = self.env.ref("workflow_core.group_executor")
        users = (
            self.env["res.users"]
            .sudo()
            .search(
                [
                    ("company_ids", "in", self.company_id.id),
                    ("active", "=", True),
                    ("share", "=", False),
                    ("all_group_ids", "in", group.id),
                ],
                limit=500,
                order="name, id",
            )
        )
        return [{"id": user.id, "name": user.name} for user in users]

    def _lock_draft(self) -> None:
        self.ensure_one()
        self.check_access("read")
        # 与发布/新版本/启动同一把 definition 锁, 固定锁顺序避免死锁。
        lock_record(self.definition_id)
        lock_record(self)
        if self.state != "draft":
            raise UserError(self.env._("已发布版本不可编辑。"))

    def save_graph(self, graph: dict, revision: int) -> dict:
        self.definition_id._check_manage()
        with self.env.cr.savepoint():
            self._lock_draft()
            if type(revision) is not int or revision != self.revision:
                raise UserError(self.env._("草稿已被其他人修改, 请刷新后重试。"))
            validate_payload(graph, self._node_types())
            self._validate_configs(graph)
            self._check_assignees(graph)
            elevated = self.sudo()
            elevated.edge_ids.unlink()
            elevated.node_ids.unlink()
            by_key = {}
            for node in graph["nodes"]:
                by_key[node["id"]] = (
                    self.env["workflow.node"]
                    .sudo()
                    .create(
                        {
                            "version_id": self.id,
                            "key": node["id"],
                            "kind": node["type"],
                            "name": node["data"]["label"],
                            "assignee_id": node["data"]["assignee_id"] or False,
                            "position": node["position"],
                            "background_color": node["data"].get("background_color"),
                            "config": node["data"].get("config", {}),
                        },
                    )
                    .id
                )
            self.env["workflow.edge"].sudo().create(
                [
                    {
                        "version_id": self.id,
                        "key": edge["id"],
                        "sequence": index,
                        "source_id": by_key[edge["source"]],
                        "target_id": by_key[edge["target"]],
                        "source_handle": edge.get("sourceHandle"),
                        "target_handle": edge.get("targetHandle"),
                        "is_default": edge["data"]["default"],
                        "rule": edge["data"]["rule"],
                    }
                    for index, edge in enumerate(graph["edges"])
                ],
            )
            elevated.write(
                {"viewport": graph["viewport"], "revision": self.revision + 1},
            )
        return self.get_canvas()

    def _check_assignees(self, graph: dict) -> None:
        ids = {n["data"]["assignee_id"] for n in graph["nodes"]} - {0}
        users = self.env["res.users"].sudo().browse(ids).exists()
        if len(users) != len(ids) or any(
            not u.active
            or u.share
            or self.company_id not in u.company_ids
            or not u.has_group("workflow_core.group_executor")
            for u in users
        ):
            raise UserError(self.env._("负责人必须是本公司有效的工作流执行人员。"))

    def action_validate(self) -> bool:
        self.ensure_one()
        canvas = self.get_canvas()
        validate_graph(canvas["graph"], canvas["fields"], self._node_types())
        self._validate_configs(canvas["graph"])
        self._check_assignees(canvas["graph"])
        return True

    def action_publish(self, revision: int) -> dict:
        require_group(self, "group_publisher")
        with self.env.cr.savepoint():
            self._lock_draft()
            if type(revision) is not int or revision != self.revision:
                raise UserError(self.env._("流程已改变, 请刷新后重新发布。"))
            self.action_validate()
            self.sudo().write(
                {
                    "state": "published",
                    "published_by": self.env.uid,
                    "published_at": fields.Datetime.now(),
                },
            )
            self.definition_id._set_published_version(self)
        return self.get_canvas()

    def _node_types(self) -> list:
        return (
            self.env["workflow.node"]._fields["kind"]._description_selection(self.env)
        )

    def _node_options(self) -> dict:
        return {}

    def _validate_configs(self, graph: dict) -> None:
        for node in graph["nodes"]:
            self.env["workflow.node"]._validate_config(
                node["type"],
                node["data"].get("config", {}),
                self,
            )
