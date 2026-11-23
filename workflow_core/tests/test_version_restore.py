from odoo.exceptions import AccessError, UserError
from odoo.tests import HttpCase, tagged

from .common import WorkflowCase


@tagged("post_install", "-at_install")
class TestVersionRestore(WorkflowCase, HttpCase):
    def setUp(self):
        super().setUp()
        self.template = self.published()
        self.old = self.template.published_version_id
        action = self.template.action_new_version()
        self.new = self.env["workflow.version"].browse(action["params"]["version_id"])
        graph = self.new.get_canvas()["graph"]
        graph["nodes"][1]["data"]["label"] = "新版任务"
        self.new.with_user(self.manager).save_graph(graph, 1)
        self.new.with_user(self.publisher).action_publish(2)

    def test_restore_preserves_instances_and_frozen_versions(self):
        initial = self.instance(self.template, key="before")
        graph = self.old.get_canvas()["graph"]
        published = self.old.published_at
        self.old.with_user(self.publisher).action_restore()
        self.assertEqual(self.template.published_version_id, self.old)
        self.assertEqual(self.template.version_activated_by, self.publisher)
        self.assertEqual(
            self.template.action_designer()["params"]["version_id"],
            self.old.id,
        )
        self.assertTrue(self.old.is_current)
        self.assertFalse(self.new.is_current)
        self.assertEqual(self.old.get_canvas()["graph"], graph)
        self.assertEqual(self.old.published_at, published)
        self.assertEqual(initial.version_id, self.new)
        self.assertEqual(initial.task_ids.name, "新版任务")
        self.assertEqual(self.instance(self.template, key="after").version_id, self.old)
        activated_at = self.template.version_activated_at
        self.old.with_user(self.publisher).action_restore()
        self.assertEqual(self.template.version_activated_at, activated_at)
        action = self.template.action_new_version()
        draft = self.env["workflow.version"].browse(action["params"]["version_id"])
        self.assertEqual(draft.number, 3)
        self.assertEqual(draft.get_canvas()["graph"], graph)

    def test_restore_permissions_and_stale_canvas_start(self):
        template = self.template.with_user(self.worker)
        action = template.action_start(0, "same", self.new.id)
        with self.assertRaises(AccessError):
            self.old.with_user(self.designer).action_restore()
        self.old.with_user(self.publisher).action_restore()
        with self.assertRaises(UserError):
            template.action_start(0, "stale", self.new.id)
        self.assertEqual(template.action_start(0, "same", self.new.id), action)
        draft_id = self.template.action_new_version()["params"]["version_id"]
        with self.assertRaises(UserError):
            self.env["workflow.version"].browse(draft_id).with_user(
                self.publisher,
            ).action_restore()
        self.assertEqual(self.template.published_version_id, self.old)
        with self.assertRaises(AccessError):
            self.template.write({"version_activated_by": self.worker.id})

    def test_restore_from_template_form(self):
        self.browser_js(
            f"/odoo/action-workflow_core.definitions/{self.template.id}",
            """
            (async () => {
                const wait = async (find) => {
                    for (let i = 0; i < 400; i++) {
                        const found = find();
                        if (found) return found;
                        await new Promise(resolve => setTimeout(resolve, 50));
                    }
                    throw new Error('Version restore control did not update');
                };
                const button = () => document.querySelector('button[name=action_restore]');
                (await wait(button)).click();
                (await wait(() => document.querySelector('.modal button.btn-primary'))).click();
                await wait(() => button()?.closest('tr')?.querySelector('[name=number]')?.textContent.trim() === '2');
                console.log('test successful');
            })();
            """,
            login=self.publisher.login,
            timeout=90,
        )
        self.env.invalidate_all()
        self.assertEqual(self.template.published_version_id, self.old)
