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
make test-v5             # Only v5 unit tests (Phase 1 stack)

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
.venv-uv/bin/uv run python -m glances                       # Standalone TUI (v4)
.venv-uv/bin/uv run python -m glances -w                    # Web server (default port 61208)
.venv-uv/bin/uv run python -m glances -C conf/glances.conf  # With specific config
```

### Running Glances v5 (Phase 1)

```bash
make run-v5              # Start the v5 FastAPI server on :61208 with conf/glances.conf
make run-v5-debug        # Same, debug-level logging
make set-password-v5     # Interactive PBKDF2 hash for [outputs] password — paste into glances.conf

# Equivalent direct invocations:
.venv-uv/bin/uv run python -m glances.main_v5 -C conf/glances.conf
.venv-uv/bin/uv run python -m glances.main_v5 --bind 0.0.0.0 --port 61299
.venv-uv/bin/uv run python -m glances.main_v5 --set-password
```

After the migration completes (Phase 4), the v5 server will become the default `glances` entry point.
