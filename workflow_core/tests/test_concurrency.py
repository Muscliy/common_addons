import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from psycopg2.errors import SerializationFailure

from odoo import api
from odoo.orm.environments import Transaction
from odoo.sql_db import db_connect
from odoo.tests import TransactionCase, tagged

from .common import purge_workflow, sequential


@tagged("post_install", "-at_install")
class TestConcurrency(TransactionCase):
    def _transaction(self, operation):
        # 使用独立连接和真正提交, 不复用 TransactionCase 的测试游标。
        for _attempt in range(5):
            try:
                with db_connect(self.cr.dbname).cursor() as cr:
                    # post_install 期间主线程持有 registry 加载锁。复用已经加载的
                    # registry, 但每个连接拥有独立 Transaction/cache, 不复用测试游标。
                    cr.transaction = Transaction(self.registry)
                    env = api.Environment(cr, 2, {})
                    result = operation(env)
                    cr.commit()
                    return result
            except SerializationFailure:
                continue
        message = "Concurrent operation exceeded serialization retries"
        raise AssertionError(message)

    def test_same_request_and_same_task_are_processed_once(self):
        def setup(env):
            definition = env["workflow.definition"].create(
                {"name": "Concurrent workflow", "code": uuid.uuid4().hex},
            )
            version = definition.version_ids
            version.save_graph(sequential(2), 0)
            version.action_publish(1)
            return definition.id

        definition_id = self._transaction(setup)
        try:
            barrier = Barrier(2)

            def start():
                barrier.wait(timeout=10)
                return self._transaction(
                    lambda env: (
                        env["workflow.definition"]
                        .browse(definition_id)
                        .action_start(0, "same-request")["params"]["instance_id"]
                    ),
                )

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: start(), range(2)))
            self.assertEqual(results[0], results[1])
            instance_id = results[0]
            task_id = self._transaction(
                lambda env: env["workflow.instance"].browse(instance_id).task_ids.id,
            )
            barrier = Barrier(2)

            def complete():
                barrier.wait(timeout=10)
                return self._transaction(
                    lambda env: env["workflow.task"].browse(task_id).action_complete(),
                )

            with ThreadPoolExecutor(max_workers=2) as pool:
                self.assertEqual(
                    list(pool.map(lambda _: complete(), range(2))),
                    [True, True],
                )

            def verify(env):
                instance = env["workflow.instance"].browse(instance_id)
                self.assertEqual(instance.state, "done")
                self.assertEqual(len(instance.task_ids), 1)
                self.assertEqual(len(instance.node_instance_ids), 3)
                self.assertEqual(
                    len(
                        instance.log_ids.filtered(
                            lambda log: log.event == "task_completed",
                        ),
                    ),
                    1,
                )
                self.assertEqual(
                    env["workflow.instance"].search_count(
                        [("definition_id", "=", definition_id)],
                    ),
                    1,
                )

            self._transaction(verify)
        finally:
            # 只清除本测试自己提交的记录, 保留普通用户不可删除审计的契约。
            with db_connect(self.cr.dbname).cursor() as cr:
                purge_workflow(cr, definition_id)
                cr.commit()
