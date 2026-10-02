# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Tests for the Anthropic Claude provider adapter."""

import unittest
from unittest.mock import patch

from odoo.tests import tagged

from ..services.providers.anthropic_provider import AnthropicProvider
from .common import MOCK_ANTHROPIC_RESPONSE, _make_mock_response


@tagged("post_install", "-at_install")
class TestAnthropicProvider(unittest.TestCase):
    """Unit tests for AnthropicProvider — all HTTP calls are mocked."""

    def setUp(self):
        super().setUp()
        self.provider = AnthropicProvider(api_key="sk-ant-test-key")

    # -- Headers --------------------------------------------------------

    def test_headers_use_x_api_key(self):
        headers = self.provider._build_headers()
        self.assertEqual(headers["x-api-key"], "sk-ant-test-key")
        self.assertEqual(headers["anthropic-version"], "2023-06-01")
        self.assertNotIn("Authorization", headers)

    # -- Payload --------------------------------------------------------

    def test_system_prompt_extracted_to_top_level(self):
        """System messages are moved to the top-level 'system' field."""
        msgs = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
        ]
        payload = self.provider._build_payload(msgs, "claude-3-5-haiku", 0.3, 1024)
        self.assertEqual(payload["system"], "You are helpful.")
        # User message should remain, system should not be in messages
        self.assertEqual(len(payload["messages"]), 1)
        self.assertEqual(payload["messages"][0]["role"], "user")

    def test_payload_without_system_prompt(self):
        """No 'system' key when there is no system message."""
        msgs = [{"role": "user", "content": "Hello"}]
        payload = self.provider._build_payload(msgs, "claude-3-5-haiku", 0.5, 512)
        self.assertNotIn("system", payload)

    # -- Response parsing -----------------------------------------------

    def test_parse_valid_response(self):
        result = self.provider._parse_response(MOCK_ANTHROPIC_RESPONSE)
        self.assertEqual(result["content"], "This is a test AI response from Claude.")
        self.assertEqual(result["tokens_used"], 150)  # 100 + 50

    def test_parse_empty_content_blocks(self):
        result = self.provider._parse_response({"content": []})
        self.assertEqual(result["content"], "")

    # -- Full chat_completion -------------------------------------------

    @patch("ai_chatter_assistant.services.providers.base.requests.post")
    def test_chat_completion_success(self, mock_post):
        mock_post.return_value = _make_mock_response(MOCK_ANTHROPIC_RESPONSE)
        result = self.provider.chat_completion(
            [
                {"role": "system", "content": "Be concise."},
                {"role": "user", "content": "Summarise this."},
            ],
            model="claude-3-5-haiku",
        )
        self.assertIn("Claude", result["content"])
        # Verify the payload sent extracted the system prompt
        call_kwargs = mock_post.call_args
        sent_payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        self.assertEqual(sent_payload["system"], "Be concise.")
