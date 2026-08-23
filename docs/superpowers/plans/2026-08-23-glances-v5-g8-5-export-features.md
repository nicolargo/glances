# G8-5 — Export features (#1527, #3211, #3423): Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close three export-related issues on top of the iso-v4 port: document that export runs in every mode (#1527), serve the export-filtered view from the REST API and MCP (#3211), and give AMPs a numeric `result_float` field (#3423).

**Architecture:** `GlancesPluginBase` gains a third payload view, `get_api_payload()`, sharing one private projection helper with `get_export()` so the two cannot drift. It strips `exportable: False` fields but **keeps** `_levels`, because the WebUI colours cells from them. The REST routes and the MCP adapter move onto it. Separately, the AMP plugin declares a real `result_float` field rather than synthesizing it in the InfluxDB normaliser.

**Tech Stack:** Python 3.9+, FastAPI, pytest + pytest-asyncio (auto mode), Sphinx/RST for the docs.

**Spec:** `docs/superpowers/specs/2026-08-23-glances-v5-g8-5-export-features-design.md`

**Depends on:** G8-1 (`2026-08-22-glances-v5-g8-export-base.md`) complete. Runs after G8-2/3/4 (the six exporters), but does not depend on them.

## Global Constraints

- **Never commit.** Every task ends with `git add`, never `git commit`. The maintainer commits personally. Never add a `Co-Authored-By` trailer.
- **Never touch `NEWS.rst`.** The changelog is written at release time.
- **v4 code is read-only.** `glances/exports/export.py`, `glances/plugins/*/__init__.py` and every `glances/exports/glances_*/__init__.py` must be byte-identical. This includes the misleading `_float` comment in `normalize_for_influxdb` — it stays until the Phase 4 cleanup.
- **`get_export()` behaviour must not change.** G8-1's tests in `tests/test_export_base_v5.py` cover it directly and must stay green **without being edited**. If a change to `get_export()`'s output is needed to make a new test pass, the refactor is wrong.
- **`_levels` stays in the API payload.** Stripping it breaks the WebUI (G9) before it is written.
- **Additive only for AMPs.** `result` keeps its name, type and value; `result_float` sits beside it.
- Tests run with `uv run pytest` (not bare `pytest` — there is no `python` on PATH). Full-suite baseline entering this plan: **2551 passed, 1 skipped**.
- Before building any diff for review, `git diff --name-only` must be empty — an unstaged file silently omits approved work.
- If `tests/test_restful.py` fails, check `pgrep -af pytest` first: two concurrent pytest runs fight over the test server port and that is almost always the cause.

---

## File Structure

| File | Responsibility |
|---|---|
| `glances/plugins/plugin/base_v5.py` | `_project()` helper; `get_api_payload()`; `get_export()` refactored onto the helper. |
| `glances/routes_v5.py` | `/api/5/{plugin_name}` and `/api/5/all` serve the filtered view. |
| `glances/outputs/mcp_adapter_v5.py` | `MCPPluginAdapter.get_raw()` and `getAllAsDict()` serve the filtered view. |
| `glances/plugins/amps/model_v5.py` | `result_float` declared and filled. |
| `docs/gw/index.rst` | Export-in-all-modes statement + server-mode CPU warning. |
| `tests/test_plugin_base_v5.py` | Tests for the new view (append). |
| `tests/test_routes_v5.py` | Route tests (append). |
| `tests/test_mcp_adapter_v5.py` | MCP tests (append). |
| `tests/test_plugin_amps_v5.py` | `result_float` tests (append) + the exact-field-set test it forces to change. |

---

### Task 1: `_project()` and `get_api_payload()`

**Files:**
- Modify: `glances/plugins/plugin/base_v5.py` (the consumers section, around `get_export()` / `_project_exportable()`)
- Test: `tests/test_plugin_base_v5.py` (append)

**Interfaces:**
- Consumes: `self.store`, `self._fields`, `self.IS_COLLECTION`, `self.plugin_name`.
- Produces:
  - `GlancesPluginBase._project(d: dict, *, keep_internal: bool) -> dict`
  - `GlancesPluginBase.get_api_payload() -> dict[str, Any]` — **always a dict**, including for collection plugins.
  - `get_export()` unchanged in behaviour, reimplemented on `_project(..., keep_internal=False)`. `_project_exportable()` is replaced by `_project()` and must not survive as a second, near-identical helper.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_plugin_base_v5.py`, reusing its `FakeScalarPlugin` and
`FakeCollectionPlugin`.

**Read this before writing the tests.** Both fakes DECLARE an `internal_only`
field with `exportable: False`, but neither `_grab_stats()` actually PRODUCES
it — the default payloads are `{"percent": 50.0, "total": 1024}` and the
two-item network-shaped list. A test asserting `"internal_only" not in payload`
against the default fixture would therefore pass no matter what the
implementation does: it would assert nothing. Both fakes accept an explicit
`payload=` constructor argument; use it, so the field genuinely reaches the
store and the filter has something to remove. (`internal_only` is a declared
field, so `_remove_parameters()` keeps it in the store payload.)

```python
@pytest.mark.asyncio
async def test_get_api_payload_keeps_levels_and_drops_non_exportable(config):
    store = StatsStoreV5()
    plugin = FakeScalarPlugin(
        store, config, payload={"percent": 50.0, "total": 1024, "internal_only": "secret"}
    )
    await plugin.update()

    assert "internal_only" in store.get("fakescalar"), "guard: the fixture must publish it"

    payload = plugin.get_api_payload()

    assert isinstance(payload, dict)
    assert "_levels" in payload, "the WebUI colours cells from _levels"
    assert "internal_only" not in payload, "exportable: False must be filtered"
    assert payload["percent"] == 50.0


@pytest.mark.asyncio
async def test_get_api_payload_keeps_the_collection_envelope(config):
    store = StatsStoreV5()
    plugin = FakeCollectionPlugin(store, config)
    await plugin.update()

    payload = plugin.get_api_payload()

    assert isinstance(payload, dict), "collections keep their store envelope"
    assert "_levels" in payload
    assert isinstance(payload["data"], list)


@pytest.mark.asyncio
async def test_get_api_payload_projects_inside_the_collection_data(config):
    """The trap: projecting only the envelope leaves every item unfiltered.

    `data` is not a declared field, so a naive `.get("exportable", True)`
    returns True and the whole list survives with its non-exportable
    fields intact.
    """
    store = StatsStoreV5()
    plugin = FakeCollectionPlugin(
        store,
        config,
        payload=[
            {"name": "eth0", "rx": 10, "internal_only": "secret"},
            {"name": "eth1", "rx": 20, "internal_only": "secret"},
        ],
    )
    await plugin.update()

    assert any("internal_only" in i for i in store.get("fakecollection")["data"]), (
        "guard: the fixture must publish it"
    )

    payload = plugin.get_api_payload()

    assert payload["data"], "fixture must produce at least one item"
    for item in payload["data"]:
        assert "internal_only" not in item
        assert "rx" in item


@pytest.mark.asyncio
async def test_get_api_payload_is_empty_before_the_first_cycle(config):
    store = StatsStoreV5()
    plugin = FakeScalarPlugin(store, config)

    assert plugin.get_api_payload() == {}


@pytest.mark.asyncio
async def test_get_export_is_unchanged_by_the_refactor(config):
    """get_export() still strips every `_*` key, unlike get_api_payload()."""
    store = StatsStoreV5()
    plugin = FakeScalarPlugin(
        store, config, payload={"percent": 50.0, "total": 1024, "internal_only": "secret"}
    )
    await plugin.update()

    exported = plugin.get_export()

    assert "_levels" not in exported
    assert "internal_only" not in exported
    assert exported["percent"] == 50.0
```

Check the module's fixture name for the config object (`config`, `cfg`…) and the
exact `FakeCollectionPlugin` default payload shape before writing; match them.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_plugin_base_v5.py -k api_payload -v`
Expected: FAIL — `AttributeError: 'FakeScalarPlugin' object has no attribute 'get_api_payload'`

- [ ] **Step 3: Write the implementation**

Replace `_project_exportable()` with the parameterised helper and add the new view:

```python
    def _project(self, d: dict[str, Any], *, keep_internal: bool) -> dict[str, Any]:
        """Filter one payload dict for a consumer.

        `keep_internal=False` (exporters): drop every `_*` key and every
        field declared `exportable: False`.
        `keep_internal=True` (REST, MCP): keep `_*` keys — `_levels` is what
        a UI colours cells from — while still dropping non-exportable fields.

        One helper, two views, so the REST and export projections cannot
        drift apart (issue #3211).
        """
        return {
            k: v
            for k, v in d.items()
            if (keep_internal and k.startswith("_"))
            or (not k.startswith("_") and self._fields.get(k, {}).get("exportable", True))
        }

    def get_api_payload(self) -> dict[str, Any]:
        """Filtered view for the REST API and the MCP adapter (issue #3211).

        Drops fields declared `exportable: False`; KEEPS `_levels`.

        Always returns a dict, unlike `get_export()`, which returns a bare
        list for collection plugins: the API serves the payload shape its
        clients already know, envelope included.
        """
        payload = self.store.get(self.plugin_name, {})
        if not isinstance(payload, dict):
            # Defensive: the store always holds a dict for plugins.
            return {}

        out = self._project(payload, keep_internal=True)
        if self.IS_COLLECTION:
            # `data` is not a declared field, so the envelope projection
            # above passes the list through untouched. Each item must be
            # projected on its own or every non-exportable field survives.
            out["data"] = [self._project(item, keep_internal=True) for item in payload.get("data", [])]
        return out
```

and rewrite `get_export()`'s body to call `self._project(..., keep_internal=False)` in place of `self._project_exportable(...)`, leaving its docstring, signature and return shape exactly as they are.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_plugin_base_v5.py -v`
Expected: PASS, including every pre-existing test in the module.

- [ ] **Step 5: Prove `get_export()` did not regress**

Run: `uv run pytest tests/test_export_base_v5.py -v`
Expected: unchanged pass count from G8-1. These tests must pass **without being edited** — if any needed a change, the refactor altered `get_export()`'s behaviour and must be reworked.

- [ ] **Step 6: Confirm the old helper is gone**

Run: `grep -rn "_project_exportable" glances/ tests/`
Expected: no output. Two near-identical projection helpers is exactly the drift this task exists to prevent.

- [ ] **Step 7: Stage**

```bash
git add glances/plugins/plugin/base_v5.py tests/test_plugin_base_v5.py
```

---

### Task 2: REST routes serve the filtered view

**Files:**
- Modify: `glances/routes_v5.py` (`all_stats` at ~line 121, `plugin_payload` at ~line 159)
- Test: `tests/test_routes_v5.py` (append)

**Interfaces:**
- Consumes: `GlancesPluginBase.get_api_payload()` from Task 1; the existing `_plugins(request)` and `_resolve_plugin(request, name)` helpers in `routes_v5.py`.
- Produces: no new symbols — two handlers change what they read.

- [ ] **Step 1: Give the fakes a non-exportable field**

`tests/test_routes_v5.py` defines `FakeScalarPlugin` and `FakeCollectionPlugin`
(around lines 47-68). Neither declares an `exportable: False` field, so there is
currently nothing for the filter to remove. Add one to each:

```python
class FakeScalarPlugin(GlancesPluginBase[dict]):
    plugin_name: ClassVar[str] = "fakescalar"
    IS_COLLECTION: ClassVar[bool] = False
    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "percent": {"description": "Usage percentage.", "unit": "percent"},
        "total": {"description": "Total.", "unit": "bytes"},
        "secret": {"description": "Not for export.", "unit": "string", "exportable": False},
    }

    async def _grab_stats(self) -> dict:
        return {"percent": 42.0, "total": 1024, "secret": "hunter2"}


class FakeCollectionPlugin(GlancesPluginBase[list]):
    plugin_name: ClassVar[str] = "fakecollection"
    IS_COLLECTION: ClassVar[bool] = True
    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "name": {"description": "Item name.", "unit": "string", "primary_key": True},
        "rx": {"description": "Received bytes.", "unit": "bytes"},
        "secret": {"description": "Not for export.", "unit": "string", "exportable": False},
    }

    async def _grab_stats(self) -> list:
        return [
            {"name": "eth0", "rx": 100, "secret": "hunter2"},
            {"name": "lo", "rx": 0, "secret": "hunter2"},
        ]
```

Change nothing else about them — several existing tests assert on `percent`,
`total`, `rx` and the plugin names.

- [ ] **Step 2: Write the failing test**

Append to `tests/test_routes_v5.py`, in the module's own style (`config_factory`,
`store`, `_populate`, `_make_app_with_plugins`, `TestClient`):

```python
def test_plugin_payload_drops_non_exportable_fields(config_factory, store):
    config = config_factory()
    plugin = FakeScalarPlugin(store, config)
    _populate(store, plugin)
    app = _make_app_with_plugins(config, store, plugins=[plugin])
    with TestClient(app) as client:
        payload = client.get("/api/5/fakescalar").json()
    assert payload["percent"] == 42.0
    assert "secret" not in payload


def test_plugin_payload_keeps_levels(config_factory, store):
    """The WebUI (G9) colours cells from _levels — it must survive the filter."""
    config = config_factory()
    plugin = FakeScalarPlugin(store, config)
    _populate(store, plugin)
    app = _make_app_with_plugins(config, store, plugins=[plugin])
    with TestClient(app) as client:
        payload = client.get("/api/5/fakescalar").json()
    assert "_levels" in payload


def test_plugin_payload_collection_projects_each_item(config_factory, store):
    """Projecting only the envelope leaves every item unfiltered — the trap."""
    config = config_factory()
    plugin = FakeCollectionPlugin(store, config)
    _populate(store, plugin)
    app = _make_app_with_plugins(config, store, plugins=[plugin])
    with TestClient(app) as client:
        payload = client.get("/api/5/fakecollection").json()
    assert isinstance(payload["data"], list)
    assert payload["data"], "fixture publishes two items"
    for item in payload["data"]:
        assert "secret" not in item
        assert "rx" in item


def test_all_drops_non_exportable_fields(config_factory, store):
    config = config_factory()
    plugin = FakeScalarPlugin(store, config)
    _populate(store, plugin)
    app = _make_app_with_plugins(config, store, plugins=[plugin])
    with TestClient(app) as client:
        body = client.get("/api/5/all").json()
    assert body["fakescalar"]["percent"] == 42.0
    assert "secret" not in body["fakescalar"]
    assert "_levels" in body["fakescalar"]
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_routes_v5.py -k "non_exportable or keeps_levels or projects_each_item" -v`
Expected: FAIL — `secret` is present, because the routes still serve the raw store payload.

- [ ] **Step 4: Write the implementation**

In `glances/routes_v5.py`:

```python
    @router.get("/all")
    async def all_stats(request: Request) -> dict[str, Any]:
        # Registry read, not a store read: `/all` must apply each plugin's
        # export filter (issue #3211), which only the plugin can do.
        # Empty payloads are SKIPPED, preserving the existing contract that a
        # registered-but-never-updated plugin is absent from `/all` rather
        # than present with an empty body.
        out: dict[str, Any] = {}
        for name, plugin in _plugins(request).items():
            payload = plugin.get_api_payload()
            if payload:
                out[name] = payload
        return out
```

```python
    @router.get("/{plugin_name}")
    async def plugin_payload(plugin_name: str, request: Request):
        plugins = _plugins(request)
        if plugin_name not in plugins:
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_name!r} not found")
        # Plugin is registered but may not have published a payload yet
        # (scheduler cycle 0). Return a bare JSON ``null`` so clients can
        # distinguish "unknown plugin" (404) from "data not yet available"
        # without surfacing a transient as an error.
        payload = plugins[plugin_name].get_api_payload()
        if not payload:
            return JSONResponse(content=None)
        return payload
```

`get_api_payload()` returns `{}` where the store returned `None`, so the cycle-0
guard becomes `if not payload`. The `null` response body is unchanged — clients
depend on that distinction.

Update the route table in the module docstring (around line 23) where it says
`store.as_dict()`.

- [ ] **Step 5: Run the whole route module**

Run: `uv run pytest tests/test_routes_v5.py -v`
Expected: PASS, **including these two pre-existing tests, unedited**:
- `test_all_excludes_unwritten_plugins` — pins that a never-updated plugin is
  absent from `/all`. It is why the implementation skips empty payloads. If it
  fails, the skip is missing.
- `test_plugin_payload_scalar` — pins `percent == 42.0` still reaching clients.

- [ ] **Step 6: Check the OpenAPI surface did not break**

Run:
```bash
uv run python -c "
from glances.config_v5 import GlancesConfigV5
from glances.stats_store_v5 import StatsStoreV5
from glances.webserver_v5 import build_app
app = build_app(config=GlancesConfigV5(), store=StatsStoreV5(), alerts=None)
print(sorted(app.openapi()['paths']))
"
```
Expected: `/api/5/all` and `/api/5/{plugin_name}` still present; no route lost.

- [ ] **Step 6: Stage**

```bash
git add glances/routes_v5.py tests/test_routes_v5.py
```

---

### Task 3: MCP adapter serves the filtered view

**Files:**
- Modify: `glances/outputs/mcp_adapter_v5.py` (`MCPPluginAdapter.get_raw()` ~line 97, `getAllAsDict()` ~line 165)
- Test: `tests/test_mcp_adapter_v5.py` (append)

**Interfaces:**
- Consumes: `get_api_payload()` from Task 1; the adapter's existing `self._plugin`, `self._store`, `self._synthetic_payload`, `self._by_name`.
- Produces: no new symbols.

An MCP client is a consumer like any other; leaving it on the raw payload would recreate exactly the inconsistency #3211 is about.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_mcp_adapter_v5.py`, matching its existing fixture style:

```python
def test_mcp_plugin_payload_drops_non_exportable_fields(mcp_stats):
    payload = mcp_stats.get_plugin("fakescalar").get_raw()

    assert "internal_only" not in payload
    assert "_levels" in payload


def test_mcp_all_drops_non_exportable_fields(mcp_stats):
    payload = mcp_stats.getAllAsDict()

    assert "internal_only" not in payload["fakescalar"]


def test_mcp_synthetic_plugin_still_bypasses_the_filter(mcp_stats):
    """`alert` has no real plugin behind it — it must keep working."""
    payload = mcp_stats.get_plugin("alert").get_raw()

    assert isinstance(payload, list)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_mcp_adapter_v5.py -k "non_exportable" -v`
Expected: FAIL — `internal_only` present.

- [ ] **Step 3: Write the implementation**

In `MCPPluginAdapter.get_raw()`, keep the synthetic-payload branch first and untouched, then read through the plugin instead of the store:

```python
        if self._synthetic_payload is not None:
            return self._synthetic_payload() if callable(self._synthetic_payload) else self._synthetic_payload
        if self._plugin is None:
            return {}
        # Filtered view, same as the REST API (issue #3211).
        return self._plugin.get_api_payload()
```

Keep a `self._store` fallback only if the adapter can legitimately exist without `self._plugin` — read the constructor and decide; if `_plugin` is always set for non-synthetic adapters, drop the store read rather than leaving a dead branch.

In `getAllAsDict()`:

```python
    def getAllAsDict(self) -> dict[str, Any]:  # noqa: N802
        """Return a snapshot of every plugin's filtered payload (issue #3211)."""
        return {name: plugin.get_api_payload() for name, plugin in self._by_name.items()}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_mcp_adapter_v5.py -v`
Expected: PASS, including every pre-existing MCP test.

- [ ] **Step 5: Stage**

```bash
git add glances/outputs/mcp_adapter_v5.py tests/test_mcp_adapter_v5.py
```

---

### Task 4: AMP `result_float`

**Files:**
- Modify: `glances/plugins/amps/model_v5.py` (`fields_description` ~line 44, `_grab_stats()` ~line 62)
- Test: `tests/test_plugin_amps_v5.py`

**Interfaces:**
- Consumes: nothing from earlier tasks — independent of Tasks 1-3.
- Produces: a `result_float` field in every AMP item, visible to every exporter, the REST API and the WebUI. Also a module-level `_as_float(value) -> float | None` helper in `glances/plugins/amps/model_v5.py`.

- [ ] **Step 1: Update the field-set test that will otherwise fail**

`tests/test_plugin_amps_v5.py::test_fields_description` asserts the EXACT field
set. Adding a field makes it fail. That is correct and intended — extend the
expected set rather than loosening the assertion:

```python
def test_fields_description(store, cfg):
    p = PluginModel(store, cfg("[global]\nrefresh = 2\n"))
    assert set(p.fields_description) == {
        "name",
        "result",
        "result_float",
        "refresh",
        "timer",
        "count",
        "countmin",
        "countmax",
        "regex",
    }
```

- [ ] **Step 2: Write the failing tests**

Append to `tests/test_plugin_amps_v5.py`. The module's fixtures are `store`,
`cfg` (a factory taking a config body) and `procs`, plus the `_settle(plugin)`
helper that drains in-flight AMP tasks — the existing `test_payload_shape` is
the pattern to copy. An AMP's `result` is its command's stdout, so `echo 42`
yields the string `"42\n"`.

```python
async def test_result_float_carries_the_number(store, cfg, procs):
    """A numeric AMP result must reach InfluxDB as a number (issue #3423)."""
    procs([])
    p = PluginModel(store, cfg("[amp_queue]\nenable=true\nrefresh=30\ncommand=echo 42\n"))
    await p.update()
    await _settle(p)
    await p.update()
    item = store.get("amps", {})["data"][0]
    assert item["result"].strip() == "42"
    assert item["result_float"] == 42.0


async def test_result_float_is_none_for_text(store, cfg, procs):
    """A text result contributes no numeric series rather than a misleading 0.0."""
    procs([])
    p = PluginModel(store, cfg("[amp_conntrack]\nenable=true\nrefresh=30\ncommand=echo tracked\n"))
    await p.update()
    await _settle(p)
    await p.update()
    item = store.get("amps", {})["data"][0]
    assert item["result"].strip() == "tracked"
    assert item["result_float"] is None


def test_as_float_helper():
    from glances.plugins.amps.model_v5 import _as_float

    assert _as_float("42\n") == 42.0
    assert _as_float(7) == 7.0
    assert _as_float("3.5") == 3.5
    assert _as_float("tracked") is None
    assert _as_float(None) is None
    assert _as_float("") is None
```

`float("42\n")` is 42.0 — Python strips surrounding whitespace — so no manual
`.strip()` is needed in the helper.

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_plugin_amps_v5.py -k "result_float or as_float or fields_description" -v`
Expected: FAIL — `KeyError: 'result_float'` and `ImportError` on `_as_float`.

- [ ] **Step 4: Write the implementation**

In `fields_description`, immediately after the `result` entry:

```python
        "result_float": {
            "description": "Numeric value of `result` when it parses as a number, else None.",
            "unit": "number",
        },
```

In `_grab_stats()`, beside `"result": amp.result(),`:

```python
                "result_float": _as_float(amp.result()),
```

Calling `amp.result()` twice is fine — it is a plain accessor on the AMP object,
not a command re-run. If a reviewer objects, bind it to a local first.

And a module-level helper:

```python
def _as_float(value: Any) -> float | None:
    """Return `value` as a float, or None when it is not numeric.

    v4's InfluxDB normaliser coerces `result` to a string because an AMP may
    return either text or a number (#3419), and its comment promises a
    companion `_float` field that its code never creates. This is that field
    (#3423) — declared on the plugin, so it reaches every exporter and the
    REST API rather than only InfluxDB.

    None rather than 0.0 for a text result: `normalize_for_influxdb()` skips
    None fields, so a text-only AMP contributes no numeric series instead of
    a misleading zero.
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
```

- [ ] **Step 5: Run the whole AMP module**

Run: `uv run pytest tests/test_plugin_amps_v5.py -v`
Expected: PASS, including `test_payload_shape` and the level-ladder tests, unedited.

- [ ] **Step 6: Verify it reaches the export payload with no export-layer change**

Run: `uv run pytest tests/test_export_base_v5.py -v`
Expected: unchanged pass count. `result_float` is a declared field, so
`get_export()` picks it up with no edit to the export layer at all — that is the
point of declaring it on the plugin rather than synthesizing it in the InfluxDB
normaliser.

- [ ] **Step 7: Stage**

```bash
git add glances/plugins/amps/model_v5.py tests/test_plugin_amps_v5.py
```

---

### Task 5: Document export in all modes (#1527)

**Files:**
- Modify: `docs/gw/index.rst`

**Interfaces:** none — documentation only.

- [ ] **Step 1: Fix the broken sentence already in the page**

The page currently reads:

```
A common options section is also available:

 is the `exclude_fields` option, which allows you to specify
```

That sentence is truncated and pre-existing. It sits inside the very paragraph this task extends, so repair it rather than building on top of it:

```
A common options section is also available. It holds the ``exclude_fields``
option, which lets you drop fields from every exporter at once (comma-separated
list of regular expressions):
```

This is the only adjacent fix this plan authorises. Do not restyle the rest of the page.

- [ ] **Step 2: Add the export cadence key to the same block**

The `[export]` example currently shows only `exclude_fields`. Add the `refresh` key G8-1 documented in `conf/glances.conf`, keeping it commented so the example matches shipped defaults, and normalise the block's indentation (it currently mixes 3 and 4 spaces):

```ini
    [export]
    # Common section for all exporters
    # Do not export following fields (comma separated list of regex)
    exclude_fields=.*_critical,.*_careful,.*_warning,.*\.key$
    # Export refresh rate, in seconds. Defaults to the [global] refresh rate.
    # A value lower than the global refresh is clamped up to it.
    #refresh=10
```

- [ ] **Step 3: Add the all-modes section**

After the common-options block, before the `toctree`:

```rst
Export in server mode
---------------------

Glances exports stats in **standalone and server mode** alike. A headless
server such as::

    glances -s --export influxdb2

is a supported deployment: stats are collected and exported continuously, with
no client connected. This closes a long-standing limitation of Glances 4, where
the server only collected on a client's request.

.. warning::

    Server mode consumes more CPU at rest than Glances 4 did. The Glances 5
    scheduler polls every plugin on its own refresh interval whether or not
    anyone is watching, which is what makes the REST API responsive. The
    mitigation is the refresh rate: raise ``[global] refresh`` for the
    baseline, ``[<plugin>] refresh`` for expensive plugins such as
    ``sensors``, and ``[export] refresh`` for the export flush itself. Most
    plugins already ship a slower default than the global rate.
```

- [ ] **Step 4: Verify the docs build**

Run: `uv run python -m sphinx -b html -q docs docs/_build/html 2>&1 | tail -20`
Expected: no new warning naming `docs/gw/index.rst`. If Sphinx is not installed in the venv, say so in the report and instead validate the RST by eye: directive indentation, a blank line after `.. warning::`, and `::` before the literal block.

- [ ] **Step 5: Stage**

```bash
git add docs/gw/index.rst
```

---

### Task 6: Full verification and hooks

**Files:** all files touched by Tasks 1-5.

- [ ] **Step 1: Confirm no other consumer still reads the raw store**

Run: `grep -rn "store.get(\|store.as_dict()" glances/routes_v5.py glances/outputs/mcp_adapter_v5.py`
Expected: no hit that serves a plugin payload to a client. The TUI (`glances/outputs/curses_renderer_v5.py`, `glances_curses_v5.py`) legitimately keeps reading the store directly — it is not an API consumer and must not change.

- [ ] **Step 2: Run the full suite**

Run: `uv run pytest -q`
Expected: no new failures versus the 2551-passed baseline. If `tests/test_restful.py` fails, check `pgrep -af pytest` for a concurrent run before investigating anything else.

- [ ] **Step 3: Smoke-test the API end to end**

```bash
timeout 12 uv run python -m glances.main_v5 -s --port 61299 &
sleep 6
curl -s http://localhost:61299/api/5/cpu | head -c 400; echo
curl -s http://localhost:61299/api/5/network | head -c 400; echo
```
Expected: both carry `_levels`; neither carries `time_since_update`; `network` keeps its `{"data": [...]}` envelope with the per-item fields intact.

- [ ] **Step 4: Run the hooks**

```bash
git add -A
make pre-commit
```
Expected: the only failure is the pre-existing `check-shebang-scripts-are-executable` on `tests/test_plugin_containers.py`, `tests/test_plugin_init_value.py`, `tests/test_plugin_model.py` — files this plan never touches. Restage and re-run if `ruff-format` rewrites anything.

- [ ] **Step 5: Stage the final state**

```bash
git add -A
git status --short
git diff --name-only   # must print nothing
```

Do NOT commit. Report the staged file list to the maintainer.
