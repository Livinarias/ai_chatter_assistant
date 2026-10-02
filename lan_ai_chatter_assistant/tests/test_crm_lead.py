# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Tests for CRM lead generation from chatter threads."""

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import MOCK_LEAD_JSON_RESPONSE, AITestCase, _make_mock_response


@tagged("post_install", "-at_install")
class TestCrmLead(AITestCase):
    """Integration tests for AI-powered CRM lead creation."""

    def setUp(self):
        super().setUp()
        self._setup_ai_config()
        self.partner = (
            self.env["res.partner"]
            .with_user(self.ai_user)
            .create({"name": "Lead Source Partner"})
        )
        self.partner.sudo().message_post(
            body="<p>Hi, we need a custom ERP integration for our company Acme Corp.</p>",
            message_type="email",
        )

    @patch(
        "lan_ai_chatter_assistant.services.providers.base.requests.post",
        return_value=_make_mock_response(MOCK_LEAD_JSON_RESPONSE),
    )
    @patch(
        "lan_ai_chatter_assistant.services.encryption.decrypt_api_key",
        return_value="sk-test",
    )
    def test_create_lead_from_thread(self, mock_decrypt, mock_post):
        """A CRM lead is created with AI-extracted data."""
        CrmLead = self.env["crm.lead"].with_user(self.ai_user)
        result = CrmLead.action_ai_create_lead_from_thread(
            "res.partner", self.partner.id
        )

        self.assertIn("lead_id", result)
        lead = self.env["crm.lead"].browse(result["lead_id"])
        self.assertTrue(lead.exists())
        self.assertEqual(lead.name, "New software project")
        self.assertEqual(lead.contact_name, "John Doe")
        self.assertEqual(lead.partner_name, "Acme Corp")
        self.assertEqual(lead.expected_revenue, 15000)
        self.assertTrue(lead.ai_generated)

    @patch(
        "lan_ai_chatter_assistant.services.encryption.decrypt_api_key",
        return_value="sk-test",
    )
    def test_create_lead_no_messages_raises(self, mock_decrypt):
        """UserError when source record has no messages."""
        empty_partner = (
            self.env["res.partner"].sudo().create({"name": "Empty Lead Partner"})
        )
        CrmLead = self.env["crm.lead"].with_user(self.ai_user)
        with self.assertRaises(UserError):
            CrmLead.action_ai_create_lead_from_thread("res.partner", empty_partner.id)

    def test_parse_lead_json_valid(self):
        """_ai_parse_lead_json extracts data from valid JSON."""
        CrmLead = self.env["crm.lead"]
        data = CrmLead._ai_parse_lead_json(
            '{"contact_name": "Jane", "opportunity_title": "Deal"}'
        )
        self.assertEqual(data["contact_name"], "Jane")
        self.assertEqual(data["opportunity_title"], "Deal")

    def test_parse_lead_json_with_markdown_fences(self):
        """JSON wrapped in ```json ... ``` fences is parsed correctly."""
        CrmLead = self.env["crm.lead"]
        raw = '```json\n{"opportunity_title": "Big deal"}\n```'
        data = CrmLead._ai_parse_lead_json(raw)
        self.assertEqual(data["opportunity_title"], "Big deal")

    def test_parse_lead_json_invalid_fallback(self):
        """Invalid JSON falls back gracefully with raw content."""
        CrmLead = self.env["crm.lead"]
        data = CrmLead._ai_parse_lead_json("not json at all")
        self.assertIn("opportunity_title", data)
        self.assertIn("not json at all", data.get("description", ""))

    def test_ai_generated_field(self):
        """The ai_generated field exists and defaults to False."""
        lead = self.env["crm.lead"].create({"name": "Manual Lead"})
        self.assertFalse(lead.ai_generated)
