# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Tests for the DeepSeek provider adapter."""

import unittest
from unittest.mock import patch

from odoo.tests import tagged

from ..services.providers.deepseek_provider import DeepSeekProvider
from .common import MOCK_OPENAI_RESPONSE, _make_mock_response


@tagged("post_install", "-at_install")
class TestDeepSeekProvider(unittest.TestCase):
    """Unit tests for DeepSeekProvider."""

    def setUp(self):
        super().setUp()
        self.provider = DeepSeekProvider(api_key="ds-test-key")

    def test_endpoint(self):
        self.assertEqual(
            self.provider.ENDPOINT,
            "https://api.deepseek.com/v1/chat/completions",
        )

    def test_headers_bearer_token(self):
        headers = self.provider._build_headers()
        self.assertEqual(headers["Authorization"], "Bearer ds-test-key")

    def test_payload_openai_compatible(self):
        msgs = [{"role": "user", "content": "Hi"}]
        payload = self.provider._build_payload(msgs, "deepseek-chat", 0.3, 1024)
        self.assertEqual(payload["model"], "deepseek-chat")
        self.assertIn("messages", payload)

    def test_parse_response_openai_format(self):
        result = self.provider._parse_response(MOCK_OPENAI_RESPONSE)
        self.assertEqual(result["content"], "This is a test AI response.")
        self.assertEqual(result["tokens_used"], 150)

    @patch("ai_chatter_assistant.services.providers.base.requests.post")
    def test_chat_completion_success(self, mock_post):
        mock_post.return_value = _make_mock_response(MOCK_OPENAI_RESPONSE)
        result = self.provider.chat_completion(
            [{"role": "user", "content": "Hi"}],
            model="deepseek-chat",
        )
        self.assertEqual(result["content"], "This is a test AI response.")
        # Verify correct endpoint was called
        call_args = mock_post.call_args
        self.assertIn(
            "deepseek.com",
            (
                call_args[0][0]
                if call_args[0]
                else call_args.kwargs.get("url", call_args[0][0])
            ),
        )
