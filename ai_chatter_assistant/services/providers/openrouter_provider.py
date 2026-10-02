# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""OpenRouter chat-completion adapter.

OpenRouter acts as a unified gateway to dozens of AI models.  Its API is
wire-compatible with OpenAI's ``/v1/chat/completions`` but requires an
extra ``HTTP-Referer`` header for usage tracking.
"""

from typing import Any

from .base import AIProvider
from .factory import AIProviderFactory


class OpenRouterProvider(AIProvider):
    """Strategy implementation for the OpenRouter API."""

    name = "openrouter"
    ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

    def _build_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
            "HTTP-Referer": "https://odoo-ai-assistant.app",
            "X-Title": "Odoo AI Chatter Assistant",
        }

    def _build_payload(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        return {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

    def _parse_response(self, data: dict[str, Any]) -> dict[str, Any]:
        content = ""
        choices = data.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "")

        usage = data.get("usage", {})
        tokens_used = usage.get("total_tokens", 0)

        return {
            "content": content.strip(),
            "tokens_used": tokens_used,
        }


# Self-register with the factory
AIProviderFactory.register("openrouter", OpenRouterProvider)
