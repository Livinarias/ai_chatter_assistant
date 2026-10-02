# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Shared test fixtures and mock data for AI tests."""

from unittest.mock import MagicMock

from odoo.tests import TransactionCase

# ---------------------------------------------------------------------------
# Mock API responses
# ---------------------------------------------------------------------------

MOCK_OPENAI_RESPONSE = {
    "choices": [
        {
            "message": {
                "content": "This is a test AI response.",
            },
            "finish_reason": "stop",
        }
    ],
    "usage": {
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "total_tokens": 150,
    },
}

MOCK_ANTHROPIC_RESPONSE = {
    "content": [
        {
            "type": "text",
            "text": "This is a test AI response from Claude.",
        }
    ],
    "usage": {
        "input_tokens": 100,
        "output_tokens": 50,
    },
}

MOCK_LEAD_JSON_RESPONSE = {
    "choices": [
        {
            "message": {
                "content": '{"contact_name": "John Doe", '
                '"company_name": "Acme Corp", '
                '"opportunity_title": "New software project", '
                '"expected_revenue": 15000, '
                '"description": "Client needs a custom ERP integration."}',
            }
        }
    ],
    "usage": {"total_tokens": 200},
}

# Fernet test key — generated once for test purposes only.
# NEVER use this in production.
TEST_FERNET_KEY = "ZmFrZS1rZXktZm9yLXRlc3Rpbmctb25seS0xMjM0NTY3OA=="

# A proper Fernet key for actual encrypt/decrypt tests
# Generated with: Fernet.generate_key()
TEST_FERNET_KEY_VALID = None  # Will be set dynamically in tests


def _make_mock_response(json_data, status_code=200):
    """Create a mock ``requests.Response``."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data
    mock_resp.text = str(json_data)
    return mock_resp


class AITestCase(TransactionCase):
    """Base test case with common setup for AI module tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create a test user with AI group
        cls.ai_user = cls.env["res.users"].create(
            {
                "name": "AI Test User",
                "login": "ai_test_user",
                "email": "ai_test@example.com",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref("lan_ai_chatter_assistant.group_ai_user").id,
                        ],
                    )
                ],
            }
        )

        # Create a test user WITHOUT AI group
        cls.non_ai_user = cls.env["res.users"].create(
            {
                "name": "Non-AI Test User",
                "login": "non_ai_test_user",
                "email": "non_ai_test@example.com",
                "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )

    def _setup_ai_config(
        self, provider="openai", api_key="sk-test-key-123", model="gpt-4o-mini"
    ):
        """Configure AI settings for tests using mock encryption."""
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("lan_ai_chatter_assistant.ai_provider", provider)
        ICP.set_param("lan_ai_chatter_assistant.ai_model_name", model)
        ICP.set_param("lan_ai_chatter_assistant.ai_timeout", "15")
        ICP.set_param("lan_ai_chatter_assistant.ai_temperature", "0.3")
        ICP.set_param("lan_ai_chatter_assistant.ai_max_tokens", "1024")
        ICP.set_param("lan_ai_chatter_assistant.ai_rate_limit_per_hour", "50")
        # Store the key as-is for test simplicity; encryption tests
        # are in test_encryption.py
        ICP.set_param("lan_ai_chatter_assistant.ai_api_key", api_key)
