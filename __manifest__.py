# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "AI Chatter Assistant",
    "version": "17.0.1.0.0",
    "category": "Productivity",
    "summary": "AI summaries, smart reply drafts, and CRM lead generation in Chatter",
    "description": """
AI Chatter Assistant
====================
AI-powered productivity assistant integrated directly into Odoo Chatter and CRM.

Key Features:
-------------
* **Thread Summaries**: Condense long discussions into 3 bullet points with 1 click.
* **Smart Reply**: Draft context-aware responses with custom instructions.
* **Instant CRM Lead**: Convert customer inquiries in threads into CRM leads automatically.
* **Multi-Provider Support**: Compatible with OpenAI, Anthropic Claude, DeepSeek, and OpenRouter.
* **Dual Encryption**: Choose between auto-generated database key (Simple) or environment variable (Secure).
* **Usage & Rate Control**: Set per-user hourly request limits and audit token consumption.

Third-Party Services & Privacy Disclosure:
------------------------------------------
This module connects directly and exclusively from your Odoo server to the external AI provider 
endpoint selected in your settings (OpenAI, Anthropic, DeepSeek, or OpenRouter) using your own API key.
* No intermediate or relay servers are used.
* Message content is sent only upon explicit user action (clicking an AI button).
* API keys are encrypted at rest using AES-128 Fernet encryption.
    """,
    "author": "Livingston Arias Narváez",
    "website": "https://github.com/Livinarias",
    "support": "livinarias88@gmail.com",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
        "crm",
    ],
    "external_dependencies": {
        "python": ["cryptography", "requests"],
    },
    "data": [
        # Security – order matters: groups first, then ACLs, then rules
        "security/security_groups.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        # Views
        "views/res_config_settings_views.xml",
        "views/crm_lead_views.xml",
        # Wizards
        "wizard/ai_reply_wizard_views.xml",
        # Data
        "data/ai_cron.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "ai_chatter_assistant/static/src/xml/chatter_ai_buttons.xml",
            "ai_chatter_assistant/static/src/js/chatter.js",
        ],
    },
    "demo": [],
    "installable": True,
    "application": True,
    "auto_install": False,
    "images": [
        "static/description/banner.png",
    ],
}
