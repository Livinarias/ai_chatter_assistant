# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Tests for security: ACLs, record rules, and groups."""

from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import AITestCase


@tagged("post_install", "-at_install")
class TestSecurity(AITestCase):
    """Integration tests for access control and record rules."""

    def test_group_ai_user_exists(self):
        """The group_ai_user security group is properly defined."""
        group = self.env.ref("ai_chatter_assistant.group_ai_user")
        self.assertTrue(group.exists())

    def test_ai_user_has_group(self):
        """The test AI user belongs to group_ai_user."""
        self.assertTrue(
            self.ai_user.has_group("ai_chatter_assistant.group_ai_user")
        )

    def test_non_ai_user_lacks_group(self):
        """The non-AI test user does not belong to group_ai_user."""
        self.assertFalse(
            self.non_ai_user.has_group("ai_chatter_assistant.group_ai_user")
        )

    def test_ai_user_inherits_internal_user(self):
        """group_ai_user implies base.group_user."""
        group = self.env.ref("ai_chatter_assistant.group_ai_user")
        internal = self.env.ref("base.group_user")
        self.assertIn(internal, group.implied_ids)

    def test_non_admin_cannot_read_ai_config_params(self):
        """Record rule hides ai_chatter_assistant.* params from non-admins."""
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("ai_chatter_assistant.ai_provider", "openai")

        # Switch to non-admin user
        ICP_user = self.env["ir.config_parameter"].with_user(self.ai_user)
        params = ICP_user.search(
            [("key", "like", "ai_chatter_assistant.%")]
        )
        # Record rule should filter these out
        self.assertFalse(
            params,
            "Non-admin users should not see ai_chatter_assistant.* params.",
        )

    def test_admin_can_read_ai_config_params(self):
        """Admins bypass record rules and can see AI params."""
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("ai_chatter_assistant.ai_provider", "openai")

        # Admin search — should find the param
        params = ICP.search(
            [("key", "=", "ai_chatter_assistant.ai_provider")]
        )
        self.assertTrue(params.exists())

    def test_ai_user_can_create_usage_log(self):
        """AI users have create access to ai.usage.log."""
        UsageLog = self.env["ai.usage.log"].with_user(self.ai_user)
        log = UsageLog.create(
            {
                "user_id": self.ai_user.id,
                "feature": "chatter_summary",
                "status": "success",
            }
        )
        self.assertTrue(log.exists())

    def test_ai_user_can_create_reply_wizard(self):
        """AI users can create and read the reply wizard."""
        Wizard = self.env["ai.reply.wizard"].with_user(self.ai_user)
        wiz = Wizard.create(
            {
                "source_model": "res.partner",
                "source_id": self.env.user.partner_id.id,
            }
        )
        self.assertTrue(wiz.exists())
