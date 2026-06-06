# Glances v5 Phase 2 — G1 (Trivials) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the six "trivial" v4 plugins (`uptime`, `system`, `core`, `version`, `psutilversion`, `now`) to the v5 `model_v5` contract, and add a v4-style **header line** to the curses TUI so `system` (left) + `uptime` (right) render above the top row — matching v4's iconic header.

**Architecture:** Each plugin gets a `glances/plugins/<name>/model_v5.py` (scalar, `GlancesPluginBase[dict]`). Auto-discovery (`main_v5.discover_plugins`) wires every new plugin into the scheduler, REST API and TUI registry with zero central edits. Plugins not shown in the v4 TUI (`core`, `version`, `psutilversion`) declare a new base-class flag `DISPLAY_IN_TUI = False` so they stay REST/export-only. The three displayed plugins (`uptime`, `system`, `now`) get a `render_curses_v5.py`; `uptime`+`system` route to a brand-new `header` slot painted on row 0.

**Tech Stack:** Python 3, asyncio, psutil, `platform` stdlib, pytest + pytest-asyncio (`asyncio_mode=auto`), curses (mocked in tests).

**Hard rules (project memory):**
- `feedback-tui-v5-must-mirror-v4` — read each v4 `msg_curse()` + the catalogue (`docs/architecture/tui-v4-rendering-patterns.md`) BEFORE writing a renderer. Do not invent "clean generic" layouts.
- `feedback-news-rst-not-during-dev` — **do NOT touch `NEWS.rst`.** No task in this plan edits it.
- `feedback-never-push-or-open-pr` — stop at the local-commit boundary. No `git push`, no `gh pr create`. The final task's "PR" step is replaced by a local summary.

---

## File Structure

| Path | Responsibility | Action |
|---|---|---|
| `glances/plugins/plugin/base_v5.py` | add `DISPLAY_IN_TUI` class flag | Modify |
| `glances/main_v5.py` | filter the TUI registry on `DISPLAY_IN_TUI` | Modify |
| `glances/outputs/curses_renderer_v5.py` | new `header` slot: `Frame.header`, `HEADER_SLOT`, `slot_for("header")`, `build_frame` routing | Modify |
| `glances/outputs/glances_curses_v5.py` | paint the header line on row 0 (`_paint_header`, shift body down) | Modify |
| `glances/plugins/uptime/model_v5.py` | scalar: `seconds` since boot | Create |
| `glances/plugins/uptime/render_curses_v5.py` | header-right block `Uptime: <h>` | Create |
| `glances/plugins/system/model_v5.py` | scalar: os/hostname/platform/distro/version/hr_name | Create |
| `glances/plugins/system/render_curses_v5.py` | header-left block `hostname  hr_name` | Create |
| `glances/plugins/now/model_v5.py` | scalar: `iso` + `custom` date strings | Create |
| `glances/plugins/now/render_curses_v5.py` | left-sidebar one-liner (custom date, padded 23) | Create |
| `glances/plugins/core/model_v5.py` | scalar: `phys` + `log`; `DISPLAY_IN_TUI=False` | Create |
| `glances/plugins/version/model_v5.py` | scalar: `version`; `DISPLAY_IN_TUI=False` | Create |
| `glances/plugins/psutilversion/model_v5.py` | scalar: `version`; `DISPLAY_IN_TUI=False` | Create |
| `tests/test_plugin_base_v5.py` | cover `DISPLAY_IN_TUI` default + override | Modify |
| `tests/test_main_v5.py` | cover registry filtering | Modify |
| `tests/test_curses_renderer_v5.py` | cover header slot routing | Modify |
| `tests/test_curses_v5.py` | cover `_paint_header` placement | Modify |
| `tests/test_plugin_uptime_v5.py` | uptime model | Create |
| `tests/test_plugin_uptime_render_curses_v5.py` | uptime renderer | Create |
| `tests/test_plugin_system_v5.py` | system model | Create |
| `tests/test_plugin_system_render_curses_v5.py` | system renderer | Create |
| `tests/test_plugin_now_v5.py` | now model | Create |
| `tests/test_plugin_now_render_curses_v5.py` | now renderer | Create |
| `tests/test_plugin_core_v5.py` | core model | Create |
| `tests/test_plugin_version_v5.py` | version + psutilversion models | Create |

Each Task = **one commit**.

---

## Reference patterns (read before coding)

- v5 scalar plugin shape: `glances/plugins/memswap/model_v5.py`, `glances/plugins/load/model_v5.py`.
- v5 plugin test shape: `tests/test_plugin_mem_v5.py` (fixtures `store`, `config`, `_config_with`).
- v5 renderer shape: `glances/plugins/mem/render_curses_v5.py`; its test `tests/test_plugin_mem_render_curses_v5.py`.
- v5 base contract: `glances/plugins/plugin/base_v5.py` — scalar `_grab_stats()` returns a `dict`; the base injects metadata, computes `_levels`, filters undeclared fields, and writes `{**stats, **metadata, "_levels": {...}}` to the store.
- v5 config API: `config.get(section, option, default)` (coerces to `type(default)`).
- v4 sources to mirror: `glances/plugins/{uptime,system,now,core,version,psutilversion}/__init__.py`.
- TUI catalogue: `docs/architecture/tui-v4-rendering-patterns.md`.

**Key contract notes:**
- A scalar plugin with no `watched` field produces an empty `_levels` — fine.
- The generic scalar renderer (`render_scalar_plugin`) would render `system`/`uptime` as a `LABEL value` table — wrong for the header. That is why both ship a custom `render_curses_v5.py`.
- `format_value(value, {"unit": "seconds"})` formats an int second-count as `3d04h` / `5h02m` / `12m30s` / `45s` (see `curses_formatters_v5.format_seconds`).

---

## Task 1: base-class `DISPLAY_IN_TUI` flag + registry filter

**Files:**
- Modify: `glances/plugins/plugin/base_v5.py`
- Modify: `glances/main_v5.py:359` (the `registry = [...]` line in `assemble`)
- Test: `tests/test_plugin_base_v5.py`, `tests/test_main_v5.py`

**Context:** Auto-discovery puts every plugin into the TUI registry. `core`/`version`/`psutilversion` have no `msg_curse` in v4 (not shown). We mirror v4's `display_curse` with a class flag, default `True`, and filter the registry in `assemble`. REST registration is unaffected (it iterates the full `plugins` list, not the registry).

- [ ] **Step 1: Write the failing base-class tests.** Append to `tests/test_plugin_base_v5.py`:

```python
def test_display_in_tui_defaults_true():
    """Plugins are shown in the TUI unless they opt out."""
    from glances.plugins.plugin.base_v5 import GlancesPluginBase

    assert GlancesPluginBase.DISPLAY_IN_TUI is True


def test_display_in_tui_can_be_overridden():
    """A subclass can hide itself from the TUI (mirrors v4 display_curse=False)."""
    from glances.plugins.plugin.base_v5 import GlancesPluginBase

    class _Hidden(GlancesPluginBase):
        plugin_name = "hidden_probe"
        IS_COLLECTION = False
        DISPLAY_IN_TUI = False

        async def _grab_stats(self):
            return {}

    assert _Hidden.DISPLAY_IN_TUI is False
```

- [ ] **Step 2: Run them — expect FAIL** (`AttributeError: ... DISPLAY_IN_TUI`).

Run: `uv run pytest tests/test_plugin_base_v5.py -k display_in_tui -v`
Expected: FAIL.

- [ ] **Step 3: Add the flag.** In `glances/plugins/plugin/base_v5.py`, directly below the `EMITS_ALERTS` ClassVar block (≈ line 84), insert:

```python
    DISPLAY_IN_TUI: ClassVar[bool] = True
    """Whether this plugin is rendered in the curses TUI.

    Mirrors v4's ``display_curse``. Default True. Set False for plugins
    that exist only for the REST API / exporters and were never shown in
    the v4 TUI (``core``, ``version``, ``psutilversion``). The flag is
    read by ``main_v5.assemble`` when it builds the TUI registry; it does
    not affect REST registration (every discovered plugin is served)."""
```

- [ ] **Step 4: Run base tests — expect PASS.**

Run: `uv run pytest tests/test_plugin_base_v5.py -k display_in_tui -v`
Expected: PASS.

- [ ] **Step 5: Write the failing registry-filter test.** Append to `tests/test_main_v5.py`:

```python
def test_assemble_registry_excludes_non_display_plugins(config, monkeypatch):
    """The TUI registry skips plugins with DISPLAY_IN_TUI=False; REST keeps all."""
    from glances.plugins.plugin.base_v5 import GlancesPluginBase

    class _Shown(GlancesPluginBase):
        plugin_name = "shown_probe"
        IS_COLLECTION = False
        DISPLAY_IN_TUI = True

        async def _grab_stats(self):
            return {}

    class _Hidden(GlancesPluginBase):
        plugin_name = "hidden_probe"
        IS_COLLECTION = False
        DISPLAY_IN_TUI = False

        async def _grab_stats(self):
            return {}

    store = StatsStoreV5()
    fakes = [_Shown(store, config), _Hidden(store, config)]
    monkeypatch.setattr("glances.main_v5.discover_plugins", lambda *a, **k: fakes)

    args = build_parser().parse_args([])  # TUI mode (no -s)
    _app, _scheduler, _host, _port, tui = assemble(args, config)

    registry_names = [name for name, _is_coll in tui.registry]
    assert "shown_probe" in registry_names
    assert "hidden_probe" not in registry_names
```

> If `StatsStoreV5` / `build_parser` are not already imported at the top of `tests/test_main_v5.py`, add them (they are used by sibling tests — `build_parser` is imported around line 37, `StatsStoreV5` around line 41; reuse those imports).

- [ ] **Step 6: Run it — expect FAIL** (`hidden_probe` still present).

Run: `uv run pytest tests/test_main_v5.py -k registry_excludes -v`
Expected: FAIL.

- [ ] **Step 7: Apply the one-line filter.** In `glances/main_v5.py`, inside `assemble`, change:

```python
        registry = [(p.plugin_name, p.IS_COLLECTION) for p in plugins]
```
to:
```python
        registry = [(p.plugin_name, p.IS_COLLECTION) for p in plugins if p.DISPLAY_IN_TUI]
```

- [ ] **Step 8: Run the filter test + full main/base suites — expect PASS.**

Run: `uv run pytest tests/test_main_v5.py tests/test_plugin_base_v5.py -v`
Expected: PASS (no regressions).

- [ ] **Step 9: Commit.**

```bash
git add glances/plugins/plugin/base_v5.py glances/main_v5.py tests/test_plugin_base_v5.py tests/test_main_v5.py
git commit -m "feat(v5): DISPLAY_IN_TUI base flag — exclude REST-only plugins from the TUI"
```

---

## Task 2: TUI `header` slot (renderer side)

**Files:**
- Modify: `glances/outputs/curses_renderer_v5.py`
- Test: `tests/test_curses_renderer_v5.py`

**Context:** v4 renders `system` (hostname + OS, flush-left) and `uptime` (flush-right) on a dedicated header line above the top row. v5 deferred this ("optional header — not in G0"). We add a fourth slot, `header`, to `Frame`, route `system`/`uptime` into it via a new `HEADER_SLOT`, and order it `system` then `uptime`. The painter (Task 3) places `header` on row 0.

- [ ] **Step 1: Read** `docs/architecture/tui-v4-rendering-patterns.md` §system (and the v4 `system`/`uptime` `msg_curse` quoted in this plan's Tasks 4–5).

- [ ] **Step 2: Write the failing routing tests.** Append to `tests/test_curses_renderer_v5.py`:

```python
def test_slot_for_header_plugins():
    from glances.outputs.curses_renderer_v5 import slot_for

    assert slot_for("system") == "header"
    assert slot_for("uptime") == "header"
    assert slot_for("cpu") == "top"
    assert slot_for("network") == "left"


def test_build_frame_routes_system_and_uptime_to_header():
    from glances.outputs.curses_renderer_v5 import build_frame

    snapshot = {
        "system": {"hostname": "h", "hr_name": "Ubuntu", "_levels": {}},
        "uptime": {"seconds": 3600, "_levels": {}},
        "cpu": {"total": 5.0, "_levels": {}},
    }
    fields = {
        "system": {"hostname": {"unit": "string"}, "hr_name": {"unit": "string"}},
        "uptime": {"seconds": {"unit": "seconds"}},
        "cpu": {"total": {"unit": "percent", "watched": True, "label": "CPU"}},
    }
    registry = [("system", False), ("uptime", False), ("cpu", False)]
    frame = build_frame(
        store_snapshot=snapshot,
        fields_by_plugin=fields,
        registry=registry,
        alerts_history=[],
    )
    header_names = [b.name for b in frame.header]
    # Ordered: system first, uptime last (HEADER_SLOT order).
    assert header_names == ["system", "uptime"]
    # They must NOT leak into the other slots.
    assert "system" not in [b.name for b in frame.top + frame.left + frame.right]
    assert "uptime" not in [b.name for b in frame.top + frame.left + frame.right]
    # cpu still lands in the top row.
    assert "cpu" in [b.name for b in frame.top]
```

- [ ] **Step 3: Run — expect FAIL** (`Frame` has no `header`; `slot_for` returns `"left"`).

Run: `uv run pytest tests/test_curses_renderer_v5.py -k "header" -v`
Expected: FAIL.

- [ ] **Step 4: Implement the slot.** In `glances/outputs/curses_renderer_v5.py`:

(a) Add the slot tuple next to `TOP_SLOT` (≈ line 54):

```python
HEADER_SLOT: tuple[str, ...] = ("system", "uptime")
```

(b) In `slot_for`, add the header check first (≈ line 80):

```python
def slot_for(plugin_name: str) -> str:
    """Return the layout slot for a plugin: 'header', 'top', 'left', or 'right'."""
    if plugin_name in HEADER_SLOT:
        return "header"
    if plugin_name in TOP_SLOT:
        return "top"
    if plugin_name in RIGHT_SLOT:
        return "right"
    # Default to left sidebar (matches v4: an unknown plugin lands there).
    return "left"
```

(c) Add a `header` field to `Frame` (≈ line 216):

```python
@dataclass
class Frame:
    """The complete TUI screen, sliced into v4-equivalent slots."""

    header: list[PluginBlock] = field(default_factory=list)
    top: list[PluginBlock] = field(default_factory=list)
    left: list[PluginBlock] = field(default_factory=list)
    right: list[PluginBlock] = field(default_factory=list)
```

(d) In `build_frame`, route the `header` slot. In the per-plugin loop where the block is appended (≈ lines 742–748), extend the slot dispatch:

```python
        block = PluginBlock(name=plugin_name, rows=rows)
        slot = slot_for(plugin_name)
        if slot == "header":
            frame.header.append(block)
        elif slot == "top":
            frame.top.append(block)
        elif slot == "right":
            frame.right.append(block)
        else:
            frame.left.append(block)
```

(e) Add the header ordering sort next to the existing slot sorts (≈ line 753, before the `frame.top.sort(...)` block):

```python
    frame.header.sort(key=lambda b: HEADER_SLOT.index(b.name) if b.name in HEADER_SLOT else len(HEADER_SLOT))
```

- [ ] **Step 5: Run header tests — expect PASS.**

Run: `uv run pytest tests/test_curses_renderer_v5.py -k "header" -v`
Expected: PASS.

- [ ] **Step 6: Run the full renderer suite — expect PASS (no regressions).**

Run: `uv run pytest tests/test_curses_renderer_v5.py -v`
Expected: PASS.

- [ ] **Step 7: Commit.**

```bash
git add glances/outputs/curses_renderer_v5.py tests/test_curses_renderer_v5.py
git commit -m "feat(v5): TUI header slot — route system + uptime to a dedicated header line"
```

---

## Task 3: paint the header line (painter side)

**Files:**
- Modify: `glances/outputs/glances_curses_v5.py` (`_paint`, new `_paint_header`)
- Test: `tests/test_curses_v5.py`

**Context:** `Frame.header` exists but the painter ignores it. We paint header blocks on row 0 — first block flush-left, last block flush-right (v4 fidelity) — then shift the top row + body down by the header height (0 or 1).

- [ ] **Step 1: Write the failing painter tests.** Append to `tests/test_curses_v5.py`:

```python
def test_paint_header_places_first_left_and_last_right(fake_store, fake_alerts, fake_config):
    """Header: first block flush-left at x=0; last block's right edge near max_x."""
    from glances.outputs import glances_curses_v5 as tui_mod
    from glances.outputs.curses_renderer_v5 import Cell, PluginBlock, Row

    tui = tui_mod.TuiV5(
        store=fake_store, alerts=fake_alerts, config=fake_config,
        registry=[], fields_by_plugin={}, refresh_interval=0.01,
    )
    left = PluginBlock(name="system", rows=[Row(cells=[Cell(text="myhost Ubuntu")])])
    right = PluginBlock(name="uptime", rows=[Row(cells=[Cell(text="Uptime: 3d04h")])])

    fake_stdscr = MagicMock()
    height = tui._paint_header(fake_stdscr, [left, right], y0=0, max_x=80)

    assert height == 1
    calls = [(c.args[0], c.args[1], c.args[2]) for c in fake_stdscr.addstr.call_args_list]
    # Left block at x=0.
    assert any(y == 0 and x == 0 and "myhost" in text for (y, x, text) in calls)
    # Right block flush-right: its x is max_x - width("Uptime: 3d04h").
    expected_right_x = 80 - len("Uptime: 3d04h")
    assert any(y == 0 and x == expected_right_x and "Uptime" in text for (y, x, text) in calls)


def test_paint_header_empty_returns_zero(fake_store, fake_alerts, fake_config):
    from glances.outputs import glances_curses_v5 as tui_mod

    tui = tui_mod.TuiV5(
        store=fake_store, alerts=fake_alerts, config=fake_config,
        registry=[], fields_by_plugin={}, refresh_interval=0.01,
    )
    assert tui._paint_header(MagicMock(), [], y0=0, max_x=80) == 0


def test_paint_shifts_top_row_below_header(fake_store, fake_alerts, fake_config):
    """When a header is present, the top row starts at y=1, not y=0."""
    from glances.outputs import glances_curses_v5 as tui_mod
    from glances.outputs.curses_renderer_v5 import Cell, Frame, PluginBlock, Row

    tui = tui_mod.TuiV5(
        store=fake_store, alerts=fake_alerts, config=fake_config,
        registry=[], fields_by_plugin={}, refresh_interval=0.01,
    )
    frame = Frame(
        header=[PluginBlock(name="system", rows=[Row(cells=[Cell(text="myhost")])])],
        top=[PluginBlock(name="cpu", rows=[Row(cells=[Cell(text="CPU 5%")])])],
    )
    fake_stdscr = MagicMock()
    fake_stdscr.getmaxyx.return_value = (24, 80)
    tui._paint(fake_stdscr, frame)

    calls = [(c.args[0], c.args[2]) for c in fake_stdscr.addstr.call_args_list]
    # Header on row 0, CPU top-row on row 1.
    assert any(y == 0 and "myhost" in text for (y, text) in calls)
    assert any(y == 1 and "CPU" in text for (y, text) in calls)
```

- [ ] **Step 2: Run — expect FAIL** (`_paint_header` does not exist; header not painted).

Run: `uv run pytest tests/test_curses_v5.py -k "header or shifts_top_row" -v`
Expected: FAIL.

- [ ] **Step 3: Add `_paint_header` and wire it into `_paint`.** In `glances/outputs/glances_curses_v5.py`:

(a) Add the method just above `_paint_top_row` (≈ line 498):

```python
    def _paint_header(self, stdscr, blocks: list[PluginBlock], y0: int, max_x: int) -> int:
        """Paint the header line (v4 parity): first block flush-left, last
        block flush-right. Returns the header height (0 when empty, else the
        tallest block painted — normally 1).

        Only the first and last blocks are positioned explicitly; the header
        is expected to hold at most two blocks (system + uptime). Any middle
        block (not expected in v5) is skipped rather than overlapped.
        """
        if not blocks:
            return 0
        height = 0
        first = blocks[0]
        self._paint_block(stdscr, first, y0, 0, max_x, fit_to_term=False)
        height = max(height, first.height)
        if len(blocks) > 1:
            last = blocks[-1]
            # Flush-right, but never overlap the flush-left block.
            x = max(first.width + 1, max_x - last.width)
            if x < max_x:
                self._paint_block(stdscr, last, y0, x, max(1, max_x - x), fit_to_term=False)
                height = max(height, last.height)
        return height
```

(b) Update `_paint` (≈ lines 459–486) to paint the header first and shift everything down. Replace the body of `_paint` with:

```python
    def _paint(self, stdscr, frame: Frame) -> None:
        """Lay out the frame on the terminal, mirroring v4:

        header line        (hostname/OS ............ Uptime)  row 0
        top blocks         (cpu | mem | load | ...)  side-by-side
        <separator line>
        left blocks         right blocks              two vertical columns
        """
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()

        # 0. Header line (system flush-left, uptime flush-right).
        header_height = self._paint_header(stdscr, frame.header, 0, max_x)

        # 1. Top row, below the header.
        top_y0 = header_height
        top_height = self._paint_top_row(stdscr, frame.top, top_y0, max_x)

        # 2. Separator under the top row (if any top content was painted).
        body_y0 = top_y0 + top_height
        if top_height > 0 and body_y0 < max_y:
            self._paint_separator(stdscr, body_y0, 0, max_x)
            body_y0 += 1

        # 3. Below the top row: left + right sidebars side-by-side.
        body_height = max(0, max_y - body_y0)
        if body_height > 0:
            left_width = self._sidebar_split(frame, max_x)
            right_x = left_width + self._SIDEBAR_SEPARATOR_GAP
            right_width = max(0, max_x - right_x)

            self._paint_sidebar(stdscr, frame.left, body_y0, 0, left_width, body_height)
            self._paint_sidebar(stdscr, frame.right, body_y0, right_x, right_width, body_height)
```

- [ ] **Step 4: Run the new painter tests — expect PASS.**

Run: `uv run pytest tests/test_curses_v5.py -k "header or shifts_top_row" -v`
Expected: PASS.

- [ ] **Step 5: Run the full TUI suite — expect PASS (no regressions).**

Run: `uv run pytest tests/test_curses_v5.py -v`
Expected: PASS.

- [ ] **Step 6: Commit.**

```bash
git add glances/outputs/glances_curses_v5.py tests/test_curses_v5.py
git commit -m "feat(v5): paint the TUI header line (system left, uptime right) on row 0"
```

---

## Task 4: `uptime` plugin (model + renderer)

**Files:**
- Create: `glances/plugins/uptime/model_v5.py`, `glances/plugins/uptime/render_curses_v5.py`
- Test: `tests/test_plugin_uptime_v5.py`, `tests/test_plugin_uptime_render_curses_v5.py`

**v4 reference:** `glances/plugins/uptime/__init__.py` — `update()` computes `datetime.now() - datetime.fromtimestamp(psutil.boot_time())`; `get_export()` returns `{'seconds': int(total_seconds)}`; `msg_curse()` returns `Uptime: <str>` (flush-right header). The canonical v5 field is therefore `seconds` (matches the v4 export contract).

- [ ] **Step 1: Read** the v4 source above and the catalogue §uptime (if present).

- [ ] **Step 2: Write the failing model tests.** Create `tests/test_plugin_uptime_v5.py`:

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `uptime` plugin."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.uptime.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfigV5()


def test_plugin_identity(store, config):
    plugin = PluginModel(store, config)
    assert plugin.plugin_name == "uptime"
    assert plugin.IS_COLLECTION is False
    assert plugin.DISPLAY_IN_TUI is True


async def test_update_writes_seconds_since_boot(store, config):
    plugin = PluginModel(store, config)
    # boot_time = now - 3600 → uptime ≈ 3600 s.
    with patch("glances.plugins.uptime.model_v5.time.time", return_value=1_000_000.0), patch(
        "glances.plugins.uptime.model_v5.psutil.boot_time", return_value=1_000_000.0 - 3600
    ):
        await plugin.update()
    payload = store.get("uptime")
    assert payload is not None
    assert payload["seconds"] == 3600


async def test_seconds_is_exportable(store, config):
    plugin = PluginModel(store, config)
    with patch("glances.plugins.uptime.model_v5.time.time", return_value=1_000_000.0), patch(
        "glances.plugins.uptime.model_v5.psutil.boot_time", return_value=1_000_000.0 - 120
    ):
        await plugin.update()
    exported = plugin.get_export()
    assert exported == {"seconds": 120}


async def test_grab_tolerates_psutil_failure(store, config):
    plugin = PluginModel(store, config)
    with patch("glances.plugins.uptime.model_v5.psutil.boot_time", side_effect=OSError("nope")):
        await plugin.update()
    # Empty payload, no crash.
    assert store.get("uptime") == {"_levels": {}, "time_since_update": 0.0}
```

- [ ] **Step 3: Run — expect FAIL** (module missing).

Run: `uv run pytest tests/test_plugin_uptime_v5.py -v`
Expected: FAIL (ModuleNotFoundError).

- [ ] **Step 4: Implement the model.** Create `glances/plugins/uptime/model_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — uptime plugin (scalar).

Migrated from `glances/plugins/uptime/__init__.py`. v4 stored a formatted
string; v5 stores the canonical ``seconds`` since boot (matching v4's
``get_export`` contract ``{'seconds': N}``). The TUI renderer formats it
to ``3d04h`` style via the ``seconds`` unit formatter.

SNMP support is **not ported to v5** (architecture §10).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, ClassVar

import psutil

from glances.plugins.plugin.base_v5 import GlancesPluginBase

logger = logging.getLogger(__name__)


class PluginModel(GlancesPluginBase[dict]):
    """System uptime plugin (scalar)."""

    plugin_name: ClassVar[str] = "uptime"
    IS_COLLECTION: ClassVar[bool] = False

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "seconds": {
            "description": "Seconds elapsed since the system booted.",
            "unit": "seconds",
        },
    }

    async def _grab_stats(self) -> dict:
        try:
            boot = await asyncio.to_thread(psutil.boot_time)
        except (OSError, RuntimeError) as exc:
            logger.debug("uptime: psutil.boot_time() unavailable: %s", exc)
            return {}
        return {"seconds": int(max(0.0, time.time() - boot))}
```

- [ ] **Step 5: Run model tests — expect PASS.**

Run: `uv run pytest tests/test_plugin_uptime_v5.py -v`
Expected: PASS.

- [ ] **Step 6: Write the failing renderer tests.** Create `tests/test_plugin_uptime_render_curses_v5.py`:

```python
"""Glances v5 — tests for the uptime curses renderer (header-right block)."""

from __future__ import annotations

from glances.plugins.uptime.render_curses_v5 import render

UPTIME_FIELDS = {"seconds": {"unit": "seconds"}}


def test_render_shows_uptime_label_and_value():
    rows = render({"seconds": 273_840, "_levels": {}}, UPTIME_FIELDS)  # 3d04h
    assert len(rows) == 1
    flat = " ".join(c.text for c in rows[0].cells)
    assert "Uptime:" in flat
    assert "3d04h" in flat


def test_render_empty_payload_yields_no_rows():
    assert render({}, UPTIME_FIELDS) == []
```

- [ ] **Step 7: Run — expect FAIL** (renderer module missing).

Run: `uv run pytest tests/test_plugin_uptime_render_curses_v5.py -v`
Expected: FAIL.

- [ ] **Step 8: Implement the renderer.** Create `glances/plugins/uptime/render_curses_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI renderer for the uptime plugin (header-right block).

Mirrors v4 ``uptime.msg_curse``: a single ``Uptime: <value>`` line. In the
v5 layout this block is routed to the header slot and painted flush-right
(see ``curses_renderer_v5.HEADER_SLOT`` + ``glances_curses_v5._paint_header``).
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_formatters_v5 import format_value
from glances.outputs.curses_renderer_v5 import Cell, Row


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]]) -> list[Row]:
    if not payload or payload.get("seconds") is None:
        return []
    value = format_value(payload["seconds"], fields_desc.get("seconds", {"unit": "seconds"}))
    return [Row(cells=[Cell(text="Uptime:"), Cell(text=value)])]
```

- [ ] **Step 9: Run renderer tests — expect PASS.**

Run: `uv run pytest tests/test_plugin_uptime_render_curses_v5.py -v`
Expected: PASS.

- [ ] **Step 10: Commit.**

```bash
git add glances/plugins/uptime/model_v5.py glances/plugins/uptime/render_curses_v5.py \
        tests/test_plugin_uptime_v5.py tests/test_plugin_uptime_render_curses_v5.py
git commit -m "feat(v5): G1 — port uptime plugin to v5 (seconds since boot + header-right render)"
```

---

## Task 5: `system` plugin (model + renderer)

**Files:**
- Create: `glances/plugins/system/model_v5.py`, `glances/plugins/system/render_curses_v5.py`
- Test: `tests/test_plugin_system_v5.py`, `tests/test_plugin_system_render_curses_v5.py`

**v4 reference:** `glances/plugins/system/__init__.py` — `get_stats_from_std_sys_lib` populates `os_name`/`hostname`/`platform`/`linux_distro`/`os_version`, then `add_human_readable_name` builds `hr_name`. `msg_curse()` = `hostname` (TITLE) + ` hr_name ` (flush-left header). Port the local-only path; SNMP is dropped (architecture §10). `system_info_msg` config key (section `[system]`) overrides `hr_name`.

- [ ] **Step 1: Read** the v4 source (quoted in the discovery notes) + catalogue §system.

- [ ] **Step 2: Write the failing model tests.** Create `tests/test_plugin_system_v5.py`:

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `system` plugin."""

from __future__ import annotations

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.system.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfigV5()


def _config_with(tmp_path, monkeypatch, body: str) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    xdg = tmp_path / "xdg"
    cfg_dir = xdg / "glances"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "glances.conf").write_text(body)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    return GlancesConfigV5()


def test_plugin_identity(store, config):
    plugin = PluginModel(store, config)
    assert plugin.plugin_name == "system"
    assert plugin.IS_COLLECTION is False
    assert plugin.DISPLAY_IN_TUI is True


async def test_update_collects_linux_system_info(store, config, monkeypatch):
    monkeypatch.setattr("glances.plugins.system.model_v5.platform.system", lambda: "Linux")
    monkeypatch.setattr("glances.plugins.system.model_v5.platform.node", lambda: "myhost")
    monkeypatch.setattr("glances.plugins.system.model_v5.platform.architecture", lambda: ("64bit", ""))
    monkeypatch.setattr("glances.plugins.system.model_v5.platform.release", lambda: "6.8.0-generic")
    monkeypatch.setattr(
        "glances.plugins.system.model_v5._linux_distro", lambda: "Ubuntu 24.04"
    )
    plugin = PluginModel(store, config)
    await plugin.update()
    payload = store.get("system")
    assert payload["os_name"] == "Linux"
    assert payload["hostname"] == "myhost"
    assert payload["platform"] == "64bit"
    assert payload["linux_distro"] == "Ubuntu 24.04"
    assert payload["os_version"] == "6.8.0-generic"
    # hr_name combines distro + platform + kernel for Linux.
    assert "Ubuntu 24.04" in payload["hr_name"]
    assert "64bit" in payload["hr_name"]


async def test_system_info_msg_overrides_hr_name(tmp_path, monkeypatch, store):
    config = _config_with(tmp_path, monkeypatch, "[system]\nsystem_info_msg={hostname} rocks\n")
    monkeypatch.setattr("glances.plugins.system.model_v5.platform.system", lambda: "Linux")
    monkeypatch.setattr("glances.plugins.system.model_v5.platform.node", lambda: "myhost")
    monkeypatch.setattr("glances.plugins.system.model_v5.platform.architecture", lambda: ("64bit", ""))
    monkeypatch.setattr("glances.plugins.system.model_v5.platform.release", lambda: "6.8.0")
    monkeypatch.setattr("glances.plugins.system.model_v5._linux_distro", lambda: "Ubuntu 24.04")
    plugin = PluginModel(store, config)
    await plugin.update()
    assert store.get("system")["hr_name"] == "myhost rocks"


async def test_no_watched_field_means_empty_levels(store, config, monkeypatch):
    monkeypatch.setattr("glances.plugins.system.model_v5.platform.system", lambda: "Linux")
    monkeypatch.setattr("glances.plugins.system.model_v5.platform.node", lambda: "h")
    monkeypatch.setattr("glances.plugins.system.model_v5.platform.architecture", lambda: ("64bit", ""))
    monkeypatch.setattr("glances.plugins.system.model_v5.platform.release", lambda: "6")
    monkeypatch.setattr("glances.plugins.system.model_v5._linux_distro", lambda: "Ubuntu")
    plugin = PluginModel(store, config)
    await plugin.update()
    assert store.get("system")["_levels"] == {}
```

- [ ] **Step 3: Run — expect FAIL** (module missing).

Run: `uv run pytest tests/test_plugin_system_v5.py -v`
Expected: FAIL.

- [ ] **Step 4: Implement the model.** Create `glances/plugins/system/model_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — system plugin (scalar host/OS metadata).

Migrated from `glances/plugins/system/__init__.py`. Local-only: SNMP is
dropped in v5 (architecture §10). The ``[system] system_info_msg`` config
key overrides the human-readable name, exactly like v4.
"""

from __future__ import annotations

import asyncio
import logging
import os
import platform
import re
from typing import Any, ClassVar

from glances.config_v5 import GlancesConfigV5
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.stats_store_v5 import StatsStoreV5

logger = logging.getLogger(__name__)


def _linux_os_release() -> str:
    """Read a human distro name from /etc/os-release (NAME + VERSION_ID)."""
    pretty_name = ""
    ashtray: dict[str, str] = {}
    keys = ["NAME", "VERSION_ID"]
    try:
        with open(os.path.join("/etc", "os-release")) as f:
            for line in f:
                for key in keys:
                    if line.startswith(key):
                        ashtray[key] = re.sub(r'^"|"$', "", line.strip().split("=")[1])
    except OSError:
        return pretty_name
    if "NAME" in ashtray:
        pretty_name = ashtray["NAME"]
    if "VERSION_ID" in ashtray:
        pretty_name += f" {ashtray['VERSION_ID']}"
    return pretty_name


def _linux_distro() -> str:
    """Best-effort Linux distribution string (platform.linux_distribution was
    removed in Python 3.8 — fall back to /etc/os-release)."""
    legacy = getattr(platform, "linux_distribution", None)
    if callable(legacy):
        try:
            parts = legacy()
            if parts and parts[0]:
                return " ".join(parts[:2])
        except Exception:
            pass
    return _linux_os_release()


class PluginModel(GlancesPluginBase[dict]):
    """Host / operating-system metadata plugin (scalar)."""

    plugin_name: ClassVar[str] = "system"
    IS_COLLECTION: ClassVar[bool] = False

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "os_name": {"description": "Operating system name.", "unit": "string"},
        "hostname": {"description": "Hostname.", "unit": "string"},
        "platform": {"description": "Platform (32 or 64 bits).", "unit": "string"},
        "linux_distro": {"description": "Linux distribution.", "unit": "string"},
        "os_version": {"description": "Operating system version.", "unit": "string"},
        "hr_name": {"description": "Human readable operating system name.", "unit": "string"},
    }

    def __init__(self, store: StatsStoreV5, config: GlancesConfigV5) -> None:
        super().__init__(store, config)
        # Optional operator override for the human-readable name (v4 parity).
        self._info_msg = self.config.get("system", "system_info_msg", "")

    async def _grab_stats(self) -> dict:
        return await asyncio.to_thread(self._collect)

    def _collect(self) -> dict[str, Any]:
        stats: dict[str, Any] = {
            "os_name": platform.system(),
            "hostname": platform.node(),
            "platform": platform.architecture()[0],
            "linux_distro": "",
            "os_version": "",
        }
        os_name = stats["os_name"]
        if os_name == "Linux":
            stats["linux_distro"] = _linux_distro()
            stats["os_version"] = platform.release()
        elif os_name.endswith("BSD") or os_name == "SunOS":
            stats["os_version"] = platform.release()
        elif os_name == "Darwin":
            stats["os_version"] = platform.mac_ver()[0]
        elif os_name == "Windows":
            win = platform.win32_ver()
            stats["os_version"] = " ".join(win[::2])
        stats["hr_name"] = self._human_name(stats)
        return stats

    def _human_name(self, stats: dict[str, Any]) -> str:
        if self._info_msg:
            try:
                return self._info_msg.format(**stats)
            except (KeyError, IndexError) as e:
                logger.debug("system: invalid system_info_msg (%s)", e)
        if stats["os_name"] == "Linux":
            return "{linux_distro} {platform} / {os_name} {os_version}".format(**stats)
        return "{os_name} {os_version} {platform}".format(**stats)
```

- [ ] **Step 5: Run model tests — expect PASS.**

Run: `uv run pytest tests/test_plugin_system_v5.py -v`
Expected: PASS.

- [ ] **Step 6: Write the failing renderer tests.** Create `tests/test_plugin_system_render_curses_v5.py`:

```python
"""Glances v5 — tests for the system curses renderer (header-left block)."""

from __future__ import annotations

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.system.render_curses_v5 import render

SYSTEM_FIELDS = {
    "hostname": {"unit": "string"},
    "hr_name": {"unit": "string"},
}


def test_render_shows_hostname_as_header_and_hr_name():
    payload = {"hostname": "myhost", "hr_name": "Ubuntu 24.04 64bit", "_levels": {}}
    rows = render(payload, SYSTEM_FIELDS)
    assert len(rows) == 1
    cells = rows[0].cells
    # Hostname is the TITLE (HEADER role).
    assert cells[0].text == "myhost"
    assert cells[0].color == ColorRole.HEADER
    flat = " ".join(c.text for c in cells)
    assert "Ubuntu 24.04 64bit" in flat


def test_render_empty_payload_yields_no_rows():
    assert render({}, SYSTEM_FIELDS) == []
```

- [ ] **Step 7: Run — expect FAIL.**

Run: `uv run pytest tests/test_plugin_system_render_curses_v5.py -v`
Expected: FAIL.

- [ ] **Step 8: Implement the renderer.** Create `glances/plugins/system/render_curses_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI renderer for the system plugin (header-left block).

Mirrors v4 ``system.msg_curse``: ``hostname`` (TITLE) followed by the
human-readable OS name. Routed to the header slot and painted flush-left
(see ``curses_renderer_v5.HEADER_SLOT``). Client/SNMP status lines are not
ported (v5 standalone only).
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import Cell, ColorRole, Row


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]]) -> list[Row]:
    if not payload or not payload.get("hostname"):
        return []
    cells = [Cell(text=str(payload["hostname"]), color=ColorRole.HEADER)]
    hr_name = payload.get("hr_name")
    if hr_name:
        cells.append(Cell(text=str(hr_name)))
    return [Row(cells=cells)]
```

- [ ] **Step 9: Run renderer tests — expect PASS.**

Run: `uv run pytest tests/test_plugin_system_render_curses_v5.py -v`
Expected: PASS.

- [ ] **Step 10: Commit.**

```bash
git add glances/plugins/system/model_v5.py glances/plugins/system/render_curses_v5.py \
        tests/test_plugin_system_v5.py tests/test_plugin_system_render_curses_v5.py
git commit -m "feat(v5): G1 — port system plugin to v5 (host/OS metadata + header-left render)"
```

---

## Task 6: `now` plugin (model + renderer)

**Files:**
- Create: `glances/plugins/now/model_v5.py`, `glances/plugins/now/render_curses_v5.py`
- Test: `tests/test_plugin_now_v5.py`, `tests/test_plugin_now_render_curses_v5.py`

**v4 reference:** `glances/plugins/now/__init__.py` — `update()` writes `iso` (ISO-8601) + `custom` (strftime; `[global] strftime_format` or a tz-aware default). `msg_curse()` shows only `custom`, left-padded to 23 chars. `now` is already listed in `LEFT_SLOT`.

- [ ] **Step 1: Read** the v4 source + catalogue §now (if present).

- [ ] **Step 2: Write the failing model tests.** Create `tests/test_plugin_now_v5.py`:

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `now` plugin."""

from __future__ import annotations

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.now.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfigV5()


def _config_with(tmp_path, monkeypatch, body: str) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    xdg = tmp_path / "xdg"
    cfg_dir = xdg / "glances"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "glances.conf").write_text(body)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    return GlancesConfigV5()


def test_plugin_identity(store, config):
    plugin = PluginModel(store, config)
    assert plugin.plugin_name == "now"
    assert plugin.IS_COLLECTION is False
    assert plugin.DISPLAY_IN_TUI is True


async def test_update_writes_iso_and_custom(store, config):
    plugin = PluginModel(store, config)
    await plugin.update()
    payload = store.get("now")
    assert "iso" in payload and "custom" in payload
    # ISO-8601 contains a 'T' separator.
    assert "T" in payload["iso"]
    assert payload["custom"]


async def test_custom_format_from_config(tmp_path, monkeypatch, store):
    config = _config_with(tmp_path, monkeypatch, "[global]\nstrftime_format=%Y\n")
    plugin = PluginModel(store, config)
    await plugin.update()
    custom = store.get("now")["custom"]
    # %Y → 4-digit year only.
    assert len(custom) == 4 and custom.isdigit()
```

- [ ] **Step 3: Run — expect FAIL.**

Run: `uv run pytest tests/test_plugin_now_v5.py -v`
Expected: FAIL.

- [ ] **Step 4: Implement the model.** Create `glances/plugins/now/model_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — now (current date/time) plugin (scalar).

Migrated from `glances/plugins/now/__init__.py`. Writes ``iso`` (ISO-8601)
and ``custom`` (strftime, ``[global] strftime_format`` or a tz-aware
default). The TUI shows only ``custom`` (left-padded), v4 parity.
"""

from __future__ import annotations

import asyncio
import datetime
from time import strftime, tzname
from typing import Any, ClassVar

from glances.config_v5 import GlancesConfigV5
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.stats_store_v5 import StatsStoreV5


class PluginModel(GlancesPluginBase[dict]):
    """Current date/time plugin (scalar)."""

    plugin_name: ClassVar[str] = "now"
    IS_COLLECTION: ClassVar[bool] = False

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "custom": {"description": "Current date in custom format.", "unit": "string"},
        "iso": {"description": "Current date in ISO 8601 format.", "unit": "string"},
    }

    def __init__(self, store: StatsStoreV5, config: GlancesConfigV5) -> None:
        super().__init__(store, config)
        self._strftime = self.config.get("global", "strftime_format", "")

    async def _grab_stats(self) -> dict:
        return await asyncio.to_thread(self._collect)

    def _collect(self) -> dict[str, Any]:
        iso = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()
        if self._strftime:
            custom = strftime(self._strftime)
        elif len(tzname[1]) > 6:
            custom = strftime("%Y-%m-%d %H:%M:%S %z")
        else:
            custom = strftime("%Y-%m-%d %H:%M:%S %Z")
        return {"iso": iso, "custom": custom}
```

- [ ] **Step 5: Run model tests — expect PASS.**

Run: `uv run pytest tests/test_plugin_now_v5.py -v`
Expected: PASS.

- [ ] **Step 6: Write the failing renderer tests.** Create `tests/test_plugin_now_render_curses_v5.py`:

```python
"""Glances v5 — tests for the now curses renderer (left-sidebar one-liner)."""

from __future__ import annotations

from glances.plugins.now.render_curses_v5 import render

NOW_FIELDS = {"custom": {"unit": "string"}, "iso": {"unit": "string"}}


def test_render_shows_custom_only_padded():
    payload = {"custom": "2026-06-06 12:00:00 CEST", "iso": "2026-06-06T12:00:00+02:00", "_levels": {}}
    rows = render(payload, NOW_FIELDS)
    assert len(rows) == 1
    text = rows[0].cells[0].text
    assert text.startswith("2026-06-06 12:00:00 CEST")
    # Padded to at least 23 chars (v4 parity).
    assert len(text) >= 23
    # ISO is not shown in the TUI.
    assert "T" not in text


def test_render_empty_payload_yields_no_rows():
    assert render({}, NOW_FIELDS) == []
```

- [ ] **Step 7: Run — expect FAIL.**

Run: `uv run pytest tests/test_plugin_now_render_curses_v5.py -v`
Expected: FAIL.

- [ ] **Step 8: Implement the renderer.** Create `glances/plugins/now/render_curses_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI renderer for the now plugin (left-sidebar one-liner).

Mirrors v4 ``now.msg_curse``: the ``custom`` date string left-padded to 23
chars (the v4 process-list padding). The ISO field is REST-only.
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import Cell, Row

_NOW_PAD = 23


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]]) -> list[Row]:
    custom = payload.get("custom") if payload else None
    if not custom:
        return []
    return [Row(cells=[Cell(text=f"{str(custom):{_NOW_PAD}}")])]
```

- [ ] **Step 9: Run renderer tests — expect PASS.**

Run: `uv run pytest tests/test_plugin_now_render_curses_v5.py -v`
Expected: PASS.

- [ ] **Step 10: Commit.**

```bash
git add glances/plugins/now/model_v5.py glances/plugins/now/render_curses_v5.py \
        tests/test_plugin_now_v5.py tests/test_plugin_now_render_curses_v5.py
git commit -m "feat(v5): G1 — port now plugin to v5 (iso + custom date, left-sidebar render)"
```

---

## Task 7: `core` plugin (REST-only)

**Files:**
- Create: `glances/plugins/core/model_v5.py`
- Test: `tests/test_plugin_core_v5.py`

**v4 reference:** `glances/plugins/core/__init__.py` — `update()` writes `{"phys": psutil.cpu_count(logical=False), "log": psutil.cpu_count()}`; explicitly `display_curse=False` (the load plugin shows the core count). So `DISPLAY_IN_TUI=False`.

- [ ] **Step 1: Read** the v4 source.

- [ ] **Step 2: Write the failing model tests.** Create `tests/test_plugin_core_v5.py`:

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `core` plugin (REST-only)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.core.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfigV5()


def test_plugin_identity(store, config):
    plugin = PluginModel(store, config)
    assert plugin.plugin_name == "core"
    assert plugin.IS_COLLECTION is False
    # v4 display_curse=False — not shown in the TUI.
    assert plugin.DISPLAY_IN_TUI is False


async def test_update_writes_phys_and_log(store, config):
    plugin = PluginModel(store, config)
    with patch("glances.plugins.core.model_v5.psutil.cpu_count", side_effect=lambda logical=True: 4 if logical else 2):
        await plugin.update()
    payload = store.get("core")
    assert payload["phys"] == 2
    assert payload["log"] == 4


async def test_grab_tolerates_failure(store, config):
    plugin = PluginModel(store, config)
    with patch("glances.plugins.core.model_v5.psutil.cpu_count", side_effect=OSError("nope")):
        await plugin.update()
    assert store.get("core") == {"_levels": {}, "time_since_update": 0.0}
```

- [ ] **Step 3: Run — expect FAIL.**

Run: `uv run pytest tests/test_plugin_core_v5.py -v`
Expected: FAIL.

- [ ] **Step 4: Implement the model.** Create `glances/plugins/core/model_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — core plugin (CPU core counts, REST-only).

Migrated from `glances/plugins/core/__init__.py`. v4 sets
``display_curse=False`` (the load plugin surfaces the core count), so v5
sets ``DISPLAY_IN_TUI=False``. The data is still served via REST and
consumable by exporters.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

import psutil

from glances.plugins.plugin.base_v5 import GlancesPluginBase

logger = logging.getLogger(__name__)


class PluginModel(GlancesPluginBase[dict]):
    """CPU core-count plugin (scalar, REST-only)."""

    plugin_name: ClassVar[str] = "core"
    IS_COLLECTION: ClassVar[bool] = False
    DISPLAY_IN_TUI: ClassVar[bool] = False

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "phys": {
            "description": "Number of physical cores (hyper-thread CPUs excluded).",
            "unit": "number",
        },
        "log": {
            "description": "Number of logical CPU cores (physical cores × threads per core).",
            "unit": "number",
        },
    }

    async def _grab_stats(self) -> dict:
        try:
            phys, log = await asyncio.to_thread(self._counts)
        except (OSError, RuntimeError, NameError) as exc:
            logger.debug("core: psutil.cpu_count() unavailable: %s", exc)
            return {}
        return {"phys": phys, "log": log}

    @staticmethod
    def _counts() -> tuple[int | None, int | None]:
        return psutil.cpu_count(logical=False), psutil.cpu_count()
```

- [ ] **Step 5: Run model tests — expect PASS.**

Run: `uv run pytest tests/test_plugin_core_v5.py -v`
Expected: PASS.

- [ ] **Step 6: Commit.**

```bash
git add glances/plugins/core/model_v5.py tests/test_plugin_core_v5.py
git commit -m "feat(v5): G1 — port core plugin to v5 (phys/log counts, REST-only)"
```

---

## Task 8: `version` + `psutilversion` plugins (REST-only)

**Files:**
- Create: `glances/plugins/version/model_v5.py`, `glances/plugins/psutilversion/model_v5.py`
- Test: `tests/test_plugin_version_v5.py`

**v4 reference:** `glances/plugins/version/__init__.py` stores `glances.__version__`; `glances/plugins/psutilversion/__init__.py` stores `'.'.join(map(str, glances.psutil_version_info))`. Neither has `msg_curse` → both `DISPLAY_IN_TUI=False`. (`from glances import __version__, psutil_version_info` is confirmed working.)

- [ ] **Step 1: Read** both v4 sources.

- [ ] **Step 2: Write the failing model tests.** Create `tests/test_plugin_version_v5.py`:

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the version + psutilversion plugins (REST-only)."""

from __future__ import annotations

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.psutilversion.model_v5 import PluginModel as PsutilVersionPlugin
from glances.plugins.version.model_v5 import PluginModel as VersionPlugin
from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfigV5()


def test_version_identity(store, config):
    plugin = VersionPlugin(store, config)
    assert plugin.plugin_name == "version"
    assert plugin.DISPLAY_IN_TUI is False


def test_psutilversion_identity(store, config):
    plugin = PsutilVersionPlugin(store, config)
    assert plugin.plugin_name == "psutilversion"
    assert plugin.DISPLAY_IN_TUI is False


async def test_version_reports_glances_version(store, config):
    from glances import __version__

    plugin = VersionPlugin(store, config)
    await plugin.update()
    assert store.get("version")["version"] == __version__


async def test_psutilversion_reports_dotted_psutil_version(store, config):
    from glances import psutil_version_info

    plugin = PsutilVersionPlugin(store, config)
    await plugin.update()
    expected = ".".join(str(i) for i in psutil_version_info)
    assert store.get("psutilversion")["version"] == expected
```

- [ ] **Step 3: Run — expect FAIL.**

Run: `uv run pytest tests/test_plugin_version_v5.py -v`
Expected: FAIL.

- [ ] **Step 4: Implement both models.**

Create `glances/plugins/version/model_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — version plugin (Glances version string, REST-only).

Migrated from `glances/plugins/version/__init__.py`. No v4 ``msg_curse`` →
``DISPLAY_IN_TUI=False``. Constant data (changes only on upgrade).
"""

from __future__ import annotations

from typing import Any, ClassVar

from glances import __version__ as _GLANCES_VERSION
from glances.plugins.plugin.base_v5 import GlancesPluginBase


class PluginModel(GlancesPluginBase[dict]):
    """Glances version plugin (scalar, REST-only)."""

    plugin_name: ClassVar[str] = "version"
    IS_COLLECTION: ClassVar[bool] = False
    DISPLAY_IN_TUI: ClassVar[bool] = False

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "version": {"description": "Glances version.", "unit": "string"},
    }

    async def _grab_stats(self) -> dict:
        return {"version": _GLANCES_VERSION}
```

Create `glances/plugins/psutilversion/model_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — psutilversion plugin (psutil version string, REST-only).

Migrated from `glances/plugins/psutilversion/__init__.py`. No v4
``msg_curse`` → ``DISPLAY_IN_TUI=False``. Constant data.
"""

from __future__ import annotations

from typing import Any, ClassVar

from glances import psutil_version_info as _PSUTIL_VERSION_INFO
from glances.plugins.plugin.base_v5 import GlancesPluginBase


class PluginModel(GlancesPluginBase[dict]):
    """psutil version plugin (scalar, REST-only)."""

    plugin_name: ClassVar[str] = "psutilversion"
    IS_COLLECTION: ClassVar[bool] = False
    DISPLAY_IN_TUI: ClassVar[bool] = False

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "version": {"description": "psutil version.", "unit": "string"},
    }

    async def _grab_stats(self) -> dict:
        return {"version": ".".join(str(i) for i in _PSUTIL_VERSION_INFO)}
```

- [ ] **Step 5: Run model tests — expect PASS.**

Run: `uv run pytest tests/test_plugin_version_v5.py -v`
Expected: PASS.

- [ ] **Step 6: Commit.**

```bash
git add glances/plugins/version/model_v5.py glances/plugins/psutilversion/model_v5.py \
        tests/test_plugin_version_v5.py
git commit -m "feat(v5): G1 — port version + psutilversion plugins to v5 (REST-only)"
```

---

## Task 9: integration sweep + catalogue footer

**Files:**
- Modify: `docs/architecture/tui-v4-rendering-patterns.md` (mark migrated plugins)
- (No `NEWS.rst` — see hard rules.)

- [ ] **Step 1: Full v5 suite.**

Run: `make test-v5`
Expected: PASS (all green).

- [ ] **Step 2: v4 non-regression.** The v4 plugin files are untouched; confirm v4 tests still pass.

Run: `make test`
Expected: PASS. (If `make test` is too broad/slow, at minimum run the v4 plugin tests: `uv run pytest tests/test_plugin_*.py -k "not v5"`.)

- [ ] **Step 3: Lint + format.**

Run: `make lint && make format`
Expected: clean (no diffs after format; no lint errors).

- [ ] **Step 4: Integration assertion — registry shape.** Add to `tests/test_main_v5.py`:

```python
def test_assemble_tui_registry_shows_displayables_hides_rest_only(config):
    """End-to-end: the real discovered plugins route correctly.

    Displayed trivials (uptime/system/now) appear in the TUI registry;
    REST-only trivials (core/version/psutilversion) do not. cpu/mem stay
    displayed. All six are still discovered (served via REST)."""
    from glances.main_v5 import discover_plugins

    store = StatsStoreV5()
    all_names = {p.plugin_name for p in discover_plugins(store, config)}
    for name in ("uptime", "system", "now", "core", "version", "psutilversion"):
        assert name in all_names, f"{name} not discovered"

    args = build_parser().parse_args([])  # TUI mode
    _app, _scheduler, _host, _port, tui = assemble(args, config)
    registry_names = {name for name, _ in tui.registry}
    # Displayed.
    for name in ("uptime", "system", "now"):
        assert name in registry_names
    # REST-only — excluded from the TUI registry.
    for name in ("core", "version", "psutilversion"):
        assert name not in registry_names
```

Run: `uv run pytest tests/test_main_v5.py -k tui_registry_shows -v`
Expected: PASS.

- [ ] **Step 5: Smoke render (manual, operational).** Visually compare v5 against v4 on the same host:

```bash
make run-v5        # v5 TUI — confirm header line: hostname + OS left, Uptime right;
                   # 'now' date in the left sidebar.
glances            # v4 TUI — eyeball parity of the header line + now.
```

Note any visual divergence in the commit body (do **not** edit NEWS.rst).

- [ ] **Step 6: Catalogue footer.** In `docs/architecture/tui-v4-rendering-patterns.md`, under each of the §system, §uptime (and §now if present) sections, append a line:

```markdown
> ✅ v5: `glances/plugins/<name>/render_curses_v5.py` (Phase 2 G1). Header line painted by `glances_curses_v5._paint_header`.
```

(If the catalogue has no §uptime/§now section, add a short one mirroring the existing format — source pointer + one-line layout note. Keep it terse.)

- [ ] **Step 7: Commit.**

```bash
git add docs/architecture/tui-v4-rendering-patterns.md tests/test_main_v5.py
git commit -m "docs(v5): G1 — mark trivials migrated in TUI catalogue + registry integration test"
```

---

## Self-Review (run after all tasks)

1. **Spec coverage (Phase 2 design §4 G1 = uptime, system, core, version, psutilversion, now):** all six have `model_v5.py` (Tasks 4–8). ✅
2. **TUI parity:** uptime + system render in a v4-style header line (Tasks 2–5); now renders left-sidebar padded-23 (Task 6). core/version/psutilversion hidden (v4 `display_curse=False`). ✅
3. **No dead code:** every model is auto-discovered → scheduler + REST; displayed ones are also wired into the TUI via the registry + renderer discovery. ✅
4. **No NEWS.rst edits.** ✅ (hard rule)
5. **No push / no PR.** ✅ (final task ends at local commit + manual smoke)
6. **Type/name consistency:** `DISPLAY_IN_TUI` used identically across base, main, models; `HEADER_SLOT` / `Frame.header` / `_paint_header` consistent across renderer + painter.

## Wrap-up

After all tasks merge locally, update project memory:
- `project_v5_g1_trivials_done.md` — "Phase 2 G1 (trivials) done: uptime/system/now have model_v5 + render_curses_v5; core/version/psutilversion are REST-only (DISPLAY_IN_TUI=False). TUI gained a header slot (system left, uptime right) painted by `_paint_header`."

Next slot per spec §4.2: **G2** — `memswap` (already done) + `quicklook` base (CPU+MEM+load+cores, no GPU). The remaining unported plugins are quicklook, then G4 hardware (sensors/gpu/npu/wifi/ip + SSRF), G6 external integrations, G7 alert.
