# Skill: Debug a Glances Issue

Help diagnose and fix a bug in Glances.

## Instructions

1. **Understand the issue**: Ask for or identify:
   - Error message or traceback
   - Glances version and OS
   - How to reproduce (standalone, web server, client/server, Docker?)
   - Relevant config section from `glances.conf`

2. **Locate the code path**: Based on the mode and plugin involved:
   - Standalone TUI: `glances/standalone.py` → `glances/outputs/glances_curses.py`
   - Web server: `glances/webserver.py` → `glances/outputs/glances_restful_api.py`
   - Client/server: `glances/client.py` / `glances/server.py`
   - Plugin issue: `glances/plugins/<name>/__init__.py`
   - Export issue: `glances/exports/glances_<name>/__init__.py`
   - Process list: `glances/processes.py`
   - Configuration: `glances/config.py`

3. **Run Glances in debug mode** to get detailed logs:
   ```bash
   .venv-uv/bin/uv run python -m glances -d 2>&1 | tail -100
   ```

4. **Reproduce with tests** when possible:
   ```bash
   .venv-uv/bin/uv run pytest tests/test_core.py -v -k "test_name" 2>&1
   ```

5. **Fix and verify**:
   - Apply surgical, atomic edits
   - Run the relevant test suite
   - Run `make format && make lint`
   - Verify no regressions with `make test-core`

## Common pitfalls

- **psutil version differences**: Some psutil APIs behave differently across OS — always check `glances/globals.py` for platform flags (`LINUX`, `MACOS`, `WINDOWS`, `BSD`)
- **Plugin update cycle**: Stats are `None` on first call — handle gracefully
- **Snap confinement**: `PermissionError` at `open()`, not at `read()` — wrap the right call
- **Docker socket access**: Requires mounting `/var/run/docker.sock` and proper permissions
