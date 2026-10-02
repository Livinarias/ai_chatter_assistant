# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Tests for rate limiting logic in ai.usage.log."""

from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import AITestCase, MOCK_OPENAI_RESPONSE, _make_mock_response


@tagged("post_install", "-at_install")
class TestRateLimiting(AITestCase):
    """Integration tests for per-user rate limiting."""

    def setUp(self):
        super().setUp()
        self._setup_ai_config()

    def _create_log_entries(self, user, count, feature="chatter_summary"):
        """Create *count* success log entries for *user*."""
        UsageLog = self.env["ai.usage.log"].sudo()
        for _ in range(count):
            UsageLog.create(
                {
                    "user_id": user.id,
                    "feature": feature,
                    "status": "success",
                }
            )

    def test_under_limit_not_rate_limited(self):
        """User with fewer calls than the limit is not blocked."""
        self._create_log_entries(self.ai_user, 10)
        UsageLog = self.env["ai.usage.log"].sudo()
        self.assertFalse(
            UsageLog._is_rate_limited(self.ai_user, "chatter_summary")
        )

    def test_at_limit_is_rate_limited(self):
        """User with exactly the limit number of calls is blocked."""
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("ai_chatter_assistant.ai_rate_limit_per_hour", "5")
        self._create_log_entries(self.ai_user, 5)

        UsageLog = self.env["ai.usage.log"].sudo()
        self.assertTrue(
            UsageLog._is_rate_limited(self.ai_user, "chatter_summary")
        )

    def test_zero_limit_means_unlimited(self):
        """Setting rate limit to 0 disables rate limiting."""
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("ai_chatter_assistant.ai_rate_limit_per_hour", "0")
        self._create_log_entries(self.ai_user, 1000)

        UsageLog = self.env["ai.usage.log"].sudo()
        self.assertFalse(
            UsageLog._is_rate_limited(self.ai_user, "chatter_summary")
        )

    def test_error_entries_not_counted(self):
        """Error log entries should not count toward the rate limit."""
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("ai_chatter_assistant.ai_rate_limit_per_hour", "5")

        UsageLog = self.env["ai.usage.log"].sudo()
        for _ in range(10):
            UsageLog.create(
                {
                    "user_id": self.ai_user.id,
                    "feature": "chatter_summary",
                    "status": "error",
                    "error_message": "test error",
                }
            )
        # Only success entries count, so still not limited
        self.assertFalse(
            UsageLog._is_rate_limited(self.ai_user, "chatter_summary")
        )

    def test_old_entries_not_counted(self):
        """Entries older than 1 hour should not count."""
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("ai_chatter_assistant.ai_rate_limit_per_hour", "5")

        UsageLog = self.env["ai.usage.log"].sudo()
        old_time = fields.Datetime.now() - timedelta(hours=2)
        for _ in range(10):
            log = UsageLog.create(
                {
                    "user_id": self.ai_user.id,
                    "feature": "chatter_summary",
                    "status": "success",
                }
            )
            # Force old timestamp
            log.write({"timestamp": old_time})

        self.assertFalse(
            UsageLog._is_rate_limited(self.ai_user, "chatter_summary")
        )

    def test_different_users_independent(self):
        """Rate limits are per-user, not global."""
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("ai_chatter_assistant.ai_rate_limit_per_hour", "5")
        self._create_log_entries(self.ai_user, 5)

        # Give the non-ai user the group temporarily for this test
        non_ai = self.non_ai_user
        UsageLog = self.env["ai.usage.log"].sudo()
        # Other user should not be limited
        self.assertFalse(
            UsageLog._is_rate_limited(non_ai, "chatter_summary")
        )
