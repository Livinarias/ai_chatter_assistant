# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Tests for mail.thread AI summarisation."""

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import MOCK_OPENAI_RESPONSE, AITestCase, _make_mock_response


@tagged("post_install", "-at_install")
class TestMailThread(AITestCase):
    """Integration tests for the chatter summarisation feature."""

    def setUp(self):
        super().setUp()
        self._setup_ai_config()
        # Create a partner (which has mail.thread) with messages
        self.partner = (
            self.env["res.partner"]
            .with_user(self.ai_user)
            .create({"name": "Test Thread Partner"})
        )

    def _post_messages(self, partner, count=3):
        """Post *count* test messages on the partner's chatter."""
        for i in range(count):
            partner.sudo().message_post(
                body=f"<p>Test message {i + 1}: discussing the project.</p>",
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )

    @patch(
        "lan_ai_chatter_assistant.services.providers.base.requests.post",
        return_value=_make_mock_response(MOCK_OPENAI_RESPONSE),
    )
    @patch(
        "lan_ai_chatter_assistant.services.encryption.decrypt_api_key",
        return_value="sk-test",
    )
    def test_summarize_posts_internal_note(self, mock_decrypt, mock_post):
        """Summarisation posts an internal note with the AI response."""
        self._post_messages(self.partner)

        self.partner.action_ai_summarize()

        # Check that a note was posted
        notes = self.env["mail.message"].search(
            [
                ("res_id", "=", self.partner.id),
                ("model", "=", "res.partner"),
                ("subtype_id", "=", self.env.ref("mail.mt_note").id),
            ]
        )
        self.assertTrue(notes.exists())
        self.assertIn("AI Summary", notes[0].body)

    @patch(
        "lan_ai_chatter_assistant.services.encryption.decrypt_api_key",
        return_value="sk-test",
    )
    def test_summarize_no_messages_raises(self, mock_decrypt):
        """UserError when there are no messages to summarise."""
        # New partner with no messages
        empty_partner = (
            self.env["res.partner"]
            .with_user(self.ai_user)
            .create({"name": "Empty Partner"})
        )
        with self.assertRaises(UserError):
            empty_partner.action_ai_summarize()

    def test_collect_messages_strips_html(self):
        """_ai_collect_messages returns plain text without HTML tags."""
        self.partner.sudo().message_post(
            body="<p><b>Bold</b> text with <a href='#'>link</a></p>",
            message_type="comment",
        )
        text = self.partner._ai_collect_messages(10)
        self.assertNotIn("<p>", text)
        self.assertNotIn("<b>", text)
        self.assertIn("Bold", text)

    def test_collect_messages_limits_count(self):
        """Only the specified number of messages are returned."""
        self._post_messages(self.partner, count=15)
        text = self.partner._ai_collect_messages(5)
        # Count lines (each message = one line)
        lines = [line for line in text.split("\n") if line.strip()]
        self.assertLessEqual(len(lines), 5)

    @patch(
        "lan_ai_chatter_assistant.services.encryption.decrypt_api_key",
        return_value="sk-test",
    )
    def test_get_provider_and_params_no_provider(self, mock_decrypt):
        """UserError when no provider is configured."""
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("lan_ai_chatter_assistant.ai_provider", "")

        with self.assertRaises(UserError) as ctx:
            self.partner._ai_get_provider_and_params()
        self.assertIn("No AI provider", str(ctx.exception))

    @patch(
        "lan_ai_chatter_assistant.services.encryption.decrypt_api_key",
        return_value="sk-test",
    )
    def test_get_provider_and_params_no_key(self, mock_decrypt):
        """UserError when no API key is stored."""
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("lan_ai_chatter_assistant.ai_provider", "openai")
        ICP.set_param("lan_ai_chatter_assistant.ai_api_key", "")

        with self.assertRaises(UserError) as ctx:
            self.partner._ai_get_provider_and_params()
        self.assertIn("No API key", str(ctx.exception))
