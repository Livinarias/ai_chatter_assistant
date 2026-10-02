# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Tests for the OpenAI provider adapter."""

import unittest
from unittest.mock import patch

from odoo.tests import tagged

from ..services.providers.base import AIProviderError
from ..services.providers.openai_provider import OpenAIProvider
from .common import MOCK_OPENAI_RESPONSE, _make_mock_response


@tagged("post_install", "-at_install")
class TestOpenAIProvider(unittest.TestCase):
    """Unit tests for OpenAIProvider — all HTTP calls are mocked."""

    def setUp(self):
        super().setUp()
        self.provider = OpenAIProvider(api_key="sk-test-key")

    # -- Headers --------------------------------------------------------

    def test_headers_contain_bearer_token(self):
        headers = self.provider._build_headers()
        self.assertEqual(headers["Authorization"], "Bearer sk-test-key")
        self.assertEqual(headers["Content-Type"], "application/json")

    # -- Payload --------------------------------------------------------

    def test_payload_format(self):
        msgs = [{"role": "user", "content": "Hello"}]
        payload = self.provider._build_payload(msgs, "gpt-4o-mini", 0.5, 512)
        self.assertEqual(payload["model"], "gpt-4o-mini")
        self.assertEqual(payload["messages"], msgs)
        self.assertEqual(payload["temperature"], 0.5)
        self.assertEqual(payload["max_tokens"], 512)

    # -- Response parsing -----------------------------------------------

    def test_parse_valid_response(self):
        result = self.provider._parse_response(MOCK_OPENAI_RESPONSE)
        self.assertEqual(result["content"], "This is a test AI response.")
        self.assertEqual(result["tokens_used"], 150)

    def test_parse_empty_choices(self):
        result = self.provider._parse_response({"choices": []})
        self.assertEqual(result["content"], "")
        self.assertEqual(result["tokens_used"], 0)

    # -- Full chat_completion -------------------------------------------

    @patch("ai_chatter_assistant.services.providers.base.requests.post")
    def test_chat_completion_success(self, mock_post):
        mock_post.return_value = _make_mock_response(MOCK_OPENAI_RESPONSE)
        result = self.provider.chat_completion(
            [{"role": "user", "content": "Hi"}],
            model="gpt-4o-mini",
        )
        self.assertEqual(result["content"], "This is a test AI response.")
        mock_post.assert_called_once()

    @patch("ai_chatter_assistant.services.providers.base.requests.post")
    def test_chat_completion_401_raises(self, mock_post):
        mock_post.return_value = _make_mock_response(
            {"error": {"message": "Invalid key"}}, status_code=401
        )
        with self.assertRaises(AIProviderError) as ctx:
            self.provider.chat_completion(
                [{"role": "user", "content": "Hi"}], model="gpt-4o-mini"
            )
        self.assertIn("Invalid or expired", str(ctx.exception))

    @patch("ai_chatter_assistant.services.providers.base.requests.post")
    def test_chat_completion_429_raises(self, mock_post):
        mock_post.return_value = _make_mock_response({}, status_code=429)
        with self.assertRaises(AIProviderError) as ctx:
            self.provider.chat_completion(
                [{"role": "user", "content": "Hi"}], model="gpt-4o-mini"
            )
        self.assertIn("Rate limit", str(ctx.exception))

    @patch("ai_chatter_assistant.services.providers.base.requests.post")
    def test_chat_completion_timeout_raises(self, mock_post):
        import requests as req

        mock_post.side_effect = req.Timeout("timed out")
        with self.assertRaises(AIProviderError) as ctx:
            self.provider.chat_completion(
                [{"role": "user", "content": "Hi"}], model="gpt-4o-mini"
            )
        self.assertIn("timed out", str(ctx.exception))

    @patch("ai_chatter_assistant.services.providers.base.requests.post")
    def test_chat_completion_connection_error_raises(self, mock_post):
        import requests as req

        mock_post.side_effect = req.ConnectionError("no route")
        with self.assertRaises(AIProviderError) as ctx:
            self.provider.chat_completion(
                [{"role": "user", "content": "Hi"}], model="gpt-4o-mini"
            )
        self.assertIn("Could not connect", str(ctx.exception))

    # -- Test connection ------------------------------------------------

    @patch("ai_chatter_assistant.services.providers.base.requests.post")
    def test_test_connection_success(self, mock_post):
        mock_post.return_value = _make_mock_response(MOCK_OPENAI_RESPONSE)
        self.assertTrue(self.provider.test_connection(model="gpt-4o-mini"))

    # -- Constructor ----------------------------------------------------

    def test_empty_api_key_raises(self):
        with self.assertRaises(AIProviderError):
            OpenAIProvider(api_key="")
