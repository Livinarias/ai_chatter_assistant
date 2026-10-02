# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Anthropic Claude chat-completion adapter.

Uses the Anthropic Messages API (``/v1/messages``) which has a different
authentication scheme (``x-api-key`` header) and response format compared
to the OpenAI-compatible providers.
"""

from typing import Any

from .base import AIProvider
from .factory import AIProviderFactory


class AnthropicProvider(AIProvider):
    """Strategy implementation for the Anthropic Messages API."""

    name = "anthropic"
    ENDPOINT = "https://api.anthropic.com/v1/messages"
    ANTHROPIC_VERSION = "2023-06-01"

    def _build_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-api-key": self._api_key,
            "anthropic-version": self.ANTHROPIC_VERSION,
        }

    def _build_payload(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        # Anthropic requires the system prompt as a top-level field, not
        # inside the messages array.
        system_content = ""
        filtered_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_content = msg.get("content", "")
            else:
                filtered_messages.append(msg)

        payload: dict[str, Any] = {
            "model": model,
            "messages": filtered_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_content:
            payload["system"] = system_content
        return payload

    def _parse_response(self, data: dict[str, Any]) -> dict[str, Any]:
        content = ""
        content_blocks = data.get("content", [])
        if content_blocks:
            # The first block with type="text" holds the reply.
            for block in content_blocks:
                if block.get("type") == "text":
                    content = block.get("text", "")
                    break

        usage = data.get("usage", {})
        tokens_used = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)

        return {
            "content": content.strip(),
            "tokens_used": tokens_used,
        }


# Self-register with the factory
AIProviderFactory.register("anthropic", AnthropicProvider)
