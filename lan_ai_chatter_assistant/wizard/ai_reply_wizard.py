# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""AI Reply Wizard — assisted draft generation for chatter replies.

Opens as a modal dialog from the chatter.  The user can optionally type
instructions (e.g. *"Offer a 5% discount"*).  Clicking **Generate Draft**
calls the AI and fills in the ``generated_reply`` field, which the user can
then review, edit and copy into the chatter composer.
"""

import html
import logging

from markupsafe import Markup
from odoo import _, fields, models
from odoo.exceptions import UserError

from ..services.decorators import ai_feature
from ..services.prompts import REPLY_SYSTEM_PROMPT, REPLY_USER_PROMPT
from ..services.providers.base import AIProviderError

_logger = logging.getLogger(__name__)


class AIReplyWizard(models.TransientModel):
    _name = "ai.reply.wizard"
    _description = "AI Reply Wizard"

    # Context fields (populated when the wizard is opened)
    source_model = fields.Char(
        string="Source Model",
        required=True,
    )
    source_id = fields.Integer(
        string="Source Record ID",
        required=True,
    )

    # User input
    instructions = fields.Text(
        string="Additional Instructions",
        help="Optional guidance for the AI, e.g. 'Offer a 5%% discount'.",
    )

    # AI output
    generated_reply = fields.Html(
        string="Generated Reply",
        readonly=True,
    )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    @ai_feature("reply_draft")
    def action_generate_reply(self):
        """Call the AI provider and fill *generated_reply*.

        Returns the wizard action so the modal stays open with the result.
        """
        self.ensure_one()

        source = self.env[self.source_model].browse(self.source_id)
        if not source.exists():
            raise UserError(_("Source record not found."))

        # 1. Collect messages -------------------------------------------
        messages_text = source._ai_collect_messages(10)
        if not messages_text:
            raise UserError(_("There are no messages to base the reply on."))

        # 2. Build prompt -----------------------------------------------
        user_instructions = self.instructions or _("Reply professionally.")
        ai_messages = [
            {"role": "system", "content": REPLY_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": REPLY_USER_PROMPT.format(
                    messages=messages_text,
                    instructions=user_instructions,
                ),
            },
        ]

        # 3. Call AI ----------------------------------------------------
        provider, model, kwargs = source._ai_get_provider_and_params()
        try:
            result = provider.chat_completion(ai_messages, model, **kwargs)
        except AIProviderError as exc:
            raise UserError(str(exc)) from exc

        # 4. Store generated text in wizard field ----------------------
        reply = result.get("content", "").strip()
        if reply:
            import re

            # Strip XML thinking tags (e.g. <think>...</think>)
            reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL).strip()
            # If the model produced a markdown thinking block (e.g. "Here's a thinking process: ...")
            if "Here's a thinking process" in reply or "Thinking Process:" in reply:
                # Look for common end-of-thinking markers or quotes
                parts = re.split(
                    r"(?:Drafting the Reply[^\n]*\n|Here is the (?:draft|reply)[^\n]*:\s*|\n\n---\n\n)",
                    reply,
                    flags=re.IGNORECASE,
                )
                if len(parts) > 1:
                    reply = parts[-1].strip()

            paragraphs = [
                f"<p>{html.escape(p).replace(chr(10), '<br/>')}</p>"
                for p in reply.split("\n\n")
                if p.strip()
            ]
            self.generated_reply = (
                Markup("".join(paragraphs))
                if paragraphs
                else Markup(f"<p>{html.escape(reply)}</p>")
            )
        else:
            self.generated_reply = ""

        # Return the same wizard form so the user sees the result
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_post_reply(self):
        """Post the generated reply as a comment on the source record.

        This is an optional convenience — the user may also copy-paste.
        """
        self.ensure_one()
        if not self.generated_reply:
            raise UserError(_("No reply has been generated yet."))

        source = self.env[self.source_model].browse(self.source_id)
        if not source.exists():
            raise UserError(_("Source record not found."))

        source.message_post(
            body=Markup(self.generated_reply),
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )

        return {"type": "ir.actions.act_window_close"}
