import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, new_test_user, tagged
from odoo.tools import SQL

from .common import approval_graph
from odoo.addons.workflow_core.tests import test_concurrency as core_concurrency


@tagged("post_install", "-at_install")
class TestApprovalConcurrency(TransactionCase):
    _transaction = core_concurrency.TestConcurrency._transaction

    def test_competing_candidates_advance_only_once(self):
        def setup(env):
            user = new_test_user(
                env(context={"no_reset_password": True}),
                login=f"approval_race_{uuid.uuid4().hex}",
                groups="workflow_tier_validation.group_approver",
            )
            group = env["res.groups"].create(
                {
                    "name": f"Approval race {uuid.uuid4().hex}",
                    "user_ids": [Command.set([env.uid, user.id])],
                },
            )
            definition = env["workflow.definition"].create(
                {
                    "name": "Concurrent approval",
                    "code": uuid.uuid4().hex,
                },
            )
            version = definition.version_ids
            version.save_graph(
                approval_graph([{"kind": "group", "ref": group.id}], env.uid),
                0,
            )
            version.action_publish(1)
            instance_id = definition.action_start()["params"]["instance_id"]
            approval = env["workflow.approval"].search(
                [("instance_id", "=", instance_id)],
            )
            return definition.id, user.id, group.id, approval.id, approval.review_ids.id

        definition_id, user_id, group_id, approval_id, review_id = self._transaction(
            setup,
        )
        try:
            barrier = Barrier(2)

            def decide(uid):
                barrier.wait(timeout=10)
                try:
                    self._transaction(
                        lambda env: (
                            env["workflow.approval"]
                            .with_user(uid)
                            .browse(
                                approval_id,
                            )
                            .action_decide("approve", "concurrent", review_id)
                        ),
                    )
                    return True
                except UserError:
                    return False

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(decide, [2, user_id]))
            self.assertEqual(sorted(results), [False, True])

            def verify(env):
                approval = env["workflow.approval"].browse(approval_id)
                instance = approval.instance_id
                self.assertEqual(approval.state, "approved")
                self.assertEqual(len(instance.task_ids), 1)
                self.assertEqual(
                    len(
                        instance.log_ids.filtered(
                            lambda log: log.event == "approval_approved",
                        ),
                    ),
                    1,
                )
                # A committed duplicate from the winner is idempotent as well.
                approval.with_user(approval.review_ids.done_by).action_decide(
                    "approve",
                    "retry",
                    review_id,
                )
                self.assertEqual(approval.review_ids.comment, "concurrent")

            self._transaction(verify)
        finally:
            self._transaction(
                lambda env: self._cleanup(env, definition_id, user_id, group_id),
            )

    def _cleanup(self, env, definition_id, user_id, group_id):
        # Only the exact fixture committed by this test is removed; runtime APIs stay append-only.
        cr = env.cr
        cr.execute(
            "DELETE FROM tier_review WHERE workflow_approval_id IN "
            "(SELECT id FROM abt_workflow_approval WHERE instance_id IN "
            "(SELECT id FROM abt_workflow_instance WHERE definition_id = %s))",
            [definition_id],
        )
        cr.execute(
            "DELETE FROM tier_definition WHERE workflow_approval_id IN "
            "(SELECT id FROM abt_workflow_approval WHERE instance_id IN "
            "(SELECT id FROM abt_workflow_instance WHERE definition_id = %s))",
            [definition_id],
        )
        for table in (
            "abt_workflow_approval",
            "abt_workflow_execution_log",
            "abt_workflow_task",
            "abt_workflow_node_instance",
        ):
            cr.execute(
                SQL(
                    "DELETE FROM %s WHERE instance_id IN "
                    "(SELECT id FROM abt_workflow_instance WHERE definition_id = %s)",
                    SQL.identifier(table),
                    definition_id,
                ),
            )
        cr.execute(
            "DELETE FROM abt_workflow_instance WHERE definition_id = %s",
            [definition_id],
        )
        cr.execute(
            "UPDATE abt_workflow_definition SET published_version_id = NULL WHERE id = %s",
            [definition_id],
        )
        for table in ("abt_workflow_edge", "abt_workflow_node"):
            cr.execute(
                SQL(
                    "DELETE FROM %s WHERE version_id IN "
                    "(SELECT id FROM abt_workflow_version WHERE definition_id = %s)",
                    SQL.identifier(table),
                    definition_id,
                ),
            )
        cr.execute(
            "DELETE FROM abt_workflow_version WHERE definition_id = %s",
            [definition_id],
        )
        cr.execute("DELETE FROM abt_workflow_definition WHERE id = %s", [definition_id])
        env["res.groups"].browse(group_id).unlink()
        env["res.users"].browse(user_id).unlink()
