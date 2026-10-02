# Contributing to LAN AI Chatter Assistant

Thank you for your interest in contributing to **LAN AI Chatter Assistant**! We welcome community contributions, bug reports, and feature enhancements to make Odoo daily communication more productive.

To maintain code stability, security, and consistent quality across all supported Odoo releases, please read and follow these guidelines.

---

## 🔒 Governance & Branch Management Policy

The primary stability branches are **strictly maintained and protected by the project author (@Livinarias)**:

| Branch | Description | Direct Push Policy |
|---|---|---|
| `main` | Base development branch & general documentation | ❌ Protected — Pull Request Only |
| `17.0` | Production release branch for **Odoo 17.0** (Odoo Apps Store) | ❌ Protected — Pull Request Only |
| `18.0` | Production release branch for **Odoo 18.0** | ❌ Protected — Pull Request Only |

> [!IMPORTANT]
> **No direct commits or pushes to `main`, `17.0`, or `18.0` are permitted.** All community contributions must follow the **Fork & Pull Request** workflow described below.

---

## 🛠️ Contribution Workflow (Step-by-Step)

### 1. Fork the Repository
Click the **Fork** button at the top right of this repository to create your own copy under your personal GitHub account.

### 2. Clone Your Fork Locally
```bash
git clone https://github.com/YOUR_USERNAME/ai_chatter_assistant.git
cd ai_chatter_assistant
```

### 3. Create a Dedicated Feature or Fix Branch
Always branch off the target Odoo version you are addressing:
* For Odoo 17 fixes/features: branch from `17.0`
* For Odoo 18 fixes/features: branch from `18.0`
* For general repository tooling: branch from `main`

```bash
# Example for an Odoo 17 feature:
git checkout 17.0
git pull origin 17.0
git checkout -b feature/17.0-your-feature-name

# Example for a bug fix:
git checkout -b fix/17.0-short-description
```

**Branch naming convention:**
* `feature/<version>-<description>`: For new capabilities
* `fix/<version>-<description>`: For bug fixes
* `docs/<description>`: For documentation updates
* `refactor/<version>-<description>`: For code refactoring without behavior change

---

## 📋 Coding Standards & Quality Checks

All code must adhere to the official **OCA (Odoo Community Association)** quality standards.

### 1. Install & Run Pre-commit
We use `pre-commit` to automatically run `black`, `isort`, `flake8`, and `pylint-odoo`:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

### 2. Code Rules
* **Code Formatting:** Formatted with **Black** and **isort** (`--profile=black`).
* **Python Standards:** PEP 8 compliance checked via **Flake8** (`--max-line-length=120`).
* **Odoo Linter:** Validated with **pylint-odoo** for clean API usage and manifest structure.
* **Security & Privacy:**
  * Never hardcode API keys or credentials.
  * Respect the module's AES-128 Fernet encryption architecture.
  * Ensure `ir.config_parameter` keys use the `lan_ai_chatter_assistant.` prefix.
* **Translations:** Wrap all user-facing strings in `_("...")` from `odoo._`.
* **Testing:** Every new feature or bug fix must include corresponding automated tests in `lan_ai_chatter_assistant/tests/`.

---

## ✍️ Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

* `feat(feature-name): add support for new AI model`
* `fix(chatter): resolve timeout issue on large message threads`
* `docs(readme): update setup instructions for Docker`
* `test(lead): add test coverage for empty partner phone`
* `refactor(provider): optimize Anthropic payload builder`

---

## 🚀 Submitting a Pull Request (PR)

1. Push your branch to your fork on GitHub:
   ```bash
   git push -u origin feature/17.0-your-feature-name
   ```
2. Open a Pull Request from your branch into the target upstream branch (`17.0`, `18.0`, or `main`).
3. Fill in the PR description template:
   * **What does this PR do?**
   * **Why is it needed?**
   * **How did you test it?** (Include logs or test commands)
4. Ensure all automated GitHub Actions checks (linting, tests, coverage) pass with a green checkmark.

---

## 🔍 Review and Merge Process

* **Reviewer:** All PRs are reviewed and approved exclusively by the repository maintainer (@Livinarias).
* **Feedback:** If revisions are requested, make the changes in your branch and push again. The PR will update automatically.
* **Merge:** Once approved, your PR will be merged into the target version branch and included in the next release tag.

---

## 🐛 Reporting Bugs & Security Issues

* **Bugs & Enhancements:** Please open an issue in the [GitHub Issues](https://github.com/Livinarias/ai_chatter_assistant/issues) tab. Describe steps to reproduce, expected behavior, and Odoo version.
* **Security Concerns:** For sensitive vulnerabilities, please email the author directly at [livinarias88@gmail.com](mailto:livinarias88@gmail.com) rather than opening a public issue.

---

## 📄 License

By contributing, you agree that your contributions will be licensed under the **GNU Lesser General Public License v3 (LGPL-3)**.
