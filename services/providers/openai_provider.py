# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""OpenAI chat-completion adapter.

Compatible with the standard ``/v1/chat/completions`` endpoint used by
OpenAI models (GPT-4o, GPT-4o-mini, etc.).
"""

from typing import Any

from .base import AIProvider
from .factory import AIProviderFactory


class OpenAIProvider(AIProvider):
    """Strategy implementation for the OpenAI API."""

    name = "openai"
    ENDPOINT = "https://api.openai.com/v1/chat/completions"

    def _build_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
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
AIProviderFactory.register("openai", OpenAIProvider)
