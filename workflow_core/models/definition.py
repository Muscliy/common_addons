import re
import uuid

from odoo import Command, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from odoo.addons.workflow_core.services.access import (
    business_record,
    lock_record,
    require_group,
)
from odoo.addons.workflow_core.services.engine import start_instance

FLOW_CODE_PATTERN = re.compile(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")


class WorkflowDefinition(models.Model):
    _name = "workflow.definition"
    _description = "流程模板"
    _table = "abt_workflow_definition"
    _check_company_auto = True

    name = fields.Char(required=True)
    description = fields.Text(string="流程说明")
    group_id = fields.Many2one(
        "workflow.group", string="流程分组", ondelete="restrict", index=True,
    )
    icon = fields.Image(string="流程图标", max_width=256, max_height=256)
    application_menu_id = fields.Many2one(
        "ir.ui.menu",
        string="所属模块",
        domain=[("parent_id", "=", False)],
        ondelete="set null",
        help="关联费用、财务等现有应用，用于流程分类展示。",
    )
    category_id = fields.Many2one(
        "workflow.category", string="流程类别", ondelete="restrict", index=True,
    )
    manager_id = fields.Many2one(
        "res.users", string="流程管理员", required=True, ondelete="restrict",
        default=lambda self: self.env.user, index=True,
        domain="[('share', '=', False), ('active', '=', True), ('company_ids', 'in', [company_id])]",
    )
    can_manage = fields.Boolean(compute="_compute_can_manage")
    code = fields.Char(
        required=True,
        copy=False,
        help="仅使用英文字母、数字和分隔用的短横线，例如 FLOW-1。新建时留空可自动生成。",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    department_id = fields.Many2one(
        "hr.department",
        string="所属部门",
        domain="[('company_id', '=', company_id)]",
        ondelete="restrict",
        help="留空允许本公司有发起权限的用户启动。填写后仅所选部门的在职员工可以启动。",
    )
    model_id = fields.Many2one(
        "ir.model",
        string="业务模型",
        domain=lambda self: [("model", "in", sorted(self._allowed_business_models()))],
    )
    version_ids = fields.One2many("workflow.version", "definition_id")
    published_version_id = fields.Many2one(
        "workflow.version",
        readonly=True,
        copy=False,
        ondelete="restrict",
    )
    version_activated_by = fields.Many2one("res.users", readonly=True, copy=False)
    version_activated_at = fields.Datetime(readonly=True, copy=False)
    active = fields.Boolean(default=True)
    canvas_preview = fields.Json(compute="_compute_canvas_preview")
    starter_group_ids = fields.Many2many(
        "res.groups",
        "abt_workflow_starter_group_rel",
        "definition_id",
        "group_id",
        string="原有发起用户组",
    )
    _code_unique = models.Constraint(
        "UNIQUE(company_id, code)",
        "同一公司流程编码必须唯一。",
    )

    def _can_manage(self) -> bool:
        self.ensure_one()
        return self.env.su or self.env.user.has_group("workflow_core.group_manager") or self.manager_id == self.env.user

    @api.depends("manager_id")
    @api.depends_context("uid")
    def _compute_can_manage(self):
        for template in self:
            template.can_manage = template._can_manage()

    def _check_manage(self) -> None:
        self.check_access("write")
        if any(not template._can_manage() for template in self):
            raise AccessError(self.env._("只有指定流程管理员可以维护此流程。"))

    def _ensure_manager_access(self) -> None:
        # Assignment grants only the basic workflow role, never global designer/publisher rights.
        managers = self.manager_id.filtered(lambda user: not user.has_group("workflow_core.group_user"))
        if managers:
            self.env.ref("workflow_core.group_user").sudo().write({
                "user_ids": [Command.link(user.id) for user in managers],
            })

    @api.constrains("manager_id", "company_id")
    def _check_manager(self):
        for template in self:
            manager = template.manager_id.sudo()
            if not manager.active or manager.share or template.company_id not in manager.company_ids:
                raise ValidationError(self.env._("流程管理员必须是所属公司的有效内部用户。"))

    @api.constrains("application_menu_id", "category_id")
    def _check_category(self):
        for template in self:
            if template.application_menu_id.parent_id:
                raise ValidationError(self.env._("所属模块必须是 Odoo 应用根菜单。"))
            if template.category_id and template.category_id.application_menu_id != template.application_menu_id:
                raise ValidationError(self.env._("流程类别必须属于当前选择的模块。"))

    @api.onchange("application_menu_id")
    def _onchange_application(self):
        if self.category_id.application_menu_id != self.application_menu_id:
            self.category_id = False

    def _allowed_business_models(self) -> set[str]:
        models = {"res.partner"}
        if "hr.expense" in self.env:
            models.add("hr.expense")
        return models

    @api.constrains("model_id", "company_id", "department_id")
    def _check_scope(self):
        for record in self:
            if record.company_id not in self.env.companies:
                raise AccessError(self.env._("不能维护未授权公司的流程。"))
            if (
                record.department_id
                and record.department_id.company_id != record.company_id
            ):
                raise ValidationError(self.env._("所属部门必须属于流程的所属公司。"))
            if (
                record.model_id
                and record.model_id.sudo().model not in self._allowed_business_models()
            ):
                raise ValidationError(self.env._("业务模型未注册。"))

    @api.constrains("code")
    def _check_code_format(self):
        for template in self:
            if not FLOW_CODE_PATTERN.fullmatch(template.code or ""):
                raise ValidationError(
                    self.env._("流程编码仅允许字母、数字及分隔短横线，例如 FLOW-1。"),
                )

    def _assign_codes(self, vals_list):
        default_code = self.default_get(["code"]).get("code")
        values = [dict(vals, code=vals.get("code", default_code)) for vals in vals_list]
        reserved = {vals["code"] for vals in values if isinstance(vals["code"], str)}
        sequence = self.env.ref("workflow_core.sequence_workflow_definition").sudo()
        templates = self.sudo().with_context(active_test=False)
        for vals in values:
            if vals["code"]:
                continue
            while True:
                code = sequence.next_by_id()
                if code not in reserved and not templates.search_count(
                    [("code", "=", code)],
                ):
                    vals["code"] = code
                    reserved.add(code)
                    break
        return values

    @api.model_create_multi
    def create(self, vals_list):
        require_group(self, "group_designer")
        if any(self._activation_fields() & vals.keys() for vals in vals_list):
            raise AccessError(self.env._("不能直接指定已发布版本。"))
        # 显式赋值覆盖 context default, 防止绕过公开 create 的版本保护。
        records = super().create(
            [
                dict(vals, **dict.fromkeys(self._activation_fields(), False))
                for vals in self._assign_codes(vals_list)
            ],
        )
        for record in records:
            self.env["workflow.version"].sudo().create(
                {"definition_id": record.id, "number": 1},
            )
        records._ensure_manager_access()
        return records

    def write(self, vals):
        self._check_manage()
        if self._activation_fields() & vals.keys():
            raise AccessError(self.env._("请通过发布操作切换有效版本。"))
        if {"model_id", "company_id"} & vals.keys() and any(
            record.version_ids.filtered(lambda v: v.state == "published")
            for record in self
        ):
            raise UserError(self.env._("已有发布版本, 不能更改业务模型或公司。"))
        result = super().write(vals)
        if "manager_id" in vals:
            self._ensure_manager_access()
        return result

    def unlink(self):
        if self.mapped("version_ids").filtered(lambda v: v.state == "published"):
            raise UserError(self.env._("已有发布版本的流程不能删除, 请归档。"))
        return super().unlink()

    def _activation_fields(self) -> set[str]:
        return {"published_version_id", "version_activated_by", "version_activated_at"}

    def _set_published_version(self, version) -> None:
        super(WorkflowDefinition, self.sudo()).write(
            {
                "published_version_id": version.id,
                "version_activated_by": self.env.uid,
                "version_activated_at": fields.Datetime.now(),
            },
        )

    def _designer_version(self):
        version = self.version_ids.sorted("number", reverse=True)[:1]
        if version.state == "published":
            return self.published_version_id or version
        return version

    @api.depends("published_version_id", "version_ids.state", "version_ids.revision")
    def _compute_canvas_preview(self) -> None:
        versions = {
            definition.id: definition._designer_version() for definition in self
        }
        version_ids = [version.id for version in versions.values() if version]
        for definition in self:
            version = versions[definition.id].with_prefetch(version_ids)
            definition.canvas_preview = {
                "nodes": [
                    {
                        "id": node.key,
                        "type": node.kind,
                        "label": node.name,
                        "position": node.position,
                        "color": node.background_color,
                    }
                    for node in version.node_ids
                ],
                "edges": [
                    {
                        "source": line.source_id.key,
                        "target": line.target_id.key,
                        "sourceHandle": line.source_handle or "right",
                        "targetHandle": line.target_handle or "left",
                    }
                    for line in version.edge_ids
                ],
            }

    def action_designer(self) -> dict:
        self.ensure_one()
        self.check_access("read")
        return self._designer_version().action_designer()

    def action_new_version(self) -> dict:
        self.ensure_one()
        self._check_manage()
        with self.env.cr.savepoint():
            lock_record(self)
            latest = self.version_ids.sorted("number", reverse=True)[:1]
            if latest.state == "draft":
                return latest.action_designer()
            version = (
                self.env["workflow.version"]
                .sudo()
                .create(
                    {
                        "definition_id": self.id,
                        "number": latest.number + 1,
                    },
                )
                .with_env(self.env)
            )
            source = self.published_version_id or latest
            version.save_graph(source.get_canvas()["graph"], 0)
            return version.action_designer()

    def _starter_department_allowed(self) -> bool:
        if not self.department_id:
            return True
        return bool(
            self.env["hr.employee"]
            .sudo()
            .with_context(active_test=True)
            .search_count(
                [
                    ("user_id", "=", self.env.uid),
                    ("company_id", "=", self.company_id.id),
                    ("department_id", "=", self.department_id.id),
                    ("department_id.active", "=", True),
                    ("department_id.company_id", "=", self.company_id.id),
                ],
                limit=1,
            ),
        )

    def action_start(
        self,
        res_id: int = 0,
        request_key: str = "",
        expected_version_id: int = 0,
    ) -> dict:
        self.ensure_one()
        self.check_access("read")
        require_group(self, "group_executor")
        if self.starter_group_ids and not (
            self.starter_group_ids & self.env.user.all_group_ids
        ):
            raise AccessError(self.env._("你不属于此流程允许启动的用户组。"))
        if not isinstance(request_key, str) or len(request_key) > 100:
            raise ValidationError(self.env._("请求标识格式不正确。"))
        if type(expected_version_id) is not int or expected_version_id < 0:
            raise ValidationError(self.env._("流程版本标识不正确。"))
        key = request_key or uuid.uuid4().hex
        with self.env.cr.savepoint():
            lock_record(self)
            if not self.active or not self.published_version_id:
                raise UserError(self.env._("流程尚未发布或已停用。"))
            if not self._starter_department_allowed():
                raise AccessError(self.env._("仅所属部门的在职员工可以发起此流程。"))
            record = business_record(self, res_id)
            instance = start_instance(self, record, key, expected_version_id)
            return instance.with_env(self.env).action_monitor()
