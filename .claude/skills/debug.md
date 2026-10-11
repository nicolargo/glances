# Skill: Debug a Glances Issue

Help diagnose and fix a bug in Glances.

## Instructions

1. **Understand the issue**: Ask for or identify:
   - Error message or traceback
   - Glances version and OS
   - How to reproduce (standalone, web server, client/server, Docker?)
   - Relevant config section from `glances.conf`

2. **Locate the code path**: Based on the mode and plugin involved:
   - Startup / CLI: `glances/main.py`
   - Standalone TUI: `glances/outputs/glances_curses.py` (`Tui`) → `glances/outputs/curses_renderer.py`
   - Web server: `glances/webserver.py` → `glances/routes.py`
   - WebUI: `glances/outputs/static/js/`
   - Client/server: `glances/client.py` (`-c`, over the REST API) / `glances/webserver.py` (`-s`)
   - Scheduler / alerts: `glances/scheduler.py` / `glances/alerts.py`
   - Plugin issue: `glances/plugins/<name>/model.py` (TUI layout: `render_curses.py`)
   - Export issue: `glances/exports/glances_<name>/export.py`
   - Process list: `glances/processes.py`
   - Configuration: `glances/config.py`

3. **Run Glances in debug mode** to get detailed logs:
   ```bash
   .venv-uv/bin/uv run python -m glances -d 2>&1 | tail -100
   ```

4. **Reproduce with tests** when possible:
   ```bash
   .venv-uv/bin/uv run pytest tests/test_plugin_<name>.py -v -k "test_name" 2>&1
   ```

5. **Fix and verify**:
   - Apply surgical, atomic edits
   - Run the relevant test suite
   - Run `make format && make lint`
   - Verify no regressions with `make test`

## Common pitfalls

- **psutil version differences**: Some psutil APIs behave differently across OS — always check `glances/globals.py` for platform flags (`LINUX`, `MACOS`, `WINDOWS`, `BSD`)
- **Plugin update cycle**: a plugin has no payload before its first update (`GET /api/5/<plugin>` → `200 null`), and `rate: True` fields are absent on the first cycle — handle gracefully
- **Snap confinement**: `PermissionError` at `open()`, not at `read()` — wrap the right call
- **Docker socket access**: Requires mounting `/var/run/docker.sock` and proper permissions
