from odoo.exceptions import AccessError, UserError
from odoo.tools import SQL


def require_group(records, group: str) -> None:
    if not records.env.user.has_group(f"workflow_core.{group}"):
        raise AccessError(records.env._("没有执行此操作的工作流权限。"))


def lock_record(record) -> None:
    """锁定顺序由调用者保证。不跳过锁, 冲突交由 Odoo 事务重试。"""
    record.ensure_one()
    record.flush_recordset()
    # REPEATABLE READ 下只锁不写不能刷新快照, 等锁请求可能看不到新实例。
    # 无值变化的 UPDATE 产生 MVCC 冲突, 让 Odoo 重新开启事务判断幂等键。
    record.env.cr.execute(
        SQL(
            "UPDATE %s SET write_date = write_date WHERE id = %s RETURNING id",
            SQL.identifier(record._table),
            record.id,
        ),
    )
    if not record.env.cr.fetchone():
        raise UserError(record.env._("记录已不存在, 请刷新。"))
    record.invalidate_recordset()


def require_internal_write(records) -> None:
    if not records.env.su:
        raise AccessError(records.env._("运行数据只能通过已授权的工作流操作修改。"))


def business_record(definition, res_id: int):
    """只允许经流程配置授权的模型, 使用原调用者检查记录和公司。"""
    if not definition.model_id:
        if res_id:
            raise UserError(definition.env._("此流程未配置业务模型。"))
        return None
    if type(res_id) is not int or res_id <= 0:
        raise UserError(definition.env._("请选择有效的业务记录。"))
    model = definition.model_id.sudo().model
    if model not in definition._allowed_business_models():
        raise AccessError(definition.env._("业务模型未注册。"))
    record = definition.env[model].browse(res_id).exists()
    if not record:
        raise UserError(definition.env._("业务记录已不存在。"))
    record.check_access("read")
    if (
        "company_id" in record._fields
        and record.company_id
        and record.company_id != definition.company_id
    ):
        raise AccessError(definition.env._("业务记录与流程必须属于同一公司。"))
    return record
