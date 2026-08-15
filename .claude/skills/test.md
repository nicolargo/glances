# Skill: Run Tests

Run the appropriate Glances test suite based on the current changes or user request.

## Instructions

1. First, check which files have been modified using `git diff --name-only` (staged + unstaged).
2. Determine which test suite(s) to run based on the changed files:
   - Changes in `glances/plugins/` → `make test-plugins` and/or specific `pytest tests/test_plugin_<name>.py`
   - Changes in `glances/outputs/glances_restful_api.py` or `glances/outputs/glances_mcp.py` → `make test-restful`
   - Changes in `glances/outputs/static/` → `make test-webui`
   - Changes in `glances/exports/` → `make test-exports` (requires Docker)
   - Changes in `glances/client.py` or `glances/server.py` → `make test-xmlrpc`
   - Changes in core files (`glances/*.py`) → `make test-core`
   - If unsure or broad changes → `make test` (runs all tests)
3. If the user specifies a test target (e.g., "run core tests"), use that directly.
4. Run the tests using the Makefile targets. The virtualenv must already exist (`.venv-uv/`).
5. If tests fail, analyze the output and suggest fixes.

## Available test commands

```bash
make test              # All tests
make test-core         # Core unit tests
make test-plugins      # Plugin tests
make test-api          # API unit tests
make test-restful      # REST API tests
make test-webui        # WebUI tests (Selenium)
make test-xmlrpc       # XML-RPC tests
make test-exports      # All export integration tests (needs Docker)
make test-perf         # Performance tests
make test-memoryleak   # Memory leak tests

# Single test file or specific test:
.venv-uv/bin/uv run pytest tests/test_core.py
.venv-uv/bin/uv run pytest tests/test_core.py::TestGlances::test_000_update
```
