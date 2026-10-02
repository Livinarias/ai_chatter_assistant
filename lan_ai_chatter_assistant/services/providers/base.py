# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Abstract base class for AI providers (Strategy pattern).

Every concrete provider **must** subclass :class:`AIProvider` and implement
the three protected helpers that vary between API formats:

* :meth:`_build_headers`
* :meth:`_build_payload`
* :meth:`_parse_response`

The public entry point :meth:`chat_completion` orchestrates the full
request lifecycle (build → send → parse → normalise errors).
"""

import abc
import json
import logging
from typing import Any

import requests

_logger = logging.getLogger(__name__)

# Default values – can be overridden per-call or via Odoo settings.
DEFAULT_TIMEOUT = 15  # seconds
DEFAULT_TEMPERATURE = 0.3
DEFAULT_MAX_TOKENS = 1024


class AIProviderError(Exception):
    """Raised when an AI provider returns a non-recoverable error."""


class AIProvider(abc.ABC):
    """Abstract Strategy for calling an AI chat-completion API."""

    # Subclasses MUST set these.
    name: str = ""
    ENDPOINT: str = ""

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise AIProviderError("API key is required.")
        self._api_key = api_key

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str,
        *,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> dict[str, Any]:
        """Send a chat-completion request and return a normalised result.

        Returns:
            dict with at least:
                ``content`` (str) – the assistant reply text.
                ``tokens_used`` (int) – total tokens consumed (if reported).
        """
        headers = self._build_headers()
        payload = self._build_payload(messages, model, temperature, max_tokens)

        _logger.debug(
            "AI request → %s | model=%s | tokens_limit=%s",
            self.ENDPOINT,
            model,
            max_tokens,
        )

        read_timeout = max(5, int(timeout or DEFAULT_TIMEOUT))
        connect_timeout = 5
        try:
            response = requests.post(
                self.ENDPOINT,
                headers=headers,
                json=payload,
                timeout=(connect_timeout, read_timeout),
            )
        except requests.ConnectionError as exc:
            raise AIProviderError(
                f"Could not connect to {self.name} API at {self.ENDPOINT}."
            ) from exc
        except requests.Timeout as exc:
            raise AIProviderError(
                f"Request to {self.name} timed out after {read_timeout}s. "
                "The AI model took too long to respond. If using a free or busy model on OpenRouter, "
                "try a faster model like 'openai/gpt-4o-mini' or increase the timeout in Settings."
            ) from exc

        if response.status_code == 401:
            raise AIProviderError(f"Invalid or expired API key for {self.name}.")
        if response.status_code == 429:
            raise AIProviderError(
                f"Rate limit exceeded on {self.name}. Try again later."
            )
        if response.status_code >= 400:
            detail = (
                self._safe_json(response)
                .get("error", {})
                .get("message", response.text[:300])
            )
            raise AIProviderError(
                f"{self.name} returned HTTP {response.status_code}: {detail}"
            )

        data = self._safe_json(response)
        return self._parse_response(data)

    def test_connection(self, model: str, *, timeout: int = 10) -> bool:
        """Send a minimal request to verify the API key is valid.

        Returns ``True`` on success; raises :class:`AIProviderError` on
        failure.
        """
        self.chat_completion(
            messages=[{"role": "user", "content": "Say OK"}],
            model=model,
            max_tokens=5,
            timeout=timeout,
        )
        return True

    # ------------------------------------------------------------------
    # Template-method hooks (subclasses implement these)
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def _build_headers(self) -> dict[str, str]:
        """Return HTTP headers including authorisation."""

    @abc.abstractmethod
    def _build_payload(
        self,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        """Return the JSON-serialisable request body."""

    @abc.abstractmethod
    def _parse_response(self, data: dict[str, Any]) -> dict[str, Any]:
        """Parse the raw API response into ``{content, tokens_used}``."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_json(response: requests.Response) -> dict[str, Any]:
        """Attempt to parse JSON; return empty dict on failure."""
        try:
            return response.json()
        except (json.JSONDecodeError, ValueError):
            return {}
