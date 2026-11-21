from datetime import timedelta

from odoo import api, fields, models

from .access import check_playground_access


class PlaygroundOrder(models.Model):
    _name = 'web.component.playground.order'
    _description = 'Component Playground Demo Order'
    _table = 'abt_web_component_playground_order'
    _order = 'name'

    name = fields.Char('订单号', required=True)
    user_id = fields.Many2one('res.users', required=True, default=lambda self: self.env.user, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', '客户', default=lambda self: self.env.user.partner_id)
    order_date = fields.Date('订单日期', default=fields.Date.context_today)
    salesperson_id = fields.Many2one('res.users', '销售员', default=lambda self: self.env.user)
    state = fields.Selection([('draft', '草稿'), ('confirmed', '已确认'), ('done', '已完成')], default='draft', string='状态')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    amount = fields.Monetary('金额')
    note = fields.Text('备注')

    def check_access(self, operation):
        check_playground_access(self.env)
        return super().check_access(operation)

    def _check_access(self, operation):
        # OCB 19 checks this hook for searches and record operations.  The
        # public check_access override alone is bypassed by some ORM paths.
        if not self.env.su:
            check_playground_access(self.env)
        return super()._check_access(operation)

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, *, active_test=True, bypass_access=False):
        check_playground_access(self.env)
        return super()._search(
            domain, offset=offset, limit=limit, order=order,
            active_test=active_test, bypass_access=bypass_access,
        )

    def read(self, fields=None, load='_classic_read'):
        check_playground_access(self.env)
        return super().read(fields, load=load)

    def export_data(self, fields_to_export):
        check_playground_access(self.env)
        return super().export_data(fields_to_export)

    @api.model
    def get_views(self, views, options=None):
        check_playground_access(self.env)
        return super().get_views(views, options)

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        check_playground_access(self.env)
        return super().get_view(view_id, view_type, **options)

    @api.model
    def open_playground(self):
        check_playground_access(self.env)
        if not self.search_count([]):
            today = fields.Date.context_today(self)
            self.create([{
                'name': f'DEMO-{index:04d}',
                'order_date': today - timedelta(days=index),
                'state': ('draft', 'confirmed', 'done')[index % 3],
                'amount': 123.45 * index,
                'note': '仅用于本地组件验证：可编辑、分页、排序、分组和切换可选字段。' * (1 + index % 3),
            } for index in range(1, 41)])
        # Return only this fixed action's safe metadata after checking the original user.
        # The project theme also inspects action fields before the core sudo metadata read.
        return self.env['ir.actions.actions'].sudo()._for_xml_id('custom_web_components.action_playground_list')
