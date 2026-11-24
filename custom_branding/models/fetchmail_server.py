import imaplib

from odoo import models


# Python's imaplib does not include RFC 2971's ID command in its command table.
imaplib.Commands.setdefault("ID", ("AUTH",))


class FetchmailServer(models.Model):
    _inherit = "fetchmail.server"

    def _imap_login(self, connection):
        super()._imap_login(connection)
        if (self.server or "").lower() not in {
            "imap.126.com",
            "imap.163.com",
            "imap.yeah.net",
        }:
            return

        connection.__obj__._simple_command(
            "ID",
            '("name" "Odoo" "version" "18.0" "vendor" "tyh")',
        )
