import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from odoo.sql_db import db_connect
from odoo.tests import TransactionCase, tagged

from . import test_concurrency as core_concurrency
from .common import parallel_graph, purge_workflow


@tagged("post_install", "-at_install")
class TestParallelConcurrency(TransactionCase):
    _transaction = core_concurrency.TestConcurrency._transaction

    def test_two_branches_finishing_together_create_one_successor(self):
        def setup(env):
            definition = env["workflow.definition"].create(
                {
                    "name": "Concurrent parallel join",
                    "code": uuid.uuid4().hex,
                },
            )
            version = definition.version_ids
            version.save_graph(parallel_graph(2), 0)
            version.action_publish(1)
            instance_id = definition.action_start()["params"]["instance_id"]
            return (
                definition.id,
                instance_id,
                env["workflow.instance"].browse(instance_id).task_ids.ids,
            )

        definition_id, instance_id, tasks = self._transaction(setup)
        try:
            barrier = Barrier(2)

            def complete(task_id):
                barrier.wait(timeout=10)
                return self._transaction(
                    lambda env: env["workflow.task"].browse(task_id).action_complete(),
                )

            with ThreadPoolExecutor(max_workers=2) as pool:
                self.assertEqual(list(pool.map(complete, tasks)), [True, True])

            def verify(env):
                instance = env["workflow.instance"].browse(instance_id)
                self.assertEqual(instance.state, "running")
                self.assertEqual(len(instance.task_ids), 3)
                self.assertEqual(
                    len(instance.task_ids.filtered(lambda t: t.state == "pending")),
                    1,
                )
                self.assertEqual(
                    len(
                        instance.node_instance_ids.filtered(
                            lambda a: a.node_id.kind == "join",
                        ),
                    ),
                    1,
                )
                self.assertEqual(
                    len(
                        instance.log_ids.filtered(
                            lambda log: log.event == "parallel_joined",
                        ),
                    ),
                    1,
                )
                for task_id in tasks:
                    env["workflow.task"].browse(task_id).action_complete("retry")
                self.assertEqual(len(instance.task_ids), 3)
                instance.task_ids.filtered(
                    lambda t: t.state == "pending",
                ).action_complete()
                self.assertEqual(instance.state, "done")

            self._transaction(verify)
        finally:
            with db_connect(self.cr.dbname).cursor() as cr:
                purge_workflow(cr, definition_id)
                cr.commit()
