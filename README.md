# AI Chatter & CRM Assistant — Odoo Module

[![CI](https://github.com/Livinarias/ai_chatter_assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/Livinarias/ai_chatter_assistant/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/Livinarias/ai_chatter_assistant/branch/main/graph/badge.svg)](https://codecov.io/gh/Livinarias/ai_chatter_assistant)
[![License: LGPL-3](https://img.shields.io/badge/License-LGPL--3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)

> 🤖 AI-powered assistant for Odoo Chatter & CRM — summarise threads, draft replies and generate leads.

## Features

| Feature | Description |
|---|---|
| 🧠 **Chatter Summary** | Summarise the latest thread messages into 3 executive bullet points |
| ✨ **AI Reply Draft** | Generate context-aware reply drafts with optional custom instructions |
| 🎯 **CRM Lead Generation** | Extract contact, company and opportunity data from e-mails in 1 click |
| 🔌 **Multi-Provider** | OpenAI, Anthropic Claude, DeepSeek, OpenRouter — pluggable via Strategy + Factory |
| 🔐 **Dual Encryption Modes** | Simple mode (auto-generated key) or Secure mode (environment variable) |
| ⚡ **Rate Limiting** | Per-user hourly limits, configurable from Settings |
| 📊 **Usage Logging** | Full audit trail in `ai.usage.log` (auto-cleaned after 30 days) |

## Compatibility

| Odoo Version | Status |
|---|---|
| 17.0 (Community & Enterprise) | ✅ Supported |
| 18.0 (Community & Enterprise) | ✅ Supported |

## Installation

1. Clone into your Odoo addons path:
   ```bash
   git clone https://github.com/Livinarias/ai_chatter_assistant.git
   ```

2. Install Python dependencies:
   ```bash
   pip install cryptography requests
   ```

3. Choose your encryption mode:
   - **Simple Mode (Default):** Zero configuration needed! The AES-128 Fernet key is generated automatically in System Parameters upon first saving.
   - **Secure Mode (Recommended for production):** Set the encryption master key in your environment:
     ```bash
     export AI_ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
     ```

4. Restart Odoo and install the module from **Apps**.

## Configuration

1. Go to **Settings → General Settings → AI Assistant**.
2. Select your AI provider (OpenAI, Anthropic, DeepSeek, OpenRouter).
3. Enter your API key (it will be encrypted automatically).
4. Choose the model name (e.g. `gpt-4o-mini`, `claude-3-5-haiku`).
5. Click **Test Connection** to verify.

## Architecture

```
Strategy + Factory pattern for providers
├── AIProvider (abstract base)
├── OpenAIProvider
├── AnthropicProvider
├── DeepSeekProvider
└── OpenRouterProvider

@ai_feature decorator → permissions + rate limit + logging
Fernet encryption → API keys at rest
Record Rules → config params hidden from non-admins
```

## Development

### Pre-commit hooks

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

### Running tests

```bash
odoo-bin --test-enable --stop-after-init -d test_db -i ai_chatter_assistant
```

### Coverage

```bash
coverage run --source=ai_chatter_assistant odoo-bin --test-enable --stop-after-init -d test_db -i ai_chatter_assistant
coverage report
```

## License

This module is licensed under [LGPL-3](https://www.gnu.org/licenses/lgpl-3.0.html).
