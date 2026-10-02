# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Tests for the @ai_feature decorator."""

from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import MOCK_OPENAI_RESPONSE, AITestCase, _make_mock_response


@tagged("post_install", "-at_install")
class TestAIFeatureDecorator(AITestCase):
    """Integration tests for the @ai_feature decorator."""

    def setUp(self):
        super().setUp()
        self._setup_ai_config()

    def test_user_without_group_raises_access_error(self):
        """Non-AI users get AccessError when calling decorated methods."""
        partner = (
            self.env["res.partner"]
            .with_user(self.non_ai_user)
            .create({"name": "Test Decorator Partner"})
        )
        with self.assertRaises(AccessError):
            partner.action_ai_summarize()

    @patch(
        "lan_ai_chatter_assistant.services.providers.base.requests.post",
        return_value=_make_mock_response(MOCK_OPENAI_RESPONSE),
    )
    @patch(
        "lan_ai_chatter_assistant.services.encryption.decrypt_api_key",
        return_value="sk-test",
    )
    def test_user_with_group_succeeds(self, mock_decrypt, mock_post):
        """AI users can call decorated methods."""
        partner = (
            self.env["res.partner"]
            .with_user(self.ai_user)
            .create({"name": "Test Decorator Partner"})
        )
        # Post a message so there is content to summarise
        partner.message_post(body="Hello, this is a test message.")

        # Should not raise
        result = partner.action_ai_summarize()
        self.assertIn("content", result)

    @patch(
        "lan_ai_chatter_assistant.services.providers.base.requests.post",
        return_value=_make_mock_response(MOCK_OPENAI_RESPONSE),
    )
    @patch(
        "lan_ai_chatter_assistant.services.encryption.decrypt_api_key",
        return_value="sk-test",
    )
    def test_decorator_logs_success(self, mock_decrypt, mock_post):
        """Successful calls are logged in ai.usage.log."""
        partner = (
            self.env["res.partner"]
            .with_user(self.ai_user)
            .create({"name": "Test Log Partner"})
        )
        partner.message_post(body="Hello!")
        partner.action_ai_summarize()

        log = (
            self.env["ai.usage.log"]
            .sudo()
            .search(
                [
                    ("user_id", "=", self.ai_user.id),
                    ("feature", "=", "chatter_summary"),
                    ("status", "=", "success"),
                ],
                limit=1,
            )
        )
        self.assertTrue(log.exists())

    @patch(
        "lan_ai_chatter_assistant.services.encryption.decrypt_api_key",
        return_value="sk-test",
    )
    def test_decorator_logs_error(self, mock_decrypt):
        """Failed calls are logged with error status."""
        partner = (
            self.env["res.partner"]
            .with_user(self.ai_user)
            .create({"name": "Test Error Partner"})
        )
        partner.message_post(body="Test content")

        with patch(
            "lan_ai_chatter_assistant.services.providers.base.requests.post",
            side_effect=Exception("API down"),
        ):
            with self.assertRaises(Exception):
                partner.action_ai_summarize()

        log = (
            self.env["ai.usage.log"]
            .sudo()
            .search(
                [
                    ("user_id", "=", self.ai_user.id),
                    ("feature", "=", "chatter_summary"),
                    ("status", "=", "error"),
                ],
                limit=1,
            )
        )
        self.assertTrue(log.exists())
        self.assertIn("API down", log.error_message)
