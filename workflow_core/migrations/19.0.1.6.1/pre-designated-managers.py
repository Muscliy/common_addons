def migrate(cr, version):
    # Preserve ownership of legacy templates before the required field is initialized.
    cr.execute("ALTER TABLE abt_workflow_definition ADD COLUMN IF NOT EXISTS manager_id integer")
    cr.execute("""
        UPDATE abt_workflow_definition AS template
           SET manager_id = creator.id
          FROM res_users AS creator
         WHERE template.manager_id IS NULL
           AND template.create_uid = creator.id
           AND creator.active AND NOT creator.share
    """)
    cr.execute("""
        UPDATE abt_workflow_definition
           SET manager_id = (
               SELECT res_id FROM ir_model_data
                WHERE module = 'base' AND name = 'user_admin' AND model = 'res.users'
           )
         WHERE manager_id IS NULL
    """)
