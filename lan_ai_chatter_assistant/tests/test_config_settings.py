# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Tests for res.config.settings AI fields."""

from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import MOCK_OPENAI_RESPONSE, AITestCase, _make_mock_response


@tagged("post_install", "-at_install")
class TestConfigSettings(AITestCase):
    """Integration tests for AI configuration settings."""

    def test_set_and_get_provider(self):
        """Provider selection is persisted in ir.config_parameter."""
        settings = self.env["res.config.settings"].create({"ai_provider": "anthropic"})
        settings.set_values()

        ICP = self.env["ir.config_parameter"].sudo()
        self.assertEqual(ICP.get_param("lan_ai_chatter_assistant.ai_provider"), "anthropic")

    @patch(
        "lan_ai_chatter_assistant.models.res_config_settings.encrypt_api_key",
        return_value="encrypted-value",
    )
    def test_set_values_encrypts_api_key(self, mock_encrypt):
        """API key is encrypted before being stored."""
        settings = self.env["res.config.settings"].create(
            {"ai_api_key": "sk-my-secret-key"}
        )
        settings.set_values()
        mock_encrypt.assert_called_once()
        self.assertEqual(mock_encrypt.call_args[0][0], "sk-my-secret-key")

        ICP = self.env["ir.config_parameter"].sudo()
        self.assertEqual(
            ICP.get_param("lan_ai_chatter_assistant.ai_api_key"),
            "encrypted-value",
        )

    def test_set_values_secure_mode_without_env_raises(self):
        """UserError when secure mode is selected but AI_ENCRYPTION_KEY is missing."""
        import os

        with patch.dict(os.environ, {"AI_ENCRYPTION_KEY": ""}):
            settings = self.env["res.config.settings"].create(
                {"ai_encryption_mode": "secure", "ai_api_key": "sk-test"}
            )
            with self.assertRaises(UserError):
                settings.set_values()

    @patch(
        "lan_ai_chatter_assistant.models.res_config_settings.decrypt_api_key",
        return_value="sk-decrypted",
    )
    def test_get_values_decrypts_api_key(self, mock_decrypt):
        """API key is decrypted when loading settings."""
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("lan_ai_chatter_assistant.ai_api_key", "encrypted-value")

        settings = self.env["res.config.settings"].create({})
        values = settings.get_values()
        self.assertEqual(values["ai_api_key"], "sk-decrypted")

    @patch(
        "lan_ai_chatter_assistant.models.res_config_settings.decrypt_api_key",
        side_effect=ValueError("Cannot decrypt"),
    )
    def test_get_values_handles_decrypt_failure(self, mock_decrypt):
        """Graceful fallback when decryption fails."""
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("lan_ai_chatter_assistant.ai_api_key", "bad-data")

        settings = self.env["res.config.settings"].create({})
        values = settings.get_values()
        self.assertEqual(values["ai_api_key"], "")

    def test_default_values(self):
        """Default values are set correctly."""
        settings = self.env["res.config.settings"].create({})
        self.assertEqual(settings.ai_timeout, 15)
        self.assertEqual(settings.ai_temperature, 0.3)
        self.assertEqual(settings.ai_max_tokens, 1024)
        self.assertEqual(settings.ai_rate_limit_per_hour, 50)

    # -- Test Connection button -----------------------------------------

    def test_test_connection_no_provider_raises(self):
        """UserError when no provider is selected."""
        settings = self.env["res.config.settings"].create(
            {"ai_provider": False, "ai_api_key": "sk-key"}
        )
        with self.assertRaises(UserError):
            settings.action_ai_test_connection()

    def test_test_connection_no_key_raises(self):
        """UserError when no API key is entered."""
        settings = self.env["res.config.settings"].create(
            {"ai_provider": "openai", "ai_api_key": ""}
        )
        with self.assertRaises(UserError):
            settings.action_ai_test_connection()

    @patch(
        "lan_ai_chatter_assistant.services.providers.base.requests.post",
        return_value=_make_mock_response(MOCK_OPENAI_RESPONSE),
    )
    def test_test_connection_success(self, mock_post):
        """Successful test returns a notification action."""
        settings = self.env["res.config.settings"].create(
            {
                "ai_provider": "openai",
                "ai_api_key": "sk-valid-key",
                "ai_model_name": "gpt-4o-mini",
            }
        )
        result = settings.action_ai_test_connection()
        self.assertEqual(result["type"], "ir.actions.client")
        self.assertEqual(result["tag"], "display_notification")
        self.assertEqual(result["params"]["type"], "success")

    def test_auto_generate_encryption_key_in_system_parameters(self):
        """Encryption key is automatically created in ir.config_parameter if not present."""
        ICP = self.env["ir.config_parameter"].sudo()
        # Remove any existing key
        ICP.search([("key", "=", "lan_ai_chatter_assistant.encryption_key")]).unlink()

        from ..services.encryption import get_or_create_encryption_key

        key = get_or_create_encryption_key(self.env)
        self.assertTrue(key)
        self.assertEqual(ICP.get_param("lan_ai_chatter_assistant.encryption_key"), key)
