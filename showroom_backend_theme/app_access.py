"""Server-owned policy; never infer deployment mode from request parameters."""
import os

from odoo import _
from odoo.exceptions import AccessError


def apps_enabled():
    return os.environ.get("TYH_RUNTIME") == "local"


def check_apps_access():
    if not apps_enabled():
        raise AccessError(_("应用管理仅在本地启动时开放，服务器部署环境请通过运维命令安装应用。"))


def is_app_model(model):
    return model.startswith(("ir.module.", "base.module.", "base.import.module"))
