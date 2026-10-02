# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Tests for the ai.usage.log TransientModel."""

from odoo.tests import tagged

from .common import AITestCase


@tagged("post_install", "-at_install")
class TestUsageLog(AITestCase):
    """Integration tests for ai.usage.log model."""

    def test_create_success_entry(self):
        """A success log entry is created with correct fields."""
        UsageLog = self.env["ai.usage.log"].sudo()
        UsageLog._log_usage(
            user=self.ai_user,
            feature="chatter_summary",
            status="success",
            tokens_used=150,
        )
        log = UsageLog.search([("user_id", "=", self.ai_user.id)], limit=1)
        self.assertTrue(log.exists())
        self.assertEqual(log.feature, "chatter_summary")
        self.assertEqual(log.status, "success")
        self.assertEqual(log.tokens_used, 150)

    def test_create_error_entry(self):
        """An error log entry includes the error message."""
        UsageLog = self.env["ai.usage.log"].sudo()
        UsageLog._log_usage(
            user=self.ai_user,
            feature="reply_draft",
            status="error",
            error_message="API key invalid",
        )
        log = UsageLog.search(
            [
                ("user_id", "=", self.ai_user.id),
                ("status", "=", "error"),
            ],
            limit=1,
        )
        self.assertTrue(log.exists())
        self.assertEqual(log.error_message, "API key invalid")

    def test_transient_max_hours(self):
        """The model has a 30-day TTL configured."""
        self.assertEqual(
            self.env["ai.usage.log"]._transient_max_hours,
            24 * 30,
        )

    def test_provider_field_populated(self):
        """The provider field is read from ir.config_parameter."""
        self._setup_ai_config(provider="anthropic")
        UsageLog = self.env["ai.usage.log"].sudo()
        UsageLog._log_usage(
            user=self.ai_user,
            feature="lead_generation",
            status="success",
        )
        log = UsageLog.search([("user_id", "=", self.ai_user.id)], limit=1)
        self.assertEqual(log.provider, "anthropic")

    def test_all_features_valid(self):
        """All selection keys for 'feature' are accepted."""
        UsageLog = self.env["ai.usage.log"].sudo()
        for feature in (
            "chatter_summary",
            "reply_draft",
            "lead_generation",
            "connection_test",
        ):
            log = UsageLog.create(
                {
                    "user_id": self.ai_user.id,
                    "feature": feature,
                    "status": "success",
                }
            )
            self.assertEqual(log.feature, feature)
