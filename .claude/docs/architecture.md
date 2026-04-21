# Glances Architecture

## Modes (selected in `glances/main.py` -> dispatched in `glances/__init__.py`)

- **Standalone** -- curses TUI (`glances/standalone.py`)
- **Client/Server** -- XML-RPC remote monitoring (`glances/client.py`, `glances/server.py`)
- **Web server** -- FastAPI REST API + Vue.js WebUI + optional MCP (`glances/webserver.py`)

## Stats Engine (`glances/stats.py`)

Central orchestrator that dynamically discovers and loads all plugins and
exports. Exposes `get<PluginName>()` magic methods. Runs plugin updates
concurrently.

## Plugin System (`glances/plugins/`)

- **Base class:** `GlancesPluginModel` in `glances/plugins/plugin/model.py`
- **Convention:** each plugin lives in `glances/plugins/<name>/__init__.py`,
  exports a class inheriting from `GlancesPluginModel`
- **Interface:** `update()` fetches data (typically from psutil), stores in
  `self.stats`; `fields_description` dict declares field metadata (unit,
  thresholds, rates, alerts)
- **Dependency DAG:** `glances/plugins/plugin/dag.py` -- declares inter-plugin
  dependencies (e.g. `cpu` depends on `core`), used by the REST API to resolve
  fetch order
- **Auto-discovery:** plugins are discovered automatically -- no central
  registration needed; just add a new directory under `glances/plugins/`
- **~39 plugins:** cpu, mem, memswap, network, diskio, fs, containers, gpu,
  sensors, processlist, alert, etc.

## Export System (`glances/exports/`)

- **Base class:** `GlancesExport` in `glances/exports/export.py`
- **Convention:** each exporter in `glances/exports/glances_<name>/__init__.py`,
  class named `Export`
- **Auto-discovery:** same pattern as plugins -- no central registration needed
- **Non-exportable plugins** (hardcoded filter): alert, help, plugin,
  psutilversion, quicklook, version
- **~26 exporters:** CSV, JSON, InfluxDB (v1/v2/v3), Prometheus, Elasticsearch,
  Kafka, MQTT, etc.

## REST API (`glances/outputs/glances_restful_api.py`)

FastAPI app with Basic + JWT auth, CORS, optional TLS, DNS rebinding
protection. Endpoints under `/api/<plugin>` for stats, `/api/<plugin>/history`
for time-series.

All new configuration keys must be declared and loaded in
`GlancesRestfulApi.load_config()`. Advanced options use config-file keys only
(no CLI flag) -- follow the `cors_origins` pattern.

## MCP Server (`glances/outputs/glances_mcp.py`)

FastMCP-based, mounted as ASGI in the FastAPI app. Provides resources (plugin
stats, limits, history) and prompts (system health, alerts analysis).

## Process Manager (`glances/processes.py`)

Complex module (~31 KB) managing the process list with threading, sorting, and
filtering. Used by the `processlist` plugin.

## Configuration (`glances/config.py`)

INI format, searched in `~/.config/glances/`, `/etc/glances/`, and bundled
`conf/`. Per-plugin sections with thresholds and options. Sensitive keys
(passwords, tokens, API keys) are filtered from public API responses.
