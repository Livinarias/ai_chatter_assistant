# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Cross-cutting decorator for AI features.

The :func:`ai_feature` decorator wraps any Odoo model method that invokes
an AI provider.  It enforces three concerns in a single, reusable place:

1. **Permission check** – the calling user must belong to
   ``ai_chatter_assistant.group_ai_user``.
2. **Rate-limit check** – the user must not have exceeded the configured
   hourly call limit.
3. **Usage logging** – every call (success or failure) is recorded in
   ``ai.usage.log``.
"""

import functools
import logging

from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)


def ai_feature(feature_name: str):
    """Decorator factory for AI-powered Odoo methods.

    Args:
        feature_name: Technical name of the feature, matching one of the
            ``ai.usage.log`` feature selection keys (e.g.
            ``'chatter_summary'``, ``'reply_draft'``,
            ``'lead_generation'``).

    Example::

        @ai_feature("chatter_summary")
        def action_ai_summarize(self):
            ...
    """

    def decorator(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            # ----- 1. Permission gate -----
            if not self.env.user.has_group(
                "ai_chatter_assistant.group_ai_user"
            ):
                raise AccessError(
                    "You do not have permission to use AI features. "
                    "Contact your administrator."
                )

            # ----- 2. Rate-limit gate -----
            UsageLog = self.env["ai.usage.log"].sudo()
            if UsageLog._is_rate_limited(self.env.user, feature_name):
                raise UserError(
                    "You have reached the AI usage limit for this hour. "
                    "Please try again later."
                )

            # ----- 3. Execute & log -----
            try:
                result = method(self, *args, **kwargs)
                UsageLog._log_usage(
                    user=self.env.user,
                    feature=feature_name,
                    status="success",
                    tokens_used=result.get("tokens_used", 0)
                    if isinstance(result, dict)
                    else 0,
                )
                return result
            except Exception as exc:
                UsageLog._log_usage(
                    user=self.env.user,
                    feature=feature_name,
                    status="error",
                    error_message=str(exc),
                )
                raise

        return wrapper

    return decorator
