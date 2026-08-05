# Glances v5 — G6C `mpp` port Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the v4 `mpp` plugin (Rockchip Media Process Platform engines) to v5, and stop it writing to `/proc` — a monitoring tool must not mutate kernel state.

**Architecture:** The v4 hardware card `glances/plugins/mpp/cards/rockchip_mpp.py` is reused as a pure collector, exactly as `npu/model_v5.py` reuses `npu/cards/*`. The single edit to that card removes `_ensure_load_interval()`, which wrote to `/proc/mpp_service/load_interval`. Because that file gates the kernel's load reporting — and `_parse_load()` is the sole source of engines — the plugin now publishes nothing until an operator sets it manually. Two mitigations make that legible: a prerequisite section at the top of `docs/aoa/mpp.rst`, and a once-per-process WARNING from `model_v5.py` naming the exact command.

**Tech Stack:** Python, `asyncio.to_thread`, `glances/plugins/plugin/base_v5.py`, pytest

**Spec:** `docs/superpowers/specs/2026-08-04-glances-v5-g6c-design.md` §5

## Global Constraints

- **Never commit, push, or open a PR.** Every task ends with `git add` only. Never add a `Co-Authored-By` trailer.
- **Do not touch `NEWS.rst`.** The `/proc` change is release-note material the maintainer picks up at release time.
- Run `make pre-commit` before staging each task — not just `make lint && make format`. Treat a failure as blocking. gitleaks scans the **git index**, so `git add` before re-running it.
- Full v5 suite must stay green: `make test-v5`.
- SPDX header on every new file; `from __future__ import annotations` in every new module and test.
- `DISABLED_BY_DEFAULT = True` — v4 ships `[mpp] disable=True`. Do not change the default.
- **No code in this plugin may open any file for writing.** That is the point of the group's one approved edit; a regression test enforces it.

---

### Task 1: Remove the `/proc` write from the card

**Files:**
- Modify: `glances/plugins/mpp/cards/rockchip_mpp.py`
- Test: `tests/test_plugin_mpp_v5.py` (create)

**Interfaces:**
- Produces: `RockchipMPP(mpp_root_folder="/")` keeps its public surface unchanged — `is_available()`, `disable()`, `get_stats()`, `exit()`, `.proc_path`. Only the private write path disappears.

This is the only edit G6C makes to a v4 file. It is safe: merges flow `develop → develop-v5` only, so v4 users are unaffected until the eventual `develop-v5 → develop` merge at the 5.0.0 release candidate (spec §5.3).

**What to delete** (four sites, all in `glances/plugins/mpp/cards/rockchip_mpp.py`):

1. the `_LOAD_INTERVAL_MS = 1000` constant (`:40`)
2. the `self._load_interval_set = False` attribute (`:51`)
3. the whole `_ensure_load_interval()` method (`:66-80`)
4. the `self._ensure_load_interval()` call inside `get_stats()` (`:100`)

Delete nothing else. `_read_file()` stays exactly as it is — it already wraps `open()` inside the `try`, which is required under Snap strict confinement.

- [ ] **Step 1: Write the failing test**

Create `tests/test_plugin_mpp_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Unit tests for the v5 ``mpp`` plugin.

The headline behaviour under test: Glances must never write to ``/proc``.
See docs/superpowers/specs/2026-08-04-glances-v5-g6c-design.md §5.2
"""

from __future__ import annotations

import builtins
import inspect

from glances.plugins.mpp.cards import rockchip_mpp
from glances.plugins.mpp.cards.rockchip_mpp import RockchipMPP

LOAD_CONTENT = """\
21f40000.rkvenc           load:  24.80% utilization:  24.39%
22140100.rkvdec           load:  28.23% utilization:  13.38%
22170000.jpegd            load:   0.00% utilization:   0.00%
"""


def _make_root(tmp_path, load_content="", sessions_content=""):
    """Build a fake `<root>/proc/mpp_service/` tree and return the root."""
    proc = tmp_path / "proc" / "mpp_service"
    proc.mkdir(parents=True)
    (proc / "load").write_text(load_content)
    (proc / "sessions-summary").write_text(sessions_content)
    (proc / "load_interval").write_text("0")
    return str(tmp_path)


def test_card_never_opens_a_file_for_writing(tmp_path, monkeypatch):
    """Regression guard for the design decision: no writes to /proc, ever."""
    root = _make_root(tmp_path, LOAD_CONTENT)
    real_open = builtins.open
    modes: list[str] = []

    def _recording_open(file, mode="r", *args, **kwargs):
        modes.append(mode)
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", _recording_open)
    RockchipMPP(mpp_root_folder=root).get_stats()

    assert modes, "the card should have opened at least one file"
    assert all("w" not in m and "a" not in m and "+" not in m for m in modes), (
        f"the card opened a file for writing: {modes}"
    )


def test_load_interval_file_is_left_untouched(tmp_path):
    root = _make_root(tmp_path, LOAD_CONTENT)
    interval = tmp_path / "proc" / "mpp_service" / "load_interval"
    RockchipMPP(mpp_root_folder=root).get_stats()
    assert interval.read_text() == "0", "Glances must not change the kernel setting"


def test_no_load_interval_machinery_remains():
    """The removal must be complete, not just unreachable."""
    source = inspect.getsource(rockchip_mpp)
    assert "_ensure_load_interval" not in source
    assert "_LOAD_INTERVAL_MS" not in source
    assert "_load_interval_set" not in source


def test_get_stats_parses_engines(tmp_path):
    root = _make_root(tmp_path, LOAD_CONTENT)
    stats = RockchipMPP(mpp_root_folder=root).get_stats()
    by_id = {s["engine_id"]: s for s in stats}
    assert set(by_id) == {"rockchip_rkvenc", "rockchip_rkvdec", "rockchip_jpegd"}
    assert by_id["rockchip_rkvenc"]["load"] == 24.80
    assert by_id["rockchip_rkvdec"]["utilization"] == 13.38


def test_empty_load_file_yields_no_engines(tmp_path):
    """With load_interval at 0 the kernel writes nothing — the plugin goes silent."""
    root = _make_root(tmp_path, "")
    assert RockchipMPP(mpp_root_folder=root).get_stats() == []


def test_absent_proc_tree_is_unavailable(tmp_path):
    card = RockchipMPP(mpp_root_folder=str(tmp_path))
    assert card.is_available() is False
    assert card.get_stats() == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_plugin_mpp_v5.py -v`
Expected: `test_card_never_opens_a_file_for_writing`, `test_load_interval_file_is_left_untouched` and `test_no_load_interval_machinery_remains` FAIL — the card still writes `1000` into `load_interval`. The parsing tests should already pass.

- [ ] **Step 3: Delete the write path**

Apply the four deletions listed above. After the edit, `get_stats()` reads:

```python
    def get_stats(self) -> list[dict]:
        """Get stats for all MPP engines.

        Returns a list of dicts (one per engine).
        """
        if not self._available:
            return []

        # Parse per-engine load
        engines = self._parse_load()

        # Count active sessions per engine
        self._count_sessions(engines)

        return [e.__dict__ for e in engines.values()]
```

Add a short note in the module docstring recording why there is no write, so a future contributor does not "restore" it:

```
Glances never writes to ``/proc``. The kernel only reports engine load once
``/proc/mpp_service/load_interval`` is non-zero, which the operator must set
themselves — see ``docs/aoa/mpp.rst``. Until then this card correctly
reports no engines.
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_plugin_mpp_v5.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Run the full v5 suite**

Run: `make test-v5`
Expected: no new failures. Also run `uv run pytest tests/ -k mpp -v` to catch any v4 mpp test that asserted the write.

- [ ] **Step 6: Pre-commit, then stage**

```bash
git add glances/plugins/mpp/cards/rockchip_mpp.py tests/test_plugin_mpp_v5.py
make pre-commit
```

Do **not** commit.

---

### Task 2: `model_v5.py` — projection plus the once-per-process WARNING

**Files:**
- Create: `glances/plugins/mpp/model_v5.py`
- Test: `tests/test_plugin_mpp_v5.py` (append)

**Interfaces:**
- Produces: `glances.plugins.mpp.model_v5.PluginModel`, a `GlancesPluginBase[list]` with `plugin_name = "mpp"`, primary key `engine_id`. Item shape: `{"engine_id", "name", "type", "load", "utilization", "sessions"}`.
- Consumes: `RockchipMPP` from Task 1, called through `asyncio.to_thread`.

The WARNING lives here, not in the card: the card stays a dumb reader, and the once-per-process latch belongs to the plugin instance (spec §5.2b).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_plugin_mpp_v5.py`:

```python
import asyncio
import logging

from glances.plugins.mpp.model_v5 import PluginModel


def _plugin_on(root, store_with, config_with):
    plugin = PluginModel(store_with(), config_with({}))
    plugin._card = RockchipMPP(mpp_root_folder=root)
    return plugin


def test_grab_stats_projects_the_card_output(tmp_path, store_with, config_with):
    plugin = _plugin_on(_make_root(tmp_path, LOAD_CONTENT), store_with, config_with)
    stats = asyncio.run(plugin._grab_stats())
    assert {s["engine_id"] for s in stats} == {
        "rockchip_rkvenc",
        "rockchip_rkvdec",
        "rockchip_jpegd",
    }


def test_load_thresholds_resolve(tmp_path, store_with, config_with):
    store = store_with()
    plugin = PluginModel(store, config_with({"mpp": {"load_warning": "20"}}))
    plugin._card = RockchipMPP(mpp_root_folder=_make_root(tmp_path, LOAD_CONTENT))
    asyncio.run(plugin.update())
    levels = store.get("mpp")["_levels"]
    # rkvenc is at 24.8%, above the configured warning of 20.
    assert levels["rockchip_rkvenc"]["load"]["level"] == "warning"


def test_empty_load_warns_once_across_cycles(tmp_path, store_with, config_with, caplog):
    plugin = _plugin_on(_make_root(tmp_path, ""), store_with, config_with)
    with caplog.at_level(logging.WARNING):
        asyncio.run(plugin.update())
        asyncio.run(plugin.update())
        asyncio.run(plugin.update())
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1, "the operator hint must not repeat every cycle"
    assert "load_interval" in warnings[0].getMessage()


def test_no_warning_when_engines_are_reported(tmp_path, store_with, config_with, caplog):
    plugin = _plugin_on(_make_root(tmp_path, LOAD_CONTENT), store_with, config_with)
    with caplog.at_level(logging.WARNING):
        asyncio.run(plugin.update())
    assert [r for r in caplog.records if r.levelno == logging.WARNING] == []


def test_no_warning_when_the_card_is_unavailable(tmp_path, store_with, config_with, caplog):
    """No Rockchip hardware is not an operator mistake — stay quiet."""
    plugin = _plugin_on(str(tmp_path), store_with, config_with)
    with caplog.at_level(logging.WARNING):
        asyncio.run(plugin.update())
    assert [r for r in caplog.records if r.levelno == logging.WARNING] == []


def test_mpp_class_flags():
    assert PluginModel.plugin_name == "mpp"
    assert PluginModel.IS_COLLECTION is True
    assert PluginModel.EMITS_ALERTS is True
    assert PluginModel.DISABLED_BY_DEFAULT is True
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_plugin_mpp_v5.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glances.plugins.mpp.model_v5'`

- [ ] **Step 3: Write the implementation**

Create `glances/plugins/mpp/model_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — MPP plugin (collection, per media engine).

Migrated from `glances/plugins/mpp/__init__.py`. Reuses the v4 hardware
card `glances/plugins/mpp/cards/rockchip_mpp.py` as a pure collector,
the same way `npu/model_v5.py` reuses `npu/cards/*`.

**Glances does not write to `/proc`.** The Rockchip kernel driver only
reports engine load once `/proc/mpp_service/load_interval` is non-zero.
v4 silently wrote that setting; v5 does not, because a monitoring tool
must not mutate a global kernel setting. Until the operator sets it, the
card reports no engines — so this plugin logs one WARNING naming the
exact command, then stays quiet. See `docs/aoa/mpp.rst`.

**Default-disabled**: v4 ships `[mpp] disable=True`.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

from glances.plugins.mpp.cards.rockchip_mpp import RockchipMPP
from glances.plugins.plugin.base_v5 import GlancesPluginBase

logger = logging.getLogger(__name__)

_PERCENT_THRESHOLDS = {"careful": 50.0, "warning": 70.0, "critical": 90.0}

_NO_LOAD_HINT = (
    "mpp: the MPP service is present but reports no engine load. The kernel "
    "only publishes load once /proc/mpp_service/load_interval is non-zero, and "
    "Glances does not set it. Run as root, once per boot: "
    "echo 1000 > /proc/mpp_service/load_interval — see docs/aoa/mpp.rst"
)


class PluginModel(GlancesPluginBase[list]):
    """Per-MPP-engine plugin (collection)."""

    plugin_name: ClassVar[str] = "mpp"
    IS_COLLECTION: ClassVar[bool] = True
    EMITS_ALERTS: ClassVar[bool] = True
    # Mirrors v4 `[mpp] disable=True`.
    DISABLED_BY_DEFAULT: ClassVar[bool] = True

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "engine_id": {
            "description": "Engine identification (e.g. rockchip_rkvenc).",
            "unit": "string",
            "primary_key": True,
        },
        "name": {"description": "Engine name (RKVENC, RKVDEC, RKJPEGD).", "unit": "string"},
        "type": {"description": "Engine type (enc, dec, jpeg).", "unit": "string"},
        "load": {
            "description": "Engine load.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": True,
            "default_thresholds": _PERCENT_THRESHOLDS,
        },
        "utilization": {"description": "Engine utilization.", "unit": "percent"},
        "sessions": {"description": "Number of active sessions.", "unit": "number"},
    }

    def __init__(self, store: Any, config: Any) -> None:
        super().__init__(store, config)
        self._card = RockchipMPP()
        self._warned_no_load = False

    def _collect(self) -> list:
        if not self._card.is_available():
            # No Rockchip MPP hardware here. Not an operator mistake — the
            # plugin simply has nothing to report.
            return []
        try:
            stats = self._card.get_stats()
        except Exception as exc:  # noqa: BLE001 — a faulty card must not kill the loop
            logger.debug("mpp: collection failed, disabling the card: %s", exc)
            self._card.disable()
            return []

        if not stats and not self._warned_no_load:
            # The service exists but publishes nothing: almost always the
            # unset load_interval. Say so once, with the fix.
            self._warned_no_load = True
            logger.warning(_NO_LOAD_HINT)
        return stats

    async def _grab_stats(self) -> list:
        return await asyncio.to_thread(self._collect)

    def stop(self) -> None:
        self._card.exit()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_plugin_mpp_v5.py -v`
Expected: PASS (12 tests)

- [ ] **Step 5: Run the full v5 suite**

Run: `make test-v5`
Expected: no new failures.

- [ ] **Step 6: Pre-commit, then stage**

```bash
git add glances/plugins/mpp/model_v5.py tests/test_plugin_mpp_v5.py
make pre-commit
```

Do **not** commit.

---

### Task 3: renderer, slot registration, and the documented prerequisite

**Files:**
- Create: `glances/plugins/mpp/render_curses_v5.py`
- Modify: `glances/outputs/curses_renderer_v5.py:61` — `TOP_SLOT`
- Modify: `docs/aoa/mpp.rst`
- Test: `tests/test_plugin_mpp_v5.py` (append)

**Interfaces:**
- Consumes: the payload published by Task 2 — `{"data": [...], "_levels": {engine_id: {load: {level, prominent}}}}`.
- Produces: `render(payload, fields_desc) -> list[Row]`, discovered automatically from the module path. Only the slot tuple is edited by hand.

**Slot placement.** v4 lists `mpp` in `_top` between `npu` and `gpu` (`glances/outputs/glances_curses.py:110`). v5's `TOP_SLOT` currently omits it even though `_FULL_QUICKLOOK_HIDDEN` already names it. Change line 61 to:

```python
TOP_SLOT: tuple[str, ...] = ("quicklook", "cpu", "percpu", "npu", "mpp", "gpu", "mem", "memswap", "load")
```

v4 reference (`glances/plugins/mpp/__init__.py::msg_curse`): an `MPP` title line, then per engine `{name:<8}{type:>5}`, the load as `{load:>6.1f}%` coloured by its level (`N/A` right-padded to 7 when `load` is `None`), and `  <n> sess` appended only when the session count is non-zero.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_plugin_mpp_v5.py`:

```python
from glances.outputs.curses_renderer_v5 import TOP_SLOT, slot_for
from glances.plugins.mpp.render_curses_v5 import render

_MPP_FIELDS = PluginModel.fields_description


def test_mpp_sits_between_npu_and_gpu_in_the_top_slot():
    assert slot_for("mpp") == "top"
    assert TOP_SLOT.index("npu") < TOP_SLOT.index("mpp") < TOP_SLOT.index("gpu")


def test_render_empty_payload_returns_no_rows():
    assert render({}, _MPP_FIELDS) == []
    assert render({"data": []}, _MPP_FIELDS) == []


def test_render_one_row_per_engine_plus_header():
    payload = {
        "data": [
            {"engine_id": "rockchip_rkvenc", "name": "RKVENC", "type": "enc", "load": 24.8, "sessions": 2},
            {"engine_id": "rockchip_jpegd", "name": "JPEGD", "type": "jpeg", "load": 0.0, "sessions": 0},
        ],
        "_levels": {"rockchip_rkvenc": {"load": {"level": "careful", "prominent": True}}},
    }
    rows = render(payload, _MPP_FIELDS)
    assert len(rows) == 3
    assert "MPP" in "".join(c.text for c in rows[0].cells)
    first = "".join(c.text for c in rows[1].cells)
    assert "RKVENC" in first and "24.8%" in first
    assert "2 sess" in first
    # A zero session count is omitted, as in v4.
    assert "sess" not in "".join(c.text for c in rows[2].cells)


def test_render_shows_na_when_load_is_missing():
    payload = {"data": [{"engine_id": "e", "name": "RKVDEC", "type": "dec", "load": None, "sessions": 0}]}
    rows = render(payload, _MPP_FIELDS)
    assert "N/A" in "".join(c.text for c in rows[1].cells)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_plugin_mpp_v5.py -k "render or top_slot" -v`
Expected: FAIL — missing renderer module, and `mpp` absent from `TOP_SLOT`.

- [ ] **Step 3: Register the slot**

Edit `glances/outputs/curses_renderer_v5.py:61` as shown above. Leave `_FULL_QUICKLOOK_HIDDEN` alone — it already includes `mpp`.

- [ ] **Step 4: Write the renderer**

Create `glances/plugins/mpp/render_curses_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the mpp plugin (top slot).

Mirrors v4 `mpp.msg_curse()`:

    MPP
    RKVENC    enc   24.8%  2 sess
    JPEGD    jpeg    0.0%
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row


def _load_role(levels: dict[str, Any], engine_id: Any) -> ColorRole:
    entry = levels.get(engine_id, {})
    level = entry.get("load", {}).get("level") if isinstance(entry, dict) else None
    return _LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT)


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]]) -> list[Row]:
    if not isinstance(payload, dict):
        return []
    engines = payload.get("data")
    if not isinstance(engines, list) or not engines:
        return []
    levels = payload.get("_levels") if isinstance(payload.get("_levels"), dict) else {}

    rows: list[Row] = [Row(cells=[Cell(text="MPP", color=ColorRole.HEADER, bold=True)])]
    for engine in engines:
        if not isinstance(engine, dict):
            continue
        label = "{:<8}{:>5}".format(str(engine.get("name", "unknown")), str(engine.get("type", "")))
        cells = [Cell(text=label)]

        load = engine.get("load")
        if load is None:
            cells.append(Cell(text="{:>7}".format("N/A")))
        else:
            cells.append(Cell(text=f"{load:>6.1f}%", color=_load_role(levels, engine.get("engine_id"))))

        # v4 omits the session column entirely when the count is zero.
        sessions = engine.get("sessions") or 0
        if sessions:
            cells.append(Cell(text=f"  {sessions} sess"))

        rows.append(Row(cells=cells))
    return rows
```

- [ ] **Step 5: Document the prerequisite**

Edit `docs/aoa/mpp.rst`. Insert this **before** the existing config block, immediately after the introductory paragraphs — it is a prerequisite, not a footnote:

```rst
Prerequisite
------------

The Rockchip kernel driver only publishes engine load once
``/proc/mpp_service/load_interval`` is non-zero. Glances does **not** set it:
a monitoring tool should not mutate a global kernel setting that other
readers share.

Until you set it yourself, the plugin reports no engines at all. As root,
once per boot::

    echo 1000 > /proc/mpp_service/load_interval

To make it persistent, set it from a systemd unit ordered after the MPP
driver is loaded, or from your distribution's local startup script.

Glances logs a single warning at startup when the MPP service is present but
reports no load, so a forgotten setting is easy to spot in the logs.
```

Keep the rest of the page as it is.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run pytest tests/test_plugin_mpp_v5.py -v`
Expected: PASS (16 tests)

- [ ] **Step 7: Run the full v5 suite**

Run: `make test-v5`
Expected: no new failures. If an existing layout test asserts the exact contents of `TOP_SLOT`, update it to include `mpp` rather than reverting the registration.

- [ ] **Step 8: Pre-commit, then stage**

```bash
git add glances/plugins/mpp/render_curses_v5.py glances/outputs/curses_renderer_v5.py \
        docs/aoa/mpp.rst tests/test_plugin_mpp_v5.py
make pre-commit
```

Do **not** commit. Report that all three tasks are staged.

---

## Manual smoke test (maintainer)

Requires Rockchip hardware. With `[mpp] disable=False`:

```bash
# Before setting load_interval: expect an empty payload and ONE warning line.
python -m glances.main_v5 -s -d 2>&1 | grep -i load_interval
curl -s http://127.0.0.1:61208/api/5/mpp          # {"data": [], ...}

# After the documented prerequisite:
echo 1000 > /proc/mpp_service/load_interval
curl -s http://127.0.0.1:61208/api/5/mpp          # engines with load/utilization
curl -s http://127.0.0.1:61208/api/5/mpp/limits   # {"load": {"careful": 50, ...}}
python -m glances.main_v5                          # MPP block between NPU and GPU
```

Confirm `/proc/mpp_service/load_interval` still reads `1000` — and that a run started before you set it never changed the file.
