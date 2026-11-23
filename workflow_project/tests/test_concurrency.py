import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from odoo.tests import TransactionCase, tagged

from .common import project_graph
from odoo.addons.workflow_core.tests import test_concurrency as core_concurrency
from odoo.addons.workflow_core.tests.common import purge_workflow


@tagged("post_install", "-at_install")
class TestProjectConcurrency(TransactionCase):
    _transaction = core_concurrency.TestConcurrency._transaction

    def test_workflow_and_native_completion_race_advances_once(self):
        def setup(env):
            project = env["project.project"].create(
                {"name": "Race project", "company_id": env.company.id},
            )
            definition = env["workflow.definition"].create(
                {"name": "Project race", "code": uuid.uuid4().hex},
            )
            version = definition.version_ids
            version.save_graph(project_graph(project.id, [2]), 0)
            version.action_publish(1)
            instance_id = definition.action_start()["params"]["instance_id"]
            link = env["workflow.project.link"].search(
                [("instance_id", "=", instance_id)],
            )
            return definition.id, project.id, link.id, link.project_task_id.id

        definition_id, project_id, link_id, task_id = self._transaction(setup)
        try:
            barrier = Barrier(2)

            def complete(native):
                barrier.wait(timeout=10)
                return self._transaction(
                    lambda env: (
                        env["project.task"].browse(task_id).write({"state": "1_done"})
                        if native
                        else env["workflow.project.link"]
                        .browse(link_id)
                        .action_decide("complete")
                    ),
                )

            with ThreadPoolExecutor(max_workers=2) as pool:
                self.assertEqual(list(pool.map(complete, [False, True])), [True, True])

            def verify(env):
                link = env["workflow.project.link"].browse(link_id)
                self.assertEqual(link.state, "done")
                self.assertEqual(link.project_task_id.state, "1_done")
                self.assertEqual(len(link.instance_id.task_ids), 1)
                self.assertEqual(
                    len(
                        link.instance_id.log_ids.filtered(
                            lambda log: log.event == "project_task_completed",
                        ),
                    ),
                    1,
                )

            self._transaction(verify)
        finally:

            def cleanup(env):
                env.cr.execute(
                    "DELETE FROM abt_workflow_project_link WHERE id = %s",
                    [link_id],
                )
                purge_workflow(env.cr, definition_id)
                env["project.task"].browse(task_id).unlink()
                env["project.project"].browse(project_id).unlink()

            self._transaction(cleanup)
