from werkzeug.exceptions import NotFound

from odoo import http
from odoo.addons.web.controllers.dataset import DataSet
from odoo.addons.web.controllers.home import Home

from ..app_access import apps_enabled, check_apps_access, is_app_model


class AppAccessHome(Home):
    @http.route()
    def web_client(self, s_action=None, **kw):
        if not apps_enabled() and "apps" in kw.get("subpath", "").split("/"):
            raise NotFound()
        return super().web_client(s_action=s_action, **kw)


class AppAccessDataSet(DataSet):
    @http.route()
    def call_kw(self, model, method, args, kwargs, path=None):
        if is_app_model(model):
            check_apps_access()
        return super().call_kw(model, method, args, kwargs, path=path)

    @http.route()
    def call_button(self, model, method, args, kwargs, path=None):
        if is_app_model(model):
            check_apps_access()
        return super().call_button(model, method, args, kwargs, path=path)
