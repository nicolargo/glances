# Glances Common Commands

## Development Setup

```bash
make install-uv          # Install UV in .venv-uv/
make venv-dev            # Create virtualenv with all deps + dev tools + pre-commit hooks
```

## Tests

```bash
make test                # All tests (via pytest)
make test-core           # Core unit tests (tests/test_core.py)
make test-plugins        # Plugin tests (tests/test_plugin_*.py)
make test-restful        # REST API tests (tests/test_routes.py, tests/test_webserver.py)
make test-webui          # WebUI tests (browser tests need Playwright + Chromium)
make test-js             # WebUI JavaScript unit tests (node --test tests/js/*.mjs)
make test-exports        # All export integration tests (shell scripts, need Docker)

# Single test file or specific test:
.venv-uv/bin/uv run pytest tests/test_core.py
.venv-uv/bin/uv run pytest tests/test_core.py::TestGlances::test_016_subsample
```

## Linting & Formatting

```bash
make format              # Ruff format
make lint                # Ruff check --fix
make pre-commit          # All pre-commit hooks (ruff, gitleaks, shellcheck, etc.)
```

## WebUI

```bash
make webui               # npm ci && npm run build (outputs public/glances.js + public/browser.js in glances/outputs/static/)
```

## Running Glances

```bash
make run                 # Standalone TUI with conf/glances.conf
make run-debug           # Same, debug-level logging
make run-webserver       # Web server (REST API + WebUI) on :61208 with conf/glances.conf
make run-webserver-mcp   # Same, with the MCP server
make run-client          # TUI client of a local server (-c localhost)
make set-password        # Interactive PBKDF2 hash for [outputs] password — paste into glances.conf

# Equivalent direct invocations:
.venv-uv/bin/uv run python -m glances                       # Standalone TUI
.venv-uv/bin/uv run python -m glances -w                    # Web server (default port 61208)
.venv-uv/bin/uv run python -m glances -C conf/glances.conf  # With specific config
.venv-uv/bin/uv run python -m glances -w --bind 0.0.0.0 --port 61299
.venv-uv/bin/uv run python -m glances --set-password
```
