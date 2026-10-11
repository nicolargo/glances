# Glances v5 — smart plugin port (G4B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the v4 `smart` plugin (SMART disk attributes) to the v5 asyncio architecture, reusing the v4 pySMART grabber and mirroring the v4 `SMART disks` TUI layout.

**Architecture:** A collection `PluginModel(GlancesPluginBase[list])` whose `_grab_stats()` gates on root (`is_admin()`) and on the pySMART import, wraps the module-level v4 helper `get_smart_data(hide_attributes)` in `asyncio.to_thread`, and reshapes each v4 numeric-keyed device dict into `{"name": DeviceName, "attributes": [attr, …]}` so the flat v5 field filter passes the nested list through intact. A pure `render_curses_v5.render()` reproduces the v4 per-device / per-attribute block within the 34-char LEFT sidebar budget. No levels, no alerts (`EMITS_ALERTS = False`).

**Tech Stack:** Python, pySMART, asyncio (to_thread), curses renderer v5, pytest

## Global Constraints

- **Mirror v4**: read the v4 `msg_curse()` + grabber before writing each renderer/model; divergent "clean generic" layouts are regressions.
- **LEFT sidebar width budget = 34 chars, separators included** (`col1 + 1 + col2 + 1 + … ≤ 34`; overshooting clips the rightmost column).
- **Reuse the v4 grabber** (`get_smart_data`) via `asyncio.to_thread` (no rewrite of pySMART parsing); guard on `ImportError` independently.
- **Empty registry / empty stats must stay valid** (absent hardware / non-root / missing pySMART → empty collection, not a crash).
- **No dead code**, no speculative config keys, surgical edits.
- **Do not touch `NEWS.rst`** during development (release-time only).
- **No commits/push/PR** — stage only.
- Tests: `.venv/bin/python -m pytest`; lint `ruff check` + `ruff format`.

---

## File Structure

New files:

- `glances/plugins/smart/model_v5.py` — `PluginModel(GlancesPluginBase[list])`.
- `glances/plugins/smart/render_curses_v5.py` — `render(payload, fields_desc=None, view=None) -> list[Row]`.
- `tests/test_plugin_smart_v5.py` — model tests.
- `tests/test_plugin_smart_render_curses_v5.py` — renderer tests.

Edited files:

- `docs/aoa/smart.rst` — add a short note on the v5 `attributes` list shape (mirror existing style). `smart` is already in `docs/aoa/index.rst` — do NOT re-add.

Untouched (reused verbatim):

- `glances/plugins/smart/__init__.py` — v4 module providing `get_smart_data`, `import_error_tag`, `LARGE_VALUE_KEYS`.
- `glances/plugins/plugin/base_v5.py` — base class (`IS_COLLECTION`, primary_key, `_remove_parameters` filters only top-level item keys → nested `attributes` list passes through).
- `glances/outputs/curses_renderer_v5.py` — `Cell` / `Row` / `ColorRole` / `title_role`.

**Naming/type invariants (all tasks):** class `PluginModel`; `plugin_name = "smart"`; `IS_COLLECTION = True`; `EMITS_ALERTS = False`; primary key field `name`; render signature `render(payload, fields_desc=None, view=None) -> list[Row]`.

---

### Task 1 — Model identity, fields_description, EMITS_ALERTS

**Files:** `glances/plugins/smart/model_v5.py`, `tests/test_plugin_smart_v5.py`

**Interfaces:**
- Consumes: `GlancesPluginBase[list]` (base), `StatsStoreV5`, `GlancesConfigV5`.
- Produces: `PluginModel` class with `plugin_name`, `IS_COLLECTION`, `EMITS_ALERTS`, `fields_description` (`name` primary_key; `attributes` internal/watched False), `_primary_key == "name"`.

Steps:

- [ ] Write the failing identity/fields test in `tests/test_plugin_smart_v5.py`:

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the v5 smart plugin model."""

from __future__ import annotations

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.smart.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    return GlancesConfigV5()


def _cfg_with(tmp_path, monkeypatch, body: str) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    xdg = tmp_path / "xdg"
    cfg_dir = xdg / "glances"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "glances.conf").write_text(body)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    return GlancesConfigV5()


def test_plugin_identity(store, config):
    p = PluginModel(store, config)
    assert p.plugin_name == "smart"
    assert p.IS_COLLECTION is True
    assert p._primary_key == "name"


def test_fields_description_flags():
    fd = PluginModel.fields_description
    assert fd["name"]["primary_key"] is True
    # attributes is an internal, non-watched nested list (survives the flat filter).
    assert fd["attributes"].get("internal") is True
    assert fd["attributes"].get("watched", False) is False


def test_emits_alerts_false():
    # v4 smart has no colouring/alerts — the port must not raise alerts.
    assert PluginModel.EMITS_ALERTS is False
```

- [ ] Run (expect FAIL — module does not exist):
  `.venv/bin/python -m pytest tests/test_plugin_smart_v5.py::test_plugin_identity -v`

- [ ] Create `glances/plugins/smart/model_v5.py` with the identity/schema skeleton (grabber added in Task 2):

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — smart plugin (collection, per-device).

Ported from `glances/plugins/smart/__init__.py`. Reuses the v4 module-level
grabber `get_smart_data(hide_attributes)` (pySMART) verbatim, wrapped in
`asyncio.to_thread` and gated on root (`is_admin()`) + the pySMART import.

v4 keys each device dict by NUMERIC attribute ids, which the flat v5 field
filter would strip. Each device is therefore RESHAPED into
`{"name": DeviceName, "attributes": [attr, …]}` (attrs sorted by the v4
numeric order); `_remove_parameters` filters only top-level item keys, so the
nested `attributes` list passes through intact.

No levels, no alerts (EMITS_ALERTS = False) — v4 smart is display-only.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

import glances.plugins.smart as smart_v4
from glances.globals import is_admin
from glances.plugins.plugin.base_v5 import GlancesPluginBase

logger = logging.getLogger(__name__)


class PluginModel(GlancesPluginBase[list]):
    """SMART disk attributes plugin (collection)."""

    plugin_name: ClassVar[str] = "smart"
    IS_COLLECTION: ClassVar[bool] = True
    # v4 smart is display-only: no watched fields, no colouring, no alerts.
    EMITS_ALERTS: ClassVar[bool] = False

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "name": {
            "description": "Device identification string (e.g. '/dev/sda Samsung SSD 850').",
            "unit": "string",
            "primary_key": True,
        },
        "attributes": {
            "description": "List of SMART attribute dicts (name, key, raw, value, worst, threshold, ...).",
            "unit": "list",
            "internal": True,
            "watched": False,
        },
    }

    def __init__(self, store: Any, config: Any) -> None:
        super().__init__(store, config)
        self._hide_attributes = self._parse_hide_attributes()

    def _parse_hide_attributes(self) -> list[str]:
        """Parse `[smart] hide_attributes=a,b,c` into a list (v4 parity)."""
        raw = self.config.get("smart", "hide_attributes", "")
        if not raw:
            return []
        logger.info("Following SMART attributes will not be displayed: %s", raw)
        return [a for a in str(raw).split(",")]

    async def _grab_stats(self) -> list:
        # Grabber added in Task 2.
        return []
```

- [ ] Run (expect PASS):
  `.venv/bin/python -m pytest tests/test_plugin_smart_v5.py::test_plugin_identity tests/test_plugin_smart_v5.py::test_fields_description_flags tests/test_plugin_smart_v5.py::test_emits_alerts_false -v`

- [ ] `git add glances/plugins/smart/model_v5.py tests/test_plugin_smart_v5.py` — then STOP (this repo FORBIDS `git commit`).

---

### Task 2 — Grabber: root gate, import guard, to_thread, reshape, hide_attributes

**Files:** `glances/plugins/smart/model_v5.py`, `tests/test_plugin_smart_v5.py`

**Interfaces:**
- Consumes: `is_admin()`; `smart_v4.import_error_tag` (module attribute, dynamic); `smart_v4.get_smart_data(hide_attributes)` returning `list[{'DeviceName': str, <int|str>: attr_dict, …}]`; `[smart] hide_attributes` config.
- Produces: `list[{"name": DeviceName, "attributes": [attr_dict, …]}]` (attrs sorted by v4 numeric key order; non-numeric keys keep insertion order).

Steps:

- [ ] Append the failing grabber tests to `tests/test_plugin_smart_v5.py`:

```python
def _fake_device(name="/dev/sda Samsung SSD 850"):
    # v4 shape: DeviceName + numeric attribute keys (out of order on purpose).
    return {
        "DeviceName": name,
        5: {"name": "Reallocated_Sector_Ct", "key": "Reallocated_Sector_Ct", "raw": 0, "value": 100},
        1: {"name": "Raw_Read_Error_Rate", "key": "Raw_Read_Error_Rate", "raw": 200, "value": 100},
        9: {"name": "Power_On_Hours", "key": "Power_On_Hours", "raw": 12345, "value": 99},
    }


@pytest.mark.asyncio
async def test_grab_reshapes_numeric_keys_to_attributes_list(store, config, monkeypatch):
    p = PluginModel(store, config)
    monkeypatch.setattr("glances.plugins.smart.model_v5.is_admin", lambda: True)
    monkeypatch.setattr(smart_module, "import_error_tag", False)
    monkeypatch.setattr(smart_module, "get_smart_data", lambda hide: [_fake_device()])

    rows = await p._grab_stats()
    assert len(rows) == 1
    dev = rows[0]
    assert dev["name"] == "/dev/sda Samsung SSD 850"
    # Numeric keys flattened into a list, sorted by the v4 numeric order (1,5,9).
    assert [a["name"] for a in dev["attributes"]] == [
        "Raw_Read_Error_Rate",
        "Reallocated_Sector_Ct",
        "Power_On_Hours",
    ]
    # DeviceName is not smuggled into the attributes list.
    assert all("DeviceName" not in a for a in dev["attributes"])


@pytest.mark.asyncio
async def test_grab_passes_hide_attributes_to_helper(tmp_path, monkeypatch, store):
    config = _cfg_with(tmp_path, monkeypatch, "[smart]\nhide_attributes=Self-tests,Errors\n")
    p = PluginModel(store, config)
    assert p._hide_attributes == ["Self-tests", "Errors"]

    captured = {}

    def _grab(hide):
        captured["hide"] = hide
        return []

    monkeypatch.setattr("glances.plugins.smart.model_v5.is_admin", lambda: True)
    monkeypatch.setattr(smart_module, "import_error_tag", False)
    monkeypatch.setattr(smart_module, "get_smart_data", _grab)
    await p._grab_stats()
    assert captured["hide"] == ["Self-tests", "Errors"]


@pytest.mark.asyncio
async def test_grab_empty_when_not_root(store, config, monkeypatch):
    p = PluginModel(store, config)
    monkeypatch.setattr("glances.plugins.smart.model_v5.is_admin", lambda: False)
    # get_smart_data must NOT be called when not root.
    monkeypatch.setattr(smart_module, "get_smart_data", lambda hide: (_ for _ in ()).throw(AssertionError("called")))
    assert await p._grab_stats() == []


@pytest.mark.asyncio
async def test_grab_empty_when_import_error(store, config, monkeypatch):
    p = PluginModel(store, config)
    monkeypatch.setattr("glances.plugins.smart.model_v5.is_admin", lambda: True)
    monkeypatch.setattr(smart_module, "import_error_tag", True)
    monkeypatch.setattr(smart_module, "get_smart_data", lambda hide: (_ for _ in ()).throw(AssertionError("called")))
    assert await p._grab_stats() == []


@pytest.mark.asyncio
async def test_grab_non_numeric_keys_keep_insertion_order(store, config, monkeypatch):
    """#2904: some attribute keys are not numeric — reshape must not crash and
    must preserve insertion order for that device."""
    p = PluginModel(store, config)
    dev = {"DeviceName": "/dev/nvme0 NVMe", "bytesWritten": {"name": "Bytes written", "key": "bytesWritten", "raw": 1}}
    monkeypatch.setattr("glances.plugins.smart.model_v5.is_admin", lambda: True)
    monkeypatch.setattr(smart_module, "import_error_tag", False)
    monkeypatch.setattr(smart_module, "get_smart_data", lambda hide: [dev])
    rows = await p._grab_stats()
    assert [a["key"] for a in rows[0]["attributes"]] == ["bytesWritten"]
```

  Add near the imports of the test file:
```python
import glances.plugins.smart as smart_module
```

- [ ] Run (expect FAIL — `_grab_stats` still returns `[]`):
  `.venv/bin/python -m pytest tests/test_plugin_smart_v5.py::test_grab_reshapes_numeric_keys_to_attributes_list -v`

- [ ] Replace the placeholder `_grab_stats` in `model_v5.py` with the full grabber + reshape:

```python
async def _grab_stats(self) -> list:
    """Grab SMART data (root-gated, pySMART-guarded) and reshape.

    Mirrors v4 `update()`: non-root disables the plugin (→ empty), a
    missing pySMART import disables it (→ empty). Otherwise the v4 helper
    runs in a worker thread and each device is reshaped for v5.
    """
    if not is_admin():
        # v4 calls `disable(args, "smart")` when not admin; here we simply
        # yield an empty collection (base keeps it valid).
        return []
    if smart_v4.import_error_tag:
        return []
    devices = await asyncio.to_thread(smart_v4.get_smart_data, self._hide_attributes)
    return [self._reshape(dev) for dev in devices if isinstance(dev, dict)]


@staticmethod
def _reshape(device: dict) -> dict:
    """Flatten a v4 numeric-keyed device dict into the v5 shape.

    `{'DeviceName': str, <num>: attr, …}` -> `{"name": str, "attributes": [attr, …]}`.
    Attribute keys are sorted by their v4 numeric id (`sorted(key=int)`);
    non-numeric keys (#2904) keep insertion order.
    """
    name = device.get("DeviceName", "")
    keys = [k for k in device if k != "DeviceName"]
    try:
        keys = sorted(keys, key=int)
    except (TypeError, ValueError):
        pass  # #2904 — some keys are not numeric; keep insertion order.
    return {"name": name, "attributes": [device[k] for k in keys]}
```

- [ ] Run (expect PASS):
  `.venv/bin/python -m pytest tests/test_plugin_smart_v5.py -v`

- [ ] `git add glances/plugins/smart/model_v5.py tests/test_plugin_smart_v5.py` — then STOP (no `git commit`).

---

### Task 3 — Curses renderer (`SMART disks`)

**Files:** `glances/plugins/smart/render_curses_v5.py`, `tests/test_plugin_smart_render_curses_v5.py`

**Interfaces:**
- Consumes: collection payload `{"data": [{"name": str, "attributes": [attr, …]}], "_levels": {}}`; `Cell` / `Row` / `title_role` from `curses_renderer_v5`; `auto_unit` from `glances.globals`; `LARGE_VALUE_KEYS` from `glances.plugins.smart`.
- Produces: `list[Row]` — a `SMART disks` header, then per device a name row + one row per attribute (name col + value rjust 8). Widths honour `_NAME_COL_WIDTH + 1 + _VALUE_COL_WIDTH ≤ 34`.

Steps:

- [ ] Write the failing renderer tests in `tests/test_plugin_smart_render_curses_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — tests for the smart curses renderer."""

from __future__ import annotations

from glances.globals import auto_unit
from glances.plugins.smart.render_curses_v5 import (
    _LEFT_SIDEBAR_MAX_WIDTH,
    _NAME_COL_WIDTH,
    _VALUE_COL_WIDTH,
    render,
)


def _attr(name, key=None, raw=0, value=100):
    return {"name": name, "key": key if key is not None else name, "raw": raw, "value": value}


def _payload(devices, levels=None):
    return {"data": devices, "_levels": levels or {}}


def _flat(rows):
    return "\n".join(" ".join(c.text for c in r.cells) for r in rows)


def test_empty_returns_header_only():
    rows = render(_payload([]))
    assert "SMART disks" in _flat(rows)
    assert len(rows) == 1  # header only


def test_header_device_and_attributes():
    dev = {"name": "/dev/sda Samsung SSD 850", "attributes": [_attr("Power_On_Hours", raw=12345)]}
    rows = render(_payload([dev]))
    flat = _flat(rows)
    assert "SMART disks" in flat
    assert "/dev/sda Samsung SSD 850" in flat
    # underscores rendered as spaces
    assert "Power On Hours" in flat
    assert "12345" in flat


def test_large_value_key_uses_auto_unit():
    dev = {"name": "/dev/nvme0 NVMe", "attributes": [_attr("Bytes written", key="bytesWritten", raw=1500000)]}
    rows = render(_payload([dev]))
    flat = _flat(rows)
    expected = auto_unit(1500000)  # e.g. '1.4M'
    assert expected in flat
    assert "1500000" not in flat  # raw not shown for a LARGE_VALUE_KEYS attribute


def test_none_raw_renders_blank_value():
    dev = {"name": "/dev/sda", "attributes": [_attr("Some_Attr", raw=None)]}
    rows = render(_payload([dev]))
    # attribute row present, value cell is blank (not the string 'None').
    assert "None" not in _flat(rows)


def test_row_fits_left_sidebar_budget():
    """name col + 1 separator + value col must fit the 34-char left sidebar."""
    assert _NAME_COL_WIDTH + 1 + _VALUE_COL_WIDTH <= _LEFT_SIDEBAR_MAX_WIDTH
    dev = {"name": "/dev/sda Samsung SSD 850 EVO extra long", "attributes": [_attr("Power_On_Hours", raw=12345)]}
    rows = render(_payload([dev]))
    for r in rows:
        # every attribute row is exactly [name_cell, value_cell]; the device
        # and header rows are single cells clamped to the block width.
        if len(r.cells) == 2:
            assert len(r.cells[0].text) + 1 + len(r.cells[1].text) <= _LEFT_SIDEBAR_MAX_WIDTH
        else:
            assert len(r.cells[0].text) <= _LEFT_SIDEBAR_MAX_WIDTH
```

- [ ] Run (expect FAIL — renderer does not exist):
  `.venv/bin/python -m pytest tests/test_plugin_smart_render_curses_v5.py::test_header_device_and_attributes -v`

- [ ] Create `glances/plugins/smart/render_curses_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the smart plugin.

Mirrors v4 `smart.msg_curse()`: a `SMART disks` header, then per device a
name line followed by one line per SMART attribute (`name` + right-aligned
raw value). LEFT sidebar; the two-cell attribute rows must fit the 34-char
left-sidebar maximum *including* the one-space separator the painter inserts:

    name (_NAME_COL_WIDTH) + 1 + value (_VALUE_COL_WIDTH) = 25 + 1 + 8 = 34

Overshooting by one char makes the painter truncate the value cell.

    SMART disks
    /dev/sda Samsung SSD 850
     Power On Hours            12345
     Reallocated Sector Ct         0
"""

from __future__ import annotations

from typing import Any

from glances.globals import auto_unit
from glances.outputs.curses_renderer_v5 import Cell, Row, title_role
from glances.plugins.smart import LARGE_VALUE_KEYS

_NAME_COL_WIDTH = 25
_VALUE_COL_WIDTH = 8
# Painter inserts a 1-space separator between the two cells, so the block
# spans _NAME_COL_WIDTH + 1 + _VALUE_COL_WIDTH. Must stay <= the left-sidebar
# maximum or the trailing value is clipped (see module docstring).
_LEFT_SIDEBAR_MAX_WIDTH = 34


def _attr_name_text(name: Any) -> str:
    """Leading-space-indented attribute name, '_'→' ', clamped to the column."""
    display = " " + str(name).replace("_", " ")
    return display[:_NAME_COL_WIDTH].ljust(_NAME_COL_WIDTH)


def _attr_value_text(attr: dict[str, Any]) -> str:
    """Format the raw value: auto_unit for LARGE_VALUE_KEYS, else str; None→''."""
    raw = attr.get("raw")
    if raw is None:
        text = ""
    elif attr.get("key") in LARGE_VALUE_KEYS:
        text = auto_unit(raw)
    else:
        text = str(raw)
    return text.rjust(_VALUE_COL_WIDTH)


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]] | None = None, view=None) -> list[Row]:
    header = Row(cells=[Cell(text="SMART disks".ljust(_NAME_COL_WIDTH), color=title_role(payload), bold=True)])
    rows: list[Row] = [header]

    if not isinstance(payload, dict):
        return rows
    devices = payload.get("data")
    if not isinstance(devices, list):
        return rows

    for device in devices:
        if not isinstance(device, dict):
            continue
        name = str(device.get("name", ""))
        rows.append(Row(cells=[Cell(text=name[:_LEFT_SIDEBAR_MAX_WIDTH])]))
        for attr in device.get("attributes", []):
            if not isinstance(attr, dict):
                continue
            rows.append(
                Row(
                    cells=[
                        Cell(text=_attr_name_text(attr.get("name", ""))),
                        Cell(text=_attr_value_text(attr)),
                    ]
                )
            )
    return rows
```

- [ ] Run (expect PASS):
  `.venv/bin/python -m pytest tests/test_plugin_smart_render_curses_v5.py -v`

- [ ] `git add glances/plugins/smart/render_curses_v5.py tests/test_plugin_smart_render_curses_v5.py` — then STOP (no `git commit`).

---

### Task 4 — Docs note + full suite + lint

**Files:** `docs/aoa/smart.rst`

**Interfaces:**
- Consumes: nothing.
- Produces: a short v5 note on the `attributes` list shape, mirroring the existing `.rst` style. (`smart` is already listed in `docs/aoa/index.rst` — do NOT re-add.)

Steps:

- [ ] Append to `docs/aoa/smart.rst` (after the existing `hide_attributes` block), matching the file's tone:

```rst

.. note::
    In the REST API (v4+) each device is exposed as an object with a ``name``
    field (device identification string) and an ``attributes`` list; every
    entry carries the SMART attribute ``name``, ``key``, ``raw`` and ``value``.
```

- [ ] Run the full smart suite (expect PASS):
  `.venv/bin/python -m pytest tests/test_plugin_smart_v5.py tests/test_plugin_smart_render_curses_v5.py -v`

- [ ] Lint + format the new files (expect clean):
  `ruff check glances/plugins/smart/model_v5.py glances/plugins/smart/render_curses_v5.py tests/test_plugin_smart_v5.py tests/test_plugin_smart_render_curses_v5.py && ruff format glances/plugins/smart/model_v5.py glances/plugins/smart/render_curses_v5.py tests/test_plugin_smart_v5.py tests/test_plugin_smart_render_curses_v5.py`

- [ ] `git add docs/aoa/smart.rst glances/plugins/smart/model_v5.py glances/plugins/smart/render_curses_v5.py tests/test_plugin_smart_v5.py tests/test_plugin_smart_render_curses_v5.py` — then STOP (no `git commit`).

---

## Final self-check (spec §4.2 → task map)

| §4.2 requirement | Task |
| --- | --- |
| Grabber = v4 `get_smart_data(hide_attributes)` in `to_thread`, ImportError-guarded | 2 |
| Root required — `not is_admin()` → empty | 2 |
| No SNMP | (omitted by construction — only `_grab_stats`, no snmp path) |
| Reshape numeric keys → `{"name", "attributes": [...]}`, sorted by v4 numeric order | 2 |
| `_remove_parameters` passes nested `attributes` through (top-level filter only) | 1 (fields_description) verified via reshape test in 2 |
| fields_description: `name` primary_key, `attributes` internal/watched False | 1 |
| Levels NONE, `EMITS_ALERTS = False` | 1 |
| Renderer header `SMART disks` | 3 |
| Per device name line truncated to block width | 3 |
| Per attribute: ` {name '_'→' '}` + value rjust 8; `auto_unit(raw)` for LARGE_VALUE_KEYS else `str(raw)`; None→`""` | 3 |
| Width budget ≤ 34 | 3 |
| Config `hide_attributes` (comma-separated) dropped at grab time (by v4 helper) | 2 |
| Docs note in `smart.rst` (no index re-add) | 4 |
| Tests: identity/fields, reshape, hide_attributes, root-absent empty, LARGE_VALUE_KEYS auto_unit, EMITS_ALERTS False, width-budget | 1–3 |
