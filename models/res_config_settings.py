# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Admin settings for the AI Chatter Assistant.

Extends ``res.config.settings`` to expose AI provider configuration in
**Settings → General Settings → AI Assistant** section.  All values are
persisted in ``ir.config_parameter`` (company-independent).

Supports two encryption modes:
- Simple: Key generated and stored in System Parameters.
- High Security: Master key required from the AI_ENCRYPTION_KEY environment variable.
"""

import logging
import os

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..services.encryption import (
    decrypt_api_key,
    encrypt_api_key,
    is_env_key_present,
)
from ..services.providers.base import AIProviderError
from ..services.providers.factory import AIProviderFactory

_logger = logging.getLogger(__name__)

# Config-parameter prefix
_P = "ai_chatter_assistant"


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # ------------------------------------------------------------------
    # Fields (all stored in ir.config_parameter)
    # ------------------------------------------------------------------

    ai_provider = fields.Selection(
        selection=[
            ("openai", "OpenAI"),
            ("anthropic", "Anthropic Claude"),
            ("deepseek", "DeepSeek"),
            ("openrouter", "OpenRouter"),
        ],
        string="AI Provider",
        config_parameter=f"{_P}.ai_provider",
        default="",
    )

    ai_api_key = fields.Char(
        string="API Key",
        help="The API key will be encrypted before being stored.",
    )

    ai_encryption_mode = fields.Selection(
        selection=[
            ("simple", "Simple (Auto-generated in Database)"),
            ("secure", "High Security (Environment Variable)"),
        ],
        string="Encryption Mode",
        config_parameter=f"{_P}.ai_encryption_mode",
        default="simple",
        required=True,
        help="Simple mode generates and stores the encryption key in System Parameters. "
             "High Security mode requires the AI_ENCRYPTION_KEY environment variable.",
    )

    ai_env_key_detected = fields.Boolean(
        string="Environment Key Detected",
        compute="_compute_ai_env_key_detected",
        help="Indicates whether AI_ENCRYPTION_KEY is currently set in the environment.",
    )

    ai_model_name = fields.Char(
        string="Model Name",
        config_parameter=f"{_P}.ai_model_name",
        default="gpt-4o-mini",
    )

    ai_timeout = fields.Integer(
        string="Request Timeout (s)",
        config_parameter=f"{_P}.ai_timeout",
        default=15,
    )

    ai_temperature = fields.Float(
        string="Temperature",
        config_parameter=f"{_P}.ai_temperature",
        default=0.3,
    )

    ai_max_tokens = fields.Integer(
        string="Max Tokens",
        config_parameter=f"{_P}.ai_max_tokens",
        default=1024,
    )

    ai_rate_limit_per_hour = fields.Integer(
        string="Rate Limit (calls / hour / user)",
        config_parameter=f"{_P}.ai_rate_limit_per_hour",
        default=50,
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------

    def _compute_ai_env_key_detected(self):
        detected = is_env_key_present()
        for rec in self:
            rec.ai_env_key_detected = detected

    # ------------------------------------------------------------------
    # Compute / inverse for encrypted API key
    # ------------------------------------------------------------------

    @api.model
    def get_values(self):
        """Load the decrypted API key into the settings form."""
        res = super().get_values()
        ICP = self.env["ir.config_parameter"].sudo()
        encrypted = ICP.get_param(f"{_P}.ai_api_key", "")
        mode = ICP.get_param(f"{_P}.ai_encryption_mode", "simple")
        try:
            res["ai_api_key"] = decrypt_api_key(encrypted, env=self.env, mode=mode) if encrypted else ""
        except ValueError:
            _logger.warning("Could not decrypt stored AI API key.")
            res["ai_api_key"] = ""
        return res

    def set_values(self):
        """Validate and encrypt the API key before persisting."""
        if self.ai_encryption_mode == "secure":
            env_key = os.environ.get("AI_ENCRYPTION_KEY", "").strip()
            if not env_key:
                raise UserError(
                    _(
                        "High Security mode requires the AI_ENCRYPTION_KEY environment "
                        "variable to be set in your container/server. Please configure it "
                        "in your docker-compose or environment before selecting this option."
                    )
                )
            try:
                from cryptography.fernet import Fernet
                Fernet(env_key.encode())
            except Exception as exc:
                raise UserError(
                    _("The configured AI_ENCRYPTION_KEY is not a valid Fernet key: %s") % exc
                )

        super().set_values()
        ICP = self.env["ir.config_parameter"].sudo()
        plain_key = self.ai_api_key or ""
        encrypted = (
            encrypt_api_key(plain_key, env=self.env, mode=self.ai_encryption_mode)
            if plain_key
            else ""
        )
        ICP.set_param(f"{_P}.ai_api_key", encrypted)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_ai_test_connection(self):
        """Test the connection to the configured AI provider.

        Bound to the *Test Connection* button in the settings view.
        """
        self.ensure_one()

        provider_name = self.ai_provider
        if not provider_name:
            raise UserError(_("Please select an AI provider first."))

        api_key = self.ai_api_key
        if not api_key:
            raise UserError(_("Please enter an API key first."))

        model_name = self.ai_model_name
        if not model_name:
            raise UserError(_("Please enter a model name first."))

        try:
            provider = AIProviderFactory.create(provider_name, api_key)
            provider.test_connection(
                model=model_name,
                timeout=min(self.ai_timeout or 15, 10),
            )
        except AIProviderError as exc:
            raise UserError(str(exc)) from exc

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Connection Successful ✅"),
                "message": _("Successfully connected to %s with model %s.") % (provider_name, model_name),
                "type": "success",
                "sticky": False,
            },
        }
