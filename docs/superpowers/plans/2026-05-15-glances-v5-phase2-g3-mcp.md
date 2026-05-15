# Glances v5 Phase 2 — G3-MCP (port MCP endpoint to v5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Wire the existing `GlancesMcpServer`
(`glances/outputs/glances_mcp.py`) into the v5 FastAPI app under
`/mcp`, gated by `args.enable_mcp` (which is already validated to
require `-s` — cf. G2 Task 1). Make the operational reality match the
G2 design alignment table where the "Server + MCP" mode is listed.

**Scope contract:** This plan does **not** rewrite the MCP server. It
introduces a thin **adapter layer** between v5's `StatsStoreV5` /
plugin registry / alerts pipeline and the duck-typed `stats` object
that `GlancesMcpServer` expects (v4 `GlancesStats`-style API:
`getPluginsList()`, `get_plugin(name)`, `getAllAsDict()`,
`getAllLimitsAsDict()`). The adapter is implemented in v5 land; the
MCP module stays untouched.

---

## Discovery summary (2026-05-15)

| v4 API used by GlancesMcpServer | v5 equivalent | Status |
|---|---|---|
| `stats.getPluginsList()` | `StatsStoreV5.keys()` | direct map |
| `stats.getAllAsDict()` | `StatsStoreV5.as_dict()` | direct map |
| `stats.get_plugin(name)` | _(no equivalent — see Task 1)_ | **adapter needed** |
| `plugin_obj.get_raw()` | `StatsStoreV5.get(name)` | adapter wraps |
| `plugin_obj.get_raw_history(...)` | _(no history in v5 yet)_ | **gap — defer (Task 4)** |
| `plugin_obj.get_limits()` | aggregate `plugin._fields[*].default_thresholds` | adapter computes |
| `stats.getAllLimitsAsDict()` | iterate all plugins' `get_limits()` | adapter computes |
| `stats.get_plugin("alert").get_raw()` | `GlancesAlerts.get_history()` | adapter wraps |
| `stats.get_plugin("processlist").get_raw()` | _(processlist not in v5 yet)_ | **gap — stub** |
| `stats.get_plugin("fs"/"diskio"/"memswap").get_raw()` | _(none in v5 yet)_ | **gap — stub** |

### v4 prompts vs v5 plugin availability

| Prompt | Plugins read | v5 available? | Decision |
|---|---|---|---|
| `system_health_summary` | cpu, mem, memswap, load, fs, network | partial (cpu, mem, load, network ✅; memswap, fs ❌) | keep — adapter returns empty dict for missing plugins, prompt template still works |
| `alert_analysis` | alert | ✅ (via `GlancesAlerts.get_history()`) | keep — wire through adapter |
| `top_processes_report` | processlist | ❌ not in v5 yet | **stub** — return empty list + note; re-enable when processlist lands |
| `storage_health` | fs, diskio | ❌ not in v5 yet | **stub** — same |

### Auth interaction

v4 ships `GlancesMcpAuthMiddleware` because the SSE transport needs
special handling (long-running response, can't be buffered). v5
already has Basic + Bearer auth in `glances/webserver_v5.py`. Must
verify: (a) the existing middleware doesn't buffer SSE streams; (b) if
it does, port the v4 middleware logic. Test step covers this — see
Task 3.

---

## File Structure

| Path | Responsibility | Action |
|---|---|---|
| `glances/outputs/mcp_adapter_v5.py` | v5 → MCP duck-typed adapter (`McpStatsAdapter`, `McpPluginView`) | Create |
| `glances/outputs/glances_mcp.py` | the existing v4 MCP server class — **untouched** | _no change_ |
| `glances/webserver_v5.py` | mount `/mcp` when `[outputs] enable_mcp` is true; auth wiring | Modify |
| `glances/main_v5.py` | propagate `args.enable_mcp` into the config overlay (like `args.api_doc`) | Modify |
| `conf/glances.conf` | document `[outputs] enable_mcp` and `mcp_allowed_hosts` keys (commented, off by default) | Modify |
| `tests/test_mcp_adapter_v5.py` | unit tests on the adapter | Create |
| `tests/test_webserver_v5.py` | gate test: flag off → /mcp returns 404; flag on → /mcp reachable | Modify |
| `tests/test_main_v5.py` | adds `test_assemble_propagates_enable_mcp_overlay` | Modify |
| `docs/architecture/glances-v5-architecture-decisions.md` | new §11 "MCP endpoint" with the adapter contract + limitations | Modify |

Each Task = 1 commit. Six tasks total.

---

## Task 1: Adapter layer (`mcp_adapter_v5.py`)

**Goal:** Expose a duck-typed object that `GlancesMcpServer` can
consume without modification.

**Interface required (extracted from `glances_mcp.py`):**

```python
class McpStatsAdapter:
    def getPluginsList(self) -> list[str]: ...
    def getAllAsDict(self) -> dict[str, Any]: ...
    def getAllLimitsAsDict(self) -> dict[str, dict[str, Any]]: ...
    def get_plugin(self, name: str) -> McpPluginView | None: ...

class McpPluginView:
    def get_raw(self) -> dict | list: ...
    def get_raw_history(self, item=None, nb: int = 0) -> dict | list: ...
    def get_limits(self) -> dict[str, Any]: ...
```

**Steps:**

- [ ] **Step 1: Write failing tests** — `tests/test_mcp_adapter_v5.py`:
  - `getPluginsList()` returns registered plugin names;
  - `get_plugin("cpu").get_raw()` returns the same dict as `store.get("cpu")`;
  - `get_plugin("unknown")` returns `None`;
  - `get_limits()` aggregates `default_thresholds` from `fields_description`;
  - history returns `{}` (or `[]` for collection plugins) — **explicit
    "deferred" semantic**, with a debug log;
  - synthetic `"alert"` plugin view returns the alerts history list.
- [ ] **Step 2: Implement** `McpStatsAdapter` + `McpPluginView`.
  - Hold references to `StatsStoreV5`, `list[GlancesPluginBase]`,
    `GlancesAlerts`.
  - Build a `dict[plugin_name → plugin_instance]` lookup at
    construction time for O(1) `get_plugin`.
  - `"alert"` is a synthetic plugin (not in the registry) — handled
    by an `if name == "alert"` branch in `get_plugin`.
  - Plugins absent from v5 (`fs`, `diskio`, `memswap`, `processlist`)
    naturally return `None` from `get_plugin` → MCP resources for
    those raise `ValueError("Plugin '<x>' not found")`, matching v4
    behaviour when a plugin is disabled.
- [ ] **Step 3: Commit.**

---

## Task 2: Mount `/mcp` in `webserver_v5.build_app`

**Goal:** Conditional mount based on the `[outputs] enable_mcp`
config key (set via CLI overlay in Task 5 below).

**Steps:**

- [ ] **Step 1: Add the optional dependency check.** Top of
  `webserver_v5.py`, mirror the `MCP_AVAILABLE` try/except already in
  `glances_mcp.py` — fail-fast with a clear error if the user sets
  `enable_mcp=True` without the `mcp` package installed.
- [ ] **Step 2: Extend `build_app(config, store, alerts=None, plugins=None)`**
  to accept the plugin registry (needed by the adapter). Currently the
  app does not hold the registry — it gets plugins via
  `register_plugin(app, plugin)` calls. Reuse `app.state.plugins`
  (already populated) instead of adding a parameter, if possible. If
  not, add `plugins=` to the signature.
- [ ] **Step 3: Inside `build_app`**, after auth setup, if
  `config.get("outputs", "enable_mcp", False)` is truthy:
  ```python
  from glances.outputs.glances_mcp import GlancesMcpServer
  from glances.outputs.mcp_adapter_v5 import McpStatsAdapter

  adapter = McpStatsAdapter(store, plugins, alerts)
  # GlancesMcpServer expects an `args`-like namespace too — synthesise a
  # minimal one from the merged config (only the keys it reads).
  fake_args = SimpleNamespace(...)
  mcp_server = GlancesMcpServer(stats=adapter, args=fake_args, config=config)
  app.mount("/mcp", mcp_server.get_asgi_app())
  logger.info("MCP endpoint mounted at /mcp")
  ```
- [ ] **Step 4: Auth posture.** If `[outputs] password` is set, the
  existing v5 auth middleware (`HTTPBasic` + Bearer) must apply to the
  MCP path. Verify the middleware doesn't buffer the SSE response body.
  If it does, port the v4 `GlancesMcpAuthMiddleware` pattern (pure
  ASGI middleware, outermost, intercepts `Authorization` header
  pre-mount). Cover with a streaming-friendly test.
- [ ] **Step 5: Tests** — `tests/test_webserver_v5.py`:
  - default config: `GET /mcp` returns 404 (mount absent);
  - `[outputs] enable_mcp=true` config: `GET /mcp` returns a non-404
    response (we don't try to drive a full SSE handshake — just
    confirm the mount is wired);
  - auth-enabled config: unauthenticated request to `/mcp` returns
    401, authenticated returns the SSE-ready response.
- [ ] **Step 6: Commit.**

---

## Task 3: CLI overlay propagation

**Goal:** `args.enable_mcp` (already validated in G2 Task 1) must
flip the config gate.

**Steps:**

- [ ] **Step 1:** In `glances/main_v5.py::assemble`, server-mode
  branch, add:
  ```python
  if args.enable_mcp:
      config._merged.setdefault("outputs", {})["enable_mcp"] = True
  ```
  alongside the existing `args.api_doc` overlay.
- [ ] **Step 2: Test** — `tests/test_main_v5.py`:
  `test_assemble_propagates_enable_mcp_overlay`: build with
  `-s --enable-mcp`, assert
  `config.get("outputs", "enable_mcp", False) is True` and that
  `app.routes` contains a mount for `/mcp`.
- [ ] **Step 3: Commit.**

---

## Task 4: Document the history + processlist gaps explicitly

**Goal:** Make the "deferred" semantics visible in the code, not
silently empty.

**Steps:**

- [ ] **Step 1: Adapter `get_raw_history`** — return `{}` and log a
  one-time WARN per plugin: `"MCP history not yet supported in v5;
  returning empty dataset for '<plugin>'"`. (Once per plugin to avoid
  log spam.)
- [ ] **Step 2: Adapter `get_plugin` for missing plugins** — for
  `fs` / `diskio` / `memswap` / `processlist`, return `None` so MCP
  raises `ValueError("Plugin '<x>' not found")`. The error already
  surfaces to the MCP client correctly — no special handling needed.
- [ ] **Step 3: Update the MCP server's docstring** **only via the
  adapter** (do NOT edit `glances_mcp.py`). Adapter docstring lists
  the v5 limitations.
- [ ] **Step 4: Tests** — add explicit cases for the WARN and the
  `ValueError`-via-`get_plugin(None)` behaviours.
- [ ] **Step 5: Commit.**

---

## Task 5: Config doc + architecture doc

**Steps:**

- [ ] **Step 1: `conf/glances.conf`** — add a commented `[outputs]`
  section documenting:
  ```ini
  # Mount the MCP (Model Context Protocol) endpoint at /mcp.
  # Off by default — requires the mcp Python package.
  # enable_mcp=true
  #
  # DNS-rebinding protection for the MCP endpoint. Comma-separated
  # list of hostnames the SSE transport will accept. Default:
  # localhost,127.0.0.1 (loopback only). "*" disables protection —
  # use only behind a trusted reverse proxy.
  # mcp_allowed_hosts=localhost,127.0.0.1
  ```
- [ ] **Step 2: Architecture doc** — new §11 "MCP endpoint":
  - opt-in via `-s --enable-mcp` (refer back to §1.5);
  - adapter layer rationale (preserve v4 MCP class as-is);
  - resource/prompt inventory + v5 limitations (history,
    processlist/fs/diskio/memswap);
  - auth posture (inherits v5 Basic + Bearer);
  - DNS-rebinding protection (`mcp_allowed_hosts`).
- [ ] **Step 3: Commit.**

---

## Task 6: Final sweep

- [ ] **Step 1:** `make test-v5` — green.
- [ ] **Step 2:** `make test` — full pytest, v4 non-regression.
- [ ] **Step 3:** `make lint && make format` — clean.
- [ ] **Step 4: Manual smoke (maintainer-driven):**
  - `make run-v5-server` — `curl -fsS http://127.0.0.1:61208/mcp` → 404.
  - `make run-v5-mcp` — `curl -fsS http://127.0.0.1:61208/mcp` →
    non-404 (SSE endpoint reachable). Optional: connect with a real
    MCP client and exercise `glances://plugins`, `glances://stats/cpu`,
    `glances://stats/cpu/history` (should return empty + WARN log).
- [ ] **Step 5: Stop at the local-commit boundary** — per memory
  [[feedback-never-push-or-open-pr]], no push, no PR.

---

## Out of scope (explicit)

1. **History storage in v5.** A real history buffer in
   `StatsStoreV5` or `GlancesPluginBase` is its own design task
   (ring buffer? rolling window? per-field vs whole-payload? export
   coupling?). Not in G3-MCP. Adapter returns empty until then.
2. **Porting v4 plugins to v5** (processlist, fs, diskio, memswap).
   Each is its own plan-sized chunk (collection plugins, OS-specific
   psutil calls, primary-key wiring). Adapter returns `None` for each
   so MCP raises the canonical "Plugin not found" error.
3. **WebSocket transport for MCP.** v4 uses SSE; we keep SSE in v5.
4. **MCP client integrations / sample notebooks.** Out of scope.

---

## Decision log

- **Alert schema (2026-05-15, user):** option **(a)** — v5-native event
  schema (`ts`, `plugin`, `key`, `field`, `level`, `previous_level`,
  `prominent`, …). No translation layer. The MCP prompt
  `alert_analysis` is free-form so schema variations are tolerated by
  the LLM consumer.

---

## Original options considered (resolved above)

The adapter's `get_plugin("alert")` returns a view wrapping
`GlancesAlerts.get_history()` — the list of recent transitions. v4's
`alert` plugin returns the same kind of payload (a list of alert
dicts) but with a slightly different schema. Two options:

(a) **Faithful to v5** — adapter exposes the v5 `GlancesAlerts`
    event schema as-is (`ts`, `plugin`, `key`, `field`, `level`,
    `previous_level`, `prominent`, …). MCP client sees v5-native
    fields. **Recommended** — avoids carrying a translation layer.

(b) **v4-compatible** — adapter translates v5 events into v4's
    flatter schema (`type`, `start`, `end`, `min`, `max`, …) so MCP
    clients reused from v4 keep working. **More work, more drift.**

Recommendation: **(a)**. The MCP prompt `alert_analysis` is a free-form
"Analyze these alerts" template — schema variations are tolerated by
the LLM consumer.

---

## Wrap-up

After merge:
1. New project memory: `project_v5_mcp.md` — adapter lives in
   `glances/outputs/mcp_adapter_v5.py`; gate is `[outputs] enable_mcp`;
   v5 limitations (no history, missing plugins) documented in archi §11.
2. Subsequent work that ports a v4-only plugin to v5 (e.g. processlist
   in a future phase) automatically extends MCP coverage with no
   change to the adapter, since `get_plugin(name)` reads from the
   registry dynamically.
