# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Tests for the OpenRouter provider adapter."""

import unittest
from unittest.mock import patch

from odoo.tests import tagged

from ..services.providers.openrouter_provider import OpenRouterProvider
from .common import MOCK_OPENAI_RESPONSE, _make_mock_response


@tagged("post_install", "-at_install")
class TestOpenRouterProvider(unittest.TestCase):
    """Unit tests for OpenRouterProvider."""

    def setUp(self):
        super().setUp()
        self.provider = OpenRouterProvider(api_key="or-test-key")

    def test_endpoint(self):
        self.assertEqual(
            self.provider.ENDPOINT,
            "https://openrouter.ai/api/v1/chat/completions",
        )

    def test_headers_include_referer(self):
        """OpenRouter requires HTTP-Referer and X-Title headers."""
        headers = self.provider._build_headers()
        self.assertEqual(headers["Authorization"], "Bearer or-test-key")
        self.assertIn("HTTP-Referer", headers)
        self.assertIn("X-Title", headers)

    def test_payload_openai_compatible(self):
        msgs = [{"role": "user", "content": "Hi"}]
        payload = self.provider._build_payload(
            msgs, "openai/gpt-4o-mini", 0.7, 2048
        )
        self.assertEqual(payload["model"], "openai/gpt-4o-mini")

    def test_parse_response_openai_format(self):
        result = self.provider._parse_response(MOCK_OPENAI_RESPONSE)
        self.assertEqual(result["content"], "This is a test AI response.")

    @patch("ai_chatter_assistant.services.providers.base.requests.post")
    def test_chat_completion_success(self, mock_post):
        mock_post.return_value = _make_mock_response(MOCK_OPENAI_RESPONSE)
        result = self.provider.chat_completion(
            [{"role": "user", "content": "Hi"}],
            model="openai/gpt-4o-mini",
        )
        self.assertEqual(result["content"], "This is a test AI response.")
