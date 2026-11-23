from odoo.tests import HttpCase, tagged

from .common import WorkflowCase


@tagged("post_install", "-at_install")
class TestDefinitionCode(WorkflowCase, HttpCase):
    def test_generated_codes_skip_archived_and_explicit_codes(self):
        templates = self.env["workflow.definition"].with_user(self.designer)
        sequence = self.env.ref("workflow_core.sequence_workflow_definition")
        next_number = sequence.number_next_actual
        existing_code = f"FLOW-{next_number}"
        manual_code = f"FLOW-{next_number + 1}"
        templates.create({"name": "旧模板", "code": existing_code, "active": False})
        first, manual, second = templates.create(
            [
                {"name": "自动一"},
                {"name": "手填", "code": manual_code},
                {"name": "自动二", "code": False},
            ],
        )
        self.assertEqual(first.code, f"FLOW-{next_number + 2}")
        self.assertEqual(manual.code, manual_code)
        self.assertEqual(second.code, f"FLOW-{next_number + 3}")
        self.assertEqual(first.copy().code, f"FLOW-{next_number + 4}")

    def test_form_saves_without_entering_a_code(self):
        self.browser_js(
            "/odoo/action-workflow_core.definitions",
            """
            (async () => {
                const wait = async check => {
                    for (let i = 0; i < 400; i++) {
                        const value = check();
                        if (value) return value;
                        await new Promise(resolve => setTimeout(resolve, 50));
                    }
                    throw new Error('Template form did not save with an automatic code');
                };
                (await wait(() => document.querySelector('.o_list_button_add'))).click();
                const name = await wait(() => document.querySelector('.o_field_widget[name=name] input'));
                name.value = '自动编码界面验收';
                name.dispatchEvent(new Event('input', { bubbles: true }));
                name.dispatchEvent(new Event('change', { bubbles: true }));
                (await wait(() => document.querySelector('.o_form_button_save'))).click();
                await wait(() => {
                    const field = document.querySelector('.o_field_widget[name=code]');
                    return /^FLOW-[0-9]+$/.test(field?.querySelector('input')?.value || field?.textContent.trim() || '');
                });
                console.log('test successful');
            })();
            """,
            login=self.designer.login,
            timeout=90,
        )
        template = self.env["workflow.definition"].search(
            [("name", "=", "自动编码界面验收")],
        )
        self.assertRegex(template.code, r"^FLOW-\d+$")
