# Contributing to better-telegram-mcp

Thank you for your interest in contributing to better-telegram-mcp! This guide will help you get started.

## Getting Started

### Prerequisites

- **mise** (recommended) or **Python 3.13+** and **uv**
- Git
- A GitHub account

**Recommended:** Use [mise](https://mise.jdx.dev/) to automatically manage Python and uv versions from `.mise.toml`.

### Setup Development Environment

1. **Fork the repository** and clone your fork

```bash
git clone https://github.com/YOUR_USERNAME/better-telegram-mcp
cd better-telegram-mcp
```

2. **Install tools and dependencies**

If using **mise** (recommended):

```bash
mise run setup
```

Without mise, ensure you have Python 3.13+ and uv installed:

```bash
uv sync --group dev
uv run pre-commit install
```

3. **Run checks**

```bash
uv run ruff check .
uv run ruff format --check .
```

## Development Workflow

### Running Locally

```bash
# Bot mode
export TELEGRAM_BOT_TOKEN="your-bot-token"
uv run better-telegram-mcp

# User mode
export TELEGRAM_API_ID="your-api-id"
export TELEGRAM_API_HASH="your-api-hash"
uv run better-telegram-mcp auth  # First time only
uv run better-telegram-mcp
```

### Making Changes

1. Create a new branch: `git checkout -b feature/your-feature-name`
2. Make your changes
3. Run checks: `uv run ruff check . && uv run ruff format .`
4. Run tests: `uv run pytest`
5. Commit your changes (see [Commit Convention](#commit-convention))
6. Push to your fork: `git push origin feature/your-feature-name`
7. Open a Pull Request

## Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

```text
<type>[optional scope]: <description>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `ci`: CI/CD changes
- `build`: Build system changes

### Examples

```text
feat: add support for inline keyboards
fix: handle Telethon session expiry
docs: update configuration examples
```

## Release Process

Releases are automated using **python-semantic-release (PSR) v10**. We strictly follow the **Conventional Commits** specification to determine version bumps and generate changelogs automatically.

### How to Release

1. Create a Pull Request with your changes.
2. Ensure your commit messages follow the convention above.
3. Merge the PR to `main`.
4. A maintainer triggers the CD workflow manually via **workflow_dispatch**:
   - Choose `beta` or `stable` release type.
   - PSR analyzes commits since the last release.
   - Bumps version, updates `CHANGELOG.md`, creates a tag.
   - Publishes to PyPI.
   - Creates a GitHub Release.
   - Builds and pushes Docker images.

You do **not** need to create manual tags or changelog entries.

## Pull Request Guidelines

- Keep PRs focused on a single feature or fix
- Update documentation if needed
- Add tests for new functionality
- Ensure all checks pass

### PR Checklist

Before submitting your PR, ensure:

- [ ] Code follows Python best practices
- [ ] All tests pass (`uv run pytest`)
- [ ] Linting passes (`uv run ruff check .`)
- [ ] Formatting is correct (`uv run ruff format --check .`)
- [ ] Commit messages follow **Conventional Commits**
- [ ] Documentation updated (if needed)

## Code Style

This project uses **Ruff** for formatting and linting.

```bash
uv run ruff check .       # Check for issues
uv run ruff check --fix . # Auto-fix issues
uv run ruff format .      # Format code
```

## Testing

```bash
uv run pytest              # Run all tests
uv run pytest -v           # Verbose output
uv run pytest --tb=short   # Short tracebacks
```

## Project Structure

```text
better-telegram-mcp/
├── src/
│   └── better_telegram_mcp/
│       ├── __init__.py
│       ├── config.py          # Configuration (Pydantic Settings)
│       ├── server.py          # MCP server (FastMCP)
│       ├── cli.py             # Auth CLI
│       ├── backends/
│       │   ├── base.py        # TelegramBackend ABC
│       │   ├── bot_backend.py # Bot API (httpx)
│       │   └── user_backend.py# MTProto (Telethon)
│       └── tools/             # 6 mega-tools
├── tests/
├── pyproject.toml
└── README.md
```

## Questions?

Feel free to open an issue for:

- Bug reports
- Feature requests
- Questions about the codebase
- Discussion about architecture

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing!**
