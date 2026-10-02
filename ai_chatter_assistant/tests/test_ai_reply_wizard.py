# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Tests for the AI Reply Wizard."""

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import MOCK_OPENAI_RESPONSE, AITestCase, _make_mock_response


@tagged("post_install", "-at_install")
class TestAIReplyWizard(AITestCase):
    """Integration tests for the AI reply wizard."""

    def setUp(self):
        super().setUp()
        self._setup_ai_config()
        self.partner = (
            self.env["res.partner"]
            .with_user(self.ai_user)
            .create({"name": "Wizard Test Partner"})
        )
        self.partner.sudo().message_post(
            body="<p>Can you offer us a discount?</p>",
            message_type="comment",
        )

    def _create_wizard(self, **kwargs):
        """Create a reply wizard for the test partner."""
        vals = {
            "source_model": "res.partner",
            "source_id": self.partner.id,
        }
        vals.update(kwargs)
        return self.env["ai.reply.wizard"].with_user(self.ai_user).create(vals)

    @patch(
        "ai_chatter_assistant.services.providers.base.requests.post",
        return_value=_make_mock_response(MOCK_OPENAI_RESPONSE),
    )
    @patch(
        "ai_chatter_assistant.services.encryption.decrypt_api_key",
        return_value="sk-test",
    )
    def test_generate_reply_fills_field(self, mock_decrypt, mock_post):
        """Generating a reply populates the generated_reply field."""
        wizard = self._create_wizard(instructions="Offer a 5% discount.")
        result = wizard.action_generate_reply()

        # Wizard should stay open
        self.assertEqual(result["type"], "ir.actions.act_window")
        self.assertEqual(result["target"], "new")

        # Reply should be populated
        wizard.invalidate_recordset()
        self.assertTrue(wizard.generated_reply)
        self.assertIn("test AI response", wizard.generated_reply)

    @patch(
        "ai_chatter_assistant.services.encryption.decrypt_api_key",
        return_value="sk-test",
    )
    def test_generate_reply_no_messages_raises(self, mock_decrypt):
        """UserError when source record has no messages."""
        empty_partner = (
            self.env["res.partner"]
            .with_user(self.ai_user)
            .create({"name": "Empty Wizard Partner"})
        )
        wizard = self._create_wizard(source_id=empty_partner.id)
        with self.assertRaises(UserError):
            wizard.action_generate_reply()

    @patch(
        "ai_chatter_assistant.services.providers.base.requests.post",
        return_value=_make_mock_response(MOCK_OPENAI_RESPONSE),
    )
    @patch(
        "ai_chatter_assistant.services.encryption.decrypt_api_key",
        return_value="sk-test",
    )
    def test_post_reply(self, mock_decrypt, mock_post):
        """Posting a reply creates a comment on the source record."""
        wizard = self._create_wizard()
        wizard.action_generate_reply()

        result = wizard.action_post_reply()
        self.assertEqual(result["type"], "ir.actions.act_window_close")

        # Check that a comment was posted
        comments = self.env["mail.message"].search(
            [
                ("res_id", "=", self.partner.id),
                ("model", "=", "res.partner"),
                ("message_type", "=", "comment"),
                ("subtype_id", "=", self.env.ref("mail.mt_comment").id),
            ],
            order="id desc",
            limit=1,
        )
        self.assertTrue(comments.exists())

    def test_post_reply_no_content_raises(self):
        """UserError when trying to post without generating first."""
        wizard = self._create_wizard()
        with self.assertRaises(UserError):
            wizard.action_post_reply()

    def test_wizard_with_custom_instructions(self):
        """Instructions field is stored correctly."""
        wizard = self._create_wizard(
            instructions="Be formal and mention the 10% loyalty discount."
        )
        self.assertEqual(
            wizard.instructions,
            "Be formal and mention the 10% loyalty discount.",
        )
