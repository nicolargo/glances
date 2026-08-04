# Glances v5 — `/limits` routes (REST + MCP fix) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose `GET /api/5/all/limits` and `GET /api/5/<plugin>/limits` returning **effective** thresholds (config layered over schema defaults), and make the MCP `glances://limits` resource consume the same source instead of the raw schema defaults it reads today.

**Architecture:** One new public method — `GlancesPluginBase.get_limits()` — owns the resolution and is the single source of truth for both surfaces. It reuses `_precompute_plugin_thresholds()` (`glances/plugins/plugin/base_v5.py:482`), already called once per cycle by `_derived_parameters`, but computes on demand rather than caching: thresholds come from config + schema, so `/limits` answers correctly before the scheduler's first cycle. Numeric thresholds sit at the top level of the payload; categorical mappings group under `_categorical`; per-item overrides group under `_per_item`. The REST routes are three-line pass-throughs; `McpPluginView.get_limits()` delegates to the same method.

**Tech Stack:** Python, FastAPI `APIRouter`, `glances/plugins/plugin/thresholds_v5.py` (`read_thresholds`, `read_thresholds_categorical`), pytest + `fastapi.testclient.TestClient`

**Spec:** `docs/superpowers/specs/2026-08-03-glances-v5-limits-routes-design.md`

## Global Constraints

- **Never commit, push, or open a PR.** Every task ends with `git add` only. The maintainer commits personally. Never add a `Co-Authored-By` trailer.
- **Do not touch `NEWS.rst`.** The changelog is updated by the maintainer at release time.
- Run `make lint && make format` before staging each task.
- Full v5 suite must stay green: `make test-v5`.
- Every new file carries the standard SPDX header used by sibling v5 modules (see `glances/routes_v5.py:1-8`).
- New modules and tests start with `from __future__ import annotations`.
- **Security invariant (spec §7):** `/limits` may only ever expose field names from `fields_description`, level names (`ok`/`careful`/`warning`/`critical`), and values of config keys shaped `<field>_<level>`, `<pk>_<field>_<level>` or `<level>`. Never widen this to a config-section dump — that is the v4 bug this design exists to avoid. No redaction is applied, and none must be added.

---

### Task 1: `GlancesPluginBase.get_limits()` — numeric + categorical

**Files:**
- Modify: `glances/plugins/plugin/base_v5.py` (add method after `_scan_pk_override_fields`, which ends at line 547)
- Test: `tests/test_plugin_base_v5_limits.py` (create — `tests/test_plugin_base_v5.py` is already 28 KB, keep `/limits` coverage in its own file)

**Interfaces:**
- Consumes: `self._precompute_plugin_thresholds()` → `{field_name: {"thresholds": {...}}}` for numeric fields, `{field_name: {"mapping": {level: set[str]}}}` for categorical ones.
- Produces: `GlancesPluginBase.get_limits() -> dict[str, Any]`. Top-level keys are field names mapping to `{level: float}`. Optional key `"_categorical"` maps to `{field_name: {level: list[str]}}` (sorted). Task 2 adds the optional `"_per_item"` key; Task 3 and Task 4 both call this method.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_plugin_base_v5_limits.py`:

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Unit tests for ``GlancesPluginBase.get_limits()``.

``get_limits()`` is the single source of truth behind both the REST
``/api/5/<plugin>/limits`` route and the MCP ``glances://limits``
resource. It returns *effective* thresholds — the plugin's config
section layered over each field's ``default_thresholds``.

See docs/superpowers/specs/2026-08-03-glances-v5-limits-routes-design.md
"""

from __future__ import annotations

import json
from typing import Any, ClassVar

from glances.plugins.plugin.base_v5 import GlancesPluginBase


class _LimitsScalar(GlancesPluginBase[dict]):
    """Scalar plugin: one watched numeric field, one unwatched field."""

    plugin_name: ClassVar[str] = "limitsscalar"
    IS_COLLECTION: ClassVar[bool] = False
    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "percent": {
            "description": "Usage percentage.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "default_thresholds": {"careful": 50.0, "warning": 70.0, "critical": 90.0},
        },
        "total": {"description": "Total.", "unit": "bytes"},
    }

    async def _grab_stats(self) -> dict:
        return {"percent": 42.0, "total": 1024}


class _LimitsThresholdField(GlancesPluginBase[dict]):
    """Field whose config-key prefix differs from its field name."""

    plugin_name: ClassVar[str] = "limitstf"
    IS_COLLECTION: ClassVar[bool] = False
    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "cpu_percent": {
            "description": "CPU usage.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "threshold_field": "cpu",
            "default_thresholds": {"careful": 50.0, "warning": 70.0},
        },
    }

    async def _grab_stats(self) -> dict:
        return {"cpu_percent": 10.0}


class _LimitsCategorical(GlancesPluginBase[dict]):
    """Categorical watched field — opt-in, no schema defaults."""

    plugin_name: ClassVar[str] = "limitscat"
    IS_COLLECTION: ClassVar[bool] = False
    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "status": {
            "description": "Process status.",
            "unit": "string",
            "watched": True,
            "threshold_type": "categorical",
            "prominent": False,
        },
    }

    async def _grab_stats(self) -> dict:
        return {"status": "S"}


class _LimitsUnwatched(GlancesPluginBase[dict]):
    """No watched field at all — e.g. the `now` / `version` plugins."""

    plugin_name: ClassVar[str] = "limitsunwatched"
    IS_COLLECTION: ClassVar[bool] = False
    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "value": {"description": "A value.", "unit": "string"},
    }

    async def _grab_stats(self) -> dict:
        return {"value": "x"}


def test_get_limits_falls_back_to_schema_defaults(store_with, config_with):
    plugin = _LimitsScalar(store_with(), config_with({}))
    assert plugin.get_limits() == {"percent": {"careful": 50.0, "warning": 70.0, "critical": 90.0}}


def test_get_limits_layers_config_over_defaults_per_level(store_with, config_with):
    config = config_with({"limitsscalar": {"percent_warning": "42"}})
    plugin = _LimitsScalar(store_with(), config)
    limits = plugin.get_limits()
    assert limits["percent"]["warning"] == 42.0
    # The levels the operator did NOT override keep their schema default.
    assert limits["percent"]["careful"] == 50.0
    assert limits["percent"]["critical"] == 90.0


def test_get_limits_omits_unwatched_fields(store_with, config_with):
    plugin = _LimitsScalar(store_with(), config_with({}))
    assert "total" not in plugin.get_limits()


def test_get_limits_reads_by_threshold_field_but_keys_by_field_name(store_with, config_with):
    config = config_with({"limitstf": {"cpu_warning": "33"}})
    plugin = _LimitsThresholdField(store_with(), config)
    limits = plugin.get_limits()
    assert "cpu_percent" in limits
    assert "cpu" not in limits
    assert limits["cpu_percent"]["warning"] == 33.0
    assert limits["cpu_percent"]["careful"] == 50.0


def test_get_limits_empty_when_no_watched_field(store_with, config_with):
    plugin = _LimitsUnwatched(store_with(), config_with({}))
    assert plugin.get_limits() == {}


def test_get_limits_groups_categorical_under_underscore_key(store_with, config_with):
    config = config_with({"limitscat": {"status_ok": "S,R,I", "status_critical": "Z,D"}})
    plugin = _LimitsCategorical(store_with(), config)
    limits = plugin.get_limits()
    assert limits["_categorical"] == {"status": {"ok": ["I", "R", "S"], "critical": ["D", "Z"]}}
    # `status` must NOT also appear at the top level (that space is numeric).
    assert "status" not in limits


def test_get_limits_categorical_is_json_serialisable(store_with, config_with):
    config = config_with({"limitscat": {"status_ok": "S,R"}})
    plugin = _LimitsCategorical(store_with(), config)
    # read_thresholds_categorical returns sets; unconverted they raise here.
    json.dumps(plugin.get_limits())


def test_get_limits_omits_categorical_key_when_unconfigured(store_with, config_with):
    plugin = _LimitsCategorical(store_with(), config_with({}))
    assert plugin.get_limits() == {}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_plugin_base_v5_limits.py -v`
Expected: FAIL — `AttributeError: '_LimitsScalar' object has no attribute 'get_limits'`

- [ ] **Step 3: Implement `get_limits()`**

In `glances/plugins/plugin/base_v5.py`, insert immediately after `_scan_pk_override_fields()` (which ends at line 547) and before `_compute_levels_for_item()`:

```python
    def get_limits(self) -> dict[str, Any]:
        """Return this plugin's **effective** thresholds, keyed by field name.

        Effective = the plugin's config section layered over each field's
        ``default_thresholds`` — exactly what drives ``_levels``. Consumed
        by the REST ``/api/5/<plugin>/limits`` route and by the MCP
        ``glances://limits`` resource, which share this single source of
        truth.

        Computed on demand rather than cached: thresholds derive from
        config + schema, not from psutil, so this answers correctly before
        the scheduler's first cycle. A cache filled by ``_derived_parameters``
        would be empty at cycle 0.

        Shape — numeric fields at the top level, categorical fields grouped
        under ``_categorical`` because their form is inverted (level → set
        of values instead of level → number)::

            {"percent": {"careful": 50.0, "warning": 70.0},
             "_categorical": {"status": {"ok": ["R", "S"]}}}

        ``_categorical`` is omitted when empty. Underscore-prefixed keys
        cannot collide with a field name: ``_remove_parameters`` strips
        every ``_*`` key from stats, so no declared field starts with one.

        Security (design §7): the key space read here is closed and
        code-controlled — field names come from ``fields_description``,
        levels from the threshold ladder. No arbitrary config key can reach
        the payload, which is what keeps ``*_action`` templates out of it.
        """
        out: dict[str, Any] = {}
        categorical: dict[str, dict[str, list[str]]] = {}

        for field_name, entry in self._precompute_plugin_thresholds().items():
            # Dispatch on the output key, not on schema["threshold_type"] —
            # _precompute_plugin_thresholds owns that mapping.
            if "thresholds" in entry:
                out[field_name] = dict(entry["thresholds"])
            elif "mapping" in entry:
                # read_thresholds_categorical returns sets, which json cannot
                # serialise. Sorted lists also make the payload deterministic.
                categorical[field_name] = {level: sorted(values) for level, values in entry["mapping"].items()}

        if categorical:
            out["_categorical"] = categorical
        return out
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_plugin_base_v5_limits.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Run the full v5 suite**

Run: `make test-v5`
Expected: no new failures.

- [ ] **Step 6: Lint, format, stage**

```bash
make lint && make format
git add glances/plugins/plugin/base_v5.py tests/test_plugin_base_v5_limits.py
```

Do **not** commit.

---

### Task 2: `_per_item` block for collection plugins

**Files:**
- Modify: `glances/plugins/plugin/base_v5.py` (new `_per_item_limits()` helper + one call added inside `get_limits()`)
- Test: `tests/test_plugin_base_v5_limits.py` (append)

**Interfaces:**
- Consumes: `self._scan_pk_override_fields()` → `set[str]`; `self._primary_key` → `str | None`; `self.store.get(self.plugin_name)` → the published payload; `read_thresholds` from `glances.plugins.plugin.thresholds_v5`.
- Produces: `get_limits()` gains an optional `"_per_item"` key → `{pk_value: {field_name: {level: float}}}`. Absent when empty. Task 3 and Task 4 need no change to consume it.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_plugin_base_v5_limits.py`. Add `import asyncio` to the existing imports at the top of the file, then append:

```python
class _LimitsCollection(GlancesPluginBase[list]):
    """Collection plugin with a per-item-overridable numeric field."""

    plugin_name: ClassVar[str] = "limitscoll"
    IS_COLLECTION: ClassVar[bool] = True
    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "interface_name": {"description": "Name.", "unit": "string", "primary_key": True},
        "rx": {
            "description": "Received bytes.",
            "unit": "bytes",
            "watched": True,
            "watch_direction": "high",
            "default_thresholds": {"careful": 70.0, "warning": 80.0},
        },
    }

    async def _grab_stats(self) -> list:
        return [{"interface_name": "eth0", "rx": 10}, {"interface_name": "wlan0", "rx": 20}]


def test_per_item_absent_when_no_override_configured(store_with, config_with):
    store = store_with()
    plugin = _LimitsCollection(store, config_with({}))
    asyncio.run(plugin.update())
    assert "_per_item" not in plugin.get_limits()


def test_per_item_reports_override_for_an_item_in_the_store(store_with, config_with):
    config = config_with({"limitscoll": {"wlan0_rx_warning": "60"}})
    store = store_with()
    plugin = _LimitsCollection(store, config)
    asyncio.run(plugin.update())
    limits = plugin.get_limits()
    # Plugin-level view is unchanged and still pk-agnostic.
    assert limits["rx"] == {"careful": 70.0, "warning": 80.0}
    # Only the overridden item appears, carrying the layered result.
    assert limits["_per_item"] == {"wlan0": {"rx": {"careful": 70.0, "warning": 60.0}}}


def test_per_item_skips_items_absent_from_the_store(store_with, config_with):
    """Documented limitation (design §4.3): an override configured for an
    item that is not currently present is not reported."""
    config = config_with({"limitscoll": {"ppp0_rx_warning": "60"}})
    store = store_with()
    plugin = _LimitsCollection(store, config)
    asyncio.run(plugin.update())
    assert "_per_item" not in plugin.get_limits()


def test_per_item_never_present_on_a_scalar_plugin(store_with, config_with):
    config = config_with({"limitsscalar": {"percent_warning": "42"}})
    store = store_with()
    plugin = _LimitsScalar(store, config)
    asyncio.run(plugin.update())
    assert "_per_item" not in plugin.get_limits()
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `uv run pytest tests/test_plugin_base_v5_limits.py -k per_item -v`
Expected: `test_per_item_reports_override_for_an_item_in_the_store` FAILS with `KeyError: '_per_item'`. The three negative tests pass vacuously — that is expected and fine; they are regression guards for Step 3.

- [ ] **Step 3: Implement `_per_item_limits()` and wire it in**

In `glances/plugins/plugin/base_v5.py`, add the helper directly after `get_limits()`:

```python
    def _per_item_limits(self) -> dict[str, dict[str, dict[str, float]]]:
        """Resolve per-item threshold overrides for a collection plugin.

        Returns ``{pk_value: {field_name: {level: value}}}``, restricted to
        items currently published in the store and to fields whose resolved
        thresholds actually differ from the plugin-level ones.

        ``_scan_pk_override_fields()`` is empty on any deployment without
        ``<pk>_<field>_<level>`` keys — the overwhelming majority — which
        short-circuits this method entirely. That guard is what keeps
        ``/limits`` cheap on processlist (500+ items).

        Categorical fields are skipped: a per-primary-key categorical
        override (e.g. a per-PID process status set) has no sensible use
        case, and including it would fork the ``_per_item`` payload shape.

        Known limitation (design §4.3): an override configured for an item
        absent from the store at call time — a downed interface, a stopped
        container — is not reported.
        """
        if not self.IS_COLLECTION or self._primary_key is None:
            return {}

        override_fields = self._scan_pk_override_fields()
        if not override_fields:
            return {}

        # A collection plugin's store payload is a dict wrapper, NOT a bare
        # list: _build_store_payload (base_v5.py:808-817) publishes
        # {"data": [...], **metadata, "_levels": {...}}.
        payload = self.store.get(self.plugin_name)
        if not isinstance(payload, dict):
            return {}
        stats = payload.get("data")
        if not isinstance(stats, list):
            return {}

        plugin_level = self._precompute_plugin_thresholds()
        schema_by_name = dict(self._watched_fields)

        out: dict[str, dict[str, dict[str, float]]] = {}
        for item in stats:
            if not isinstance(item, dict):
                continue
            pk_value = item.get(self._primary_key)
            if pk_value is None:
                continue
            per_field: dict[str, dict[str, float]] = {}
            for field_name in override_fields:
                schema = schema_by_name.get(field_name)
                if schema is None or schema.get("threshold_type") == "categorical":
                    continue
                thresholds = read_thresholds(
                    self.config,
                    self.plugin_name,
                    field=self._threshold_key(field_name, schema),
                    pk_value=str(pk_value),
                    defaults=schema.get("default_thresholds"),
                    strict=bool(schema.get("strict_thresholds", False)),
                )
                baseline = plugin_level.get(field_name, {}).get("thresholds", {})
                if thresholds and thresholds != baseline:
                    per_field[field_name] = thresholds
            if per_field:
                out[str(pk_value)] = per_field
        return out
```

Then, in `get_limits()`, insert before the `return out` line:

```python
        per_item = self._per_item_limits()
        if per_item:
            out["_per_item"] = per_item
```

No import change is needed: `read_thresholds` is already imported at `glances/plugins/plugin/base_v5.py:44`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_plugin_base_v5_limits.py -v`
Expected: PASS (12 tests)

- [ ] **Step 5: Run the full v5 suite**

Run: `make test-v5`
Expected: no new failures.

- [ ] **Step 6: Lint, format, stage**

```bash
make lint && make format
git add glances/plugins/plugin/base_v5.py tests/test_plugin_base_v5_limits.py
```

Do **not** commit.

---

### Task 3: REST routes `/api/5/all/limits` and `/api/5/<plugin>/limits`

**Files:**
- Modify: `glances/routes_v5.py` (two new handlers inside `build_router()`, plus the module docstring route table at lines 17-27)
- Modify: `docs/architecture/glances-v5-architecture-decisions.md` (§4.6 route table, around line 767)
- Test: `tests/test_routes_v5.py` (append)

**Interfaces:**
- Consumes: `GlancesPluginBase.get_limits()` from Tasks 1-2; the existing `_plugins(request)` and `_resolve_plugin(request, plugin_name)` helpers (`glances/routes_v5.py:158` and `:165`).
- Produces: two HTTP endpoints. No Python symbol other modules import.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_routes_v5.py`:

```python
# ------------------------------------------------------- /limits


class FakeLimitsPlugin(GlancesPluginBase[dict]):
    """Scalar plugin carrying thresholds, for the /limits routes."""

    plugin_name: ClassVar[str] = "fakelimits"
    IS_COLLECTION: ClassVar[bool] = False
    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "percent": {
            "description": "Usage percentage.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "default_thresholds": {"careful": 50.0, "warning": 70.0, "critical": 90.0},
        },
    }

    async def _grab_stats(self) -> dict:
        return {"percent": 42.0}


def test_plugin_limits_returns_thresholds(config_factory, store):
    config = config_factory()
    plugin = FakeLimitsPlugin(store, config)
    app = _make_app_with_plugins(config, store, plugins=[plugin])
    with TestClient(app) as client:
        r = client.get("/api/5/fakelimits/limits")
    assert r.status_code == 200
    assert r.json() == {"percent": {"careful": 50.0, "warning": 70.0, "critical": 90.0}}


def test_plugin_limits_answers_before_the_first_cycle(config_factory, store):
    """No _populate() call: thresholds come from config + schema, so unlike
    /api/5/<plugin> this route never returns null at cycle 0."""
    config = config_factory()
    plugin = FakeLimitsPlugin(store, config)
    app = _make_app_with_plugins(config, store, plugins=[plugin])
    with TestClient(app) as client:
        r = client.get("/api/5/fakelimits/limits")
    assert r.status_code == 200
    assert r.json()["percent"]["warning"] == 70.0


def test_plugin_limits_empty_dict_when_no_watched_field(config_factory, store):
    config = config_factory()
    plugin = FakeScalarPlugin(store, config)
    app = _make_app_with_plugins(config, store, plugins=[plugin])
    with TestClient(app) as client:
        r = client.get("/api/5/fakescalar/limits")
    assert r.status_code == 200
    assert r.json() == {}


def test_plugin_limits_404_on_unknown_plugin(config_factory, store):
    app = _make_app_with_plugins(config_factory(), store)
    with TestClient(app) as client:
        r = client.get("/api/5/nosuchplugin/limits")
    assert r.status_code == 404


def test_plugin_limits_404_on_reserved_name(config_factory, store):
    app = _make_app_with_plugins(config_factory(), store)
    with TestClient(app) as client:
        r = client.get("/api/5/config/limits")
    assert r.status_code == 404


def test_all_limits_is_not_captured_by_the_dynamic_route(config_factory, store):
    """Route-ordering guard: /all/limits must be declared before
    /{plugin_name}/limits, otherwise `all` is read as a plugin name."""
    config = config_factory()
    plugin = FakeLimitsPlugin(store, config)
    app = _make_app_with_plugins(config, store, plugins=[plugin])
    with TestClient(app) as client:
        r = client.get("/api/5/all/limits")
    assert r.status_code == 200
    body = r.json()
    assert "fakelimits" in body
    assert body["fakelimits"]["percent"]["critical"] == 90.0


def test_all_limits_omits_plugins_without_thresholds(config_factory, store):
    config = config_factory()
    with_limits = FakeLimitsPlugin(store, config)
    without_limits = FakeScalarPlugin(store, config)
    app = _make_app_with_plugins(config, store, plugins=[with_limits, without_limits])
    with TestClient(app) as client:
        r = client.get("/api/5/all/limits")
    body = r.json()
    assert "fakelimits" in body
    assert "fakescalar" not in body


def test_limits_routes_require_auth_when_password_is_set(config_factory, store):
    config = config_factory(password=hash_password("hunter2"))
    plugin = FakeLimitsPlugin(store, config)
    app = _make_app_with_plugins(config, store, plugins=[plugin])
    with TestClient(app) as client:
        assert client.get("/api/5/all/limits").status_code == 401
        assert client.get("/api/5/fakelimits/limits").status_code == 401
        ok = client.get("/api/5/fakelimits/limits", headers=_basic_header("glances", "hunter2"))
    assert ok.status_code == 200
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_routes_v5.py -k limits -v`
Expected: FAIL — 404 responses where 200 is asserted (the routes do not exist yet).

- [ ] **Step 3: Add the two handlers**

In `glances/routes_v5.py`, inside `build_router()`, add `/all/limits` immediately after the existing `all_stats` handler (which ends at line 120):

```python
    @router.get("/all/limits")
    async def all_limits(request: Request) -> dict[str, Any]:
        # Declared BEFORE /{plugin_name}/limits: FastAPI matches in
        # declaration order, so the dynamic route would otherwise swallow
        # `all` as a plugin name. _RESERVED_NAMES is the belt, this is the
        # braces.
        out: dict[str, Any] = {}
        for name, plugin in _plugins(request).items():
            limits = plugin.get_limits()
            if limits:
                out[name] = limits
        return out
```

Then add the per-plugin handler immediately after the existing `plugin_info` handler (which ends at line 136), so it precedes the catch-all `/{plugin_name}`:

```python
    @router.get("/{plugin_name}/limits")
    async def plugin_limits(plugin_name: str, request: Request) -> dict[str, Any]:
        plugin = _resolve_plugin(request, plugin_name)
        return plugin.get_limits()
```

Update the module docstring route table (lines 17-27) by adding these two rows after the `/api/5/all` row and the `/api/5/<plugin>/info` row respectively:

```
| ``/api/5/all/limits``         | GET    | per-plugin ``get_limits()``  |
| ``/api/5/<plugin>/limits``    | GET    | ``plugin.get_limits()``      |
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_routes_v5.py -v`
Expected: PASS — the 8 new tests plus all pre-existing ones.

- [ ] **Step 5: Update the architecture doc**

In `docs/architecture/glances-v5-architecture-decisions.md` §4.6, add two rows to the route table (which starts around line 767), after the `/api/5/all` row:

```
| `/api/5/all/limits` | GET | per-config | per-plugin `get_limits()` | Effective thresholds for every registered plugin. Plugins with no watched field are omitted. |
| `/api/5/<plugin>/limits` | GET | per-config | `plugin.get_limits()` | Effective thresholds — config layered over `default_thresholds`. `200 {}` when the plugin has no watched field; `404` if not registered. Never subject to cycle-0 `null`: thresholds come from config + schema. See `docs/superpowers/specs/2026-08-03-glances-v5-limits-routes-design.md`. |
```

- [ ] **Step 6: Run the full v5 suite**

Run: `make test-v5`
Expected: no new failures.

- [ ] **Step 7: Lint, format, stage**

```bash
make lint && make format
git add glances/routes_v5.py tests/test_routes_v5.py \
        docs/architecture/glances-v5-architecture-decisions.md
```

Do **not** commit.

---

### Task 4: MCP adapter delegates to `get_limits()`

**Files:**
- Modify: `glances/outputs/mcp_adapter_v5.py:75-130` (constructor + `get_limits`), `:174`, `:193`, `:199` (construction sites), and the `getAllLimitsAsDict` return annotation at `:166`
- Modify: `docs/architecture/glances-v5-architecture-decisions.md` §11.3 (resource inventory table, around line 1194)
- Test: `tests/test_mcp_adapter_v5.py` (append)

**Interfaces:**
- Consumes: `GlancesPluginBase.get_limits()` from Tasks 1-2.
- Produces: `McpPluginView.__init__(plugin_name, store, synthetic_payload=None, plugin=None)` — the `schema` parameter is **removed** (it becomes unused once `get_limits` delegates; leaving it would be dead code). `McpPluginView.get_limits() -> dict[str, Any]`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_mcp_adapter_v5.py`:

```python
# ---------------------------------------------------------------- limits


class _ConfigurableStub(GlancesPluginBase[dict]):
    """Scalar plugin whose thresholds can be overridden from config."""

    plugin_name: ClassVar[str] = "configurable"
    IS_COLLECTION: ClassVar[bool] = False

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "total": {
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "default_thresholds": {"careful": 50.0, "warning": 70.0, "critical": 90.0},
        },
    }

    async def _grab_stats(self) -> dict:
        return {"total": 1.0}


def test_get_all_limits_reflects_a_config_override(store_with, config_with):
    """Regression guard: the adapter used to aggregate `default_thresholds`
    straight from the schema, so `glances://limits` reported the shipped
    default even when the operator had overridden it."""
    config = config_with({"configurable": {"total_warning": "42"}})
    store = store_with()
    plugin = _ConfigurableStub(store, config)
    adapter = McpStatsAdapter(store=store, plugins=[plugin])
    assert adapter.getAllLimitsAsDict()["configurable"]["total"]["warning"] == 42.0


def test_get_plugin_limits_reflects_a_config_override(store_with, config_with):
    config = config_with({"configurable": {"total_critical": "99"}})
    store = store_with()
    plugin = _ConfigurableStub(store, config)
    adapter = McpStatsAdapter(store=store, plugins=[plugin])
    view = adapter.get_plugin("configurable")
    assert view is not None
    assert view.get_limits()["total"]["critical"] == 99.0


def test_synthetic_alert_plugin_has_no_limits(store_with, config_with):
    store = store_with()
    adapter = McpStatsAdapter(store=store, plugins=[])
    view = adapter.get_plugin("alert")
    assert view is not None
    assert view.get_limits() == {}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_mcp_adapter_v5.py -k limits -v`
Expected: `test_get_all_limits_reflects_a_config_override` and `test_get_plugin_limits_reflects_a_config_override` FAIL — the adapter returns the schema defaults (`70.0` and `90.0`) instead of the configured values.

- [ ] **Step 3: Delegate to the plugin**

In `glances/outputs/mcp_adapter_v5.py`, replace the constructor (lines 75-85) with:

```python
    def __init__(
        self,
        plugin_name: str,
        store: StatsStoreV5 | None,
        synthetic_payload: Any | None = None,
        plugin: GlancesPluginBase | None = None,
    ) -> None:
        self._plugin_name = plugin_name
        self._store = store
        self._synthetic_payload = synthetic_payload
        self._plugin = plugin
```

Replace `get_limits()` (lines 116-130) with:

```python
    def get_limits(self) -> dict[str, Any]:
        """Return the plugin's **effective** thresholds.

        Delegates to ``GlancesPluginBase.get_limits()`` so that MCP and the
        REST ``/api/5/<plugin>/limits`` route share one source of truth.
        This class previously aggregated ``default_thresholds`` straight
        from the field schema, which ignored the operator's config — the
        ``glances://limits`` resource reported shipped defaults even when a
        threshold had been overridden.

        Synthetic plugins (``alert``) have no backing plugin object and
        carry no thresholds.
        """
        if self._plugin is None:
            return {}
        return self._plugin.get_limits()
```

Update the three construction sites:

- line 174 (in `getAllLimitsAsDict`) → `view = McpPluginView(plugin_name=name, store=self._store, plugin=plugin)`
- line 193 (the synthetic `alert` view) → drop the `schema={},` argument, keep the rest
- line 199 (in `get_plugin`) → `return McpPluginView(plugin_name=name, store=self._store, plugin=plugin)`

Widen the `getAllLimitsAsDict` return annotation at line 166 from `dict[str, dict[str, dict[str, float]]]` to `dict[str, dict[str, Any]]` — the payload can now carry `_categorical` and `_per_item`.

Update the class docstring at lines 67-73 if it still mentions the schema parameter.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_mcp_adapter_v5.py -v`
Expected: PASS — the 3 new tests plus all pre-existing ones.

- [ ] **Step 5: Update the architecture doc**

In `docs/architecture/glances-v5-architecture-decisions.md` §11.3, replace the two `limits` rows (around lines 1194-1195) with:

```
| `glances://limits` | `plugin.get_limits()` — effective thresholds (config over schema defaults) | ✅ |
| `glances://limits/{plugin}` | idem, per plugin | ✅ |
```

- [ ] **Step 6: Run the full v5 suite**

Run: `make test-v5`
Expected: no new failures.

- [ ] **Step 7: Lint, format, stage**

```bash
make lint && make format
git add glances/outputs/mcp_adapter_v5.py tests/test_mcp_adapter_v5.py \
        docs/architecture/glances-v5-architecture-decisions.md
```

Do **not** commit. Report to the maintainer that all four tasks are staged and awaiting review.

---

## Deliberately out of scope

Spec §11 notes that `glances/config_v5.py::as_dict_secure()` needs the same
`action` addition to its sensitive-key regex as its v4 counterpart. That change
belongs to `/api/5/config`, not to the `/limits` routes, and it rides with the
maintainer's v4 security fix. **Do not implement it in this plan** — and do not
report it as a gap.

## Manual smoke test (maintainer)

After Task 4, with a config containing `[cpu] user_warning=42`:

```bash
python -m glances.main_v5 -s --bind 127.0.0.1 --port 61208
curl -s http://127.0.0.1:61208/api/5/cpu/limits
curl -s http://127.0.0.1:61208/api/5/all/limits
```

Expected: `user.warning == 42.0` on both, and no `*_action`, `*_log`, `refresh` or `disable` key anywhere in either payload.
