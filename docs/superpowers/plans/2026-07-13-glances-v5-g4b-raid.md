# Glances v5 — raid plugin port (G4B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the v4 `raid` plugin to the Glances v5 asyncio collection architecture (LEFT sidebar), reusing the v4 `pymdstat` grabber untouched, flattening the name-keyed array dict into a primary-keyed list, and raising alerts on degraded/inactive arrays.

**Architecture:** `PluginModel(GlancesPluginBase[list])`, `IS_COLLECTION=True`, `primary_key="name"`. `_grab_stats` wraps `pymdstat.MdStat().get_stats()['arrays']` in `asyncio.to_thread`, guarded on `ImportError` and runtime failure, and injects each array's dict key as the `name` field. `_derived_parameters` is overridden to build `self._levels = {name: {"status": {level, prominent}}}` mirroring v4 `raid_alert`. A dedicated `render_curses_v5.render` mirrors v4 `msg_curse()` (header + per-array Used/Avail rows + inactive/degraded sub-lines).

**Tech Stack:** Python, pymdstat, asyncio (to_thread), curses renderer v5, pytest

## Global Constraints

- mirror-v4: read the v4 `msg_curse()` + `raid_alert()` grabber before writing the renderer/model; divergent "clean generic" layouts are regressions.
- LEFT sidebar width budget = 34 chars incl. separators (col1+1+col2+1+col3 ≤ 34); overshooting clips the rightmost column.
- reuse v4 grabber (`pymdstat`) via `asyncio.to_thread` guarded on `ImportError` + runtime failure; no rewrite of `/proc/mdstat` parsing.
- empty registry/stats must stay valid (RAID hardware absent → empty collection, never a crash).
- alerts fire on warning+ only; `careful` is colour-only (raid has no careful tier).
- no dead code; no speculative config keys; surgical edits.
- do NOT touch `NEWS.rst` (release-time only).
- no commits/push/PR — stage only (each task ends at `git add`; NEVER `git commit`; never add a `Co-Authored-By` trailer).
- tests via `.venv/bin/python -m pytest`; lint `.venv/bin/python -m ruff check` / `.venv/bin/python -m ruff format`.

---

## File Structure

- **Create** `glances/plugins/raid/model_v5.py` — `PluginModel` collection plugin: identity, authored `fields_description`, `_grab_stats` (async grab + flatten + name injection + guards), and `_derived_parameters` override building `_levels` from the v4 `raid_alert` ladder. `EMITS_ALERTS = True`.
- **Create** `glances/plugins/raid/render_curses_v5.py` — pure `render(payload, fields_desc=None, view=None) -> list[Row]`: `RAID disks` header + per-array Used/Avail rows + inactive component sub-lines + degraded config sub-line. Owns the 34-char width budget.
- **Create** `tests/test_plugin_raid_v5.py` — model tests: identity/fields, `EMITS_ALERTS`, grab-merge + name injection + import/runtime guards, level mapping (raid0/inactive/degraded/None/ok), prominent flag.
- **Create** `tests/test_plugin_raid_render_curses_v5.py` — renderer tests: header-only, active row, raid0 count+dash, width budget, inactive component sub-lines, degraded sub-line, level colour.
- **Modify** `docs/aoa/raid.rst` — add a note that degraded/inactive arrays now raise alerts (`EMITS_ALERTS`, deliberate divergence from v4). `raid` is already in `docs/aoa/index.rst` toctree — do NOT re-add.

**Divergence from v4 (documented, per spec §4.1 / §7.1):** raid v5 sets `EMITS_ALERTS = True`. v4 was colour-only; degraded (`warning`) and inactive (`critical`) arrays now feed alert history + actions. There is no `careful` tier. This is a deliberate enhancement, called out in the model docstring and in `docs/aoa/raid.rst`.

**Note on the degraded condition:** both the level ladder and the renderer use `used is not None and available is not None and used < available` (consistent with the spec's level rule "used is None or available is None → no level; used < available → warning"). This refines v4 `msg_curse`'s truthy guard (`used and available and …`), which silently hid a genuinely degraded array reporting `used == 0`. Same predicate in both places keeps the colour and the sub-line in lock-step.

---

### Task 1: Model scaffold, identity, fields_description, EMITS_ALERTS

**Files:**
- Create: `glances/plugins/raid/model_v5.py`
- Test: `tests/test_plugin_raid_v5.py`

**Interfaces:**
- Consumes: `GlancesPluginBase` from `glances.plugins.plugin.base_v5`; `MdStat` from `pymdstat` (import-guarded to `None`).
- Produces: `PluginModel` (collection). `plugin_name="raid"`, `IS_COLLECTION=True`, `EMITS_ALERTS=True`, `_primary_key="name"`. `fields_description` keys: `name`(pk), `type`, `status`, `used`, `available`, `components`, `config`. Later tasks (2, 3) add `_grab_stats` and `_derived_parameters` to this same class.

- [ ] **Step 1: Write the failing test (identity + fields + EMITS_ALERTS)**

Create `tests/test_plugin_raid_v5.py`:

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the v5 raid plugin model."""

from __future__ import annotations

import pytest

import glances.plugins.raid.model_v5 as raid_mod
from glances.config_v5 import GlancesConfigV5
from glances.plugins.raid.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    return GlancesConfigV5()


def test_plugin_identity(store, config):
    p = PluginModel(store, config)
    assert p.plugin_name == "raid"
    assert p.IS_COLLECTION is True
    assert p._primary_key == "name"


def test_fields_description_flags():
    fd = PluginModel.fields_description
    assert fd["name"]["primary_key"] is True
    # RAID level / status / components / config are internal metadata.
    for key in ("type", "status", "components", "config"):
        assert fd[key].get("internal") is True
        assert fd[key].get("watched", False) is False
    # Disk counters are exportable but not watched (levels are bespoke).
    for key in ("used", "available"):
        assert fd[key].get("internal", False) is False
        assert fd[key].get("watched", False) is False


def test_emits_alerts_true():
    # Deliberate divergence from v4 (colour-only): degraded/inactive RAID
    # is a real incident and must feed the alert pipeline.
    assert PluginModel.EMITS_ALERTS is True
```

- [ ] **Step 2: Run it (expect FAIL — module does not exist)**

```
.venv/bin/python -m pytest tests/test_plugin_raid_v5.py::test_plugin_identity -v
```

Expect: `ModuleNotFoundError: No module named 'glances.plugins.raid.model_v5'`.

- [ ] **Step 3: Minimal implementation**

Create `glances/plugins/raid/model_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — raid plugin (collection, per-array).

Migrated from `glances/plugins/raid/__init__.py`. The v4 grabber
(`pymdstat.MdStat().get_stats()['arrays']`) returns a dict keyed by array
name; the v5 collection needs a flat list, so each array's dict key is
injected as the `name` primary-key field.

Deliberate divergence from v4: `EMITS_ALERTS = True`. v4 coloured degraded
(warning) / inactive (critical) arrays but never raised an alert. A
degraded or inactive RAID array is a real incident, so v5 feeds the alert
history + action pipeline. There is no `careful` tier for RAID.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

from glances.plugins.plugin.base_v5 import GlancesPluginBase

logger = logging.getLogger(__name__)

# Import the optional v4 grabber; absence disables the plugin (empty list).
try:
    from pymdstat import MdStat
except ImportError:
    MdStat = None  # type: ignore[assignment]


class PluginModel(GlancesPluginBase[list]):
    """RAID plugin (collection)."""

    plugin_name: ClassVar[str] = "raid"
    IS_COLLECTION: ClassVar[bool] = True
    # Divergence from v4 (colour-only): degraded/inactive arrays alert.
    EMITS_ALERTS: ClassVar[bool] = True

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "name": {
            "description": "RAID array name.",
            "unit": "string",
            "primary_key": True,
        },
        "type": {
            "description": "RAID level (e.g. raid1); None renders as UNKNOWN.",
            "unit": "string",
            "internal": True,
            "watched": False,
        },
        "status": {
            "description": "RAID array status (active/inactive).",
            "unit": "string",
            "internal": True,
            "watched": False,
        },
        "used": {
            "description": "Number of used disks.",
            "unit": "number",
            "watched": False,
        },
        "available": {
            "description": "Number of available disks.",
            "unit": "number",
            "watched": False,
        },
        "components": {
            "description": "Component disks (name -> role).",
            "unit": "string",
            "internal": True,
            "watched": False,
        },
        "config": {
            "description": "Array layout string (e.g. UU / U_).",
            "unit": "string",
            "internal": True,
            "watched": False,
        },
    }

    async def _grab_stats(self) -> list:
        raise NotImplementedError  # implemented in Task 2
```

> Note: `_grab_stats` is abstract on the base; this placeholder keeps the
> class importable for the identity/fields tests. Task 2 replaces it with
> the real implementation before any test drives it.

- [ ] **Step 4: Run the tests (expect PASS)**

```
.venv/bin/python -m pytest tests/test_plugin_raid_v5.py -v
```

Expect: `test_plugin_identity`, `test_fields_description_flags`, `test_emits_alerts_true` all PASS.

- [ ] **Step 5: Lint + stage (NEVER commit)**

```
.venv/bin/python -m ruff check glances/plugins/raid/model_v5.py tests/test_plugin_raid_v5.py
.venv/bin/python -m ruff format glances/plugins/raid/model_v5.py tests/test_plugin_raid_v5.py
git add glances/plugins/raid/model_v5.py tests/test_plugin_raid_v5.py
```

STOP. Do not commit.

---

### Task 2: `_grab_stats` — grab, flatten, inject name, guard

**Files:**
- Modify: `glances/plugins/raid/model_v5.py`
- Test: `tests/test_plugin_raid_v5.py`

**Interfaces:**
- Consumes: module-level `MdStat` (or `None`); `asyncio.to_thread`.
- Produces: `_grab_stats() -> list[dict]`, each dict shaped `{"name": str, "type": str|None, "status": str, "used": int|None, "available": int|None, "components": dict, "config": str}`. `ImportError` (MdStat is None) → `[]`; runtime failure → `[]` (base keeps last good stats). Task 3's `_derived_parameters` and the renderer consume this list.

- [ ] **Step 1: Write the failing tests (merge + name injection + guards)**

Append to `tests/test_plugin_raid_v5.py`:

```python
_MD0 = {
    "type": "raid1",
    "status": "active",
    "used": 2,
    "available": 2,
    "components": {"sda1": "0", "sdb1": "1"},
    "config": "UU",
}
_MD1 = {
    "type": "raid5",
    "status": "active",
    "used": 3,
    "available": 4,
    "components": {"sdc1": "0", "sdd1": "1", "sde1": "2"},
    "config": "UUU_",
}


class _FakeMdStat:
    """Stand-in for pymdstat.MdStat — returns a fixed name-keyed arrays dict."""

    _arrays: dict = {}

    def get_stats(self):
        return {"arrays": self._arrays}


@pytest.mark.asyncio
async def test_grab_flattens_and_injects_name(store, config, monkeypatch):
    fake = type("F", (_FakeMdStat,), {"_arrays": {"md0": dict(_MD0), "md1": dict(_MD1)}})
    monkeypatch.setattr(raid_mod, "MdStat", fake)
    p = PluginModel(store, config)
    rows = await p._grab_stats()
    by_name = {r["name"]: r for r in rows}
    assert set(by_name) == {"md0", "md1"}
    assert by_name["md0"]["type"] == "raid1"
    assert by_name["md0"]["used"] == 2
    assert by_name["md1"]["available"] == 4
    # The original array dict must carry a `name` key now (primary key).
    assert by_name["md0"]["name"] == "md0"


@pytest.mark.asyncio
async def test_grab_import_error_returns_empty(store, config, monkeypatch):
    monkeypatch.setattr(raid_mod, "MdStat", None)
    p = PluginModel(store, config)
    assert await p._grab_stats() == []


@pytest.mark.asyncio
async def test_grab_runtime_failure_returns_empty(store, config, monkeypatch):
    class _Boom(_FakeMdStat):
        def get_stats(self):
            raise OSError("cannot read /proc/mdstat")

    monkeypatch.setattr(raid_mod, "MdStat", _Boom)
    p = PluginModel(store, config)
    assert await p._grab_stats() == []
```

- [ ] **Step 2: Run them (expect FAIL — NotImplementedError)**

```
.venv/bin/python -m pytest tests/test_plugin_raid_v5.py::test_grab_flattens_and_injects_name -v
```

Expect: FAIL (`NotImplementedError`).

- [ ] **Step 3: Minimal implementation**

In `glances/plugins/raid/model_v5.py`, replace the placeholder `_grab_stats` with:

```python
    async def _grab_stats(self) -> list:
        return await asyncio.to_thread(self._collect)

    @staticmethod
    def _collect() -> list:
        """Synchronous grab (runs in a worker thread).

        Wraps the v4 pymdstat grabber. Guarded twice:
        - `MdStat is None` (import failed) -> empty collection.
        - any runtime failure (no /proc/mdstat, parse error) -> empty
          collection; the base class keeps the last good stats.

        The v4 grabber returns a dict keyed by array name; we inject that
        key as the `name` primary-key field and return a flat list.
        """
        if MdStat is None:
            return []
        try:
            arrays = MdStat().get_stats()["arrays"]
        except Exception as exc:  # noqa: BLE001 — any grab failure -> empty, keep last good
            logger.debug("raid: grab failed: %s", exc)
            return []
        out: list[dict[str, Any]] = []
        for name, array in arrays.items():
            if not isinstance(array, dict):
                continue
            row = dict(array)
            row["name"] = name
            out.append(row)
        return out
```

- [ ] **Step 4: Run the tests (expect PASS)**

```
.venv/bin/python -m pytest tests/test_plugin_raid_v5.py -v
```

Expect: all Task 1 + Task 2 tests PASS.

- [ ] **Step 5: Lint + stage (NEVER commit)**

```
.venv/bin/python -m ruff check glances/plugins/raid/model_v5.py tests/test_plugin_raid_v5.py
.venv/bin/python -m ruff format glances/plugins/raid/model_v5.py tests/test_plugin_raid_v5.py
git add glances/plugins/raid/model_v5.py tests/test_plugin_raid_v5.py
```

STOP. Do not commit.

---

### Task 3: `_derived_parameters` — level ladder (v4 `raid_alert` parity)

**Files:**
- Modify: `glances/plugins/raid/model_v5.py`
- Test: `tests/test_plugin_raid_v5.py`

**Interfaces:**
- Consumes: `self._stats` (list of array dicts from Task 2).
- Produces: `self._levels = {name: {"status": {"level": str, "prominent": False}}}`. Level ladder per array: `type == "raid0"` → `ok`; `status == "inactive"` → `critical`; `used is None or available is None` → **no entry** (DEFAULT); `used < available` → `warning`; else `ok`. The renderer (Task 4/5) reads `_levels[name]["status"]`; the alert engine (`EMITS_ALERTS=True`) ingests the same entries.

> Design note: `_levels` is keyed on the `status` field even though `status`
> is `watched: False`. We fully override `_derived_parameters` (do NOT call
> `super()`), so the base watched-field walk never runs and the `status` key
> is chosen purely as the level index (v4 parity — the v4 decoration was
> applied to the status-derived Used/Avail cells). `alerts_v5._observations`
> iterates `_levels` entries directly and reads `item.get("status")` for the
> event value — `status` stays in the payload because it is a declared field
> (internal fields are kept by `_remove_parameters`, only stripped from the
> generic renderer / exports). `prominent: False` → coloured text, no
> background highlight (sensors parity).

- [ ] **Step 1: Write the failing tests (level mapping)**

Append to `tests/test_plugin_raid_v5.py`:

```python
def _levels(p, rows):
    p._stats = rows
    p._derived_parameters()
    return p._levels


def _array(name, type_, status, used, available):
    return {
        "name": name,
        "type": type_,
        "status": status,
        "used": used,
        "available": available,
        "components": {},
        "config": "",
    }


def test_level_raid0_is_ok(store, config):
    # raid0 has no redundancy; v4 raid_alert short-circuits to OK.
    p = PluginModel(store, config)
    lv = _levels(p, [_array("md0", "raid0", "active", 2, 2)])
    assert lv["md0"]["status"]["level"] == "ok"


def test_level_inactive_is_critical(store, config):
    p = PluginModel(store, config)
    lv = _levels(p, [_array("md0", "raid1", "inactive", 2, 2)])
    assert lv["md0"]["status"]["level"] == "critical"


def test_level_degraded_is_warning(store, config):
    p = PluginModel(store, config)
    lv = _levels(p, [_array("md0", "raid5", "active", 3, 4)])
    assert lv["md0"]["status"]["level"] == "warning"


def test_level_healthy_is_ok(store, config):
    p = PluginModel(store, config)
    lv = _levels(p, [_array("md0", "raid1", "active", 2, 2)])
    assert lv["md0"]["status"]["level"] == "ok"


def test_level_none_when_counts_missing(store, config):
    p = PluginModel(store, config)
    lv = _levels(p, [_array("md0", "raid1", "active", None, 2)])
    assert "md0" not in lv  # no threshold source -> DEFAULT (no entry)


def test_level_prominent_false(store, config):
    p = PluginModel(store, config)
    lv = _levels(p, [_array("md0", "raid1", "inactive", 2, 2)])
    assert lv["md0"]["status"]["prominent"] is False
```

- [ ] **Step 2: Run them (expect FAIL — base `_derived_parameters` keys nothing on `status`)**

```
.venv/bin/python -m pytest tests/test_plugin_raid_v5.py::test_level_inactive_is_critical -v
```

Expect: FAIL (`KeyError: 'md0'` — the base override produces no `status` level for a non-watched field).

- [ ] **Step 3: Minimal implementation**

In `glances/plugins/raid/model_v5.py`, add these two methods to `PluginModel`
(after `_collect`):

```python
    def _derived_parameters(self) -> None:
        """Compute per-array alert levels (mirrors v4 `raid_alert`).

        Overrides the base watched-field walk entirely — RAID's level is a
        bespoke ladder keyed on the (non-watched) `status` field so the
        renderer and the alert engine share one index. `prominent: False`
        → coloured text, no background highlight (sensors parity).
        """
        self._levels = {}
        if not isinstance(self._stats, list):
            return
        for item in self._stats:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if name is None:
                continue
            level = self._array_level(item)
            if level is None:
                continue
            self._levels[str(name)] = {"status": {"level": level, "prominent": False}}

    @staticmethod
    def _array_level(item: dict) -> str | None:
        """RAID alert ladder (v4 `raid_alert` parity).

        raid0 (no redundancy) -> ok; inactive -> critical; missing disk
        counts -> None (DEFAULT, no colour/alert); fewer used than
        available disks -> warning (degraded); else ok.
        """
        array_type = item.get("type")
        status = item.get("status")
        used = item.get("used")
        available = item.get("available")
        if array_type == "raid0":
            return "ok"
        if status == "inactive":
            return "critical"
        if used is None or available is None:
            return None
        if used < available:
            return "warning"
        return "ok"
```

- [ ] **Step 4: Run the tests (expect PASS)**

```
.venv/bin/python -m pytest tests/test_plugin_raid_v5.py -v
```

Expect: all model tests PASS.

- [ ] **Step 5: Lint + stage (NEVER commit)**

```
.venv/bin/python -m ruff check glances/plugins/raid/model_v5.py tests/test_plugin_raid_v5.py
.venv/bin/python -m ruff format glances/plugins/raid/model_v5.py tests/test_plugin_raid_v5.py
git add glances/plugins/raid/model_v5.py tests/test_plugin_raid_v5.py
```

STOP. Do not commit.

---

### Task 4: Renderer — header + active/raid0 rows + width budget

**Files:**
- Create: `glances/plugins/raid/render_curses_v5.py`
- Test: `tests/test_plugin_raid_render_curses_v5.py`

**Interfaces:**
- Consumes: collection payload `{"data": [ {name,type,status,used,available,components,config}, … ], "_levels": {name: {"status": {level, prominent}}}}`; `Cell`, `Row`, `ColorRole`, `_LEVEL_TO_ROLE`, `title_role` from `glances.outputs.curses_renderer_v5`.
- Produces: `render(payload, fields_desc=None, view=None) -> list[Row]`. Header `RAID disks`(name col ljust 18) + `Used`(rjust 7) + `Avail`(rjust 7). Per active array a 3-cell row; raid0+active → Used=`len(components)`, Avail=`-`. Widths: `_NAME_MAX_WIDTH=18`, `_USED_COL_WIDTH=7`, `_AVAIL_COL_WIDTH=7`, `_LEFT_SIDEBAR_MAX_WIDTH=34` (18+1+7+1+7 = 34, mirrors fs). Task 5 extends this same module with inactive/degraded sub-lines.

- [ ] **Step 1: Write the failing tests (header + active + raid0 + budget)**

Create `tests/test_plugin_raid_render_curses_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — tests for the raid curses renderer."""

from __future__ import annotations

from glances.plugins.raid.render_curses_v5 import (
    _AVAIL_COL_WIDTH,
    _LEFT_SIDEBAR_MAX_WIDTH,
    _NAME_MAX_WIDTH,
    _USED_COL_WIDTH,
    render,
)


def _payload(rows, levels=None):
    return {"data": rows, "_levels": levels or {}}


def _flat(rows):
    return "\n".join(" ".join(c.text for c in r.cells) for r in rows)


def _array(name, type_="raid1", status="active", used=2, available=2, components=None, config="UU"):
    return {
        "name": name,
        "type": type_,
        "status": status,
        "used": used,
        "available": available,
        "components": components or {},
        "config": config,
    }


def test_empty_returns_header_only():
    rows = render(_payload([]))
    assert "RAID disks" in _flat(rows)
    assert len(rows) == 1  # header only


def test_header_labels():
    flat = _flat(render(_payload([])))
    assert "RAID disks" in flat
    assert "Used" in flat
    assert "Avail" in flat


def test_active_row_shows_used_and_available():
    rows = render(_payload([_array("md0", "raid1", "active", used=2, available=2)]))
    flat = _flat(rows)
    # Full name = "<TYPE> <name>".
    assert "RAID1 md0" in flat
    # Used=2, Avail=2 appear on the data row.
    data = rows[1]
    assert data.cells[1].text.strip() == "2"
    assert data.cells[2].text.strip() == "2"


def test_raid0_shows_component_count_and_dash():
    rows = render(
        _payload([_array("md9", "raid0", "active", used=None, available=None, components={"sda1": "0", "sdb1": "1"})])
    )
    data = rows[1]
    assert data.cells[1].text.strip() == "2"  # len(components)
    assert data.cells[2].text.strip() == "-"  # no "available" for raid0


def test_unknown_type_renders_uppercase_unknown():
    rows = render(_payload([_array("md0", type_=None, status="active", used=2, available=2)]))
    assert "UNKNOWN md0" in _flat(rows)


def test_width_budget():
    """name + 1 separator + used + 1 separator + avail must fit the 34-char
    left sidebar, or the painter clips the rightmost column."""
    assert _NAME_MAX_WIDTH + 1 + _USED_COL_WIDTH + 1 + _AVAIL_COL_WIDTH <= _LEFT_SIDEBAR_MAX_WIDTH


def test_level_colour_applied():
    levels = {"md0": {"status": {"level": "warning", "prominent": False}}}
    rows = render(_payload([_array("md0", "raid5", "active", used=3, available=4)], levels))
    data = rows[1]
    assert data.cells[1].color.value == "warning"
    assert data.cells[2].color.value == "warning"
    assert data.cells[1].prominent is False
```

- [ ] **Step 2: Run them (expect FAIL — module does not exist)**

```
.venv/bin/python -m pytest tests/test_plugin_raid_render_curses_v5.py::test_header_labels -v
```

Expect: `ModuleNotFoundError: No module named 'glances.plugins.raid.render_curses_v5'`.

- [ ] **Step 3: Minimal implementation**

Create `glances/plugins/raid/render_curses_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the raid plugin.

Mirrors v4 `raid.msg_curse()`: a `RAID disks` header (name col + Used +
Avail) then one row per array, with inactive/degraded sub-lines. LEFT
sidebar; the header/data block must fit the 34-char left-sidebar maximum
*including* the one-space separators the painter inserts between cells:

    name (_NAME_MAX_WIDTH) + 1 + used (7) + 1 + avail (7) = 18 + 16 = 34

Overshooting by one char makes the painter clip the rightmost column
(mirror of the fs renderer's documented budget).

    RAID disks           Used   Avail
    RAID1 md0               2       2
    RAID0 md9               2       -

Row shapes (v4 parity):
- raid0 + active   -> Used = len(components), Avail = "-".
- active non-raid0 -> Used = used, Avail = available.
- inactive         -> name-only row + `└─ Status inactive` + one line per
                      sorted component (Task 5).
- degraded         -> `└─ Degraded mode` + optional layout line (Task 5).
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row, title_role

_NAME_MAX_WIDTH = 18
_USED_COL_WIDTH = 7
_AVAIL_COL_WIDTH = 7
# Painter inserts a 1-space separator between adjacent cells, so the block
# spans _NAME_MAX_WIDTH + 1 + _USED_COL_WIDTH + 1 + _AVAIL_COL_WIDTH. Must
# stay <= the left-sidebar maximum or the trailing column is clipped.
_LEFT_SIDEBAR_MAX_WIDTH = 34


def _format_name(array_type: Any, name: str) -> str:
    """`<TYPE> <name>` (v4 parity), truncated/padded to _NAME_MAX_WIDTH."""
    type_str = str(array_type).upper() if array_type is not None else "UNKNOWN"
    full = f"{type_str} {name}"
    if len(full) > _NAME_MAX_WIDTH:
        return full[:_NAME_MAX_WIDTH]
    return full.ljust(_NAME_MAX_WIDTH)


def _status_role(levels: dict[str, Any], name: str) -> tuple[ColorRole, bool]:
    entry = levels.get(name, {}) if isinstance(levels, dict) else {}
    status_entry = entry.get("status", {}) if isinstance(entry, dict) else {}
    level = status_entry.get("level")
    prominent = bool(status_entry.get("prominent"))
    return _LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT), prominent


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]] | None = None, view=None) -> list[Row]:
    header = Row(
        cells=[
            Cell(text="RAID disks".ljust(_NAME_MAX_WIDTH), color=title_role(payload), bold=True),
            Cell(text="Used".rjust(_USED_COL_WIDTH), color=ColorRole.HEADER, bold=True),
            Cell(text="Avail".rjust(_AVAIL_COL_WIDTH), color=ColorRole.HEADER, bold=True),
        ]
    )
    rows: list[Row] = [header]

    if not isinstance(payload, dict):
        return rows
    items = payload.get("data")
    if not isinstance(items, list):
        return rows
    levels = payload.get("_levels") if isinstance(payload.get("_levels"), dict) else {}

    # Sort by array name (v4: sorted(self.stats.keys())).
    for item in sorted(items, key=lambda it: str(it.get("name", ""))):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", ""))
        if not name:
            continue
        array_type = item.get("type")
        status = item.get("status")
        used = item.get("used")
        available = item.get("available")
        components = item.get("components") or {}
        role, prominent = _status_role(levels, name)

        if array_type == "raid0" and status == "active":
            rows.append(
                Row(
                    cells=[
                        Cell(text=_format_name(array_type, name)),
                        Cell(text=str(len(components)).rjust(_USED_COL_WIDTH), color=role, prominent=prominent),
                        Cell(text="-".rjust(_AVAIL_COL_WIDTH), color=role, prominent=prominent),
                    ]
                )
            )
        elif status == "active":
            rows.append(
                Row(
                    cells=[
                        Cell(text=_format_name(array_type, name)),
                        Cell(text=str(used).rjust(_USED_COL_WIDTH), color=role, prominent=prominent),
                        Cell(text=str(available).rjust(_AVAIL_COL_WIDTH), color=role, prominent=prominent),
                    ]
                )
            )
        else:
            # inactive / unknown status: name-only row (sub-lines follow — Task 5).
            rows.append(Row(cells=[Cell(text=_format_name(array_type, name))]))

    return rows
```

- [ ] **Step 4: Run the tests (expect PASS)**

```
.venv/bin/python -m pytest tests/test_plugin_raid_render_curses_v5.py -v
```

Expect: all Task 4 renderer tests PASS.

- [ ] **Step 5: Lint + stage (NEVER commit)**

```
.venv/bin/python -m ruff check glances/plugins/raid/render_curses_v5.py tests/test_plugin_raid_render_curses_v5.py
.venv/bin/python -m ruff format glances/plugins/raid/render_curses_v5.py tests/test_plugin_raid_render_curses_v5.py
git add glances/plugins/raid/render_curses_v5.py tests/test_plugin_raid_render_curses_v5.py
```

STOP. Do not commit.

---

### Task 5: Renderer — inactive component sub-lines + degraded sub-line

**Files:**
- Modify: `glances/plugins/raid/render_curses_v5.py`
- Test: `tests/test_plugin_raid_render_curses_v5.py`

**Interfaces:**
- Consumes: same payload/items as Task 4 (adds use of `components` and `config`).
- Produces: extends `render` — after each array's main row:
  - `status == "inactive"` → `└─ Status inactive` (coloured by level) + one line per **sorted** component: `   ├─/└─ disk {role}: {name}` (tree char `└─` on the last, `├─` otherwise).
  - degraded (`type != "raid0"` and `used is not None and available is not None and used < available`) → `└─ Degraded mode` (coloured) + if `len(config) < 17`: `   └─ {config with '_'→'A'}`.

- [ ] **Step 1: Write the failing tests (inactive + degraded sub-lines)**

Append to `tests/test_plugin_raid_render_curses_v5.py`:

```python
def test_inactive_emits_status_and_component_sub_lines():
    rows = render(
        _payload(
            [_array("md0", "raid1", "inactive", used=2, available=2, components={"sda1": "0", "sdb1": "1"})],
            levels={"md0": {"status": {"level": "critical", "prominent": False}}},
        )
    )
    flat = _flat(rows)
    assert "Status inactive" in flat
    # Components sorted -> sda1 (├─) then sdb1 (└─).
    assert "├─ disk 0: sda1" in flat
    assert "└─ disk 1: sdb1" in flat


def test_inactive_status_line_coloured():
    rows = render(
        _payload(
            [_array("md0", "raid1", "inactive", used=2, available=2, components={"sda1": "0"})],
            levels={"md0": {"status": {"level": "critical", "prominent": False}}},
        )
    )
    status_cells = [c for r in rows for c in r.cells if "Status inactive" in c.text]
    assert status_cells and status_cells[0].color.value == "critical"


def test_degraded_emits_mode_and_layout_lines():
    rows = render(
        _payload(
            [_array("md0", "raid5", "active", used=3, available=4, config="U_")],
            levels={"md0": {"status": {"level": "warning", "prominent": False}}},
        )
    )
    flat = _flat(rows)
    assert "Degraded mode" in flat
    # config "U_".replace("_", "A") -> "UA".
    assert "UA" in flat


def test_degraded_layout_omitted_when_config_too_long():
    rows = render(
        _payload(
            [_array("md0", "raid5", "active", used=3, available=4, config="U" * 20)],
            levels={"md0": {"status": {"level": "warning", "prominent": False}}},
        )
    )
    flat = _flat(rows)
    assert "Degraded mode" in flat
    assert ("U" * 20) not in flat  # layout line suppressed when len(config) >= 17


def test_healthy_array_has_no_sub_lines():
    rows = render(_payload([_array("md0", "raid1", "active", used=2, available=2)]))
    flat = _flat(rows)
    assert "Degraded mode" not in flat
    assert "Status" not in flat
```

- [ ] **Step 2: Run them (expect FAIL — sub-lines not yet emitted)**

```
.venv/bin/python -m pytest tests/test_plugin_raid_render_curses_v5.py::test_inactive_emits_status_and_component_sub_lines -v
```

Expect: FAIL (`assert "Status inactive" in flat`).

- [ ] **Step 3: Minimal implementation**

In `glances/plugins/raid/render_curses_v5.py`, extend the per-array loop.
Read `config` alongside the existing locals (add after the `components` line):

```python
        config = str(item.get("config") or "")
```

Then, immediately before the `for` loop's closing (after the main-row
`if/elif/else` block that appends the array row), add the sub-line logic:

```python
        # Inactive: list the component disks under a status sub-line.
        if status == "inactive":
            rows.append(Row(cells=[Cell(text=f"└─ Status {status}", color=role, prominent=prominent)]))
            component_names = sorted(components.keys())
            for i, component in enumerate(component_names):
                tree_char = "└─" if i == len(component_names) - 1 else "├─"
                rows.append(Row(cells=[Cell(text=f"   {tree_char} disk {components[component]}: {component}")]))

        # Degraded: non-raid0 array with fewer used than available disks.
        if (
            array_type != "raid0"
            and used is not None
            and available is not None
            and used < available
        ):
            rows.append(Row(cells=[Cell(text="└─ Degraded mode", color=role, prominent=prominent)]))
            if len(config) < 17:
                rows.append(Row(cells=[Cell(text=f"   └─ {config.replace('_', 'A')}")]))
```

> Both sub-line blocks are `if` (not `elif`) — v4 parity: an inactive array
> that is also degraded prints both, and an active degraded array prints its
> Used/Avail row (Task 4) followed by the degraded sub-line.

- [ ] **Step 4: Run the full renderer suite (expect PASS)**

```
.venv/bin/python -m pytest tests/test_plugin_raid_render_curses_v5.py -v
```

Expect: all Task 4 + Task 5 renderer tests PASS.

- [ ] **Step 5: Full raid suite + lint + stage (NEVER commit)**

```
.venv/bin/python -m pytest tests/test_plugin_raid_v5.py tests/test_plugin_raid_render_curses_v5.py -v
.venv/bin/python -m ruff check glances/plugins/raid/ tests/test_plugin_raid_v5.py tests/test_plugin_raid_render_curses_v5.py
.venv/bin/python -m ruff format glances/plugins/raid/ tests/test_plugin_raid_v5.py tests/test_plugin_raid_render_curses_v5.py
git add glances/plugins/raid/render_curses_v5.py tests/test_plugin_raid_render_curses_v5.py
```

STOP. Do not commit.

---

### Task 6: Documentation — note the EMITS_ALERTS divergence in raid.rst

**Files:**
- Modify: `docs/aoa/raid.rst`

**Interfaces:**
- Consumes: nothing (docs only).
- Produces: a note that degraded/inactive arrays now raise alerts (a v5
  behaviour change vs v4). `raid` is already in `docs/aoa/index.rst`
  toctree — do NOT re-add it.

- [ ] **Step 1: Add the alert note**

In `docs/aoa/raid.rst`, insert the following block immediately **before** the
final line `This plugin is only available on GNU/Linux.` (keeping the
existing text intact):

```rst
Alerts
------

Since Glances 5, a **degraded** RAID array (fewer active than available
disks → ``warning``) and an **inactive** array (→ ``critical``) raise a
Glances alert. They appear in the alert view and trigger any configured
action, in addition to being coloured in the terminal interface. In
Glances 4 these conditions were coloured only, with no alert raised.

```

- [ ] **Step 2: Verify the doc builds / renders (no broken RST)**

```
.venv/bin/python -m sphinx -b dummy docs docs/_build/dummy -q 2>&1 | grep -i "raid\|error\|warning" || echo "no raid-related sphinx issues"
```

> If Sphinx is not installed in `.venv`, skip the build and instead
> eyeball `docs/aoa/raid.rst` to confirm the new `Alerts` section header
> underline (`------`) matches the title length and the surrounding blank
> lines are preserved.

- [ ] **Step 3: Stage (NEVER commit)**

```
git add docs/aoa/raid.rst
```

STOP. Do not commit.

---

## Final verification (run after all tasks)

- [ ] Full raid test suite green:

```
.venv/bin/python -m pytest tests/test_plugin_raid_v5.py tests/test_plugin_raid_render_curses_v5.py -v
```

- [ ] No regression in the broader suite:

```
.venv/bin/python -m pytest -q
```

- [ ] Lint + format clean on the whole plugin:

```
.venv/bin/python -m ruff check glances/plugins/raid/ tests/test_plugin_raid_v5.py tests/test_plugin_raid_render_curses_v5.py
.venv/bin/python -m ruff format --check glances/plugins/raid/ tests/test_plugin_raid_v5.py tests/test_plugin_raid_render_curses_v5.py
```

- [ ] Confirm all changes are staged (`git status`), then STOP — the
  maintainer commits, pushes, and opens any PR personally. Never add a
  `Co-Authored-By` trailer.
