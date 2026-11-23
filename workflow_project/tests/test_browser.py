from odoo.tests import HttpCase, tagged

from .common import ProjectCase


@tagged("post_install", "-at_install")
class TestProjectBrowser(ProjectCase, HttpCase):
    def test_native_task_open_complete_and_return_to_workflow(self):
        instance, link = self.begin()
        action = self.env["ir.actions.client"].create(
            {
                "name": "Project workflow browser",
                "tag": "workflow_core.canvas",
                "params": {"instance_id": instance.id},
            },
        )
        self.browser_js(
            f"/web?action={action.id}",
            r"""
            (async () => {
                const wait=async predicate=>{const end=Date.now()+20000;while(!predicate()){
                    if(Date.now()>end)throw new Error('Project UI timeout: '+document.body.innerText);
                    await new Promise(resolve=>setTimeout(resolve,50));}};
                const button=text=>[...document.querySelectorAll('button')].find(el=>el.textContent.trim()===text);
                await wait(()=>button('打开项目任务'));
                button('打开项目任务').click();
                await wait(()=>document.querySelector('button[name="action_workflow_monitor"]'));
                if(!document.querySelector('.o_form_view'))throw new Error('Native Project form missing');
                document.querySelector('button[name="action_workflow_monitor"]').click();
                await wait(()=>button('完成项目任务'));
                button('完成项目任务').click();
                await wait(()=>document.querySelector('[data-id="after"]')?.textContent.includes('等待办理')&&!button('完成项目任务'));
                if(document.querySelector('.o_workflow_action [role=alert]'))throw new Error('Project completion failed');
                console.log('test successful');
            })();
        """,
            login=self.other.login,
            timeout=90,
        )
        self.env.invalidate_all()
        self.assertEqual(link.state, "done")
        self.assertEqual(link.project_task_id.state, "1_done")
        self.assertEqual(len(instance.task_ids), 1)
