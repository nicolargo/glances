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
make test-restful        # REST API tests
make test-webui          # Selenium WebUI tests
make test-exports        # All export integration tests (shell scripts, need Docker)

# Single test file or specific test:
.venv-uv/bin/uv run pytest tests/test_core.py
.venv-uv/bin/uv run pytest tests/test_core.py::TestGlances::test_000_update
```

## Linting & Formatting

```bash
make format              # Ruff format
make lint                # Ruff check --fix
make pre-commit          # All pre-commit hooks (ruff, gitleaks, shellcheck, etc.)
```

## WebUI

```bash
make webui               # npm ci && npm run build (outputs to glances/outputs/static/public/)
```

## Running Glances

```bash
.venv-uv/bin/uv run python -m glances                       # Standalone TUI
.venv-uv/bin/uv run python -m glances -w                    # Web server (default port 61208)
.venv-uv/bin/uv run python -m glances -C conf/glances.conf  # With specific config
```
