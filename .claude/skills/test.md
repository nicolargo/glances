# Skill: Run Tests

Run the appropriate Glances test suite based on the current changes or user request.

## Instructions

1. First, check which files have been modified using `git diff --name-only` (staged + unstaged).
2. Determine which test suite(s) to run based on the changed files:
   - Changes in `glances/plugins/` → `make test-plugins` and/or specific `pytest tests/test_plugin_<name>.py`
   - Changes in `glances/webserver.py` or `glances/routes.py` → `make test-restful`
   - Changes in `glances/outputs/glances_mcp.py` or `glances/outputs/mcp_adapter.py` → `pytest tests/test_mcp_adapter.py`
   - Changes in `glances/outputs/static/` → `make test-js` and `make test-webui`
   - Changes in `glances/exports/` → `pytest tests/test_export_*.py`; `make test-exports` for the integration scripts (requires Docker)
   - Changes in `glances/client.py` → `pytest tests/test_client.py`
   - Changes in core files (`glances/*.py`) → the matching `tests/test_<module>.py`, then `make test`
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
make test-restful      # REST API tests (routes + webserver)
make test-webui        # WebUI tests (browser tests need Playwright + Chromium)
make test-js           # WebUI JavaScript unit tests (Node.js)
make test-exports      # All export integration tests (needs Docker)
make memory-leak       # Memory leak profiling

# Single test file or specific test:
.venv-uv/bin/uv run pytest tests/test_core.py
.venv-uv/bin/uv run pytest tests/test_core.py::TestGlances::test_016_subsample
```
