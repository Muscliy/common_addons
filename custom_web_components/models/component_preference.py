import json
import re

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


class ComponentPreference(models.Model):
    _name = 'web.component.preference'
    _description = 'Web Component User Preference'
    _table = 'abt_web_component_preference'
    _rec_name = 'scope'

    user_id = fields.Many2one('res.users', required=True, default=lambda self: self.env.user, ondelete='cascade', index=True)
    component_type = fields.Char(required=True, index=True)
    view_id = fields.Many2one('ir.ui.view', ondelete='cascade', index=True)
    model = fields.Char(required=True)
    key = fields.Char(required=True, default='default')
    config = fields.Json(default=dict)
    scope = fields.Char(compute='_compute_scope', store=True, precompute=True, required=True)

    _user_scope_unique = models.Constraint(
        'unique(user_id, scope)',
        'This component already has a preference for this user.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        if 'default_scope' in self.env.context:
            raise ValidationError(self.env._('Component scope is computed automatically.'))
        for values in vals_list:
            if 'config' in values and not isinstance(values['config'], dict):
                raise ValidationError(self.env._('Component configuration must be an object.'))
            if not self.env.su and values.get('user_id', self.env.uid) != self.env.uid:
                raise AccessError(self.env._('You can only create your own component preferences.'))
            if 'scope' in values:
                raise ValidationError(self.env._('Component scope is computed automatically.'))
        return super().create(vals_list)

    def write(self, values):
        if 'config' in values and not isinstance(values['config'], dict):
            raise ValidationError(self.env._('Component configuration must be an object.'))
        if not self.env.su and 'user_id' in values and values['user_id'] != self.env.uid:
            raise AccessError(self.env._('You cannot transfer component preferences to another user.'))
        if 'scope' in values:
            raise ValidationError(self.env._('Component scope is computed automatically.'))
        return super().write(values)

    @api.depends('component_type', 'view_id', 'model', 'key')
    def _compute_scope(self):
        for record in self:
            record.scope = json.dumps([record.component_type, record.view_id.id or 0, record.model, record.key])

    @api.constrains('component_type', 'view_id', 'model', 'key', 'config', 'scope')
    def _check_preference(self):
        for record in self:
            expected_scope = json.dumps([record.component_type, record.view_id.id or 0, record.model, record.key])
            if record.scope != expected_scope:
                raise ValidationError(self.env._('Component scope is computed automatically.'))
            for value in (record.component_type, record.model, record.key):
                if not value or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', value):
                    raise ValidationError(self.env._('Invalid component scope.'))
            if record.model not in self.env:
                raise ValidationError(self.env._('Unknown component model.'))
            # Internal users cannot read ir.ui.view directly; inspect only validation metadata.
            view = record.view_id.sudo()
            if record.component_type == 'list_nested':
                record._check_nested_scope(view)
            elif view and view.model != record.model:
                raise ValidationError(self.env._('The view does not belong to this model.'))
            if record.component_type == 'list' and (not view or view.type != 'list'):
                raise ValidationError(self.env._('List preferences require a saved list view.'))
            if record.config and not isinstance(record.config, dict):
                raise ValidationError(self.env._('Component configuration must be an object.'))
            try:
                encoded = json.dumps(record.config, allow_nan=False)
            except (TypeError, ValueError) as exc:
                raise ValidationError(self.env._('Invalid JSON configuration.')) from exc
            if len(encoded.encode()) > 65536:
                raise ValidationError(self.env._('Component configuration is too large.'))
            if record.component_type in ('list', 'list_nested'):
                record._check_list_config()

    def _check_nested_scope(self, view):
        if not view or not self.key.startswith('x2many:'):
            raise ValidationError(self.env._('Detail list preferences require a parent view and field path.'))
        parent_model = view.model
        for name in self.key.removeprefix('x2many:').split('.'):
            field = self.env[parent_model]._fields.get(name) if parent_model in self.env else None
            if not field or field.type not in ('one2many', 'many2many'):
                raise ValidationError(self.env._('Invalid detail list field path.'))
            parent_model = field.comodel_name
        if parent_model != self.model:
            raise ValidationError(self.env._('The detail field does not belong to this model.'))

    def _check_list_config(self):
        for name, options in (self.config or {}).items():
            if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]{0,127}', name) or not isinstance(options, dict):
                raise ValidationError(self.env._('Invalid list column configuration.'))
            if set(options) - {'sequence', 'width', 'visible', 'frozen'}:
                raise ValidationError(self.env._('Unknown list column option.'))
            for key, maximum, minimum in [('sequence', 10000, 0), ('width', 4000, 10)]:
                if key in options and (type(options[key]) is not int or not minimum <= options[key] <= maximum):
                    raise ValidationError(self.env._('Invalid column sequence or width.'))
            for key in ('visible', 'frozen'):
                if key in options and type(options[key]) is not bool:
                    raise ValidationError(self.env._('Reserved column flags must be boolean.'))

    @api.model
    def _scope_domain(self, component_type, model, view_id=False, key='default'):
        self.check_access('read')
        return [('user_id', '=', self.env.uid), ('component_type', '=', component_type),
                ('model', '=', model), ('view_id', '=', view_id), ('key', '=', key)]

    @api.model
    def get_preference(self, component_type, model, view_id=False, key='default'):
        record = self.search(self._scope_domain(component_type, model, view_id, key), limit=1)
        return record.config or {}

    @api.model
    def save_preference(self, component_type, model, view_id=False, key='default', config=None):
        domain = self._scope_domain(component_type, model, view_id, key)
        record = self.search(domain, limit=1)
        if record:
            record.write({'config': config})
        else:
            self.create({'user_id': self.env.uid, 'component_type': component_type,
                         'model': model, 'view_id': view_id, 'key': key, 'config': config})
        return True

    @api.model
    def reset_preference(self, component_type, model, view_id=False, key='default'):
        self.search(self._scope_domain(component_type, model, view_id, key)).unlink()
        return True
