# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""AI usage log model for auditing and rate-limiting.

Implemented as a ``TransientModel`` with a 30-day TTL so old entries are
cleaned up automatically by Odoo's built-in vacuum cron.
"""

import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AIUsageLog(models.TransientModel):
    _name = "ai.usage.log"
    _description = "AI Usage Log"
    _order = "timestamp desc"
    _transient_max_hours = 24 * 30  # 30 days

    user_id = fields.Many2one(
        "res.users",
        string="User",
        required=True,
        index=True,
        ondelete="cascade",
    )
    timestamp = fields.Datetime(
        string="Timestamp",
        default=fields.Datetime.now,
        required=True,
        index=True,
    )
    provider = fields.Char(string="Provider")
    feature = fields.Selection(
        [
            ("chatter_summary", "Chatter Summary"),
            ("reply_draft", "Reply Draft"),
            ("lead_generation", "Lead Generation"),
            ("connection_test", "Connection Test"),
        ],
        string="Feature",
        required=True,
    )
    tokens_used = fields.Integer(string="Tokens Used", default=0)
    status = fields.Selection(
        [
            ("success", "Success"),
            ("error", "Error"),
        ],
        string="Status",
        required=True,
    )
    error_message = fields.Text(string="Error Message")

    # ------------------------------------------------------------------
    # Rate-limiting helpers
    # ------------------------------------------------------------------

    @api.model
    def _is_rate_limited(self, user, feature_name):
        """Check if *user* has exceeded the hourly call limit.

        The limit is read from ``ir.config_parameter``
        ``ai_chatter_assistant.ai_rate_limit_per_hour`` (default 50).
        """
        ICP = self.env["ir.config_parameter"].sudo()
        limit = int(
            ICP.get_param("ai_chatter_assistant.ai_rate_limit_per_hour", "50")
        )
        if limit <= 0:
            return False  # 0 = unlimited

        one_hour_ago = fields.Datetime.now() - timedelta(hours=1)
        count = self.sudo().search_count(
            [
                ("user_id", "=", user.id),
                ("timestamp", ">=", one_hour_ago),
                ("status", "=", "success"),
            ]
        )
        return count >= limit

    @api.model
    def _log_usage(
        self, user, feature, status="success", tokens_used=0, error_message=""
    ):
        """Create an audit entry for an AI call."""
        ICP = self.env["ir.config_parameter"].sudo()
        provider = ICP.get_param("ai_chatter_assistant.ai_provider", "")
        self.sudo().create(
            {
                "user_id": user.id,
                "provider": provider,
                "feature": feature,
                "tokens_used": tokens_used,
                "status": status,
                "error_message": error_message or "",
            }
        )
