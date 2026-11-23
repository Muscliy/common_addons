from contextlib import contextmanager
from contextvars import ContextVar

from odoo.exceptions import AccessError

_active = ContextVar("workflow_approval_write", default=frozenset())


def _key(activation) -> tuple:
    return activation.env.cr.dbname, id(activation.env.cr), activation.id


@contextmanager
def approval_scope(activation):
    """Python-only capability bound to this activation and database transaction."""
    token = _active.set(_active.get() | {_key(activation)})
    try:
        yield
    finally:
        _active.reset(token)


def require_scope(approvals) -> None:
    for approval in approvals.sudo():
        if _key(approval.node_instance_id) not in _active.get():
            raise AccessError(
                approval.env._("审批数据只能通过授权的工作流审批操作修改。"),
            )


def require_activation(activation) -> None:
    if not activation or _key(activation) not in _active.get():
        raise AccessError(activation.env._("不能直接创建审批记录。"))
