# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Factory for creating AI provider instances (Factory pattern).

Providers self-register by calling :meth:`AIProviderFactory.register` at
import time.  The factory is then used by the Odoo models to obtain the
correct provider based on the admin's configuration.

Usage::

    from ai_chatter_assistant.services.providers.factory import AIProviderFactory

    provider = AIProviderFactory.create("openai", api_key="sk-...")
    result = provider.chat_completion(messages, model="gpt-4o-mini")
"""

import logging
from typing import Type

from .base import AIProvider, AIProviderError

_logger = logging.getLogger(__name__)


class AIProviderFactory:
    """Central registry + factory for AI provider classes."""

    _registry: dict[str, Type[AIProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_class: Type[AIProvider]) -> None:
        """Register a provider class under *name*.

        Called at module-import time by each concrete provider module.
        """
        if not issubclass(provider_class, AIProvider):
            raise TypeError(f"{provider_class!r} must be a subclass of AIProvider.")
        cls._registry[name] = provider_class
        _logger.debug("Registered AI provider: %s → %s", name, provider_class.__name__)

    @classmethod
    def create(cls, provider_name: str, api_key: str) -> AIProvider:
        """Instantiate and return the provider identified by *provider_name*.

        Raises:
            AIProviderError: If the provider name is unknown.
        """
        provider_class = cls._registry.get(provider_name)
        if provider_class is None:
            available = ", ".join(sorted(cls._registry)) or "(none)"
            raise AIProviderError(
                f"Unknown AI provider '{provider_name}'. " f"Available: {available}."
            )
        return provider_class(api_key=api_key)

    @classmethod
    def get_available_providers(cls) -> list[tuple[str, str]]:
        """Return a list of ``(technical_name, human_label)`` tuples.

        Useful for populating an Odoo ``Selection`` field dynamically.
        """
        return [
            (name, klass.name.replace("_", " ").title())
            for name, klass in sorted(cls._registry.items())
        ]

    @classmethod
    def _reset(cls) -> None:
        """Clear the registry – used in tests only."""
        cls._registry.clear()
