# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Tests for the AIProviderFactory — registration and creation."""

import unittest

from odoo.tests import tagged

from ..services.providers.base import AIProvider, AIProviderError
from ..services.providers.factory import AIProviderFactory


class _DummyProvider(AIProvider):
    """Minimal concrete provider for factory tests."""

    name = "dummy"
    ENDPOINT = "https://dummy.test/v1/chat"

    def _build_headers(self):
        return {"Authorization": f"Bearer {self._api_key}"}

    def _build_payload(self, messages, model, temperature, max_tokens):
        return {"model": model, "messages": messages}

    def _parse_response(self, data):
        return {"content": "dummy", "tokens_used": 0}


@tagged("post_install", "-at_install")
class TestProviderFactory(unittest.TestCase):
    """Unit tests for the provider factory registry."""

    def setUp(self):
        super().setUp()
        # Save and restore registry state to avoid test pollution
        self._original_registry = dict(AIProviderFactory._registry)

    def tearDown(self):
        AIProviderFactory._registry = self._original_registry
        super().tearDown()

    def test_register_valid_provider(self):
        """A valid AIProvider subclass can be registered."""
        AIProviderFactory.register("dummy_test", _DummyProvider)
        self.assertIn("dummy_test", AIProviderFactory._registry)

    def test_register_non_provider_raises(self):
        """Registering a class that is not an AIProvider raises TypeError."""
        with self.assertRaises(TypeError):
            AIProviderFactory.register("bad", str)

    def test_create_known_provider(self):
        """Factory creates the correct provider class."""
        AIProviderFactory.register("dummy_test", _DummyProvider)
        provider = AIProviderFactory.create("dummy_test", api_key="test-key")
        self.assertIsInstance(provider, _DummyProvider)

    def test_create_unknown_provider_raises(self):
        """Creating an unknown provider raises AIProviderError."""
        with self.assertRaises(AIProviderError) as ctx:
            AIProviderFactory.create("nonexistent", api_key="key")
        self.assertIn("nonexistent", str(ctx.exception))

    def test_get_available_providers(self):
        """get_available_providers returns sorted tuples."""
        AIProviderFactory.register("dummy_a", _DummyProvider)
        AIProviderFactory.register("dummy_b", _DummyProvider)
        available = AIProviderFactory.get_available_providers()
        names = [name for name, _ in available]
        self.assertIn("dummy_a", names)
        self.assertIn("dummy_b", names)
        # Should be sorted
        self.assertEqual(names, sorted(names))

    def test_reset_clears_registry(self):
        """_reset() empties the registry (used in test setup)."""
        AIProviderFactory.register("to_clear", _DummyProvider)
        AIProviderFactory._reset()
        self.assertEqual(len(AIProviderFactory._registry), 0)

    def test_builtin_providers_registered(self):
        """All four built-in providers are registered at import time."""
        for name in ("openai", "anthropic", "deepseek", "openrouter"):
            self.assertIn(
                name,
                self._original_registry,
                f"Provider '{name}' should be auto-registered.",
            )
