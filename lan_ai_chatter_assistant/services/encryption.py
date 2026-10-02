# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Fernet symmetric encryption utilities for API key storage.

Supports two encryption modes:
1. 'simple' (Default): Master key is auto-generated and stored in Odoo
   system parameters (``ir.config_parameter``) under
   ``ai_chatter_assistant.encryption_key``.
2. 'secure': Master key is strictly injected via the ``AI_ENCRYPTION_KEY``
   environment variable (e.g. from docker-compose / OS secrets).
"""

import logging
import os

from cryptography.fernet import Fernet, InvalidToken

_logger = logging.getLogger(__name__)

_PARAM_KEY = "ai_chatter_assistant.encryption_key"
_PARAM_MODE = "ai_chatter_assistant.ai_encryption_mode"


def _resolve_env(env=None):
    """Attempt to resolve an Odoo Environment."""
    if env is not None:
        return env
    try:
        from odoo.http import request

        if request and hasattr(request, "env") and request.env:
            return request.env
    except Exception:
        pass
    return None


def is_env_key_present() -> bool:
    """Return True if AI_ENCRYPTION_KEY is defined in environment."""
    return bool(os.environ.get("AI_ENCRYPTION_KEY", "").strip())


def get_encryption_mode(env=None) -> str:
    """Return the active encryption mode: 'simple' or 'secure'."""
    resolved_env = _resolve_env(env)
    if resolved_env is not None:
        try:
            ICP = resolved_env["ir.config_parameter"].sudo()
            mode = ICP.get_param(_PARAM_MODE, "simple")
            if mode in ("simple", "secure"):
                return mode
        except Exception as exc:
            _logger.debug("Could not read ai_encryption_mode: %s", exc)
    return "simple"


def get_encryption_key(env=None, mode=None) -> str:
    """Return the Fernet master key for the specified mode.

    Args:
        env: Odoo Environment (optional).
        mode: 'simple' or 'secure'. If None, reads from config parameter.

    Raises:
        ValueError: If mode is 'secure' and AI_ENCRYPTION_KEY is missing/invalid,
                    or if mode is 'simple' and key cannot be obtained.
    """
    resolved_env = _resolve_env(env)
    if not mode:
        mode = get_encryption_mode(resolved_env)

    if mode == "secure":
        env_key = os.environ.get("AI_ENCRYPTION_KEY", "").strip()
        if not env_key:
            raise ValueError(
                "The environment variable AI_ENCRYPTION_KEY is not set. "
                "Generate one with: "
                'python -c "from cryptography.fernet import Fernet; '
                'print(Fernet.generate_key().decode())"'
            )
        try:
            Fernet(env_key.encode())
        except Exception as exc:
            raise ValueError("AI_ENCRYPTION_KEY is not a valid Fernet key.") from exc
        return env_key

    # mode == "simple"
    if resolved_env is not None:
        try:
            ICP = resolved_env["ir.config_parameter"].sudo()
            stored_key = ICP.get_param(_PARAM_KEY, "").strip()
            if stored_key:
                return stored_key
            # Auto-generate key in system parameters on first use
            new_key = Fernet.generate_key().decode()
            ICP.set_param(_PARAM_KEY, new_key)
            _logger.info(
                "Generated and saved new AI master encryption key in ir.config_parameter."
            )
            return new_key
        except Exception as exc:
            _logger.warning("Could not access ir.config_parameter: %s", exc)

    # Fallback if no database environment is available (e.g. unit tests without DB)
    fallback_env = os.environ.get("AI_ENCRYPTION_KEY", "").strip()
    if not fallback_env:
        raise ValueError(
            "The environment variable AI_ENCRYPTION_KEY is not set. "
            "Generate one with: "
            'python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"'
        )
    try:
        Fernet(fallback_env.encode())
    except Exception as exc:
        raise ValueError("AI_ENCRYPTION_KEY is not a valid Fernet key.") from exc
    return fallback_env


def _get_fernet(env=None, mode=None) -> Fernet:
    """Return a Fernet instance initialised with the key for the given mode."""
    raw_key = get_encryption_key(env=env, mode=mode)
    try:
        return Fernet(raw_key.encode())
    except Exception as exc:
        raise ValueError("AI_ENCRYPTION_KEY is not a valid Fernet key.") from exc


def encrypt_api_key(plain_key: str, env=None, mode=None) -> str:
    """Encrypt plain_key and return ciphertext as a UTF-8 string."""
    if not plain_key:
        return ""
    fernet = _get_fernet(env=env, mode=mode)
    return fernet.encrypt(plain_key.encode("utf-8")).decode("utf-8")


def decrypt_api_key(encrypted_key: str, env=None, mode=None) -> str:
    """Decrypt encrypted_key previously produced by encrypt_api_key.

    Tries the configured mode first. If decryption fails, tries the alternate
    mode in case the key was encrypted under a previous mode before switching.
    """
    if not encrypted_key:
        return ""

    primary_mode = mode or get_encryption_mode(env)
    try:
        fernet = _get_fernet(env=env, mode=primary_mode)
        return fernet.decrypt(encrypted_key.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        # Attempt fallback to the other mode
        alt_mode = "simple" if primary_mode == "secure" else "secure"
        try:
            alt_fernet = _get_fernet(env=env, mode=alt_mode)
            decrypted = alt_fernet.decrypt(encrypted_key.encode("utf-8")).decode(
                "utf-8"
            )
            _logger.info("Decrypted API key using alternate mode '%s'.", alt_mode)
            return decrypted
        except Exception:
            pass

        _logger.error(
            "Failed to decrypt API key – token invalid or master key changed."
        )
        raise ValueError(
            "Cannot decrypt the stored API key. "
            "The encryption key or mode may have changed since the value was saved."
        )
