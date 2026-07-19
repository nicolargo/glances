# Glances v5 — folders plugin port (G6B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the v4 `folders` plugin to the v5 asyncio architecture — a collection of up to 10 monitored folders whose size is walked by the reused-verbatim `FolderList` engine, with per-folder MB-configured/byte-compared thresholds and `errno`-priority alerting (`EMITS_ALERTS=True`).

**Architecture:** A collection plugin (`model_v5.py::PluginModel`, `IS_COLLECTION=True`, primary key `path`) whose `_grab_stats()` wraps the v4 `FolderList` (`glances/folder_list.py`, reused **unchanged**) in `asyncio.to_thread`: it calls `FolderList.update(key="path")` then `.get()`, returning a fresh copy of each item dict. `FolderList` already resolves per-folder config (`folder_N_path/refresh/careful/warning/critical`) and embeds `size`/`errno` on every cycle — the per-folder `Timer` gating lives entirely inside that reused engine. Because v4's thresholds are keyed by **list position** (`folder_1_careful`), not by the primary-key **value** (`path`), the generic `<pk>_<field>_<level>` config-key override mechanism in `base_v5.py` cannot express them; the model instead overrides `_derived_parameters()` (the same hook `raid`/`sensors`/`wifi` already use for bespoke ladders) and calls the base's pure `thresholds_v5.compute_level()` directly against each item's own embedded threshold values, converting MB → bytes explicitly. `errno != 0` always wins over the size ladder. A dedicated `render_curses_v5.py` mirrors v4 `msg_curse()` (a bare `FOLDERS` title, one row per folder, path truncated from the left, size via `auto_unit` with a `?` prefix on error), rendered in the LEFT sidebar (34-char budget); `folders` is already registered in `LEFT_SLOT` — no orchestrator change.

A **blocking prerequisite** surfaces in Task 1: `GlancesConfigV5.get_value()` currently requires its `default` argument, but `FolderList.__set_folder_list` calls it **without** one (`self.config.get_value(section, key + 'path')`) for every one of the 10 folder slots, on every config that has a `[folders]` section — which the shipped `conf/glances.conf` always does. Left unfixed, instantiating the folders v5 model would raise `TypeError` immediately. Task 1 fixes the compatibility shim itself (not `folder_list.py`).

**Tech Stack:** Python, `glances/folder_list.py` (v4, reused verbatim), asyncio (`to_thread`), `glances.plugins.plugin.thresholds_v5.compute_level`, curses renderer v5, pytest

## Global Constraints

- **Mirror v4**: read v4 `msg_curse()` + `get_alert()` (`glances/plugins/folders/__init__.py`) before writing the renderer/model; divergent "clean generic" layouts are regressions.
- **Reuse `glances/folder_list.py`'s `FolderList` verbatim** — do **not** modify it. All per-folder config parsing and the per-folder `Timer` gating stay inside that engine.
- **`glances/plugins/plugin/base_v5.py` is NOT modified** — an explicit review criterion for G6B.
- **LEFT sidebar, 34-char budget** (not the MAIN/RIGHT column). `folders` is already registered in `LEFT_SLOT` in `curses_renderer_v5.py` — no layout/orchestrator change needed.
- **Empty registry / empty stats must stay valid**: no `[folders]` section, or a `[folders]` section with no `folder_N_path` configured → empty payload, not a crash.
- **Alerts fire on `warning`+ only**; `careful` is colour-only (project-wide `GlancesAlerts` rule — unaffected by this plugin).
- **Plugin titles are ALWAYS `ColorRole.HEADER`** — never escalate a title's colour from `_levels`. (Folders has no column headers at all — v4 parity, see Task 3.)
- **The MB → byte conversion is the trap**: thresholds are configured in MB, compared against a byte count. v4 does `int(threshold) * 1_000_000` (decimal mega, **not** `1024**2`). Must be explicit and covered by a test that would fail on a silent binary/decimal mixup.
- **`errno != 0` outranks the size ladder** — always, regardless of size.
- **No dead code**, no speculative config keys, surgical edits.
- **Do not touch `NEWS.rst`** during development (release-time only).
- **No commits/push/PR** — stage only (`git add`), never `git commit`.
- Tests: `.venv/bin/python -m pytest`; lint `.venv/bin/python -m ruff check` + `.venv/bin/python -m ruff format`.

---

## Key implementation findings (decided, not open)

1. **`GlancesConfigV5.get_value()` is missing v4's `default=None` fallback — blocking.** v4's `GlancesConfig.get_value(self, section, option, default=None)` (`glances/config.py:346`) is called by `FolderList.__set_folder_list` **without** a third argument for `path`, `careful`/`warning`/`critical`, and the `_action` keys (`glances/folder_list.py:64,76,80`). v5's alias, `GlancesConfigV5.get_value(self, section: str, option: str, default: T) -> T` (`glances/config_v5.py:220`), has no default value for `default` — calling it with 2 args raises `TypeError: missing 1 required positional argument: 'default'`. Confirmed by direct repro: `GlancesConfigV5().get_value('folders', 'folder_1_path')` raises today. Since the shipped `conf/glances.conf` always ships a `[folders]` section (`disable=False`), `FolderList.__init__` always takes the `__set_folder_list` branch, so this crashes on the very first construction for **every** user, not just ones who configure a folder. Task 1 fixes `get_value` to fall back to a raw (uncoerced) passthrough when `default` is omitted or `None` — mirroring v4's untyped `ConfigParser.get()` semantics, since v4 never coerced `careful`/`warning`/`critical` at read time either (`int(stat['critical'])` happens later, at alert-check time, in `folders/__init__.py::get_alert`).
2. **`FolderList` keeps its item list as a CLASS attribute — reset it between tests.** `glances/folder_list.py:30-32` declares `__folder_list = []` at class scope; `__set_folder_list` (called whenever `config.has_section('folders')` is true) does `self.__folder_list.append(value)` **without ever reassigning** `self.__folder_list = [...]` first. Because Python only mangles the name (`FolderList._FolderList__folder_list`), this list is the *same object* shared by every `FolderList` instance created with a `[folders]` section, for the lifetime of the process — confirmed: `FolderList._FolderList__folder_list is FolderList._FolderList__folder_list` across two fresh instances. In production this is invisible (Glances constructs exactly one `FolderList` per run). In a test suite that constructs many `PluginModel(store, config)` instances across many tests, folder items from earlier tests would silently leak into later ones. Task 2's test file resets the class attribute in an autouse fixture — this does **not** modify `folder_list.py`, only test-time class state.
3. **The per-folder `Timer` gate inside `FolderList.update()` is a pre-existing no-op** (`glances/folder_list.py:122`: `i in self.timer_folders`, comparing an `int` against a `list[Timer]` — always `False`, so the `not ... and ...` guard never short-circuits and every folder's size is recomputed on every call regardless of its configured `refresh`). This is existing v4 behaviour inside the reused engine; per the "reuse verbatim, do not fix" mandate it is left untouched and not exercised by any test in this plan — noted here only so nobody "fixes" it by surprise later.
4. **Per-folder thresholds are resolved via a bespoke `_derived_parameters()` override, not the base's generic per-primary-key config lookup.** `base_v5.py`'s `read_thresholds(..., pk_value=...)` builds config keys shaped `<pk_value>_<field>_<level>` — for folders that would mean `<absolute-path>_size_critical`, which is **not** a key v4 ever reads (v4 keys thresholds by **list position**: `folder_1_critical`, `folder_2_critical`, …). Inventing a path-keyed config scheme in addition would be a speculative, undocumented config surface. Instead, `FolderList` already resolves each folder's own `careful`/`warning`/`critical` (from `folder_N_*`) and embeds them directly on that folder's item dict — so the model overrides `_derived_parameters()` (the same override hook `raid`, `sensors`, and `wifi` already use for bespoke ladders — see `glances/plugins/raid/model_v5.py:120-140`) and calls the base's pure `thresholds_v5.compute_level(value, thresholds, direction)` directly per item, building `thresholds` from that item's own embedded MB values (converted to bytes). This *is* "the base's mechanism" in the sense of reusing its pure threshold-computation core; it does not reuse the config-key-pattern-matching layer, which does not fit v4's index-keyed config shape.
5. **v4's synthetic `'ERROR'` colour has no v5 equivalent — mapped onto `critical`.** v4's `get_alert()` returns the literal string `'ERROR'` when `errno != 0`, which v4's curses layer maps to a distinct `SELECTED` (bold) colour (`glances/outputs/glances_colors.py:167`). v5's `Level` type is strictly `ok`/`careful`/`warning`/`critical` and `ColorRole` has no `ERROR` variant; inventing one would require touching the shared `curses_renderer_v5.ColorRole` enum and `alerts_v5._ALERTABLE_LEVELS` (`glances/alerts_v5.py:69`, which only fires history/action events for `warning`/`critical` — an untyped `"error"` string would silently collapse to `"ok"` there and never alert). Mapping the errno case onto `"critical"` instead: (a) still outranks the size ladder unconditionally, (b) is alertable (arguably closer to v4's real behaviour of logging an ERROR event than silently becoming a no-op would be), and (c) requires zero changes to any shared v5 module. The renderer's `?` prefix is driven independently, straight off the item's own `errno` field — not off the colour.
6. **No `[folders] disable=True` self-gate is added.** v4 ships `folders` **enabled by default** (`disable=False`), same as `network`/`wifi`/`sensors` — none of which self-gate on `disable=` in v5 either, because v5's `discover_plugins` has no generic disable mechanism at all (confirmed by grep: only `npu` and `vms` implement an `_is_enabled()` self-gate, and only because *their* v4 default is `disable=True`, which v5 would otherwise silently flip to always-on — a real regression). Adding a self-gate here would be a novel, unrequested feature inconsistent with every other enabled-by-default v5 collection plugin. Out of scope.

---

## File Structure

```
glances/config_v5.py               (MODIFIED — get_value() default fallback fix)
glances/plugins/folders/
  __init__.py                      (v4 — untouched; kept for v4 runtime)
  model_v5.py                      (NEW — PluginModel: FolderList wrapping, bespoke _derived_parameters)
  render_curses_v5.py              (NEW — FOLDERS title + per-folder rows)
glances/folder_list.py             (v4 — untouched, reused verbatim)
tests/
  test_config_v5.py                (MODIFIED — get_value() no-default regression tests)
  test_plugin_folders_v5.py        (NEW — model: identity/fields/grab/empty/thresholds/errno-priority)
  test_plugin_folders_render_curses_v5.py (NEW — renderer: title/rows/truncation/size/colour)
docs/aoa/folders.rst               (update for v5; already in docs/aoa/index.rst — do NOT re-add)
conf/glances.conf                  ([folders] disable=False/refresh=60/folder_N_* already shipped — verify only)
```

---

### Task 1 — Fix `GlancesConfigV5.get_value()` no-default passthrough (blocking prerequisite)

**Files:** `glances/config_v5.py`, `tests/test_config_v5.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `GlancesConfigV5.get_value(section: str, option: str, default: T = None) -> T` — when `default` is omitted or `None`, returns the **raw, uncoerced** value from the merged config (a `str`, or `None` if the option is absent), matching v4's `GlancesConfig.get_value(section, option, default=None)` untyped passthrough. When an explicit non-`None` default is passed, behaviour is **unchanged** (delegates to `get()` for typed coercion).

Steps:

- [ ] **Step 1: Write the failing regression tests.** Append to `tests/test_config_v5.py` (reuses the existing `env` fixture and `write`/`xdg_path` helpers already defined at the top of that file):

```python
def test_get_value_without_default_returns_none_when_absent(env: Path) -> None:
    assert GlancesConfigV5().get_value("folders", "folder_1_path") is None


def test_get_value_without_default_returns_raw_string_when_present(env: Path) -> None:
    write(xdg_path(env), "[folders]\nfolder_1_path = /tmp\n")
    assert GlancesConfigV5().get_value("folders", "folder_1_path") == "/tmp"


def test_get_value_explicit_none_default_also_passes_through(env: Path) -> None:
    write(xdg_path(env), "[folders]\nfolder_1_careful = 2500\n")
    assert GlancesConfigV5().get_value("folders", "folder_1_careful", None) == "2500"


def test_get_value_with_non_none_default_still_coerces(env: Path) -> None:
    # Unchanged boundary: an explicit, non-None default still routes
    # through get() for typed coercion — locks in test_get_value_alias's
    # existing guarantee against this change.
    assert GlancesConfigV5().get_value("global", "refresh_time", 0) == 2
```

- [ ] **Step 2: Run to verify failure.**

Run: `.venv/bin/python -m pytest tests/test_config_v5.py::test_get_value_without_default_returns_none_when_absent -v`
Expected: **FAIL** — `TypeError: GlancesConfigV5.get_value() missing 1 required positional argument: 'default'`

- [ ] **Step 3: Apply the fix.** In `glances/config_v5.py`, replace the current `get_value` (lines 220–222):

```python
    def get_value(self, section: str, option: str, default: T) -> T:
        """v4 compatibility alias for get()."""
        return self.get(section, option, default)
```

with:

```python
    def get_value(self, section: str, option: str, default: T = None) -> T:  # type: ignore[assignment]
        """v4 compatibility alias for get().

        Unlike `get()`, a caller may omit `default` entirely — mirroring
        v4's `GlancesConfig.get_value(section, option, default=None)`,
        which several verbatim-reused v4 helper classes call without a
        third argument (e.g. `glances/folder_list.py::FolderList.
        __set_folder_list` reads `folder_N_path` with no default). When
        `default` is left at `None`, no type coercion is applied — the
        raw configparser string (or `None` if the option is absent) is
        returned as-is, matching v4's untyped passthrough. Passing an
        explicit non-None default is unchanged: it still delegates to
        `get()` for typed coercion.
        """
        if default is None:
            return self._merged.get(section, {}).get(option)  # type: ignore[return-value]
        return self.get(section, option, default)
```

- [ ] **Step 4: Run to verify all four new tests pass, plus the existing alias test.**

Run: `.venv/bin/python -m pytest tests/test_config_v5.py -v`
Expected: **PASS** (all tests in the file, including the pre-existing `test_get_value_alias`).

- [ ] **Step 5: Repro check — the original blocking crash is gone.**

Run: `.venv/bin/python -c "from glances.config_v5 import GlancesConfigV5; print(GlancesConfigV5().get_value('folders', 'folder_1_path'))"`
Expected output: `None` (no `TypeError`).

- [ ] **Step 6: Lint.**

Run: `.venv/bin/python -m ruff check glances/config_v5.py tests/test_config_v5.py && .venv/bin/python -m ruff format glances/config_v5.py tests/test_config_v5.py`

- [ ] **Step 7: Stage.**

```bash
git add glances/config_v5.py tests/test_config_v5.py
```
— then STOP (no commit).

---

### Task 2 — Model: identity, fields, `FolderList` wrapping, bespoke MB→byte + errno-priority levels

**Files:** `glances/plugins/folders/model_v5.py`, `tests/test_plugin_folders_v5.py`

**Interfaces:**
- Consumes: `StatsStoreV5`, `GlancesConfigV5` (fixed in Task 1), `FolderList` (`glances/folder_list.py`, `__init__(config)`, `update(key='path') -> list[dict]`, `get() -> list[dict]`), `thresholds_v5.compute_level(value, thresholds, direction) -> str`.
- Produces: `PluginModel` (`plugin_name="folders"`, `IS_COLLECTION=True`, `EMITS_ALERTS=True`, primary key `path`); payload `{"data":[...], "time_since_update":…, "_levels": {path: {"size": {"level":…, "prominent":…}}}}`.

`fields_description` (mirrors v4's module-level `fields_description` in `glances/plugins/folders/__init__.py`):

```python
fields_description: ClassVar[dict[str, dict[str, Any]]] = {
    "path": {"description": "Absolute path.", "unit": "string", "primary_key": True},
    "size": {"description": "Folder size in bytes.", "unit": "bytes"},
    "refresh": {"description": "Refresh interval in seconds.", "unit": "seconds"},
    "errno": {"description": "Return code when retrieving folder size (0 is no error).", "unit": "number"},
    "careful": {"description": "Careful threshold in MB.", "unit": "megabyte"},
    "warning": {"description": "Warning threshold in MB.", "unit": "megabyte"},
    "critical": {"description": "Critical threshold in MB.", "unit": "megabyte"},
}
```

Model body:

```python
_MB_TO_BYTES = 1_000_000  # v4 parity: int(threshold) * 1e6 — decimal mega, NOT 1024**2.


class PluginModel(GlancesPluginBase[list]):
    plugin_name: ClassVar[str] = "folders"
    IS_COLLECTION: ClassVar[bool] = True
    EMITS_ALERTS: ClassVar[bool] = True  # v4 calls glances_events.add() on every non-OK level.

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {...}  # as above

    def __init__(self, store: Any, config: Any) -> None:
        super().__init__(store, config)
        self._folders = FolderList(config)

    async def _grab_stats(self) -> list:
        await asyncio.to_thread(self._folders.update, key=self._primary_key)
        # Fresh per-item copies: FolderList mutates its own dicts in place
        # on every cycle, and _stats_previous must not alias them.
        return [dict(item) for item in self._folders.get()]

    def _derived_parameters(self) -> None:
        """Bespoke per-folder threshold ladder (mirrors v4 `get_alert`).

        See "Key implementation findings" #4-#5 above for why this bypasses
        the base's generic watched-field / per-pk-config-key walk entirely.
        """
        self._levels = {}
        if not isinstance(self._stats, list):
            return
        for item in self._stats:
            if not isinstance(item, dict):
                continue
            path = item.get("path")
            if path is None:
                continue
            level = self._folder_level(item)
            self._levels[str(path)] = {"size": {"level": level, "prominent": False}}

    @staticmethod
    def _folder_level(item: dict[str, Any]) -> str:
        if item.get("errno") not in (None, 0):
            # errno outranks the size ladder unconditionally (v4 parity).
            # No v5 Level/ColorRole for v4's synthetic 'ERROR' — mapped
            # onto 'critical' (see finding #5).
            return "critical"
        size = item.get("size")
        if size is None:
            return "ok"
        thresholds: dict[str, float] = {}
        for level_name in ("careful", "warning", "critical"):
            raw = item.get(level_name)
            if raw is None:
                continue
            try:
                thresholds[level_name] = int(raw) * _MB_TO_BYTES
            except (TypeError, ValueError):
                continue
        return compute_level(size, thresholds, direction="high")
```

Steps:

- [ ] **Step 1: Write `tests/test_plugin_folders_v5.py` — fixtures and identity/fields tests.**

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `folders` plugin (collection)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.folder_list import FolderList
from glances.plugins.folders.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture(autouse=True)
def _reset_folder_list_class_state():
    """FolderList keeps its item list as a CLASS attribute
    (glances/folder_list.py:30-32) that every instance constructed with a
    `[folders]` config section APPENDS onto rather than replacing — a
    pre-existing v4 bug (see plan's "Key implementation findings" #2),
    left untouched per the "reuse verbatim" mandate. Left unreset, folder
    items from one test would leak into the next. Reset the class
    attribute (test-time state only — does not modify folder_list.py)
    before and after every test in this file.
    """
    FolderList._FolderList__folder_list = []
    yield
    FolderList._FolderList__folder_list = []


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfigV5()


def _cfg_with(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str) -> GlancesConfigV5:
    xdg_conf = tmp_path / "xdg" / "glances" / "glances.conf"
    xdg_conf.parent.mkdir(parents=True, exist_ok=True)
    xdg_conf.write_text(textwrap.dedent(body).lstrip("\n"))
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfigV5()


def test_plugin_identity(store, config):
    p = PluginModel(store, config)
    assert p.plugin_name == "folders"
    assert p.IS_COLLECTION is True
    assert p.EMITS_ALERTS is True
    assert p._primary_key == "path"


def test_fields_description():
    fd = PluginModel.fields_description
    assert set(fd) == {"path", "size", "refresh", "errno", "careful", "warning", "critical"}
    assert fd["path"]["primary_key"] is True
```

- [ ] **Step 2: Run to verify failure.**

Run: `.venv/bin/python -m pytest tests/test_plugin_folders_v5.py::test_plugin_identity -v`
Expected: **FAIL** (module `glances.plugins.folders.model_v5` missing).

- [ ] **Step 3: Write COMPLETE `glances/plugins/folders/model_v5.py`.**

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — Folders plugin (collection, per-monitored-folder).

Migrated from `glances/plugins/folders/__init__.py`. Wraps the v4
`FolderList` engine (`glances/folder_list.py`, reused **unchanged**) —
all per-folder config parsing (`folder_N_path/refresh/careful/warning/
critical`) and the per-folder `Timer` gating live inside that engine.

Per-folder thresholds are keyed by **list position** in v4's config
(`folder_1_critical`, not `<path>_size_critical`), so they cannot be
expressed through the base class's generic per-primary-key config-key
override mechanism (`base_v5.read_thresholds(..., pk_value=...)`).
`_derived_parameters()` is overridden instead — same pattern already used
by `raid`/`sensors`/`wifi` — reusing the base's pure threshold-computation
function (`thresholds_v5.compute_level`) directly against each item's own
embedded MB thresholds, converted to bytes.

`errno != 0` (folder unreadable/missing) always outranks the size ladder
and is reported as `critical` — v5 has no dedicated Level/ColorRole for
v4's synthetic `'ERROR'` colour (see plan's "Key implementation
findings" #5).
"""

from __future__ import annotations

import asyncio
from typing import Any, ClassVar

from glances.folder_list import FolderList
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.plugins.plugin.thresholds_v5 import compute_level

_MB_TO_BYTES = 1_000_000  # v4 parity: int(threshold) * 1e6 — decimal mega, NOT 1024**2.


class PluginModel(GlancesPluginBase[list]):
    """Per-monitored-folder plugin (collection)."""

    plugin_name: ClassVar[str] = "folders"
    IS_COLLECTION: ClassVar[bool] = True
    EMITS_ALERTS: ClassVar[bool] = True  # v4 calls glances_events.add() on every non-OK level.

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "path": {"description": "Absolute path.", "unit": "string", "primary_key": True},
        "size": {"description": "Folder size in bytes.", "unit": "bytes"},
        "refresh": {"description": "Refresh interval in seconds.", "unit": "seconds"},
        "errno": {"description": "Return code when retrieving folder size (0 is no error).", "unit": "number"},
        "careful": {"description": "Careful threshold in MB.", "unit": "megabyte"},
        "warning": {"description": "Warning threshold in MB.", "unit": "megabyte"},
        "critical": {"description": "Critical threshold in MB.", "unit": "megabyte"},
    }

    def __init__(self, store: Any, config: Any) -> None:
        super().__init__(store, config)
        self._folders = FolderList(config)

    async def _grab_stats(self) -> list:
        await asyncio.to_thread(self._folders.update, key=self._primary_key)
        # Fresh per-item copies: FolderList mutates its own dicts in place
        # on every cycle, and _stats_previous must not alias them.
        return [dict(item) for item in self._folders.get()]

    def _derived_parameters(self) -> None:
        """Bespoke per-folder threshold ladder (mirrors v4 `get_alert`).

        Overrides the base watched-field walk entirely: thresholds are not
        plugin-wide and not path-keyed in config — each folder carries its
        own already-resolved careful/warning/critical (in MB) from
        `FolderList`. See the plan's "Key implementation findings" #4.
        """
        self._levels = {}
        if not isinstance(self._stats, list):
            return
        for item in self._stats:
            if not isinstance(item, dict):
                continue
            path = item.get("path")
            if path is None:
                continue
            level = self._folder_level(item)
            self._levels[str(path)] = {"size": {"level": level, "prominent": False}}

    @staticmethod
    def _folder_level(item: dict[str, Any]) -> str:
        if item.get("errno") not in (None, 0):
            return "critical"
        size = item.get("size")
        if size is None:
            return "ok"
        thresholds: dict[str, float] = {}
        for level_name in ("careful", "warning", "critical"):
            raw = item.get(level_name)
            if raw is None:
                continue
            try:
                thresholds[level_name] = int(raw) * _MB_TO_BYTES
            except (TypeError, ValueError):
                continue
        return compute_level(size, thresholds, direction="high")
```

- [ ] **Step 4: Run to verify the identity/fields tests pass.**

Run: `.venv/bin/python -m pytest tests/test_plugin_folders_v5.py -v`
Expected: **PASS** (2 tests).

- [ ] **Step 5: Add empty-configuration tests.**

```python
def test_no_folders_section_returns_empty(store, config):
    p = PluginModel(store, config)
    assert list(p._folders.get()) == []


@pytest.mark.asyncio
async def test_no_folders_section_grab_returns_empty(store, config):
    p = PluginModel(store, config)
    assert await p._grab_stats() == []


@pytest.mark.asyncio
async def test_folders_section_with_no_paths_returns_empty(tmp_path, monkeypatch):
    config = _cfg_with(tmp_path, monkeypatch, "[folders]\ndisable=False\n")
    p = PluginModel(StatsStoreV5(), config)
    assert await p._grab_stats() == []
```

- [ ] **Step 6: Run to verify.**

Run: `.venv/bin/python -m pytest tests/test_plugin_folders_v5.py -v`
Expected: **PASS** (5 tests).

- [ ] **Step 7: Add real single-folder collection tests (exercises `FolderList` + `asyncio.to_thread` end-to-end).**

```python
@pytest.mark.asyncio
async def test_single_folder_collected(tmp_path, monkeypatch):
    watched = tmp_path / "watched"
    watched.mkdir()
    (watched / "f.bin").write_bytes(b"\x00" * 4096)
    config = _cfg_with(
        tmp_path,
        monkeypatch,
        f"""
        [folders]
        disable=False
        folder_1_path={watched}
        """,
    )
    p = PluginModel(StatsStoreV5(), config)
    stats = await p._grab_stats()
    assert len(stats) == 1
    assert stats[0]["path"] == str(watched)
    assert stats[0]["size"] >= 4096
    assert stats[0]["errno"] == 0


@pytest.mark.asyncio
async def test_nonexistent_folder_has_nonzero_errno(tmp_path, monkeypatch):
    missing = tmp_path / "does-not-exist"
    config = _cfg_with(
        tmp_path,
        monkeypatch,
        f"""
        [folders]
        disable=False
        folder_1_path={missing}
        """,
    )
    p = PluginModel(StatsStoreV5(), config)
    stats = await p._grab_stats()
    assert len(stats) == 1
    assert stats[0]["path"] == str(missing)
    assert stats[0]["errno"] != 0
    assert stats[0]["size"] == 0
```

- [ ] **Step 8: Run to verify.**

Run: `.venv/bin/python -m pytest tests/test_plugin_folders_v5.py -v`
Expected: **PASS** (7 tests).

- [ ] **Step 9: Add the bespoke-ladder tests — the MB→byte trap, errno priority, and the no-threshold fallback.** These drive `_derived_parameters()` directly against synthetic items (mirrors `raid`'s `_levels()` test helper — `glances/plugins/raid/model_v5.py` test precedent), so the magnitude assertions are exact and independent of real filesystem timing.

```python
def _levels(p, items):
    p._stats = items
    p._derived_parameters()
    return p._levels


def _item(path="/tmp", size=0, errno=0, careful=None, warning=None, critical=None):
    return {
        "path": path,
        "size": size,
        "errno": errno,
        "careful": careful,
        "warning": warning,
        "critical": critical,
        "refresh": 30,
    }


def test_mb_to_byte_conversion_fires_at_decimal_magnitude(store, config):
    # careful="10" -> 10 * 1_000_000 = 10,000,000 bytes (decimal MB).
    # A WRONG *1024**2 conversion would give 10,485,760 bytes instead.
    # 10_200_000 sits strictly between the two: it must trigger "careful"
    # under the correct (decimal) conversion, and would NOT under the
    # wrong (binary) one — this is the discriminating assertion.
    p = PluginModel(store, config)
    lv = _levels(p, [_item(size=10_200_000, careful="10", warning="50", critical="100")])
    assert lv["/tmp"]["size"]["level"] == "careful"


def test_mb_to_byte_conversion_boundary_just_under_stays_ok(store, config):
    # One byte under the decimal-MB threshold (10,000,000) -> ok. Pins the
    # exact magnitude rather than merely "some threshold eventually fires".
    p = PluginModel(store, config)
    lv = _levels(p, [_item(size=9_999_999, careful="10", warning="50", critical="100")])
    assert lv["/tmp"]["size"]["level"] == "ok"


def test_errno_outranks_the_size_ladder(store, config):
    # No thresholds configured at all -> the ladder alone would say "ok".
    # errno != 0 must still force "critical".
    p = PluginModel(store, config)
    lv = _levels(p, [_item(size=100, errno=2, careful=None, warning=None, critical=None)])
    assert lv["/tmp"]["size"]["level"] == "critical"


def test_ok_when_no_thresholds_configured(store, config):
    p = PluginModel(store, config)
    lv = _levels(p, [_item(size=999_999_999, careful=None, warning=None, critical=None)])
    assert lv["/tmp"]["size"]["level"] == "ok"


def test_levels_indexed_by_path(store, config):
    p = PluginModel(store, config)
    lv = _levels(p, [_item(path="/a", size=1), _item(path="/b", size=2)])
    assert set(lv) == {"/a", "/b"}
    assert lv["/a"]["size"]["prominent"] is False
```

- [ ] **Step 10: Run to verify all tests pass.**

Run: `.venv/bin/python -m pytest tests/test_plugin_folders_v5.py -v`
Expected: **PASS** (12 tests).

- [ ] **Step 11: Lint.**

Run: `.venv/bin/python -m ruff check glances/plugins/folders/model_v5.py tests/test_plugin_folders_v5.py && .venv/bin/python -m ruff format glances/plugins/folders/model_v5.py tests/test_plugin_folders_v5.py`

- [ ] **Step 12: Stage.**

```bash
git add glances/plugins/folders/model_v5.py tests/test_plugin_folders_v5.py
```
— then STOP (no commit).

---

### Task 3 — Curses renderer (`FOLDERS` title + per-folder rows)

**Files:** `glances/plugins/folders/render_curses_v5.py`, `tests/test_plugin_folders_render_curses_v5.py`

**Interfaces:**
- Consumes: collection payload `{"data":[...], "_levels": {path: {"size": {"level":…, "prominent":…}}}}`.
- Produces: `render(payload, fields_desc=None, view=None) -> list[Row]` — a title row (`FOLDERS`, no column headers — v4 parity), then one row per folder (path cell + size cell).

Layout (mirror v4 `msg_curse`, `glances/plugins/folders/__init__.py:132-169`):
- v4's `name_max_width = max_width - 7` is reproduced with `max_width` fixed at **31**, so the block fits exactly inside the v5 LEFT-sidebar's 34-char budget once the renderer's automatic 1-space cell separator is accounted for: `_NAME_MAX_WIDTH (24) + 1 (separator) + _SIZE_COL_WIDTH (9) = 34`.
- Path: left-justified in `_NAME_MAX_WIDTH`; when longer, truncated **from the left**, keeping the tail, with a leading `_` (v4: `'_' + i['path'][-name_max_width + 1:]`) — deliberate, do not left-align-truncate.
- Size: `auto_unit`-style formatting (`format_value(value, {"unit": "bytes"})`, mirrors `fs`'s `_format_bytes` helper) right-aligned on 9 chars; when `errno != 0`, prefixed with `?` (consuming one of the 9 chars: `'?' + text.rjust(8)`), exactly matching v4's `'?{:>8}'` / `'{:>9}'` formats.
- Colour: `payload["_levels"][path]["size"]["level"]` mapped through the shared `_LEVEL_TO_ROLE` (no new ColorRole needed — see model's finding #5, which already maps the errno case onto `"critical"`).
- No `view`-driven behaviour (no sort key, no toggle) — `view` is accepted only so the discovery signature matches the group's common contract.

Steps:

- [ ] **Step 1: Write `tests/test_plugin_folders_render_curses_v5.py`.**

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — tests for the folders plugin's curses renderer."""

from __future__ import annotations

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.folders.render_curses_v5 import render


def _payload(items, levels=None):
    return {"data": items, "_levels": levels or {}}


def _folder(path="/tmp", size=1000, errno=0):
    return {"path": path, "size": size, "errno": errno}


def test_empty_returns_nothing():
    assert render(_payload([])) == []


def test_missing_data_key_returns_nothing():
    assert render({}) == []


def test_title_row_is_folders_header():
    rows = render(_payload([_folder()]))
    assert rows[0].cells[0].text.strip() == "FOLDERS"
    assert rows[0].cells[0].color == ColorRole.HEADER
    assert rows[0].cells[0].bold is True
    assert len(rows[0].cells) == 1  # no column headers — v4 parity


def test_one_row_per_folder():
    rows = render(_payload([_folder("/tmp"), _folder("/home")]))
    assert len(rows) == 3  # title + 2 folders


def test_short_path_not_truncated():
    rows = render(_payload([_folder("/tmp")]))
    assert rows[1].cells[0].text.strip() == "/tmp"


def test_long_path_truncated_from_left_with_underscore():
    long_path = "/very/long/path/that/exceeds/the/name/column/width/tail-marker"
    rows = render(_payload([_folder(long_path)]))
    cell_text = rows[1].cells[0].text
    assert cell_text.startswith("_")
    assert cell_text.strip().endswith("tail-marker")
    assert len(cell_text) == 24  # _NAME_MAX_WIDTH


def test_size_formatted_and_right_aligned():
    rows = render(_payload([_folder("/tmp", size=125 * 1024 * 1024)]))
    size_text = rows[1].cells[1].text
    assert "125.0M" in size_text
    assert len(size_text) == 9


def test_errno_prefixes_question_mark():
    rows = render(_payload([_folder("/missing", size=0, errno=2)]))
    size_text = rows[1].cells[1].text
    assert size_text.startswith("?")
    assert len(size_text) == 9


def test_size_colour_careful():
    levels = {"/tmp": {"size": {"level": "careful", "prominent": False}}}
    rows = render(_payload([_folder("/tmp", size=5_000_000)], levels))
    assert rows[1].cells[1].color == ColorRole.CAREFUL


def test_size_colour_critical_on_errno():
    levels = {"/missing": {"size": {"level": "critical", "prominent": False}}}
    rows = render(_payload([_folder("/missing", size=0, errno=2)], levels))
    assert rows[1].cells[1].color == ColorRole.CRITICAL


def test_no_level_entry_defaults_to_default_color():
    rows = render(_payload([_folder("/tmp")]))
    assert rows[1].cells[1].color == ColorRole.DEFAULT


def test_render_works_with_one_positional_arg():
    # A bare render(payload) call must work — fields_desc/view both default.
    rows = render(_payload([_folder()]))
    assert rows
```

- [ ] **Step 2: Run to verify failure.**

Run: `.venv/bin/python -m pytest tests/test_plugin_folders_render_curses_v5.py::test_title_row_is_folders_header -v`
Expected: **FAIL** (module `glances.plugins.folders.render_curses_v5` missing).

- [ ] **Step 3: Write COMPLETE `glances/plugins/folders/render_curses_v5.py`.**

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the folders plugin.

Replicates v4 ``folders.msg_curse()``: a single ``FOLDERS`` title line
(no column headers — v4 has none either), then one row per monitored
folder showing its (possibly left-truncated) path and its size.

Reference layout (v4 ``glances/plugins/folders/__init__.py:132-169``):

    FOLDERS
    /tmp                    125.0M
    _os/nicolargo/Videos     17.0G
    /nonexisting            ?     -

- Path: left-justified, truncated **from the left** (tail kept) with a
  leading ``_`` when longer than the name column — v4 parity, deliberate:
  the tail of a path is usually more identifying than the head.
- Size: right-aligned on 9 chars via an ``auto_unit``-style formatter;
  prefixed with ``?`` (consuming one of the 9 chars) when ``errno != 0``.
- Colour: driven by ``payload["_levels"][path]["size"]["level"]`` — the
  size ladder, or ``critical`` when the folder could not be read at all
  (``errno != 0`` — see ``model_v5.PluginModel._folder_level``, which
  maps v4's synthetic ``'ERROR'`` colour onto v5's ``critical`` level
  since there is no dedicated ERROR Level/ColorRole).

``view`` carries no behaviour here (no sort key, no toggle) — accepted
only so the discovery signature matches the group's common contract
(design §3, ``glances/outputs/curses_renderer_v5.py::_accepts_view``).
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_formatters_v5 import format_value
from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row

# v4 ``name_max_width = max_width - 7``, with ``max_width`` fixed at 31 so
# the rendered block fits exactly inside the v5 LEFT-sidebar's 34-char
# budget once the renderer's automatic 1-space cell separator is added:
#   name (_NAME_MAX_WIDTH=24) + 1 separator + size (_SIZE_COL_WIDTH=9) = 34
_MAX_WIDTH = 31
_NAME_MAX_WIDTH = _MAX_WIDTH - 7
_SIZE_COL_WIDTH = 9


def _format_bytes(value: Any) -> str:
    if value is None:
        return "-"
    return format_value(value, {"unit": "bytes"})


def _format_path(path: str) -> str:
    """Truncate from the LEFT (keep the tail) — v4 parity, deliberate."""
    if len(path) > _NAME_MAX_WIDTH:
        return ("_" + path[-(_NAME_MAX_WIDTH - 1) :]).ljust(_NAME_MAX_WIDTH)
    return path.ljust(_NAME_MAX_WIDTH)


def _size_cell(item: dict[str, Any], level_entry: dict[str, Any]) -> Cell:
    size = item.get("size")
    errno = item.get("errno") or 0
    text = _format_bytes(size)
    rendered = ("?" + text.rjust(_SIZE_COL_WIDTH - 1)) if errno != 0 else text.rjust(_SIZE_COL_WIDTH)
    level = level_entry.get("level") if isinstance(level_entry, dict) else None
    role = _LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT)
    prominent = bool(level_entry.get("prominent")) if isinstance(level_entry, dict) else False
    return Cell(text=rendered, color=role, prominent=prominent)


def render(
    payload: dict[str, Any],
    fields_desc: dict[str, dict[str, Any]] | None = None,
    view: dict[str, Any] | None = None,
) -> list[Row]:
    """Render the folders plugin's TUI block — mirrors v4 ``folders.msg_curse``."""
    items = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return []
    items = [i for i in items if isinstance(i, dict)]
    if not items:
        return []

    raw_levels = payload.get("_levels")
    levels_index = raw_levels if isinstance(raw_levels, dict) else {}

    rows: list[Row] = [Row(cells=[Cell(text="FOLDERS".ljust(_NAME_MAX_WIDTH), color=ColorRole.HEADER, bold=True)])]
    for item in items:
        path = str(item.get("path") or "")
        item_levels = levels_index.get(path) if isinstance(levels_index, dict) else None
        size_level = item_levels.get("size", {}) if isinstance(item_levels, dict) else {}
        rows.append(Row(cells=[Cell(text=_format_path(path)), _size_cell(item, size_level)]))
    return rows
```

- [ ] **Step 4: Run to verify all renderer tests pass.**

Run: `.venv/bin/python -m pytest tests/test_plugin_folders_render_curses_v5.py -v`
Expected: **PASS** (12 tests).

- [ ] **Step 5: Lint.**

Run: `.venv/bin/python -m ruff check glances/plugins/folders/render_curses_v5.py tests/test_plugin_folders_render_curses_v5.py && .venv/bin/python -m ruff format glances/plugins/folders/render_curses_v5.py tests/test_plugin_folders_render_curses_v5.py`

- [ ] **Step 6: Stage.**

```bash
git add glances/plugins/folders/render_curses_v5.py tests/test_plugin_folders_render_curses_v5.py
```
— then STOP (no commit).

---

### Task 4 — Config verification + docs + full-suite green

**Files:** `conf/glances.conf` (verify only), `docs/aoa/folders.rst`

**Interfaces:** none new — verification and documentation.

Steps:

- [ ] **Step 1: Verify `conf/glances.conf` `[folders]` section already ships the needed keys** (confirmed present at lines 464-489: `disable=False`, `refresh=60`, commented `folder_1_path`/`folder_1_careful`/`folder_1_warning`/`folder_1_critical`/`folder_1_refresh` examples, `folder_2_*`/`folder_3_path`/`folder_4_path`). Do **not** add, remove, or change any default. Only touch it if a diff shows a key genuinely missing.

- [ ] **Step 2: Update `docs/aoa/folders.rst` for v5.** Read the current file (already lists `path`/`careful`/`warning`/`critical`/`refresh` per-item config and the `?`/`!` legend). Append a v5 note documenting the alerting/priority behaviour without touching the existing v4-authored prose above it:

```rst
.. note::

    Since Glances v5, each folder's ``careful``/``warning``/``critical``
    threshold (in MB) is converted to bytes and compared against that
    folder's own size — thresholds are per folder, not global. A folder
    that cannot be read (non-existent path, permission denied) always
    takes priority over the size thresholds and is shown with a leading
    ``?``. The plugin feeds the alert history (``EMITS_ALERTS=True``,
    mirrors v4) and is displayed in the TUI's left sidebar.
```

Confirm `folders` is already in `docs/aoa/index.rst` (line 39 — do NOT re-add).

- [ ] **Step 3: Run the v5 folders test set.**

Run: `.venv/bin/python -m pytest tests/test_plugin_folders_v5.py tests/test_plugin_folders_render_curses_v5.py tests/test_config_v5.py -v`
Expected: **PASS**.

- [ ] **Step 4: Run the full suite to confirm no regression.**

Run: `.venv/bin/python -m pytest -q`
Expected: **PASS** (green, count increased only by the new folders + config tests; a single pre-existing unrelated failure `tests/test_actions_sanitize.py::TestSecurePopen::test_pipe` may remain — it references none of the folders modules).

- [ ] **Step 5: Lint the full touched set.**

Run: `.venv/bin/python -m ruff check glances/config_v5.py glances/plugins/folders/ tests/test_config_v5.py tests/test_plugin_folders_v5.py tests/test_plugin_folders_render_curses_v5.py && .venv/bin/python -m ruff format --check glances/config_v5.py glances/plugins/folders/ tests/test_config_v5.py tests/test_plugin_folders_v5.py tests/test_plugin_folders_render_curses_v5.py`

- [ ] **Step 6: Stage.**

```bash
git add glances/plugins/folders/ tests/test_plugin_folders_v5.py tests/test_plugin_folders_render_curses_v5.py docs/aoa/folders.rst
```
— then STOP (no commit).

---

## Final self-check (spec §5.2 / §6 / §7 coverage map)

| Spec requirement | Task |
| --- | --- |
| `PluginModel` collection, primary key `path`, up to 10 folders | Task 2 (via `FolderList`, unchanged 10-slot cap) |
| Config per folder: `folder_N_path/refresh/careful|warning|critical|{level}_action` | Task 2 (reused verbatim inside `FolderList`) |
| Reuse `FolderList` verbatim via `asyncio.to_thread`; per-folder `Timer` gating stays inside the engine | Task 2 + Key finding 3 |
| `GlancesConfigV5.get_value()` blocking incompatibility with `FolderList`'s no-default calls | Task 1 + Key finding 1 |
| `FolderList`'s shared class-level list — test isolation | Task 2 + Key finding 2 |
| Watched `size`, per-folder thresholds resolved via the base's threshold-computation core (`compute_level`), not the generic per-pk config-key walk | Task 2 + Key finding 4 |
| MB→byte conversion trap, tested at the discriminating magnitude | Task 2 (`test_mb_to_byte_conversion_fires_at_decimal_magnitude` + boundary test) |
| `errno != 0` outranks the size ladder | Task 2 (`test_errno_outranks_the_size_ladder`) + Key finding 5 |
| `EMITS_ALERTS = True` | Task 2 |
| No folder configured → empty payload, not a crash | Task 2 (`test_no_folders_section_grab_returns_empty`, `test_folders_section_with_no_paths_returns_empty`) |
| Render: title `FOLDERS`, no column headers, `name_max_width = max_width - 7`, left-truncation with leading `_`, size via `auto_unit` right-aligned on 9, `?` prefix on errno | Task 3 |
| LEFT sidebar (34-char budget); `folders` already in `LEFT_SLOT` — no orchestrator change | Task 3 (constant derivation), verified no code touches `curses_renderer_v5.py` |
| `base_v5.py` untouched | Verified — no task modifies it |
| Docs `docs/aoa/folders.rst` updated for v5 (already in index) | Task 4 |
| Config `[folders]` already shipped — verify | Task 4 |
| Tests: identity/fields, grab (real + empty), MB→byte trap, errno priority, no-threshold fallback, renderer title/rows/truncation/size/colour, `get_value` regression | Tasks 1-3 |
