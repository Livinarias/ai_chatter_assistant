# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Chatter AI features — thread summarisation.

Inherits ``mail.thread`` (an abstract mixin used by most Odoo models) to
add an AI-powered summarisation method.  When invoked, the method collects
the last N messages from the thread, sends them to the configured AI
provider and posts the summary as an internal note.
"""

import html
import logging

from markupsafe import Markup
from odoo import _, models
from odoo.exceptions import UserError

from ..services.decorators import ai_feature
from ..services.encryption import decrypt_api_key
from ..services.prompts import SUMMARY_SYSTEM_PROMPT, SUMMARY_USER_PROMPT
from ..services.providers.base import AIProviderError
from ..services.providers.factory import AIProviderFactory

_logger = logging.getLogger(__name__)

_MAX_MESSAGES = 10  # How many recent messages to feed the AI


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    # ------------------------------------------------------------------
    # Public action
    # ------------------------------------------------------------------

    @ai_feature("chatter_summary")
    def action_ai_summarize(self):
        """Generate an AI summary of the latest chatter messages.

        Posts the summary as an internal note (``subtype_xmlid =
        mail.mt_note``) so it is visible only to internal users.

        Returns:
            dict with ``content`` and ``tokens_used`` for the decorator.
        """
        self.ensure_one()

        # 1. Collect messages -------------------------------------------
        messages_text = self._ai_collect_messages(_MAX_MESSAGES)
        if not messages_text:
            raise UserError(_("There are no messages in this thread to summarise."))

        # 2. Build prompt -----------------------------------------------
        ai_messages = [
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": SUMMARY_USER_PROMPT.format(messages=messages_text),
            },
        ]

        # 3. Call AI ----------------------------------------------------
        provider, model, kwargs = self._ai_get_provider_and_params()
        try:
            result = provider.chat_completion(ai_messages, model, **kwargs)
        except AIProviderError as exc:
            raise UserError(str(exc)) from exc

        # 4. Post as internal note --------------------------------------
        summary = result.get("content", "")
        if summary:
            # Parse lines into clean HTML bullets
            lines = [line.strip() for line in summary.splitlines() if line.strip()]
            bullet_items = []
            for line in lines:
                clean_line = line.lstrip("-*•0123456789.) ").strip()
                if clean_line:
                    bullet_items.append(f"<li>{html.escape(clean_line)}</li>")

            if bullet_items:
                body_html = (
                    f"<p><b>🤖 AI Summary</b></p><ul>{''.join(bullet_items)}</ul>"
                )
            else:
                body_html = f"<p><b>🤖 AI Summary</b></p><p>{html.escape(summary)}</p>"

            self.message_post(
                body=Markup(body_html),
                subtype_xmlid="mail.mt_note",
                message_type="comment",
            )

        return result

    # ------------------------------------------------------------------
    # Helpers (reusable by other AI features on mail.thread)
    # ------------------------------------------------------------------

    def _ai_collect_messages(self, limit=_MAX_MESSAGES):
        """Return the plain-text body of the most recent *limit* messages.

        Filters out tracking / system messages to keep only real
        communication.
        """
        self.ensure_one()
        domain = [
            ("res_id", "=", self.id),
            ("model", "=", self._name),
            ("message_type", "in", ("email", "comment")),
            ("body", "!=", ""),
        ]
        msgs = self.env["mail.message"].search(domain, order="date desc", limit=limit)
        if not msgs:
            return ""

        lines = []
        for msg in reversed(msgs):
            author = msg.author_id.display_name or _("Unknown")
            # Strip HTML tags for a plain-text representation
            body = msg.body
            if body:
                body = self.env["mail.render.mixin"]._replace_local_links(body)
                # Simple tag stripping (Odoo provides no public helper)
                import re

                body = re.sub(r"<[^>]+>", "", body).strip()
            # Ignore automated AI summary notes from conversation context
            if "🤖 AI Summary" in body:
                continue
            lines.append(f"[{author}]: {body}")

        return "\n".join(lines)

    def _ai_get_provider_and_params(self):
        """Return ``(provider_instance, model_name, extra_kwargs)``.

        Reads configuration from ``ir.config_parameter`` and creates the
        provider via the factory.
        """
        ICP = self.env["ir.config_parameter"].sudo()
        prefix = "ai_chatter_assistant"

        provider_name = ICP.get_param(f"{prefix}.ai_provider", "")
        if not provider_name:
            raise UserError(
                _("No AI provider configured. Go to Settings → AI Assistant.")
            )

        encrypted_key = ICP.get_param(f"{prefix}.ai_api_key", "")
        if not encrypted_key:
            raise UserError(_("No API key configured. Go to Settings → AI Assistant."))

        try:
            api_key = decrypt_api_key(encrypted_key, env=self.env)
        except ValueError as exc:
            raise UserError(str(exc)) from exc

        model_name = ICP.get_param(f"{prefix}.ai_model_name", "gpt-4o-mini")
        try:
            timeout = int(ICP.get_param(f"{prefix}.ai_timeout", "15") or 15)
        except (ValueError, TypeError):
            timeout = 15
        timeout = max(5, min(timeout, 60))
        temperature = float(ICP.get_param(f"{prefix}.ai_temperature", "0.3") or 0.3)
        max_tokens = int(ICP.get_param(f"{prefix}.ai_max_tokens", "1024") or 1024)

        provider = AIProviderFactory.create(provider_name, api_key)

        return (
            provider,
            model_name,
            {
                "timeout": timeout,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
