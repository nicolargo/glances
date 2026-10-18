# Glances v5 — containers plugin port (G6A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the v4 `containers` plugin to the Glances v5 asyncio collection architecture (MAIN/RIGHT column), reusing the v4 Docker/Podman/LXD engine machinery (streaming threads + `ThreadPoolExecutor`) **unchanged** for performance parity, and raising CPU/MEM alerts per container via the base threshold engine.

**Architecture:** `PluginModel(GlancesPluginBase[list])`, `IS_COLLECTION=True`, `EMITS_ALERTS=True`, `primary_key="name"`. The model builds `self.watchers` (docker/podman/lxd) in `__init__` exactly as v4, and `_grab_stats` wraps the v4 flatten/merge/inject-engine/sort pipeline in `asyncio.to_thread` (`_update_watchers`). CPU/IO/net rates stay computed inside the engines' `StatsFetcher` classes. A `stop()` override tears the engine threads down on shutdown, wired through a new `GlancesPluginBase.stop()` extension point + `GlancesScheduler.stop()`. Per-container CPU/MEM thresholds keep their shipped config keys (`cpu_*`/`mem_*`) via a new `threshold_field` schema alias. A dedicated `render_curses_v5.render` mirrors v4 `msg_curse()`.

**Tech Stack:** Python, docker-py / podman / pylxd (all optional, import-guarded), asyncio (to_thread), curses renderer v5, pytest

## Global Constraints

- mirror-v4: read the v4 `msg_curse()` + `update_views()` + engines before writing the renderer/model; divergent "clean generic" layouts are regressions.
- **Reuse the v4 engines VERBATIM** (Option A): streaming threads, `ThreadedIterableStreamer`, `ThreadPoolExecutor(6)` inspect (issue #3559), and the in-`StatsFetcher` rate math are **not** rewritten. `_grab_stats` only wraps the top-level pipeline in `asyncio.to_thread`. No per-cycle blocking fan-out. Perf non-regression is non-negotiable.
- `containers` renders in the MAIN (RIGHT) column, full-width and responsive like `processlist` — **NOT** the 34-char LEFT-sidebar budget. `containers` is already in `RIGHT_SLOT` in `curses_renderer_v5.py`; no layout/orchestrator change.
- empty registry/stats must stay valid (no engine available → empty collection, never a crash).
- alerts fire on warning+ only; `careful` is colour-only (v5 engine collapses sub-warning levels).
- no dead code; no speculative config keys; surgical edits.
- do NOT touch `NEWS.rst` (release-time only).
- no commits/push/PR — stage only (each task ends at `git add`; NEVER `git commit`; never add a `Co-Authored-By` trailer).
- tests via `.venv/bin/python -m pytest`; lint `.venv/bin/python -m ruff check` / `.venv/bin/python -m ruff format`.

---

## File Structure

- **Modify** `glances/plugins/plugin/base_v5.py` — add the `stop()` no-op extension point (Task 1) and the `threshold_field` schema alias in the four threshold-resolution methods (Task 2).
- **Modify** `glances/scheduler_v5.py` — `GlancesScheduler.stop()` calls each plugin's `stop()` (Task 1).
- **Modify** `glances/outputs/glances_curses_v5.py` — thread the `--byte` flag into the per-cycle `view` (Task 3).
- **Create** `glances/plugins/containers/model_v5.py` — the collection plugin (Tasks 4–5).
- **Create** `glances/plugins/containers/render_curses_v5.py` — the TUI renderer (Task 6).
- **Create** `tests/test_plugin_base_v5_stop_and_threshold_field.py` — base extension-point tests (Tasks 1–2).
- **Modify** `tests/test_scheduler_v5.py` — scheduler `stop()` calls `plugin.stop()` (Task 1).
- **Create** `tests/test_plugin_containers_v5.py` — model tests (Tasks 4–5).
- **Create** `tests/test_plugin_containers_render_curses_v5.py` — renderer tests (Task 6).
- **Modify** `docs/aoa/containers.rst` — v5 note (Task 7). `containers` is already in `docs/aoa/index.rst` — do NOT re-add.

**Reconciliation notes (v4 source vs. spec — baked into this plan):**

1. **Memory alerting via `memory_percent`.** The spec (§6.1) said "watch `memory_usage` with `normalize_by: memory_limit`". But the base's `normalize_by` yields a **fraction** (usage/limit ∈ [0,1]), while the shipped `[containers] mem_careful=20` thresholds are **percents**. So this plan **computes a `memory_percent` field** (`memory_usage_no_cache / limit * 100`) at grab and declares **`memory_percent`** (with `threshold_field:"mem"`) as the watched field. Mirrors v4's `get_alert(value=usage_no_cache, maximum=limit)` exactly and matches `processlist`.
2. **Three distinct memory surfaces (maintainer decision — preserve v4 export parity; do NOT collapse):**
   - **`memory_usage`** (field) = the **exact value v4's engine stores/exports** (raw `usage`, minus `cache` when present). The reconciliation step **leaves it untouched** → no export/dashboard regression. **Feeds: export / REST.**
   - **`memory_usage_no_cache`** (field, `usage − inactive_file`) = computed at grab. **Feeds: the TUI MEM column (display).**
   - **`memory_percent`** (watched field, `memory_usage_no_cache / limit * 100`) = computed at grab. **Feeds: alerting (thresholds).**
   `memory_inactive_file` + `memory_limit` are kept for API parity; `/MAX` in the MEM column shows `memory_limit`.
3. **Sort is deliberately processlist-aligned (dynamic default).** The model pre-sorts each cycle by the **global** `glances_processes.sort_key` (read fresh — `auto` resolves to cpu/mem per load before the getter returns; never hardcode a static key). The renderer underlines the sorted column by comparing `view["sort_key"]` against a header→key map in the **same raw process-sort-key space** as `processlist` (`MEM → memory_percent`). No sort key is passed via payload metadata.
4. **No `__init__` prime.** v4 forces a first `update()` in `__init__` (streaming needs two samples for rates). This plan does **not** block startup with a synchronous docker call at discovery; CPU/IO/net rates simply warm over the first 1–2 scheduler cycles (shown as `_` until then). Deliberate, cleaner in the async model.
5. **`show_engine_name`/`show_pod_name`** are derived **in the renderer** from the payload data (`len({engine})>1`, `any(pod_name)`) — no need to pass them through metadata.
6. Filtering (`show`/`hide`) is done by the **base** `_filter_collection` on the `name` primary key — the grabber does **not** re-implement v4 `is_hide`.

---

### Task 1: base `stop()` teardown hook + scheduler wiring

**Files:**
- Modify: `glances/plugins/plugin/base_v5.py`
- Modify: `glances/scheduler_v5.py`
- Create: `tests/test_plugin_base_v5_stop_and_threshold_field.py`
- Modify: `tests/test_scheduler_v5.py`

**Interfaces:**
- Produces: `GlancesPluginBase.stop(self) -> None` (default no-op). `GlancesScheduler.stop()` calls `plugin.stop()` for every registered plugin (guarded, via `asyncio.to_thread`).

- [ ] **Step 1: Write the failing base-default test**

Create `tests/test_plugin_base_v5_stop_and_threshold_field.py`:

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Base-class extension points added for the G6A containers port:
- ``GlancesPluginBase.stop()`` teardown hook (default no-op).
- ``threshold_field`` schema alias in threshold resolution.
"""

from __future__ import annotations

from typing import ClassVar

import pytest

from glances.plugins.plugin.base_v5 import GlancesPluginBase


class _NoopCollection(GlancesPluginBase[list]):
    plugin_name: ClassVar[str] = "noop_collection"
    IS_COLLECTION: ClassVar[bool] = True
    fields_description: ClassVar[dict] = {"name": {"primary_key": True}}

    async def _grab_stats(self) -> list:
        return []


def _mk(store, config, cls=_NoopCollection):
    return cls(store, config)


def test_stop_default_is_noop(fake_store, fake_config):
    plugin = _mk(fake_store, fake_config)
    # Default stop() must exist and do nothing (no raise, no return value).
    assert plugin.stop() is None
```

Reuse whatever `fake_store` / `fake_config` fixtures the existing base tests use (see `tests/test_plugin_base_v5.py` / `conftest.py`); if the names differ, match them.

- [ ] **Step 2: Run it — expect FAIL**

Run: `.venv/bin/python -m pytest tests/test_plugin_base_v5_stop_and_threshold_field.py::test_stop_default_is_noop -v`
Expected: FAIL — `AttributeError: 'NoopCollection' object has no attribute 'stop'`.

- [ ] **Step 3: Add the `stop()` no-op to `GlancesPluginBase`**

In `glances/plugins/plugin/base_v5.py`, add (near the `update()` pipeline, after `update`):

```python
    def stop(self) -> None:
        """Release resources held by the plugin (background threads, sockets…).

        Default no-op. Overridden by plugins that own long-lived resources
        (e.g. ``containers`` engine streaming threads). Called once by the
        scheduler on shutdown, after the plugin's update loop is cancelled.
        Must be safe to call even if the plugin never produced stats.
        """
```

- [ ] **Step 4: Run it — expect PASS**

Run: `.venv/bin/python -m pytest tests/test_plugin_base_v5_stop_and_threshold_field.py::test_stop_default_is_noop -v`
Expected: PASS.

- [ ] **Step 5: Write the failing scheduler test**

In `tests/test_scheduler_v5.py`, add (match the file's existing fixture/async style — it already builds a `GlancesScheduler` with fake plugins):

```python
@pytest.mark.asyncio
async def test_stop_calls_plugin_stop_on_every_plugin(scheduler_factory):
    calls = []

    class _P:
        plugin_name = "p_ok"

        def __init__(self, name):
            self.plugin_name = name

        async def update(self):
            return None

        def stop(self):
            calls.append(self.plugin_name)

    class _PRaises(_P):
        def stop(self):
            calls.append(self.plugin_name)
            raise RuntimeError("boom")

    sched = scheduler_factory([_PRaises("p_bad"), _P("p_ok")])
    # stop() before run: no tasks, but must still call each plugin.stop().
    await sched.stop()
    # Both plugins torn down; the raising one did not block the other.
    assert set(calls) == {"p_bad", "p_ok"}
```

If `test_scheduler_v5.py` has no `scheduler_factory`, construct the scheduler the same way the existing tests do (build `GlancesScheduler`, `register()` each plugin with a refresh_time), then call `await sched.stop()`.

- [ ] **Step 6: Run it — expect FAIL**

Run: `.venv/bin/python -m pytest tests/test_scheduler_v5.py::test_stop_calls_plugin_stop_on_every_plugin -v`
Expected: FAIL — `stop()` currently only cancels tasks; `calls` stays empty.

- [ ] **Step 7: Wire `stop()` into `GlancesScheduler.stop()`**

In `glances/scheduler_v5.py`, replace the body of `stop()`:

```python
    async def stop(self) -> None:
        """Cancel every plugin loop, then let each plugin release resources."""
        for task in self._tasks:
            task.cancel()
        # Drain cancellations. `return_exceptions=True` swallows the
        # `CancelledError` we just raised on each task.
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        # Teardown hook: let each plugin release long-lived resources
        # (e.g. containers' engine streaming threads). Run in a thread so a
        # blocking join cannot stall the event loop, and guard each so one
        # failing teardown cannot block the others.
        for entry in self._entries:
            try:
                await asyncio.to_thread(entry.plugin.stop)
            except Exception as e:
                logger.warning("Scheduler: stop() of %s failed: %s", entry.plugin.plugin_name, e)
```

- [ ] **Step 8: Run both tests — expect PASS**

Run: `.venv/bin/python -m pytest tests/test_scheduler_v5.py::test_stop_calls_plugin_stop_on_every_plugin tests/test_plugin_base_v5_stop_and_threshold_field.py -v`
Expected: PASS.

- [ ] **Step 9: Regression + lint + stage**

Run: `.venv/bin/python -m pytest tests/test_scheduler_v5.py -q`
Expected: all pass (existing `stop()` tests unaffected — cancellation behaviour unchanged).
Run: `.venv/bin/python -m ruff check glances/plugins/plugin/base_v5.py glances/scheduler_v5.py tests/test_plugin_base_v5_stop_and_threshold_field.py tests/test_scheduler_v5.py && .venv/bin/python -m ruff format glances/plugins/plugin/base_v5.py glances/scheduler_v5.py tests/test_plugin_base_v5_stop_and_threshold_field.py tests/test_scheduler_v5.py`
Then: `git add glances/plugins/plugin/base_v5.py glances/scheduler_v5.py tests/test_plugin_base_v5_stop_and_threshold_field.py tests/test_scheduler_v5.py`

---

### Task 2: base `threshold_field` schema alias

**Files:**
- Modify: `glances/plugins/plugin/base_v5.py`
- Modify: `tests/test_plugin_base_v5_stop_and_threshold_field.py`

**Interfaces:**
- Produces: an optional `threshold_field` field-schema key. When present, the base uses it (instead of the field name) as the config-key prefix in `read_thresholds` / `read_thresholds_categorical` / `_scan_pk_override_fields`. Value lookup still uses the real field name. Default = field name (every existing plugin unaffected).

- [ ] **Step 1: Write the failing alias tests**

Append to `tests/test_plugin_base_v5_stop_and_threshold_field.py`:

```python
class _AliasCollection(GlancesPluginBase[list]):
    plugin_name: ClassVar[str] = "alias_collection"
    IS_COLLECTION: ClassVar[bool] = True
    fields_description: ClassVar[dict] = {
        "name": {"primary_key": True},
        # Value under `cpu_percent`, thresholds under the `cpu` prefix.
        "cpu_percent": {
            "watched": True,
            "watch_direction": "high",
            "threshold_field": "cpu",
        },
    }

    async def _grab_stats(self) -> list:
        return []


def test_threshold_field_alias_resolves_prefixed_keys(store_with, config_with):
    # Config uses the v4-style `cpu_*` prefix, NOT `cpu_percent_*`.
    config = config_with({"alias_collection": {"cpu_warning": "70", "cpu_critical": "90"}})
    plugin = _AliasCollection(store_with(), config)
    plugin._stats = [{"name": "web", "cpu_percent": 75.0}]
    plugin._derived_parameters()
    assert plugin._levels["web"]["cpu_percent"]["level"] == "warning"


def test_threshold_field_alias_resolves_per_pk_override(store_with, config_with):
    config = config_with({"alias_collection": {"cpu_warning": "70", "web_cpu_warning": "10"}})
    plugin = _AliasCollection(store_with(), config)
    plugin._stats = [{"name": "web", "cpu_percent": 15.0}]
    plugin._derived_parameters()
    # Per-container override `web_cpu_warning=10` wins → 15 ≥ 10 → warning.
    assert plugin._levels["web"]["cpu_percent"]["level"] == "warning"


def test_absent_threshold_field_preserves_field_name_default(store_with, config_with):
    # A field WITHOUT threshold_field keeps the field-name prefix.
    class _Plain(GlancesPluginBase[list]):
        plugin_name = "plain_collection"
        IS_COLLECTION = True
        fields_description = {
            "name": {"primary_key": True},
            "cpu_percent": {"watched": True, "watch_direction": "high"},
        }

        async def _grab_stats(self):
            return []

    config = config_with({"plain_collection": {"cpu_percent_warning": "70"}})
    plugin = _Plain(store_with(), config)
    plugin._stats = [{"name": "web", "cpu_percent": 75.0}]
    plugin._derived_parameters()
    assert plugin._levels["web"]["cpu_percent"]["level"] == "warning"
```

`store_with` / `config_with` are thin helpers over the existing test fixtures — a store factory and a config whose `.get(section, key, default)` / `.section_keys(section)` reflect the given dict. If the suite already exposes such helpers (see `tests/test_plugin_base_v5.py`), reuse them; otherwise add minimal local fakes in this test file (a dict-backed config exposing `get()` and `section_keys()`).

- [ ] **Step 2: Run — expect FAIL**

Run: `.venv/bin/python -m pytest tests/test_plugin_base_v5_stop_and_threshold_field.py -k threshold_field -v` (plus `test_absent_threshold_field...`)
Expected: the two alias tests FAIL (base looks up `cpu_percent_warning`, not `cpu_warning`); the `absent` test already PASSES.

- [ ] **Step 3: Add the alias helper + thread it through the four methods**

In `glances/plugins/plugin/base_v5.py`:

Add a small static helper:

```python
    @staticmethod
    def _threshold_key(field_name: str, schema: dict[str, Any]) -> str:
        """Config-key prefix for a watched field's thresholds.

        Defaults to the field name; a field may declare ``threshold_field``
        to decouple its config-key prefix from its value key (e.g.
        ``containers`` stores CPU under ``cpu_percent`` but reads thresholds
        from ``[containers] cpu_*``). See design §5.2.
        """
        return schema.get("threshold_field", field_name)
```

`_precompute_plugin_thresholds` — pass the alias as `field=`:

```python
        for field_name, schema in self._watched_fields:
            key = self._threshold_key(field_name, schema)
            if schema.get("threshold_type") == "categorical":
                mapping = read_thresholds_categorical(self.config, self.plugin_name, field=key)
                if mapping:
                    out[field_name] = {"mapping": mapping}
            else:
                thresholds = read_thresholds(
                    self.config,
                    self.plugin_name,
                    field=key,
                    defaults=schema.get("default_thresholds"),
                    strict=bool(schema.get("strict_thresholds", False)),
                )
                if thresholds:
                    out[field_name] = {"thresholds": thresholds}
```

(Note: the result stays keyed by the real `field_name` so item-side resolution is unchanged.)

`_resolve_numeric_thresholds` — slow path uses the alias:

```python
        return read_thresholds(
            self.config,
            self.plugin_name,
            field=self._threshold_key(field_name, schema),
            pk_value=pk_value,
            defaults=schema.get("default_thresholds"),
            strict=bool(schema.get("strict_thresholds", False)),
        )
```

`_resolve_categorical_mapping` — it lacks a `schema` param; look it up, then use the alias:

```python
        schema = self._fields.get(field_name, {})
        return read_thresholds_categorical(
            self.config, self.plugin_name, field=self._threshold_key(field_name, schema), pk_value=pk_value
        )
```

`_scan_pk_override_fields` — build the suffix/prefix from the alias, still record the real `field_name`:

```python
        for key in section_keys:
            for field_name, schema in self._watched_fields:
                tkey = self._threshold_key(field_name, schema)
                for level in levels:
                    suffix = f"_{tkey}_{level}"
                    if key.endswith(suffix) and not key.startswith(f"{tkey}_"):
                        prefix_len = len(key) - len(suffix)
                        if prefix_len > 0:
                            out.add(field_name)
                            break
```

- [ ] **Step 4: Run alias tests — expect PASS**

Run: `.venv/bin/python -m pytest tests/test_plugin_base_v5_stop_and_threshold_field.py -v`
Expected: all PASS.

- [ ] **Step 5: Full base + plugin regression (no other plugin affected)**

Run: `.venv/bin/python -m pytest tests/test_plugin_base_v5.py tests/test_plugin_processlist_v5.py tests/test_plugin_network_v5.py -q`
Expected: all pass (fields without `threshold_field` behave exactly as before — the helper returns the field name).

- [ ] **Step 6: Lint + stage**

Run: `.venv/bin/python -m ruff check glances/plugins/plugin/base_v5.py tests/test_plugin_base_v5_stop_and_threshold_field.py && .venv/bin/python -m ruff format glances/plugins/plugin/base_v5.py tests/test_plugin_base_v5_stop_and_threshold_field.py`
Then: `git add glances/plugins/plugin/base_v5.py tests/test_plugin_base_v5_stop_and_threshold_field.py`

---

### Task 3: thread `--byte` into the TUI `view`

**Files:**
- Modify: `glances/outputs/glances_curses_v5.py`
- Modify: `tests/test_curses_v5.py`

**Interfaces:**
- Produces: `view["byte"]` (bool) in the per-cycle view. Mirrors the `--fahrenheit` / `--hide-public-info` wiring (G4B). Default `False` (bits — v4 default). The containers renderer reads `view.get("byte", False)`.

**Context:** `TuiV5.__init__` already accepts flag params (`fahrenheit`, and via G4B `hide_public_info`) stored as `self._fahrenheit` etc., surfaced in `_build_view`. Add `byte` the same way. The constructor call site (`main_v5` / `_TuiV5(`) passes `fahrenheit=args.fahrenheit`; add `byte=getattr(args, "byte", False)` there too. (Find the exact call site with `grep -n "fahrenheit=" glances/outputs/glances_curses_v5.py glances/main_v5.py`.)

- [ ] **Step 1: Write the failing view test**

In `tests/test_curses_v5.py`, add (match the existing `_build_view` / TuiV5 test pattern used for `fahrenheit`):

```python
def test_build_view_carries_byte_flag(tui_factory):
    tui = tui_factory(byte=True)
    view = tui._build_view(max_x=200)
    assert view["byte"] is True


def test_build_view_byte_defaults_false(tui_factory):
    tui = tui_factory()
    view = tui._build_view(max_x=200)
    assert view["byte"] is False
```

Use the same `tui_factory` / construction helper the `fahrenheit` view tests use; if there is none, construct `TuiV5` the way those tests do and pass `byte=...`.

- [ ] **Step 2: Run — expect FAIL**

Run: `.venv/bin/python -m pytest tests/test_curses_v5.py -k byte -v`
Expected: FAIL — `TuiV5.__init__` has no `byte` param / `view` has no `byte` key.

- [ ] **Step 3: Add the `byte` param + view key**

In `glances/outputs/glances_curses_v5.py`, `TuiV5.__init__` signature — add `byte: bool = False` next to `fahrenheit`, and store `self._byte = bool(byte)` next to `self._fahrenheit`. In `_build_view`, add:

```python
        view["byte"] = self._byte
```

At the constructor call site (`_TuiV5(` in `main_v5` — or wherever `fahrenheit=` is passed), add `byte=getattr(args, "byte", False)`.

- [ ] **Step 4: Run — expect PASS**

Run: `.venv/bin/python -m pytest tests/test_curses_v5.py -k byte -v`
Expected: PASS.

- [ ] **Step 5: Regression + lint + stage**

Run: `.venv/bin/python -m pytest tests/test_curses_v5.py -q`
Expected: all pass (additive change; existing view keys unchanged).
Run: `.venv/bin/python -m ruff check glances/outputs/glances_curses_v5.py tests/test_curses_v5.py && .venv/bin/python -m ruff format glances/outputs/glances_curses_v5.py tests/test_curses_v5.py`
Then: `git add glances/outputs/glances_curses_v5.py tests/test_curses_v5.py`

---

### Task 4: containers model — identity, fields, EMITS_ALERTS, levels

**Files:**
- Create: `glances/plugins/containers/model_v5.py`
- Create: `tests/test_plugin_containers_v5.py`

**Interfaces:**
- Consumes: `GlancesPluginBase` from `glances.plugins.plugin.base_v5`.
- Produces: `PluginModel` (collection). `plugin_name="containers"`, `IS_COLLECTION=True`, `EMITS_ALERTS=True`, `_primary_key="name"`. `fields_description` per below. Task 5 adds `__init__` (engines), `_grab_stats`, `_add_metadata`, `_sort`, `stop()` to this same class.

- [ ] **Step 1: Write the failing identity/fields/levels tests**

Create `tests/test_plugin_containers_v5.py`:

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the Glances v5 containers plugin model."""

from __future__ import annotations

import pytest

from glances.plugins.containers.model_v5 import PluginModel


def _mk(store_with, config_with, section=None):
    return PluginModel(store_with(), config_with({"containers": section or {}}))


def test_identity(store_with, config_with):
    p = _mk(store_with, config_with)
    assert p.plugin_name == "containers"
    assert p.IS_COLLECTION is True
    assert p.EMITS_ALERTS is True
    assert p._primary_key == "name"


def test_fields_present(store_with, config_with):
    p = _mk(store_with, config_with)
    fd = p.fields_description
    for key in (
        "name",
        "id",
        "image",
        "status",
        "created",
        "command",
        "cpu_percent",
        "cpu_limit",
        "memory_usage",
        "memory_usage_no_cache",
        "memory_limit",
        "memory_percent",
        "io_rx",
        "io_wx",
        "network_rx",
        "network_tx",
        "ports",
        "uptime",
        "engine",
        "pod_name",
        "pod_id",
    ):
        assert key in fd, key
    assert fd["name"].get("primary_key") is True
    # Threshold aliases (design §5.2).
    assert fd["cpu_percent"]["threshold_field"] == "cpu"
    assert fd["memory_percent"]["threshold_field"] == "mem"


def test_cpu_level_uses_cpu_prefix_thresholds(store_with, config_with):
    p = _mk(store_with, config_with, {"cpu_warning": "70", "cpu_critical": "90"})
    p._stats = [{"name": "web", "cpu_percent": 95.0, "memory_percent": None}]
    p._derived_parameters()
    assert p._levels["web"]["cpu_percent"]["level"] == "critical"


def test_mem_level_uses_mem_prefix_thresholds(store_with, config_with):
    p = _mk(store_with, config_with, {"mem_careful": "20", "mem_warning": "50"})
    p._stats = [{"name": "web", "cpu_percent": None, "memory_percent": 60.0}]
    p._derived_parameters()
    assert p._levels["web"]["memory_percent"]["level"] == "warning"


def test_per_container_cpu_override(store_with, config_with):
    p = _mk(store_with, config_with, {"cpu_warning": "70", "web_cpu_warning": "10"})
    p._stats = [{"name": "web", "cpu_percent": 15.0}]
    p._derived_parameters()
    assert p._levels["web"]["cpu_percent"]["level"] == "warning"
```

Reuse the same `store_with` / `config_with` helpers as Task 2 (a dict-backed config supporting `get()` + `section_keys()`), placing shared fakes in `tests/conftest.py` if not already there.

- [ ] **Step 2: Run — expect FAIL**

Run: `.venv/bin/python -m pytest tests/test_plugin_containers_v5.py -v`
Expected: FAIL — `ModuleNotFoundError: glances.plugins.containers.model_v5`.

- [ ] **Step 3: Create the model scaffold + fields (no engines yet)**

Create `glances/plugins/containers/model_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — Containers plugin (collection, per-container).

Port of ``glances/plugins/containers/__init__.py`` (v4). Reuses the v4
Docker/Podman/LXD engine machinery VERBATIM (streaming threads +
ThreadPoolExecutor); ``_grab_stats`` only wraps the v4 flatten/merge/sort
pipeline in ``asyncio.to_thread``. CPU/IO/net rates stay computed inside the
engines' ``StatsFetcher`` classes. See design doc
docs/superpowers/specs/2026-07-14-glances-v5-g6a-design.md.
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar

from glances.plugins.plugin.base_v5 import GlancesPluginBase

logger = logging.getLogger(__name__)


class PluginModel(GlancesPluginBase[list]):
    """Per-container plugin (collection)."""

    plugin_name: ClassVar[str] = "containers"
    IS_COLLECTION: ClassVar[bool] = True
    EMITS_ALERTS: ClassVar[bool] = True

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "name": {"description": "Container name.", "unit": "string", "primary_key": True},
        "id": {"description": "Container ID.", "unit": "string"},
        "image": {"description": "Container image.", "unit": "string"},
        "status": {"description": "Container status.", "unit": "string"},
        "created": {"description": "Container creation date.", "unit": "string"},
        "command": {"description": "Container command.", "unit": "string"},
        "cpu_percent": {
            "description": "Container CPU consumption.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "threshold_field": "cpu",
        },
        "cpu_limit": {"description": "Container CPU limit.", "unit": "number"},
        "memory_usage": {
            "description": "Container memory usage (v4 export value: usage − cache when present). Feeds export/REST.",
            "unit": "byte",
        },
        "memory_usage_no_cache": {
            "description": "Container memory usage minus inactive_file. TUI display value.",
            "unit": "byte",
        },
        "memory_inactive_file": {"description": "Container memory inactive file.", "unit": "byte"},
        "memory_limit": {"description": "Container memory limit.", "unit": "byte"},
        "memory_percent": {
            "description": "Container memory usage as a percentage of its limit.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "threshold_field": "mem",
        },
        "io_rx": {"description": "Container IO bytes read rate.", "unit": "bytepersecond"},
        "io_wx": {"description": "Container IO bytes write rate.", "unit": "bytepersecond"},
        "network_rx": {"description": "Container network RX bitrate.", "unit": "bitpersecond"},
        "network_tx": {"description": "Container network TX bitrate.", "unit": "bitpersecond"},
        "ports": {"description": "Container ports.", "unit": "string"},
        "uptime": {"description": "Container uptime.", "unit": "string"},
        "engine": {"description": "Container engine (Docker, Podman, LXD).", "unit": "string"},
        "pod_name": {"description": "Pod name (Podman only).", "unit": "string"},
        "pod_id": {"description": "Pod ID (Podman only).", "unit": "string"},
    }

    async def _grab_stats(self) -> list:
        # Implemented in Task 5.
        return []
```

- [ ] **Step 4: Run — expect PASS**

Run: `.venv/bin/python -m pytest tests/test_plugin_containers_v5.py -v`
Expected: PASS (levels come from the base engine + the `threshold_field` alias from Task 2).

- [ ] **Step 5: Lint + stage**

Run: `.venv/bin/python -m ruff check glances/plugins/containers/model_v5.py tests/test_plugin_containers_v5.py && .venv/bin/python -m ruff format glances/plugins/containers/model_v5.py tests/test_plugin_containers_v5.py`
Then: `git add glances/plugins/containers/model_v5.py tests/test_plugin_containers_v5.py`

---

### Task 5: containers model — engines, `_grab_stats`, memory reconciliation, sort, `stop()`

**Files:**
- Modify: `glances/plugins/containers/model_v5.py`
- Modify: `tests/test_plugin_containers_v5.py`

**Interfaces:**
- Consumes: `DockerExtension`/`disable_plugin_docker`, `PodmanExtension`/`disable_plugin_podman`, `LxdExtension`/`disable_plugin_lxd` from `glances.plugins.containers.engines.*`; `glances_processes` + `sort_stats` from `glances.processes`.
- Produces on `PluginModel`: `__init__(store, config)` builds `self.watchers`; `_update_watchers()` (flatten/merge/inject-engine/reconcile-memory/sort); async `_grab_stats` wrapping it in `to_thread`; `_add_metadata` surfacing `disable_stats` + `max_name_size`; `stop()` override.

- [ ] **Step 1: Write the failing engine/grab/sort/stop tests**

Append to `tests/test_plugin_containers_v5.py`:

```python
class _FakeWatcher:
    def __init__(self, containers, raises=False):
        self._containers = containers
        self._raises = raises
        self.stopped = False

    def update(self, all_tag):
        if self._raises:
            raise RuntimeError("engine down")
        return {}, [dict(c) for c in self._containers]

    def stop(self):
        self.stopped = True


def _model_with_watchers(store_with, config_with, watchers, section=None):
    p = PluginModel(store_with(), config_with({"containers": section or {}}))
    p.watchers = watchers
    return p


@pytest.mark.asyncio
async def test_grab_merges_engines_and_injects_engine_field(store_with, config_with):
    # memory_usage=250 simulates the engine's v4 export value (usage−cache);
    # the nested memory dict drives the no-cache + percent surfaces.
    d = {
        "name": "web",
        "key": "name",
        "memory_usage": 250,
        "memory": {"usage": 300, "inactive_file": 100, "limit": 1000},
    }
    p = _model_with_watchers(store_with, config_with, {"docker": _FakeWatcher([d])})
    out = await p._grab_stats()
    assert len(out) == 1
    assert out[0]["engine"] == "docker"
    # Three memory surfaces:
    assert out[0]["memory_usage"] == 250  # export (v4 value, untouched)
    assert out[0]["memory_usage_no_cache"] == 200  # display (usage − inactive_file)
    assert out[0]["memory_percent"] == 20.0  # alert  (200 / 1000 * 100)


@pytest.mark.asyncio
async def test_grab_partial_failure_keeps_other_engine(store_with, config_with):
    ok = {"name": "web", "memory": {}}
    p = _model_with_watchers(
        store_with,
        config_with,
        {"bad": _FakeWatcher([], raises=True), "docker": _FakeWatcher([ok])},
    )
    out = await p._grab_stats()
    assert [c["name"] for c in out] == ["web"]


@pytest.mark.asyncio
async def test_grab_empty_when_no_watcher(store_with, config_with):
    p = _model_with_watchers(store_with, config_with, {})
    assert await p._grab_stats() == []


def test_stop_calls_each_watcher(store_with, config_with):
    w1, w2 = _FakeWatcher([]), _FakeWatcher([])
    p = _model_with_watchers(store_with, config_with, {"docker": w1, "podman": w2})
    p.stop()
    assert w1.stopped and w2.stopped


def test_stop_one_raising_watcher_does_not_block_others(store_with, config_with):
    class _Boom(_FakeWatcher):
        def stop(self):
            raise RuntimeError("boom")

    good = _FakeWatcher([])
    p = _model_with_watchers(store_with, config_with, {"bad": _Boom([]), "docker": good})
    p.stop()  # must not raise
    assert good.stopped


def test_metadata_carries_disable_stats_and_max_name_size(store_with, config_with):
    p = PluginModel(store_with(), config_with({"containers": {"disable_stats": "command", "max_name_size": "12"}}))
    p._add_metadata()
    assert "command" in p._metadata["disable_stats"]
    assert p._metadata["max_name_size"] == 12
```

- [ ] **Step 2: Run — expect FAIL**

Run: `.venv/bin/python -m pytest tests/test_plugin_containers_v5.py -k "grab or stop or metadata" -v`
Expected: FAIL — `_grab_stats` returns `[]`, `stop()` is the base no-op, `_add_metadata` lacks the extra keys.

- [ ] **Step 3: Implement engines, grab, reconcile, sort, metadata, stop**

Replace the imports + body of `glances/plugins/containers/model_v5.py` (keep the `fields_description` from Task 4):

```python
from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

from glances.plugins.containers.engines import ContainersExtension
from glances.plugins.containers.engines.docker import DockerExtension, disable_plugin_docker
from glances.plugins.containers.engines.lxd import LxdExtension, disable_plugin_lxd
from glances.plugins.containers.engines.podman import PodmanExtension, disable_plugin_podman
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.processes import glances_processes
from glances.processes import sort_stats as sort_stats_processes

logger = logging.getLogger(__name__)

_DEFAULT_PODMAN_SOCK = "unix:///run/user/1000/podman/podman.sock"
```

Add to the class (after `fields_description`):

```python
def __init__(self, store, config) -> None:
    super().__init__(store, config)

    # Reuse the v4 engines verbatim (Option A). Each construction is
    # guarded so a broken engine leaves the others (and an empty plugin)
    # valid.
    self.watchers: dict[str, ContainersExtension] = {}
    if not disable_plugin_docker:
        self._try_add_watcher("docker", lambda: DockerExtension())
    if not disable_plugin_podman:
        self._try_add_watcher("podman", lambda: PodmanExtension(podman_sock=self._podman_sock()))
    if not disable_plugin_lxd:
        self._try_add_watcher("lxd", lambda: LxdExtension(poll_interval=self._poll_interval()))

    # Static config surfaced to the renderer via metadata each cycle.
    raw_disable = self.config.get(self.plugin_name, "disable_stats", "")
    self._disable_stats: list[str] = (
        [s.strip() for s in raw_disable.split(",") if s.strip()]
        if isinstance(raw_disable, str)
        else list(raw_disable or [])
    )
    try:
        self._max_name_size = int(self.config.get(self.plugin_name, "max_name_size", 20))
    except (TypeError, ValueError):
        self._max_name_size = 20


def _try_add_watcher(self, engine: str, factory) -> None:
    try:
        self.watchers[engine] = factory()
    except Exception as e:
        logger.warning("containers: engine %s unavailable (%s) — skipped", engine, e)


def _podman_sock(self) -> str:
    sock = self.config.get(self.plugin_name, "podman_sock", "")
    if isinstance(sock, (list, tuple)):
        sock = sock[0] if sock else ""
    return str(sock) if sock else _DEFAULT_PODMAN_SOCK


def _poll_interval(self) -> float:
    val = self.config.get(self.plugin_name, "refresh", -1.0)
    try:
        val = float(val)
    except (TypeError, ValueError):
        val = -1.0
    return val if val > 0 else 2.0


def _all_tag(self) -> bool:
    val = self.config.get(self.plugin_name, "all", False)
    return str(val).lower() == "true"


def _update_watchers(self) -> list:
    """v4 flatten/merge/inject-engine/reconcile-memory/sort pipeline.

    Blocking (reads engine snapshots); always called via to_thread.
    show/hide filtering is left to the base ``_filter_collection`` on the
    ``name`` primary key — not re-implemented here.
    """
    all_tag = self._all_tag()
    items: list[dict[str, Any]] = []
    for engine, watcher in self.watchers.items():
        try:
            _version, containers = watcher.update(all_tag=all_tag)
        except Exception as e:
            logger.warning("containers: engine %s update failed: %s", engine, e)
            continue
        for c in containers:
            c["engine"] = engine
            self._reconcile_memory(c)
            items.append(c)
    return self._sort(items)


@staticmethod
def _reconcile_memory(container: dict[str, Any]) -> None:
    """Compute the three memory surfaces from the engine's nested
    ``memory`` dict (design §6.1, three-surface decision):

    - ``memory_usage``          — LEFT UNTOUCHED (v4 export value set by
      the engine's ``generate_stats``). Feeds export / REST.
    - ``memory_usage_no_cache`` — ``usage − inactive_file``. Feeds the
      TUI MEM column (display).
    - ``memory_percent``        — ``memory_usage_no_cache / limit * 100``.
      Feeds alerting (thresholds, ``threshold_field="mem"``).
    """
    mem = container.get("memory") or {}
    if "usage" not in mem:
        return
    usage_no_cache = mem["usage"] - mem.get("inactive_file", 0)
    container["memory_usage_no_cache"] = usage_no_cache
    container["memory_inactive_file"] = mem.get("inactive_file")
    limit = mem.get("limit")
    container["memory_percent"] = (usage_no_cache / limit * 100.0) if limit else None


@staticmethod
def _sort(stats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Faithful reimplementation of v4 ``sort_docker_stats`` — sort by the
    process engine's active sort key so containers track the process sort.

    ``glances_processes.sort_key`` is read fresh every cycle (dynamic
    default preserved: ``auto`` resolves to cpu/mem per load before the
    getter returns — never hardcode a static key). The map resolves the
    dynamically-selected key to a container column; the fallback tuple is
    only the column mapping for genuinely unmapped keys, not a static
    sort key."""
    sort_by, sort_by_secondary = {
        "memory_percent": ("memory_usage", "cpu_percent"),
        "name": ("name", "cpu_percent"),
    }.get(glances_processes.sort_key, ("cpu_percent", "memory_usage"))
    try:
        return sort_stats_processes(
            stats,
            sorted_by=sort_by,
            sorted_by_secondary=sort_by_secondary,
            reverse=glances_processes.sort_key != "name",
        )
    except Exception as e:
        logger.debug("containers: sort failed: %s", e)
        return stats


async def _grab_stats(self) -> list:
    if not self.watchers:
        return []
    try:
        return await asyncio.to_thread(self._update_watchers)
    except Exception as e:
        logger.warning("containers: grab failed: %s", e)
        return []


def _add_metadata(self) -> None:
    super()._add_metadata()
    # Static [containers] config the renderer needs (it has no config access).
    self._metadata["disable_stats"] = self._disable_stats
    self._metadata["max_name_size"] = self._max_name_size


def stop(self) -> None:
    for engine, watcher in self.watchers.items():
        try:
            watcher.stop()
        except Exception as e:
            logger.warning("containers: stop(%s) failed: %s", engine, e)
```

Remove the placeholder `_grab_stats` from Task 4. Keep `logger` defined once.

- [ ] **Step 4: Run — expect PASS**

Run: `.venv/bin/python -m pytest tests/test_plugin_containers_v5.py -v`
Expected: all PASS.

- [ ] **Step 5: Discovery smoke — the model imports and instantiates**

Run: `.venv/bin/python -c "from glances.plugins.containers.model_v5 import PluginModel; print(PluginModel.plugin_name)"`
Expected: prints `containers` with no import error (engines are import-guarded — missing docker/podman/pylxd only logs a warning).

- [ ] **Step 6: Lint + stage**

Run: `.venv/bin/python -m ruff check glances/plugins/containers/model_v5.py tests/test_plugin_containers_v5.py && .venv/bin/python -m ruff format glances/plugins/containers/model_v5.py tests/test_plugin_containers_v5.py`
Then: `git add glances/plugins/containers/model_v5.py tests/test_plugin_containers_v5.py`

---

### Task 6: containers renderer (`render_curses_v5.py`)

**Files:**
- Create: `glances/plugins/containers/render_curses_v5.py`
- Create: `tests/test_plugin_containers_render_curses_v5.py`

**Interfaces:**
- Consumes: `Cell`, `Row`, `ColorRole`, `_LEVEL_TO_ROLE`, `title_role` from `glances.outputs.curses_renderer_v5`; `payload` (`{"data": [...], "disable_stats": [...], "max_name_size": int, "_levels": {...}}`), `view` (`{"sort_key", "byte"}`).
- Produces: `render(payload, fields_desc=None, view=None) -> list[Row]` — header row + one row per container. Declares `view` → auto-registered as view-aware (`_accepts_view`). Empty `data` → the renderer is not even called (build_frame drops empty collections), but the function must still return `[]` defensively.

**Column model (mirror v4 `msg_curse`/`build_header`), each gated by `disable_stats`:** Engine (only if >1 engine in data), Pod (only if any `pod_name`), Name (`min(max_name_size, longest name)`, SORT-underline if `sort_key=="name"`), Status (`{:>10}`, coloured by status→role), Uptime (`{:>10}`), CPU% (`{:>6.1f}`, SORT if `cpu_percent`, coloured by level), MEM (`{:>7}` auto_unit(`memory_usage_no_cache`), SORT if `memory_percent`, coloured by `memory_percent` level) + `/MAX` (`{:<7}` auto_unit(`memory_limit`)), IOR/s + IOW/s (`{:>7}`/`{:<7}` auto_unit(io)+"B"), Rx/s + Tx/s (bits×8 unless `view["byte"]`, +"b"/""), Ports (`{:16}`), Command.

- [ ] **Step 1: Write failing renderer tests**

Create `tests/test_plugin_containers_render_curses_v5.py`:

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the Glances v5 containers TUI renderer."""

from __future__ import annotations

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.containers.render_curses_v5 import render


def _payload(data, levels=None, disable_stats=None, max_name_size=20):
    return {
        "data": data,
        "_levels": levels or {},
        "disable_stats": disable_stats or [],
        "max_name_size": max_name_size,
    }


def _texts(row):
    return "".join(c.text for c in row.cells)


def test_empty_data_returns_empty():
    assert render(_payload([])) == []


def test_header_and_one_row():
    data = [
        {
            "name": "web",
            "engine": "docker",
            "status": "running",
            "uptime": "1h",
            "cpu_percent": 12.0,
            "memory_usage_no_cache": 200,
            "memory_limit": 1000,
            "ports": "",
        }
    ]
    rows = render(_payload(data), None, {"sort_key": None, "byte": False})
    assert len(rows) == 2  # header + 1
    header = _texts(rows[0])
    assert "Name" in header and "CPU%" in header and "Status" in header


def test_status_colour_running_is_ok():
    data = [{"name": "web", "engine": "docker", "status": "running"}]
    rows = render(_payload(data), None, {})
    # find the status cell (text startswith "running" padded)
    status_cells = [c for c in rows[1].cells if "running" in c.text]
    assert status_cells and status_cells[0].color == ColorRole.OK


def test_status_colour_exited_is_warning():
    data = [{"name": "web", "engine": "docker", "status": "exited"}]
    rows = render(_payload(data), None, {})
    cells = [c for c in rows[1].cells if "exited" in c.text]
    assert cells and cells[0].color == ColorRole.WARNING


def test_status_colour_dead_is_critical():
    data = [{"name": "web", "engine": "docker", "status": "dead"}]
    rows = render(_payload(data), None, {})
    cells = [c for c in rows[1].cells if "dead" in c.text]
    assert cells and cells[0].color == ColorRole.CRITICAL


def test_cpu_cell_coloured_by_level():
    data = [{"name": "web", "engine": "docker", "status": "running", "cpu_percent": 95.0}]
    levels = {"web": {"cpu_percent": {"level": "critical", "prominent": False}}}
    rows = render(_payload(data, levels), None, {})
    cpu_cells = [c for c in rows[1].cells if c.text.strip() == "95.0"]
    assert cpu_cells and cpu_cells[0].color == ColorRole.CRITICAL


def test_disable_stats_hides_column():
    data = [{"name": "web", "engine": "docker", "status": "running", "cpu_percent": 12.0}]
    rows = render(_payload(data, disable_stats=["cpu"]), None, {})
    assert "CPU%" not in _texts(rows[0])


def test_engine_column_only_when_multiple_engines():
    one = [{"name": "a", "engine": "docker", "status": "running"}]
    two = [
        {"name": "a", "engine": "docker", "status": "running"},
        {"name": "b", "engine": "podman", "status": "running"},
    ]
    assert "Engine" not in _texts(render(_payload(one), None, {})[0])
    assert "Engine" in _texts(render(_payload(two), None, {})[0])


def test_pod_column_only_when_pod_present():
    no_pod = [{"name": "a", "engine": "docker", "status": "running"}]
    with_pod = [{"name": "a", "engine": "podman", "status": "running", "pod_name": "p1", "pod_id": "abc"}]
    assert "Pod" not in _texts(render(_payload(no_pod), None, {})[0])
    assert "Pod" in _texts(render(_payload(with_pod), None, {})[0])


def test_sort_underline_on_cpu():
    data = [{"name": "web", "engine": "docker", "status": "running", "cpu_percent": 12.0}]
    rows = render(_payload(data), None, {"sort_key": "cpu_percent"})
    cpu_hdr = [c for c in rows[0].cells if "CPU%" in c.text]
    assert cpu_hdr and cpu_hdr[0].underline is True


def test_sort_underline_on_mem_maps_to_memory_percent():
    # Process sort key `memory_percent` underlines the MEM header (processlist-aligned).
    data = [
        {"name": "web", "engine": "docker", "status": "running", "memory_usage_no_cache": 100, "memory_limit": 1000}
    ]
    rows = render(_payload(data), None, {"sort_key": "memory_percent"})
    mem_hdr = [c for c in rows[0].cells if c.text.strip() == "MEM"]
    assert mem_hdr and mem_hdr[0].underline is True


def test_net_bits_vs_bytes():
    data = [{"name": "web", "engine": "docker", "status": "running", "network_rx": 100, "network_tx": 0}]
    bits = render(_payload(data), None, {"byte": False})
    byts = render(_payload(data), None, {"byte": True})
    # bits multiply by 8 → different rendered Rx text
    assert _texts(bits[1]) != _texts(byts[1])
```

- [ ] **Step 2: Run — expect FAIL**

Run: `.venv/bin/python -m pytest tests/test_plugin_containers_render_curses_v5.py -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement the renderer**

Create `glances/plugins/containers/render_curses_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the containers plugin.

Mirror of v4 ``containers.msg_curse``. Header row + one row per container,
MAIN-column full width. Columns are gated by ``[containers] disable_stats``
(surfaced via payload metadata) and by the data (Engine only with >1 engine,
Pod only when a pod is present).
"""

from __future__ import annotations

from typing import Any

from glances.globals import auto_unit
from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row, title_role

# Header → the GLOBAL process sort key (view["sort_key"], dynamic/auto-resolved),
# processlist-aligned. MEM maps to memory_percent because the process sort-key
# space uses memory_percent (the model's data sort maps that onto the
# memory_usage column — same column underlined as is actually sorted).
_HEADER_SORT_KEY: dict[str, str] = {"Name": "name", "CPU%": "cpu_percent", "MEM": "memory_percent"}

# v4 container_alert(status) → ColorRole. No ERROR/INFO roles in v5 →
# dead/unhealthy fold to CRITICAL, everything unclassified to DEFAULT.
_STATUS_ROLE: dict[str, ColorRole] = {
    "running": ColorRole.OK,
    "healthy": ColorRole.OK,
    "dead": ColorRole.CRITICAL,
    "unhealthy": ColorRole.CRITICAL,
    "created": ColorRole.WARNING,
    "exited": ColorRole.WARNING,
    "paused": ColorRole.CAREFUL,
    "restarting": ColorRole.CAREFUL,
}


def _status_role(status: str) -> ColorRole:
    return _STATUS_ROLE.get(status, ColorRole.DEFAULT)


def _level_role(level_entry: Any) -> tuple[ColorRole, bool]:
    if isinstance(level_entry, dict):
        return (_LEVEL_TO_ROLE.get(level_entry.get("level"), ColorRole.DEFAULT), bool(level_entry.get("prominent")))
    return (ColorRole.DEFAULT, False)


def render(
    payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]] | None = None, view: dict[str, Any] | None = None
) -> list[Row]:
    items: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        raw = payload.get("data")
        if isinstance(raw, list):
            items = [i for i in raw if isinstance(i, dict)]
    if not items:
        return []

    view = view or {}
    sort_key = view.get("sort_key")
    to_bit, net_unit = (1, "") if view.get("byte") else (8, "b")

    disable = set(payload.get("disable_stats") or [])
    levels = payload.get("_levels") if isinstance(payload.get("_levels"), dict) else {}
    conf_max = payload.get("max_name_size") or 20
    name_w = min(int(conf_max), max((len(str(i.get("name", ""))) for i in items), default=1))

    show_engine = len({i.get("engine") for i in items}) > 1
    show_pod = any(i.get("pod_name") for i in items)
    title_color = title_role(payload)

    def hdr(label: str, width: int, *, ljust: bool = False, color: ColorRole = ColorRole.HEADER) -> Cell:
        text = f"{label:<{width}}" if ljust else f"{label:>{width}}"
        return Cell(
            text=text, color=color, bold=True, underline=bool(sort_key) and _HEADER_SORT_KEY.get(label) == sort_key
        )

    # ---- header row
    h: list[Cell] = []
    if show_engine:
        h.append(hdr("Engine", 6, ljust=True, color=title_color))
    if show_pod:
        h.append(hdr("Pod", 12, ljust=True))
    if "name" not in disable:
        h.append(hdr("Name", name_w, ljust=True, color=title_color if not show_engine else ColorRole.HEADER))
    if "status" not in disable:
        h.append(hdr("Status", 10))
    if "uptime" not in disable:
        h.append(hdr("Uptime", 10))
    if "cpu" not in disable:
        h.append(hdr("CPU%", 6))
    if "mem" not in disable:
        h.append(hdr("MEM", 7))
        h.append(Cell(text=f"/{'MAX':<7}", color=ColorRole.HEADER, bold=True))
    if "diskio" not in disable:
        h.append(hdr("IOR/s", 7))
        h.append(hdr("IOW/s", 7, ljust=True))
    if "networkio" not in disable:
        h.append(hdr("Rx/s", 7))
        h.append(hdr("Tx/s", 7, ljust=True))
    if "ports" not in disable:
        h.append(hdr("Ports", 16, ljust=True))
    if "command" not in disable:
        h.append(hdr("Command", 8, ljust=True))
    rows: list[Row] = [Row(cells=h)]

    # ---- data rows
    for c in items:
        item_levels = levels.get(c.get("name"), {}) if isinstance(levels, dict) else {}
        cells: list[Cell] = []
        if show_engine:
            cells.append(Cell(text=f"{str(c.get('engine', '')):<6}"))
        if show_pod:
            cells.append(Cell(text=f"{str(c.get('pod_id') or '-'):<12}"))
        if "name" not in disable:
            cells.append(Cell(text=f"{str(c.get('name', ''))[:name_w]:<{name_w}}"))
        if "status" not in disable:
            status = str(c.get("status", ""))
            cells.append(Cell(text=f"{status[:10]:>10}", color=_status_role(status)))
        if "uptime" not in disable:
            cells.append(Cell(text=f"{(c.get('uptime') or '_'):>10}"))
        if "cpu" not in disable:
            cpu = c.get("cpu_percent")
            role, prom = _level_role(item_levels.get("cpu_percent"))
            text = f"{cpu:>6.1f}" if isinstance(cpu, (int, float)) else f"{'_':>6}"
            cells.append(Cell(text=text, color=role, prominent=prom))
        if "mem" not in disable:
            # Display the no-cache value (v4 MEM column); /MAX = limit. Colour
            # from the memory_percent level. memory_usage (export) is NOT shown.
            usage, limit = c.get("memory_usage_no_cache"), c.get("memory_limit")
            role, prom = _level_role(item_levels.get("memory_percent"))
            mtext = f"{auto_unit(usage):>7}" if isinstance(usage, (int, float)) else f"{'_':>7}"
            cells.append(Cell(text=mtext, color=role, prominent=prom))
            ltext = f"/{auto_unit(limit):<7}" if isinstance(limit, (int, float)) else f"/{'_':<7}"
            cells.append(Cell(text=ltext))
        if "diskio" not in disable:
            cells.append(Cell(text=_io_cell(c.get("io_rx"), 7, ljust=False)))
            cells.append(Cell(text=_io_cell(c.get("io_wx"), 7, ljust=True)))
        if "networkio" not in disable:
            cells.append(Cell(text=_net_cell(c.get("network_rx"), to_bit, net_unit, 7, ljust=False)))
            cells.append(Cell(text=_net_cell(c.get("network_tx"), to_bit, net_unit, 7, ljust=True)))
        if "ports" not in disable:
            ports = c.get("ports") or ""
            cells.append(Cell(text=f"{(ports if ports != '' else '_'):16}"))
        if "command" not in disable:
            cells.append(Cell(text=f" {c.get('command') or '_'}"))
        rows.append(Row(cells=cells))

    return rows


def _io_cell(value: Any, width: int, *, ljust: bool) -> str:
    try:
        text = auto_unit(int(value)) + "B"
    except (TypeError, ValueError):
        text = "_"
    return f"{text:<{width}}" if ljust else f"{text:>{width}}"


def _net_cell(value: Any, to_bit: int, unit: str, width: int, *, ljust: bool) -> str:
    try:
        text = auto_unit(int(value * to_bit)) + unit
    except (TypeError, ValueError):
        text = "_"
    return f"{text:<{width}}" if ljust else f"{text:>{width}}"
```

- [ ] **Step 4: Run — expect PASS**

Run: `.venv/bin/python -m pytest tests/test_plugin_containers_render_curses_v5.py -v`
Expected: all PASS.

- [ ] **Step 5: Renderer auto-registers as view-aware + integration smoke**

Run: `.venv/bin/python -c "import inspect; from glances.plugins.containers.render_curses_v5 import render; assert 'view' in inspect.signature(render).parameters; print('view-aware OK')"`
Expected: prints `view-aware OK` (so `build_frame` passes `view=`).

- [ ] **Step 6: Lint + stage**

Run: `.venv/bin/python -m ruff check glances/plugins/containers/render_curses_v5.py tests/test_plugin_containers_render_curses_v5.py && .venv/bin/python -m ruff format glances/plugins/containers/render_curses_v5.py tests/test_plugin_containers_render_curses_v5.py`
Then: `git add glances/plugins/containers/render_curses_v5.py tests/test_plugin_containers_render_curses_v5.py`

---

### Task 7: docs — `docs/aoa/containers.rst`

**Files:**
- Modify: `docs/aoa/containers.rst`

- [ ] **Step 1: Read the current doc + confirm toctree**

Run: `.venv/bin/python -c "print(open('docs/aoa/containers.rst').read())"` and `grep -n containers docs/aoa/index.rst`
Expected: `containers` is already listed in `docs/aoa/index.rst` — do NOT re-add.

- [ ] **Step 2: Add a v5 note (config keys + alerts)**

Append (or fold into the existing config section) an admonition documenting:
- CPU/MEM alerts per container fire on `warning`+ (`careful` is colour-only).
- Threshold keys unchanged: `[containers] cpu_careful/cpu_warning/cpu_critical`, `mem_careful/mem_warning/mem_critical`, and per-container `<name>_cpu_*` / `<name>_mem_*` (MEM thresholds are a percentage of each container's memory **limit**).
- `disable_stats` accepts `name,status,uptime,cpu,mem,diskio,networkio,ports,command`.

Keep RST underline lengths matching their titles.

- [ ] **Step 3: Docs build sanity (if the project builds docs) + stage**

Run (optional, if sphinx is available): `.venv/bin/python -m sphinx -b html -q docs /tmp/g6a-docs-build 2>&1 | tail -5`
Expected: no error referencing `containers.rst`.
Then: `git add docs/aoa/containers.rst`

---

## Final verification (whole plan)

- [ ] **All containers + base + wiring tests pass**

Run: `.venv/bin/python -m pytest tests/test_plugin_containers_v5.py tests/test_plugin_containers_render_curses_v5.py tests/test_plugin_base_v5_stop_and_threshold_field.py tests/test_scheduler_v5.py tests/test_curses_v5.py -q`
Expected: all pass.

- [ ] **Full suite — no regression**

Run: `.venv/bin/python -m pytest -q`
Expected: same baseline as before the branch (only the pre-existing, unrelated `tests/test_actions_sanitize.py::TestSecurePopen::test_pipe` may fail in isolation — flag to maintainer if seen; it references none of the G6A modules).

- [ ] **Lint/format clean across all touched files**

Run: `.venv/bin/python -m ruff check glances/ tests/ && .venv/bin/python -m ruff format --check glances/plugins/containers glances/plugins/plugin/base_v5.py glances/scheduler_v5.py glances/outputs/glances_curses_v5.py`
Expected: clean.

- [ ] **Everything staged (never committed)**

Run: `git status --short`
Expected: all G6A-containers files staged (`A`/`M`), nothing committed.
