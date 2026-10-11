# Glances Architecture

## Modes (entry point `glances/__init__.py::main` -> `glances/main.py::main`)

`glances/main.py` parses the CLI and assembles the stack: config -> plugins
-> `StatsStore` -> `GlancesAlerts` -> `AsyncScheduler` -> FastAPI app.

- **Standalone** -- curses TUI (`Tui` in `glances/outputs/glances_curses.py`),
  no TCP socket bound
- **Server** -- `-s` / `-w`: FastAPI REST API + Vue.js WebUI + optional MCP
  (`glances/webserver.py`); headless, `--disable-webui` for REST only
- **Client** -- `-c <server>`: the TUI fed by a remote v5 server over
  `/api/5/all` (`glances/client.py`); there is no XML-RPC any more
- **Browser** -- `--browser`: server list in the TUI
  (`glances/outputs/browser_curses.py`), or in the WebUI with `-w --browser`

## Scheduler and store

- **`AsyncScheduler`** (`glances/scheduler.py`) -- one asyncio task per
  plugin, each calling `plugin.update()` at its own `refresh_time`; also runs
  the alerts ingest and the export loop
- **`StatsStore`** (`glances/stats_store.py`) -- latest payload per plugin;
  writes serialised, reads lockless (TUI thread, REST API, exporters)
- **`GlancesAlerts`** (`glances/alerts.py`) -- level transitions, history,
  fire-and-forget actions (`glances/actions/`)

## Plugin System (`glances/plugins/`)

- **Base class:** `GlancesPluginBase[T]` in `glances/plugins/plugin/base.py`
  (thresholds in `glances/plugins/plugin/thresholds.py`)
- **Convention:** each plugin lives in `glances/plugins/<name>/model.py`,
  class named `PluginModel`; optional per-plugin TUI layout in
  `glances/plugins/<name>/render_curses.py`
- **Interface:** `async _grab_stats()` is the only mandatory hook; the base
  class `update()` pipeline transforms, computes `_levels` and writes to the
  store. `fields_description` declares field metadata (unit, thresholds,
  rates, primary key, exportable)
- **Auto-discovery:** `discover_plugins()` in `glances/main.py` imports every
  `glances.plugins.<name>.model` -- no central registration needed
- **~34 plugins:** cpu, mem, memswap, network, diskio, fs, containers, gpu,
  sensors, processlist, etc.

## Export System (`glances/exports/`)

- **Base class:** `GlancesExportBase` in `glances/exports/export_base.py`
- **Convention:** each exporter in `glances/exports/glances_<name>/export.py`,
  class named `Export`
- **Auto-discovery:** `discover_exporters()` in `glances/main.py`, enabled by
  `--export <name>` -- no central registration needed
- **Non-exportable plugins** (`EXPORTABLE = False`): psutilversion,
  quicklook, version
- **~24 exporters:** CSV, JSON, InfluxDB (v1/v2/v3), Prometheus, Elasticsearch,
  Kafka, MQTT, etc.

## REST API (`glances/webserver.py` + `glances/routes.py`)

FastAPI app with Basic + JWT auth (`glances/security.py`), CORS, rate limiting
(`glances/ratelimit.py`), optional TLS, DNS rebinding protection. Endpoints
under `/api/5/<plugin>` for stats, `/api/5/<plugin>/history` for time-series.

Every configuration key is read with `config.get(section, key, default)` --
always with a default. Advanced options use config-file keys only (no CLI
flag) -- follow the `cors_origins` pattern.

## MCP Server (`glances/outputs/glances_mcp.py`)

FastMCP-based, mounted as ASGI in the FastAPI app (`attach_mcp()` in
`glances/webserver.py`). Provides resources (plugin stats, limits, history)
and prompts (system health, alerts analysis).

## WebUI (`glances/outputs/static/`)

Vue.js 3 sources in `js/` (entries `js/app.js`, `js/browser_app.js`), styles
in `css/glances.css`, templates `templates/index.html` / `browser.html`;
`make webui` builds `public/glances.js` and `public/browser.js`.

## Process Manager (`glances/processes.py`)

Complex module (~37 KB) managing the process list with threading, sorting, and
filtering. Used by the `processlist` plugin.

## Configuration (`glances/config.py`)

`GlancesConfig`: INI format, layered overlay of `/etc/glances/glances.conf`,
`~/.config/glances/glances.conf`, `$GLANCES_CONFIG_FILE`, `-C <path>`, then
`GLANCES_<SECTION>__<KEY>` env vars. Per-plugin sections with thresholds and
options. Sensitive keys (passwords, tokens, API keys) are filtered from public
API responses.
