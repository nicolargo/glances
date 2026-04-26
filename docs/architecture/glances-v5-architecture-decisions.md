# Glances v5.0 — Architecture Decisions

## Status: Baseline locked — ready for implementation
_Last updated: 2026-04-06_

---

## Diagrams

### Overall architecture

![Glances v5.0 — overall architecture](./glances-v5-architecture.svg)

### Remote monitoring topology (server / client modes)

![Glances v5.0 — remote monitoring topology](./glances-v5-network-topology.svg)

---

## 1. Core architecture

### 1.1 Removal of XML-RPC server

- The XML-RPC server (`:61209`) and its client are **removed entirely**.
- The remote monitoring feature (client TUI monitoring a remote server) is **preserved**, migrated to HTTP REST.
- A Glances instance in **server mode** exposes a single REST API on `:61208`.
- A Glances instance in **client mode** instantiates `GlancesPluginRemote` objects (httpx async) instead of local psutil plugins. Same `GlancesPluginBase` interface, different data source.
- **No backward compatibility** between v4 and v5. A v5 client cannot talk to a v4 server. Assumed breaking change for a major version.

### 1.2 Async plugin update loop

- Core architecture is **asyncio-based**.
- The `Asyncio Scheduler` runs `asyncio.gather()` with per-plugin `refresh_time`.
- All blocking psutil calls are wrapped with `asyncio.to_thread()` — uniformly, without exception, regardless of actual blocking duration.
- A plugin that fails during `update()` logs a warning and leaves stale data in the store. It **never crashes the gather loop**.

### 1.3 StatsStore

- Single shared `dict` protected by `asyncio.Lock` for writes.
- Reads (TUI thread, REST API, exporters) are **lockless** — consumers read between two scheduler cycles.
- No pub/sub, no event queue in v5.0.
- A `subscribe()` stub interface may be prepared for future migration but is not implemented in v5.

### 1.4 Curses TUI integration

- The TUI runs in a **dedicated thread**, reading the StatsStore synchronously.
- Curses is not async-native; a thread avoids blocking the asyncio event loop.
- The thread reads the StatsStore without a lock (same lockless contract as other consumers).

---

## 2. Configuration — GlancesConfig

- Backend: `ConfigParser` (stdlib). No new mandatory dependency.
- Loading priority (ascending):
  1. Hardcoded defaults in the class
  2. `/etc/glances/glances.conf`
  3. `~/.config/glances/glances.conf` (XDG_CONFIG_HOME respected)
  4. `$GLANCES_CONFIG_FILE` environment variable
  5. `-C <path>` CLI flag
  6. `GLANCES_<SECTION>__<KEY>=<value>` environment variable overlay (highest priority)
- Typed accessor: `get(section, option, default: T) -> T` — type inferred from default.
- `get_value()` kept as a compatibility alias. No dead code, no breakage.
- **Hot reload**: `mtime` polling every 5 seconds. Only safe keys reloaded (alert thresholds, display options). Credentials and `refresh_time` require a restart.
- `as_dict_secure()` strips passwords, SSL key paths, SNMP community strings — used by the REST API config endpoint and enforced by CVE-2026-32609.

---

## 3. Plugin system

### 3.1 GlancesPluginBase — generic base class

```python
class GlancesPluginBase(Generic[T], ABC):  # T = dict | list
```

- `GlancesPluginBase[dict]` — scalar plugins (cpu, mem, load, …)
- `GlancesPluginBase[list]` — collection plugins (network, fs, containers, …)
- The distinction is carried by the type parameter and `_grab_stats()` return type. No `is_list` flag. No discriminator field in the data.
- API semantics preserved: scalar plugins → JSON object, collection plugins → JSON array.
- **Maximum logic in the base class.** Following the same principle as v4 `GlancesPluginModel`, all generic behaviour is implemented once in `GlancesPluginBase` and never duplicated in individual plugins. Any logic that appears in more than one plugin belongs in the base class. This includes `get_export()` — exporters never access the StatsStore directly (see §7).

#### update() pipeline — based on glancesarena/asyncio/plugin.py

The `update()` method structure is derived directly from the [arena prototype](https://github.com/nicolargo/glancesarena/blob/main/asyncio/plugin.py), made async, and stripped of all view-related methods (`update_views()`, `msg_curse()` — rejected, see §3.6). The pipeline is implemented once in `GlancesPluginBase` and is not overridable by individual plugins:

```python
async def update(self) -> None:
    # Orchestration pipeline. Implemented in base class. Never overridden.
    try:
        self._stats_previous = self._stats          # 1. save previous cycle for rate computation
        await self._grab_stats()                    # 2. collect raw data (psutil via asyncio.to_thread)
        self._add_metadata()                        # 3. add time_since_update and other metadata
        self._transform()                           # 4. transformation pipeline (see below)
        await self.store.set(self.plugin_name, self._stats)  # 5. write to StatsStore
    except Exception as e:
        logger.warning("Plugin %s update failed: %s", self.plugin_name, e)
```

The `_transform()` method is itself a pipeline of four ordered steps, all implemented in the base class with per-plugin override hooks:

| Step | Base class method | Role | Override? |
|---|---|---|---|
| 1 | `_transform_gauge()` | Convert cumulative counters to rates using `_stats_previous` | Rarely — only for non-standard rate computation |
| 2 | `_expand_parameters()` | Expand compound psutil fields into sub-fields (e.g. `cpu_times` → `user`, `system`, `iowait`) | Per plugin if needed |
| 3 | `_derived_parameters()` | Compute derived fields and `_levels` | Per plugin if needed |
| 4 | `_remove_parameters()` | Filter out fields not in `fields_description` and strip internal keys | Never — base class only |

**Only `_grab_stats()` is mandatory** in individual plugins — it is the psutil call, wrapped in `asyncio.to_thread()`. All other steps have a working default in the base class that covers the common case. A plugin overrides only the steps specific to its data model (e.g. `_transform_gauge()` for network rate computation, `_expand_parameters()` for cpu times).

### 3.2 fields_description

- Module-level variable in each plugin. Same contract as v4, revised key structure (breaking change from v4 — intentional, v5 is a clean break).

| Key | Type | Description |
|---|---|---|
| `description` | `str` | Human-readable field description. Used by `/api/5/<plugin>/info` and `--api-doc`. |
| `unit` | `str` | Semantic unit: `bytes`, `percent`, `bytespers`, `string`, `seconds`, … Drives numeric formatting in all renderers. |
| `label` | `str` | Short display label, renderer-neutral. Replaces v4 `short_name`. Single source of truth for compact labels across TUI and WebUI. |
| `history` | `bool` | Whether min/max/mean statistics are computed for this field. Replaces v4 `mmm`. |
| `thresholds` | `dict` | Default alert thresholds (`careful`, `warning`, `critical`). Replaces v4 flat threshold keys. Overridable via `glances.conf`. |
| `primary_key` | `bool` | Marks the join key for `_levels` indexing in list plugins. |
| `exportable` | `bool` | Whether the field is included in `get_export()` output. Defaults to `True`. Set to `False` for internal fields (`time_since_update`, etc.). |

- `min_symbol` (v4) is **removed**. Display floor is derived from `unit` by the renderer. Plugin-specific behaviour belongs in `msg_curse()`.
- User overrides from `glances.conf` are injected into `self._fields["thresholds"]` at init via `_load_fields_description()`.
- `_transform()` filters output to declared fields only. Undeclared psutil fields do not reach the StatsStore or the API.
- Exposed via `GET /api/5/<plugin>/info`.

**Canonical example:**
```python
fields_description = {
    "percent": {
        "description": "Usage percentage.",
        "unit": "percent",
        "label": "MEM",
        "history": True,
        "thresholds": {
            "careful": 50.0,
            "warning": 70.0,
            "critical": 90.0,
        },
    },
    "total": {
        "description": "Total physical memory.",
        "unit": "bytes",
        "label": "total",
    },
    "interface_name": {
        "description": "Network interface name.",
        "unit": "string",
        "primary_key": True,
    },
}
```

### 3.3 Alert levels — _levels computed in _transform()

`_transform()` computes `_levels` as a **pure functional operation** (`f(value, thresholds) → level`), stored at root level in the StatsStore, cleanly separated from metric values.

Levels: `"ok"` / `"careful"` / `"warning"` / `"critical"`.

**Scalar plugin (dict):**
```python
# store["mem"]
{
    "percent": 72.0,
    "total": 16000000000,
    # ...
    "_levels": {
        "percent": "warning",
        "swap_percent": "ok",
    }
}
```

**Collection plugin (list):**
```python
# store["network"]
{
    "data": [
        {"interface_name": "eth0", "rx": 1200, "tx": 300},
        {"interface_name": "lo",   "rx": 0,    "tx": 0},
    ],
    "_levels": {                        # indexed by primary key, not inline
        "eth0": {"rx": "warning", "tx": "ok"},
        "lo":   {"rx": "ok",      "tx": "ok"},
    }
}
```

Primary key is declared in `fields_description` with `"primary_key": True` on the relevant field (`interface_name` for network, `device_name` for fs, etc.).

### 3.4 GlancesAlerts

- Reads `_levels` from the StatsStore. **Never recomputes thresholds.**
- Manages stateful logic: minimum duration before firing, hysteresis to prevent flapping.
- Maintains an alert history exposed via `GET /api/5/alert`. Datamodel may differ from v4 (see §9 constraints).
- Export triggers from alert actions are **not** in scope (not a v4 feature).
- **Alert scope in client/server mode (Option C):** each instance — server and client — runs its own `GlancesAlerts` stack independently. The server evaluates thresholds against locally collected data and triggers its own configured actions. The client does the same locally. The two configurations are fully independent, covering both headless server deployments and client-specific rules.

#### Action system architecture (issues #2328, #2600)

Actions follow the same modularity pattern as plugins and exporters. Adding a new action type requires creating one file — no changes to any core module.

**Directory layout:**
```
glances/actions/
├── action_base.py      ← GlancesActionBase (abstract base class)
├── shell/              ← shell command (v4 behaviour, migrated)
│   └── __init__.py
├── apprise/            ← multi-service notifications (Slack, email, Telegram, …)
│   └── __init__.py
└── llm/                ← LLM health report via LiteLLM
    └── __init__.py
```

**GlancesActionBase contract:**
```python
class GlancesActionBase(ABC):
    action_name: str = ""       # key suffix in glances.conf
    requires: list[str] = []    # optional Python dependencies

    def is_available(self) -> bool: ...   # False if requires missing

    @abstractmethod
    async def execute(
        self,
        plugin_name: str,
        level: str,             # "careful" | "warning" | "critical"
        context: dict,          # get_export() + built-in vars (see below)
        action_value: str,      # raw value from glances.conf
        repeat: bool = False,
    ) -> None: ...
```

Actions are auto-discovered at startup from the `glances/actions/` folder using the same `importlib` pattern as plugins. An action whose `requires` are not installed is skipped with a `WARNING` log — Glances always starts.

**Config key pattern:**
```
<plugin_section>.<level>_<action_name>[_repeat] = <value>
```

| Key suffix | Action type | Example value |
|---|---|---|
| `_action` / `_action_repeat` | Shell command | `echo {{percent}} > /tmp/mem.alert` |
| `_apprise` / `_apprise_repeat` | Apprise notification | `slack://token@channel` or `true` |
| `_llm` / `_llm_repeat` | LLM health report | `true` |

`_repeat` triggers the action every refresh cycle while the alert is active. Without it, the action fires once at alert entry.

Shell commands are shell-escaped before execution (CVE-2026-32608).

Apprise URLs can be defined globally once and reused across all plugins:
```ini
[outputs]
apprise_url=slack://token@channel,mailto://user:pass@smtp.example.com
apprise_body={{_glances_plugin}} is {{_glances_level}} on {{_glances_hostname}}

[mem]
critical=90
critical_apprise=true               # uses global apprise_url + apprise_body
warning_apprise=tgram://bot@channel # or override per-trigger
```

`apprise` is an **optional dependency** — only required if `_apprise` actions are configured.

**Adding a new action (contributor guide):**

Create `glances/actions/<name>/__init__.py` with a class inheriting `GlancesActionBase`. No other file needs to change. The action is auto-discovered and available as `<level>_<name>=<value>` in any plugin section of `glances.conf`. This must be documented in `SKILL-actions.md`.

Example — webhook action:
```python
# glances/actions/webhook/__init__.py
class WebhookAction(GlancesActionBase):
    """POST alert context to a webhook URL.

    Config: [mem] critical_webhook=https://hooks.example.com/alert
    """
    action_name = "webhook"
    requires = []   # httpx is already a core v5 dependency

    async def execute(self, plugin_name, level, context, action_value, repeat=False):
        url = chevron.render(action_value, context)
        async with httpx.AsyncClient() as client:
            await client.post(url, json=context, timeout=5.0)
```

#### Mustache template engine (issue #2600)

- Library: **`chevron`** (already a v4 dependency). No new dependency.
- Template context passed to `chevron.render()` is `plugin.get_export()` output — a `dict` for scalar plugins, `{"data": [...]}` for list plugins — plus built-in variables:

| Built-in variable | Value |
|---|---|
| `{{_glances_hostname}}` | Hostname of the Glances instance |
| `{{_glances_plugin}}` | Plugin name (`mem`, `fs`, …) |
| `{{_glances_level}}` | Alert level (`careful`, `warning`, `critical`) |
| `{{_glances_timestamp}}` | ISO 8601 timestamp of the alert |

- **Full Mustache spec supported**, including sections and list iteration:

```ini
# Simple substitution — v4 compatible, unchanged
warning_action=echo "mem at {{percent}}%" > /tmp/alert

# List iteration — new in v5, works for list plugins (fs, network, …)
critical_action=echo "{{#data}}{{mnt_point}} at {{percent}}% {{/data}}" > /tmp/fs.alert

# Conditional section
warning_action=echo "{{#device_name}}[{{device_name}}] {{/device_name}}{{percent}}%"
```

- All v4 templates using `{{field}}` substitution are **fully backward compatible**.

### 3.5 Plugin naming convention

- Main class: `PluginModel` (v4 convention preserved).
- Inherits from `GlancesPluginBase` instead of `GlancesPluginModel` — the only mandatory line change per plugin during migration.

### 3.6 view_layout / view_description — rejected

Both are rejected. Each renderer (TUI, WebUI) is fully responsible for its own display logic. The TUI requires dynamic layout that no declarative descriptor can encode.

### 3.7 Migration scope

- **All v4 plugins** must be migrated. No plugin omitted.
- Migration order: `mem` → `network` → remaining by increasing complexity.

---

## 4. REST API server — FastAPI

- Single server on `:61208`, replacing both Bottle (`:61208`) and XML-RPC (`:61209`).
- **No v4 API compatibility.** API version is `5`. Entry point: `/api/5/`.
- Route structure identical to v4, version number updated: `/api/5/cpu`, `/api/5/mem`, `/api/5/all`, etc.
- WebUI static files served by the same FastAPI instance. Root path configurable via `webui_root_path` in `glances.conf`, as in v4.
- `/docs` (Swagger UI) and `/redoc` exposed **by default**. Can be disabled via `glances.conf`:
  ```ini
  [outputs]
  api_doc=false
  ```
- Authentication: **Bearer token** (v4.5.0+) and **Basic Auth** (PBKDF2), both preserved. Startup `WARNING` logged when neither is configured (CVE-2026-32596).

---

## 5. Browser / multi-server mode

- The `--browser` mode is **preserved** in v5, migrated to HTTP REST.
- Static server list defined in `glances.conf [serverlist]`, contacted via HTTP REST (replacing XML-RPC polling).
- CVE-2026-32633 and CVE-2026-32634 fixes are **mandatory** (browser mode is not removed).
- **Network autodiscovery**: to be studied. `python-zeroconf` (already used in v4 for XML-RPC discovery) is the natural candidate for broadcasting HTTP REST server announcements on the local network. Decision deferred to implementation phase.

---

## 6. Remote client — GlancesPluginRemote

- Implemented with **httpx async**. Supports both Bearer token and Basic Auth, matching whatever the target server requires.
- Credentials read from `glances.conf [passwords]` keyed by hostname, same as the v4 client.

**Timeout:**
- Global default configurable in `glances.conf`:
  ```ini
  [client]
  timeout=3
  ```
- Overridable per server in the server list configuration.

**Startup behaviour (server unreachable):**
- Non-fatal. Client starts with an empty store for the affected plugin.
- TUI displays `N/A`. Scheduler retries at every refresh cycle.

**Stale data (server disappears after successful connection):**
- Last known data is preserved in the StatsStore with `"stale": true` at root level.
- TUI displays a `DISCONNECTED` banner at the top of the screen, reproducing v4 behaviour.
- Data is cleared after N consecutive failed cycles. N is configurable:
  ```ini
  [client]
  stale_max_cycles=3
  ```

---

## 7. Export modules

### 7.1 Enabled in all modes (issue #1527)

- Export is available in **all modes**: standalone, server, and client.
- In v4, the server was passive (data collected only on client request). In v5, the asyncio scheduler always runs plugins at their `refresh_time` regardless of connected clients — this is a fundamental architectural change required for a responsive REST API. Export and `GlancesAlerts` are lightweight consumers of already-computed StatsStore data; their marginal CPU overhead is small.
- The primary lever for CPU control in server mode is `refresh_time` per plugin. A headless server with no TUI should use longer refresh intervals.
- An `export_refresh_time` global option controls how frequently exporters flush data (must be ≥ `refresh_time`):
  ```ini
  [exports]
  refresh_time=10   # export every 10s even if plugins refresh every 2s
  ```
- **Documentation must warn** that v5 server mode has higher baseline CPU consumption than v4 server mode (always-on scheduler vs. lazy collection). `refresh_time` is the mitigation.

### 7.2 get_export() — consistent field filtering (issue #3211)

- Every exporter calls `plugin.get_export()` instead of reading the StatsStore directly. This is the **only** permitted access pattern for exporters.
- `get_export()` is implemented once in `GlancesPluginBase`. It returns only fields where `exportable` is not `False` in `fields_description`, and strips internal keys (`_levels`, `_mmm`, `_stale`).
- A plugin can override `get_export()` for exporter-specific transformations, but the base implementation covers the common case.

```python
# GlancesPluginBase
def get_export(self) -> dict | list:
    data = self.store.get(self.plugin_name, {})
    if isinstance(data, dict):
        return {
            k: v for k, v in data.items()
            if not k.startswith('_')
            and self._fields.get(k, {}).get('exportable', True)
        }
    # list plugin
    return [
        {k: v for k, v in item.items()
         if not k.startswith('_')
         and self._fields.get(k, {}).get('exportable', True)}
        for item in data.get('data', [])
    ]
```

### 7.3 Migration scope

- **All v4 export modules** must be migrated. No exporter omitted.
- `GlancesExportBase.update()` becomes async. Modules integrate into the main asyncio loop.
- Every migrated exporter replaces direct StatsStore access with `plugin.get_export()`.
- No new export module added during the v5 migration phase.

---

## 8. Security constraints (non-negotiable)

All v4.x security fixes are reproduced in v5.0. v5 starts from the hardened baseline.

| CVE | Fix carried forward |
|---|---|
| CVE-2026-32596 | `WARNING` at startup when REST API runs unauthenticated. Default behaviour unchanged. |
| CVE-2026-32608 | Shell-escape process names in `[action]` command templates before substitution. |
| CVE-2026-32609 | Redact password hash, SSL key paths, SNMP community strings from unauthenticated API responses (`as_dict_secure()`). |
| CVE-2026-32610 | No wildcard `Access-Control-Allow-Origin`. Allowed origins via `cors_origins` in `[outputs]`. `allow_credentials=False` is the FastAPI default. |
| CVE-2026-32611 | Parameterized DDL in DuckDB export. Plugin/metric names sanitized, never string-interpolated. |
| CVE-2026-32632 | Host validation against DNS rebinding. `webui_allowed_hosts` config key. Startup warning when unset in non-loopback mode. |
| CVE-2026-32633 | `/api/serverslist` must not return credential-bearing `uri` fields. Strip `password` and `uri` before serialization. |
| CVE-2026-32634 | Browser autodiscovery must not forward configured credentials to discovered servers. |

---

## 9. Non-negotiable constraints

- **No regression on defaults.** Local users with zero configuration must experience no behaviour change relative to v4 defaults.
- **Conservative defaults.** All new security or behavioural options are opt-in via `glances.conf`, with a `WARNING`-level log when running permissively.
- **No dead code.** Every new class and method must be wired and used.
- **Surgical edits over rewrites.** Plugin migration is incremental, one plugin at a time.
- **Test stack.** `unittest` + `unittest.mock` only. No pytest.
- **Existing v4 unit tests must pass.** All v4 unit tests are migrated to v5 and adapted where necessary (API changes, datamodel changes). A v5 release is not valid if any migrated test is failing or has been silently dropped.
- **Datamodel changes between v4 and v5 are allowed.** v5 is a clean break; API consumers must migrate. Changes must be documented in release notes.
- **All v4 plugins migrated.**
- **All v4 export modules migrated.**
- **All v4 security fixes reproduced** (§8).

---

## 10. Development strategy

### Branch model

```
main          ──────────────────────────────────────────────────► (v4 stable releases)
develop       ──────────────────────────────────────────────────► (v4 bugfixes & security)
develop-v5    ──┬──────┬──────┬──────┬──────────────────────────► (v5 development)
                │      │      │      │
             weekly  alpha  alpha  alpha  …→ beta → rc → merge develop
             merge   0.1    0.2    0.3
```

- The v5 development branch is **`develop-v5`**.
- A **weekly automated merge** `develop → develop-v5` is configured in CI. Security fixes and bugfixes land in v5 without manual action. Conflicts (restructured files) are resolved immediately, not accumulated.
- Alpha and beta releases are published to **PyPI** from `develop-v5` to gather early feedback before the final merge.
- The final merge `develop-v5 → develop` happens at v5.0.0 release candidate stage, after all plugins, exporters, and tests are green.

### Migration phases

#### Phase 0 — Scaffolding
_Goal: async skeleton running, no plugin migrated yet. All contributor skills written before any PR is accepted._

**Core architecture:**
- `GlancesPluginBase[T]` generic base class
- `GlancesActionBase` + auto-discovery
- `StatsStore` with `asyncio.Lock`
- `Asyncio Scheduler` with `asyncio.gather()`
- `GlancesConfig` v5 (env overlay, typed accessor, hot reload stub)
- CI pipeline on `develop-v5` (weekly `develop → develop-v5` merge job)
- Empty asyncio loop passes all structural tests

**Contributor skills — all written in Phase 0, before the first external PR:**

| File | Content |
|---|---|
| `.claude/skills/SKILL-plugin.md` | `GlancesPluginBase[T]`, `fields_description` v5 keys, `_transform()`, `get_export()`, async pattern, unit test requirement |
| `.claude/skills/SKILL-exporter.md` | `GlancesExportBase` async, `get_export()` as the only permitted data access, migration pattern from v4 |
| `.claude/skills/SKILL-actions.md` | `GlancesActionBase`, auto-discovery, Mustache context, Apprise optional dependency, webhook example |
| `.claude/skills/SKILL-security.md` | FastAPI security model, CVE list (§8), `as_dict_secure()`, CORS defaults, startup warnings |
| `.claude/skills/SKILL-config.md` | Env overlay, typed `get()`, `thresholds` structure, hot-reload safe vs unsafe keys |
| `.claude/skills/SKILL-ci-cd.md` | `develop-v5` pipeline, weekly merge job, alpha release tagging |
| `.claude/skills/SKILL-rest-api.md` | FastAPI route structure, auth middleware, `/api/5` conventions _(Phase 1)_ |
| `.claude/skills/SKILL-webui.md` | Vue.js 3, Bootstrap 5, SCSS — largely unchanged from v4 _(Phase 2)_ |

#### Phase 1 — Core plugins + minimal REST API
_Goal: first runnable v5 instance. Release `5.0.0a1`._

- Plugins: `mem`, `cpu`, `load`, `network`
- `GlancesAlerts` with `_levels` pipeline
- REST API `/api/5/<plugin>` for the 4 core plugins
- Curses TUI thread displaying core plugins
- Migrated unit tests for Phase 1 plugins

#### Phase 2 — All local plugins + core exporters
_Goal: feature parity with v4 for local monitoring. Release `5.0.0a2`._

- All remaining local plugins migrated
- Exporters: InfluxDB, Prometheus, CSV, JSON (most widely used)
- Full REST API `/api/5/all`
- WebUI served by FastAPI

#### Phase 3 — Remote client + all exporters + browser mode
_Goal: feature parity with v4 for all modes. Release `5.0.0b1`._

- `GlancesPluginRemote` (httpx, auth, stale data handling)
- Client mode TUI with `DISCONNECTED` banner
- All remaining export modules
- Browser / multi-server mode (static list + Zeroconf study)
- All CVE fixes verified

#### Phase 4 — Hardening & release
_Goal: production-ready. Release `5.0.0rc1` then `5.0.0`._

- All v4 unit tests migrated and passing
- Performance validation (no regression on refresh latency)
- Security audit against §8 checklist
- Release notes documenting all breaking changes and datamodel differences
- Merge `develop-v5 → develop`
- PyPI, Docker, Snap, Helm packages published
