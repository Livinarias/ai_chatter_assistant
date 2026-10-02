# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Tests for services/encryption.py — Fernet API key encryption."""

import os
import unittest
from unittest.mock import patch

from cryptography.fernet import Fernet

from odoo.tests import tagged

from ..services.encryption import decrypt_api_key, encrypt_api_key, _get_fernet


@tagged("post_install", "-at_install")
class TestEncryption(unittest.TestCase):
    """Unit tests for Fernet encrypt/decrypt helpers."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.valid_key = Fernet.generate_key().decode()

    # -- _get_fernet ----------------------------------------------------

    @patch.dict(os.environ, {"AI_ENCRYPTION_KEY": ""})
    def test_get_fernet_missing_key_raises(self):
        """ValueError when AI_ENCRYPTION_KEY is empty."""
        with self.assertRaises(ValueError) as ctx:
            _get_fernet()
        self.assertIn("AI_ENCRYPTION_KEY", str(ctx.exception))

    @patch.dict(os.environ, {"AI_ENCRYPTION_KEY": "not-a-valid-key"})
    def test_get_fernet_invalid_key_raises(self):
        """ValueError when AI_ENCRYPTION_KEY is not a valid Fernet key."""
        with self.assertRaises(ValueError) as ctx:
            _get_fernet()
        self.assertIn("valid Fernet key", str(ctx.exception))

    @patch.dict(os.environ, {})
    def test_get_fernet_unset_key_raises(self):
        """ValueError when AI_ENCRYPTION_KEY is not in the environment."""
        os.environ.pop("AI_ENCRYPTION_KEY", None)
        with self.assertRaises(ValueError):
            _get_fernet()

    # -- encrypt / decrypt roundtrip ------------------------------------

    def test_roundtrip(self):
        """Encrypting then decrypting returns the original plain text."""
        with patch.dict(os.environ, {"AI_ENCRYPTION_KEY": self.valid_key}):
            plain = "sk-abc123XYZ"
            encrypted = encrypt_api_key(plain)
            self.assertNotEqual(encrypted, plain)
            decrypted = decrypt_api_key(encrypted)
            self.assertEqual(decrypted, plain)

    def test_encrypt_empty_string(self):
        """Encrypting an empty string returns an empty string."""
        with patch.dict(os.environ, {"AI_ENCRYPTION_KEY": self.valid_key}):
            self.assertEqual(encrypt_api_key(""), "")

    def test_decrypt_empty_string(self):
        """Decrypting an empty string returns an empty string."""
        with patch.dict(os.environ, {"AI_ENCRYPTION_KEY": self.valid_key}):
            self.assertEqual(decrypt_api_key(""), "")

    def test_decrypt_corrupt_token_raises(self):
        """ValueError when the ciphertext is corrupt."""
        with patch.dict(os.environ, {"AI_ENCRYPTION_KEY": self.valid_key}):
            with self.assertRaises(ValueError) as ctx:
                decrypt_api_key("this-is-not-a-valid-token")
            self.assertIn("Cannot decrypt", str(ctx.exception))

    def test_decrypt_wrong_key_raises(self):
        """ValueError when the master key changed after encryption."""
        key_a = Fernet.generate_key().decode()
        key_b = Fernet.generate_key().decode()

        with patch.dict(os.environ, {"AI_ENCRYPTION_KEY": key_a}):
            encrypted = encrypt_api_key("my-secret")

        with patch.dict(os.environ, {"AI_ENCRYPTION_KEY": key_b}):
            with self.assertRaises(ValueError):
                decrypt_api_key(encrypted)
