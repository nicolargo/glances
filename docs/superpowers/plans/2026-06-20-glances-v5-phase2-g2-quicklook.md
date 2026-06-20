# Glances v5 Phase 2 — G2 quicklook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **PROJECT RULE — never commit.** This repository's maintainer does ALL commits personally. Wherever a step says "Stage", run `git add` ONLY and STOP. Do **not** run `git commit`, `git push`, or add any `Co-Authored-By` trailer. Report what is staged + a suggested commit message.

**Goal:** Port the v4 `quicklook` plugin (CPU + MEM + LOAD bars, per-core view, frequency header, and the full-quicklook full-width mode) to the v5 plugin/TUI contract — **without** the GPU section (deferred to G4A) and **without** sparkline history (deferred until a v5 history store exists).

**Architecture:** A scalar `model_v5.py` re-collects CPU/MEM/SWAP/LOAD + per-core + CPU metadata from the v5-native `cpu_sampler_v5.sampler` and `psutil` (no v4-plugin imports). A pure `render_curses_v5.py` reuses the existing pure `glances.outputs.glances_bars.Bar` to draw text bars into the `Cell` model, reading per-key alert levels from `payload["_levels"]`. The renderer accepts the optional `view` dict to switch between compact, per-cpu, and full-quicklook layouts. Full-quicklook toggling (`4` key) hides the other TOP-slot plugins in `build_frame` and widens the bars.

**Tech Stack:** Python 3 / asyncio, psutil, pytest (+ pytest-asyncio for the async model), the v5 curses renderer (`Cell`/`Row`/`PluginBlock`), `glances/cpu_sampler_v5.py`.

---

## Background — required reading before starting

- **v4 reference (mirror this):** `glances/plugins/quicklook/__init__.py` — `update()`, `update_views()`, `msg_curse()`, `_msg_cpu()`, `_msg_per_cpu()`, `_msg_create_line()`. The TUI MUST mirror v4 (project rule).
- **Bar primitive (reuse as-is):** `glances/outputs/glances_bars.py::Bar` — pure string output, `Bar(size, bar_char='|').percent = X; Bar.get()` → `"||||      45.0%"`.
- **v5 collection source (use this, NOT v4):** `glances/cpu_sampler_v5.py::sampler` — `await sampler.get_aggregate()` (has `.idle`), `await sampler.get_per_core()` (list, each `.idle`), `sampler.cpu_count` (logical cores).
- **Model contract reference:** `glances/plugins/load/model_v5.py`, `glances/plugins/cpu/model_v5.py`.
- **Renderer contract reference:** `glances/plugins/cpu/render_curses_v5.py`, `glances/plugins/percpu/render_curses_v5.py`, `glances/plugins/memswap/render_curses_v5.py`.
- **Renderer internals:** `glances/outputs/curses_renderer_v5.py` — `Cell`, `Row`, `ColorRole`, `_LEVEL_TO_ROLE` (module-level), `title_role()`, `build_frame()` (line ~684, has `view` param + `TOP_SLOT` at line 56), `slot_for()`. `quicklook` is ALREADY in `TOP_SLOT`.
- **TUI thread / key handling:** `glances/outputs/glances_curses_v5.py` — `_handle_key()` (line ~181) and the place where `build_frame(...)` is called with `view=`.
- **CLI args:** `glances/main_v5.py` argparser (lines ~84-150).

### Key contract facts (verified)
- A field with `internal: True, watched: False` is: **excluded** from level computation and the generic renderer, **but still present** in the `payload` passed to a custom `render()`. This is exactly how `percpu`, `cpu_name`, `cpu_hz*` reach the renderer without breaking level computation. (REST is unfiltered — these fields appear in `/api/5/quicklook`, matching v4 which also returns them.)
- A custom `render()` may be declared as `render(payload, fields_desc)` OR `render(payload, fields_desc, view=None)`. The renderer auto-detects the `view` parameter (`_accepts_view`). Use the `view` form for quicklook.
- Renderers are **pure synchronous functions** → their tests need NO pytest-asyncio. The model's `_grab_stats` is async → its tests use `@pytest.mark.asyncio` (asyncio_mode=auto is on, so the bare `async def test_*` form also works — match the neighbouring test files).

### Scope decisions (locked)
- **No GPU** (gpu_mem / gpu_proc) — deferred to G4A.
- **No sparkline** — bars only (= v4 default without history). No history store in v5 yet.
- **No ZFS mem adjustment** — v5 quicklook `mem` is the plain `(total-available)/total` percent. ZFS arc adjustment (v4) is a documented minor divergence; revisit if requested.
- **Full-quicklook IS in scope** (maintainer decision): `4` key toggle, hide other TOP plugins, widen bars.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `glances/plugins/quicklook/model_v5.py` | Scalar model: collect cpu/mem/swap/load + percpu + cpu metadata | Create |
| `glances/plugins/quicklook/render_curses_v5.py` | Pure renderer: bars, per-cpu, freq header, full mode (reads `view`) | Create |
| `glances/outputs/curses_renderer_v5.py` | `build_frame` hides TOP siblings when `view["full_quicklook"]` | Modify (~line 716) |
| `glances/outputs/glances_curses_v5.py` | `4` key toggles full_quicklook; seed `view` with full_quicklook/percpu/quicklook_width | Modify (`_handle_key`, view assembly) |
| `glances/main_v5.py` | `--percpu` and `--full-quicklook` CLI args | Modify (argparser) |
| `tests/test_plugin_quicklook_v5.py` | Model tests | Create |
| `tests/test_plugin_quicklook_render_curses_v5.py` | Renderer tests (compact / per-cpu / freq / full) | Create |
| `tests/test_curses_renderer_v5.py` | `build_frame` sibling-hiding test | Modify (append) |
| `tests/test_curses_v5.py` | `4` key toggle + view seeding test | Modify (append) |
| `docs/architecture/tui-v4-rendering-patterns.md` | Add quicklook section | Modify |

---

## Task 1: quicklook model_v5.py — collection

**Files:**
- Create: `glances/plugins/quicklook/model_v5.py`
- Test: `tests/test_plugin_quicklook_v5.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_plugin_quicklook_v5.py`:

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the v5 quicklook plugin model."""

from __future__ import annotations

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.quicklook.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    # v5 idiom (mirrors tests/test_plugin_load_v5.py): real config object
    # with the system config path redirected to an empty tmp file.
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    return GlancesConfigV5()


def test_plugin_identity(store, config):
    p = PluginModel(store, config)
    assert p.plugin_name == "quicklook"
    assert p.IS_COLLECTION is False


def test_fields_description_keys():
    fd = PluginModel.fields_description
    for key in ("cpu", "mem", "swap", "load"):
        assert fd[key]["unit"] == "percent"
        assert fd[key].get("watched") is True
    # Render-support fields are internal + not watched (never level-computed).
    for key in ("percpu", "cpu_name", "cpu_hz", "cpu_hz_current", "cpu_log_core", "cpu_phys_core"):
        assert fd[key].get("internal") is True
        assert fd[key].get("watched", False) is False


@pytest.mark.asyncio
async def test_grab_stats_shape(store, config, monkeypatch):
    """_grab_stats returns the documented scalar shape with a percpu list."""
    p = PluginModel(store, config)

    class _Sample:
        idle = 80.0

    class _FakeSampler:
        cpu_count = 4

        async def get_aggregate(self):
            return _Sample()

        async def get_per_core(self):
            return [_Sample(), _Sample()]

    import glances.plugins.quicklook.model_v5 as mod

    monkeypatch.setattr(mod, "sampler", _FakeSampler())
    monkeypatch.setattr(
        mod,
        "_collect_sync",
        lambda: {
            "mem": 42.0,
            "swap": 10.0,
            "load": 25.0,
            "cpu_log_core": 4,
            "cpu_phys_core": 2,
            "cpu_name": "Test CPU",
            "cpu_hz_current": 2_000_000_000,
            "cpu_hz": 3_000_000_000,
        },
    )

    stats = await p._grab_stats()
    assert stats["cpu"] == 20.0  # 100 - idle(80)
    assert stats["mem"] == 42.0
    assert stats["swap"] == 10.0
    assert stats["load"] == 25.0
    assert isinstance(stats["percpu"], list) and len(stats["percpu"]) == 2
    assert stats["percpu"][0] == {"cpu_number": 0, "total": 20.0}
    assert stats["cpu_name"] == "Test CPU"


@pytest.mark.asyncio
async def test_grab_stats_survives_sampler_failure(store, config, monkeypatch):
    """A sampler raising OSError yields a partial dict, not an exception."""
    p = PluginModel(store, config)

    class _BoomSampler:
        cpu_count = 1

        async def get_aggregate(self):
            raise OSError("boom")

        async def get_per_core(self):
            raise OSError("boom")

    import glances.plugins.quicklook.model_v5 as mod

    monkeypatch.setattr(mod, "sampler", _BoomSampler())
    monkeypatch.setattr(mod, "_collect_sync", lambda: {})

    stats = await p._grab_stats()
    assert "cpu" not in stats
    assert "percpu" not in stats
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_plugin_quicklook_v5.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glances.plugins.quicklook.model_v5'`.

- [ ] **Step 3: Write minimal implementation**

Create `glances/plugins/quicklook/model_v5.py`:

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — quicklook plugin (scalar composite).

Migrated from `glances/plugins/quicklook/__init__.py`. Re-collects the
CPU / MEM / SWAP / LOAD percentages plus per-core CPU usage and CPU
metadata (name, frequency, core counts) for the compact "quicklook"
top-of-screen block.

v5 differences vs v4 (see the G2 plan, scope decisions):
- **No GPU** section (deferred to G4A with the gpu plugin).
- **No sparkline** (no v5 history store yet) — bars only.
- **No ZFS** arc adjustment on `mem` — plain (total-available)/total.

Collection uses the v5-native shared sampler (`glances/cpu_sampler_v5.py`)
for CPU aggregate + per-core, exactly like the `cpu`/`percpu` plugins —
NO import from any v4 plugin module.

`percpu`, `cpu_name`, `cpu_hz*` and the core counts are declared
`internal: True, watched: False`: kept out of level computation and the
generic renderer, but still delivered in the payload to the custom
`render_curses_v5.render()`.
"""

from __future__ import annotations

import asyncio
import platform
from typing import Any, ClassVar

import psutil

from glances.cpu_sampler_v5 import sampler
from glances.plugins.plugin.base_v5 import GlancesPluginBase

# Standard Glances percent ladder (matches v4 quicklook cpu/mem/load alerts).
_PERCENT_THRESHOLDS = {"careful": 50.0, "warning": 70.0, "critical": 90.0}


def _cpu_name() -> str:
    """Best-effort human CPU name.

    Linux: first `model name` line of /proc/cpuinfo. Other OSes (or Snap
    confinement blocking the open): fall back to `platform.processor()`.
    The `open()` is inside try/except for Snap strict confinement.
    """
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except (OSError, IndexError):
        pass
    return platform.processor() or "CPU"


def _collect_sync() -> dict[str, Any]:
    """Synchronous psutil collection (runs in a worker thread).

    Each metric is independently guarded so one failing call never drops
    the others.
    """
    out: dict[str, Any] = {}

    try:
        vm = psutil.virtual_memory()
        if vm.total:
            out["mem"] = round((vm.total - vm.available) / vm.total * 100.0, 1)
    except (OSError, RuntimeError, AttributeError):
        pass

    try:
        out["swap"] = psutil.swap_memory().percent
    except (OSError, RuntimeError):
        # Illumos raises RuntimeError (v4 #1767).
        pass

    try:
        log_core = psutil.cpu_count(logical=True) or 1
        out["cpu_log_core"] = log_core
        load15 = psutil.getloadavg()[2]
        out["load"] = round(load15 / log_core * 100.0, 1)
    except (AttributeError, OSError, IndexError, ZeroDivisionError):
        pass

    try:
        out["cpu_phys_core"] = psutil.cpu_count(logical=False)
    except (OSError, RuntimeError):
        pass

    try:
        freq = psutil.cpu_freq()
        if freq is not None:
            if freq.current:
                out["cpu_hz_current"] = int(freq.current * 1_000_000)
            if freq.max:
                out["cpu_hz"] = int(freq.max * 1_000_000)
    except (OSError, RuntimeError, AttributeError, NotImplementedError):
        pass

    out["cpu_name"] = _cpu_name()
    return out


class PluginModel(GlancesPluginBase[dict]):
    """Quicklook plugin (scalar composite)."""

    plugin_name: ClassVar[str] = "quicklook"
    IS_COLLECTION: ClassVar[bool] = False

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "cpu": {
            "description": "CPU percent usage.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": True,
            "default_thresholds": _PERCENT_THRESHOLDS,
        },
        "mem": {
            "description": "MEM percent usage.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": True,
            "default_thresholds": _PERCENT_THRESHOLDS,
        },
        "swap": {
            "description": "SWAP percent usage.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "default_thresholds": _PERCENT_THRESHOLDS,
        },
        "load": {
            "description": "LOAD percent usage (15 min, normalized by core count).",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": True,
            "default_thresholds": _PERCENT_THRESHOLDS,
        },
        "percpu": {
            "description": "Per-core CPU usage (list of {cpu_number, total}).",
            "unit": "percent",
            "internal": True,
            "watched": False,
        },
        "cpu_log_core": {
            "description": "Number of logical CPU cores.",
            "unit": "number",
            "internal": True,
            "watched": False,
        },
        "cpu_phys_core": {
            "description": "Number of physical CPU cores.",
            "unit": "number",
            "internal": True,
            "watched": False,
        },
        "cpu_name": {
            "description": "CPU name.",
            "unit": "string",
            "internal": True,
            "watched": False,
        },
        "cpu_hz_current": {
            "description": "CPU current frequency (Hz).",
            "unit": "hertz",
            "internal": True,
            "watched": False,
        },
        "cpu_hz": {
            "description": "CPU max frequency (Hz).",
            "unit": "hertz",
            "internal": True,
            "watched": False,
        },
    }

    async def _grab_stats(self) -> dict:
        out: dict[str, Any] = {}

        try:
            agg = await sampler.get_aggregate()
            out["cpu"] = round(100.0 - float(agg.idle), 1)
        except (OSError, RuntimeError, AttributeError):
            pass

        try:
            cores = await sampler.get_per_core()
            out["percpu"] = [
                {"cpu_number": i, "total": round(100.0 - float(c.idle), 1)} for i, c in enumerate(cores)
            ]
        except (OSError, RuntimeError, AttributeError):
            pass

        out.update(await asyncio.to_thread(_collect_sync))
        return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_plugin_quicklook_v5.py -v`
Expected: PASS (4 tests).

Note: the test monkeypatches `mod._collect_sync` and `mod.sampler`. Because `_grab_stats` references the module-global `sampler` and calls the module-global `_collect_sync` (not `self._collect_sync`), keep both at module level exactly as written.

- [ ] **Step 5: Verify auto-discovery + lint**

Run: `python -c "from glances.main_v5 import discover_plugins" 2>/dev/null; python -m pytest tests/test_plugin_quicklook_v5.py -q && make lint`
Expected: tests pass, lint clean.

- [ ] **Step 6: Stage (do NOT commit)**

```bash
git add glances/plugins/quicklook/model_v5.py tests/test_plugin_quicklook_v5.py
```
Suggested message (for the maintainer): `feat(v5): add quicklook plugin model (G2, no GPU/sparkline)`.

---

## Task 2: quicklook render_curses_v5.py — compact bars (CPU/MEM/LOAD)

**Files:**
- Create: `glances/plugins/quicklook/render_curses_v5.py`
- Test: `tests/test_plugin_quicklook_render_curses_v5.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_plugin_quicklook_render_curses_v5.py`:

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the v5 quicklook curses renderer."""

from __future__ import annotations

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.quicklook.render_curses_v5 import render

FIELDS = {
    "cpu": {"unit": "percent"},
    "mem": {"unit": "percent"},
    "load": {"unit": "percent"},
}


def _text(row):
    return "".join(c.text for c in row.cells)


def _payload(**over):
    base = {
        "cpu": 20.0,
        "mem": 42.0,
        "swap": 10.0,
        "load": 25.0,
        "_levels": {
            "cpu": {"level": "ok", "prominent": True},
            "mem": {"level": "ok", "prominent": True},
            "load": {"level": "ok", "prominent": True},
        },
    }
    base.update(over)
    return base


def test_empty_payload_returns_title_only():
    rows = render({}, FIELDS)
    assert len(rows) == 1
    assert "CPU" in _text(rows[0])


def test_compact_has_cpu_mem_load_rows():
    rows = render(_payload(), FIELDS)
    text = "\n".join(_text(r) for r in rows)
    assert "CPU" in text
    assert "MEM" in text
    assert "LOAD" in text
    # The percent value is rendered by the Bar (e.g. "20.0%").
    assert "20.0%" in text
    assert "42.0%" in text


def test_bar_brackets_present():
    rows = render(_payload(), FIELDS)
    text = "\n".join(_text(r) for r in rows)
    assert "[" in text and "]" in text


def test_level_colors_value_cell():
    rows = render(
        _payload(_levels={"cpu": {"level": "critical", "prominent": True}}),
        FIELDS,
    )
    # The CPU bar cell carries the CRITICAL role.
    crit = [c for r in rows for c in r.cells if c.color == ColorRole.CRITICAL]
    assert crit, "expected at least one CRITICAL-coloured cell for cpu"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_plugin_quicklook_render_curses_v5.py -v`
Expected: FAIL — `ModuleNotFoundError: ... render_curses_v5`.

- [ ] **Step 3: Write minimal implementation**

Create `glances/plugins/quicklook/render_curses_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the quicklook plugin.

Mirrors v4 `quicklook.msg_curse()` (bars for CPU / MEM / LOAD, optional
per-core CPU view, and an optional CPU name/frequency header), minus the
GPU section and the sparkline history path (see the G2 plan).

The horizontal bar is drawn by reusing the pure v4 `Bar` helper
(`glances.outputs.glances_bars.Bar`) — it returns a plain string such as
``"||||||         45.0%"`` which becomes the text of a single `Cell`,
coloured by the field's alert level from ``payload["_levels"]``.

`render()` accepts the optional `view` dict (auto-detected by the
renderer). Recognised keys:
- ``view["percpu"]``         -> bool: replace the CPU bar with per-core bars
- ``view["full_quicklook"]`` -> bool: full-width mode (wider bars)
- ``view["quicklook_width"]``-> int : target bar cell width
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import Cell, ColorRole, Row, _LEVEL_TO_ROLE
from glances.outputs.glances_bars import Bar

# Default total width of a bar cell when the TUI does not pass one in
# `view` (e.g. unit tests, or the very first cycle). v4 capped the
# quicklook column at 48 — keep the inner bar comfortably under that.
_DEFAULT_BAR_WIDTH = 38

# Stats shown as bars, in v4 order. (GPU intentionally excluded in G2.)
_BAR_KEYS = ("cpu", "mem", "load")

# Per-core: top-N shown, the rest collapsed into a "CPU*" mean row (v4).
# TODO(G2+): read [percpu] max_cpu_display from config (v4 __init__.py:108);
# plumb via `view` once the TUI passes it.
_DEFAULT_MAX_CPU_DISPLAY = 4


def _role_for(payload: dict[str, Any], key: str) -> ColorRole:
    """Map the field's alert level (from `_levels`) to a colour role."""
    level = payload.get("_levels", {}).get(key, {}).get("level")
    return _LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT)


def _bar_width(view: dict[str, Any] | None) -> int:
    if view and isinstance(view.get("quicklook_width"), int) and view["quicklook_width"] > 12:
        return view["quicklook_width"]
    return _DEFAULT_BAR_WIDTH


def _bar_cells(label: str, percent: Any, role: ColorRole, width: int) -> list[Cell]:
    """`LABEL [||||      45.0%]` as label + bracket + bar + bracket cells."""
    bar = Bar(width, bar_char="|")
    try:
        bar.percent = float(percent)
    except (TypeError, ValueError):
        bar.percent = 0.0
    return [
        Cell(text=f"{label:<4} "),
        # glue: the painter inserts a space before every non-glue cell; the
        # bracketed bar must paint flush ("CPU  [||||45.0%]") for v4 parity.
        Cell(text="[", bold=True, glue=True),
        Cell(text=bar.get(), color=role, glue=True),
        Cell(text="]", bold=True, glue=True),
    ]


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]], view: dict[str, Any] | None = None) -> list[Row]:
    """Render the quicklook plugin's TUI block — mirrors v4 `quicklook.msg_curse`."""
    if not payload:
        return [Row(cells=[Cell(text="CPU", color=ColorRole.HEADER, bold=True)])]

    width = _bar_width(view)
    rows: list[Row] = []

    for key in _BAR_KEYS:
        if key == "cpu" and view and view.get("percpu") and isinstance(payload.get("percpu"), list):
            rows.extend(_per_cpu_rows(payload, width))
            continue
        if key not in payload or payload.get(key) is None:
            continue
        rows.append(Row(cells=_bar_cells(key.upper(), payload[key], _role_for(payload, key), width)))

    return rows or [Row(cells=[Cell(text="CPU", color=ColorRole.HEADER, bold=True)])]


def _per_cpu_rows(payload: dict[str, Any], width: int) -> list[Row]:
    """Top-N per-core bars + a CPU* mean row (v4 `_msg_per_cpu`)."""
    cores = [c for c in payload.get("percpu", []) if isinstance(c, dict)]
    rows: list[Row] = []
    if not cores:
        return rows

    if len(cores) > _DEFAULT_MAX_CPU_DISPLAY:
        ordered = sorted(cores, key=lambda c: float(c.get("total") or 0.0), reverse=True)
    else:
        ordered = cores

    displayed = ordered[:_DEFAULT_MAX_CPU_DISPLAY]
    role = _role_for(payload, "cpu")
    for core in displayed:
        cid = core.get("cpu_number", 0)
        label = f"CPU{cid}" if isinstance(cid, int) and cid < 10 else f"{cid:>4}"
        rows.append(Row(cells=_bar_cells(label, core.get("total"), role, width)))

    overflow = ordered[_DEFAULT_MAX_CPU_DISPLAY:]
    if overflow:
        # v4 Bar-path parity (glances/plugins/quicklook/__init__.py:322-324):
        # the "CPU*" row averages the HIDDEN (overflow) cores, not the displayed ones.
        vals = [float(c.get("total") or 0.0) for c in overflow]
        mean = sum(vals) / len(vals)
        rows.append(Row(cells=_bar_cells("CPU*", mean, role, width)))

    return rows
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_plugin_quicklook_render_curses_v5.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Stage (do NOT commit)**

```bash
git add glances/plugins/quicklook/render_curses_v5.py tests/test_plugin_quicklook_render_curses_v5.py
```
Suggested message: `feat(v5): quicklook curses renderer — compact CPU/MEM/LOAD bars (G2)`.

---

## Task 3: frequency / CPU-name header line

**Files:**
- Modify: `glances/plugins/quicklook/render_curses_v5.py`
- Test: `tests/test_plugin_quicklook_render_curses_v5.py` (append)

- [ ] **Step 1: Write the failing test (append to the render test file)**

```python
def test_header_shows_name_and_frequency():
    p = _payload(cpu_name="Test CPU", cpu_hz_current=2_000_000_000, cpu_hz=3_000_000_000)
    rows = render(p, FIELDS)
    head = _text(rows[0])
    assert "Test CPU" in head
    assert "2.00" in head and "3.00" in head and "GHz" in head


def test_header_absent_when_no_freq():
    rows = render(_payload(), FIELDS)
    # First row is a bar row (CPU), not a frequency header.
    assert "GHz" not in _text(rows[0])
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_plugin_quicklook_render_curses_v5.py -k header -v`
Expected: FAIL — no header row produced yet.

- [ ] **Step 3: Implement — add a header builder and prepend it**

In `render_curses_v5.py`, add this helper above `render()`:

```python
def _hz_to_ghz(hz: Any) -> float:
    return float(hz) / 1_000_000_000.0


def _header_row(payload: dict[str, Any]) -> Row | None:
    """CPU name + frequency line (v4 `msg_curse` lines 211-228).

    Shown only when a current frequency is available. Mirrors v4:
    ``<name> <cur>/<max>GHz`` (or just ``<cur>GHz`` when max is unknown).
    """
    cur = payload.get("cpu_hz_current")
    if cur is None:
        return None
    mx = payload.get("cpu_hz")
    if mx is not None:
        freq = f" {_hz_to_ghz(cur):.2f}/{_hz_to_ghz(mx):.2f}GHz"
    else:
        freq = f" {_hz_to_ghz(cur):.2f}GHz"
    name = payload.get("cpu_name") or "Frequency"
    return Row(cells=[Cell(text=name, color=ColorRole.HEADER), Cell(text=freq)])
```

Then, in `render()`, right after `rows: list[Row] = []`, prepend the header:

```python
    header = _header_row(payload)
    if header is not None:
        rows.append(header)
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_plugin_quicklook_render_curses_v5.py -v`
Expected: PASS (all). Note: `test_compact_has_cpu_mem_load_rows` still passes because it joins ALL rows.

- [ ] **Step 5: Stage (do NOT commit)**

```bash
git add glances/plugins/quicklook/render_curses_v5.py tests/test_plugin_quicklook_render_curses_v5.py
```
Suggested message: `feat(v5): quicklook frequency/name header (G2)`.

---

## Task 4: per-CPU view via `view["percpu"]`

The renderer already branches on `view.get("percpu")` (Task 2). This task locks the behaviour with explicit tests for top-N + `CPU*`.

**Files:**
- Test: `tests/test_plugin_quicklook_render_curses_v5.py` (append)

- [ ] **Step 1: Write the failing/locking tests**

```python
def _percpu_payload(n):
    cores = [{"cpu_number": i, "total": float(i * 7 % 100)} for i in range(n)]
    return _payload(percpu=cores)


def test_percpu_view_shows_per_core_bars():
    rows = render(_percpu_payload(2), FIELDS, view={"percpu": True})
    text = "\n".join(_text(r) for r in rows)
    assert "CPU0" in text and "CPU1" in text
    assert "MEM" in text and "LOAD" in text  # other bars still present


def test_percpu_view_caps_and_adds_star_row():
    rows = render(_percpu_payload(8), FIELDS, view={"percpu": True})
    text = "\n".join(_text(r) for r in rows)
    # Max 4 cores shown + a CPU* mean row (payload carries no freq header).
    assert "CPU*" in text
    assert text.count("CPU") == 5  # 4 cores + CPU*


def test_percpu_star_row_averages_overflow_cores():
    # totals = i*7 for i in 0..7 -> [0,7,14,21,28,35,42,49]; top-4 displayed,
    # overflow = [21,14,7,0] -> mean 10.5 (v4 Bar-path parity).
    rows = render(_percpu_payload(8), FIELDS, view={"percpu": True})
    star = [r for r in rows if "CPU*" in _text(r)]
    assert len(star) == 1
    assert "10.5%" in _text(star[0])


def test_no_percpu_view_shows_single_cpu_bar():
    rows = render(_percpu_payload(8), FIELDS)  # no view → compact
    text = "\n".join(_text(r) for r in rows)
    assert "CPU0" not in text
    assert "CPU " in text  # single aggregate CPU bar
```

- [ ] **Step 2: Run**

Run: `python -m pytest tests/test_plugin_quicklook_render_curses_v5.py -k percpu -v`
Expected: PASS (behaviour already implemented in Task 2). If any fail, fix `_per_cpu_rows` / the `render()` cpu branch — do NOT change the tests.

- [ ] **Step 3: Stage (do NOT commit)**

```bash
git add tests/test_plugin_quicklook_render_curses_v5.py
```
Suggested message: `test(v5): lock quicklook per-cpu top-N + CPU* behaviour (G2)`.

---

## Task 5: full-quicklook mode (`4` key, hide siblings, widen bars)

Three coordinated changes: CLI args (5a), `build_frame` sibling hiding (5b), TUI key toggle + view seeding (5c).

### Task 5a: CLI args `--percpu` and `--full-quicklook`

**Files:**
- Modify: `glances/main_v5.py` (argparser block, ~lines 84-150)
- Test: `tests/test_main_v5.py` (append)

- [ ] **Step 1: Write the failing test (append to `tests/test_main_v5.py`)**

```python
def test_quicklook_cli_flags_default_false():
    from glances.main_v5 import build_parser  # adjust to the real factory name

    args = build_parser().parse_args([])
    assert args.percpu is False
    assert args.full_quicklook is False


def test_quicklook_cli_flags_can_be_enabled():
    from glances.main_v5 import build_parser

    args = build_parser().parse_args(["--percpu", "--full-quicklook"])
    assert args.percpu is True
    assert args.full_quicklook is True
```

> NOTE FOR IMPLEMENTER: open `glances/main_v5.py` and find the actual parser-construction function/name. If the parser is built inline (not in a `build_parser()` factory), either (a) adapt the test to call the real entry point, or (b) extract a `build_parser()` factory first (preferred — makes args testable). Keep the change minimal.

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_main_v5.py -k quicklook_cli -v`
Expected: FAIL — unknown arguments / attribute missing.

- [ ] **Step 3: Implement — add the two args**

In `glances/main_v5.py`, alongside the other `parser.add_argument(...)` calls:

```python
    parser.add_argument(
        "--percpu",
        action="store_true",
        default=False,
        dest="percpu",
        help="Start TUI with the per-CPU view in quicklook.",
    )
    parser.add_argument(
        "--full-quicklook",
        action="store_true",
        default=False,
        dest="full_quicklook",
        help="Start TUI with the full-width quicklook (hides cpu/mem/... top blocks).",
    )
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_main_v5.py -k quicklook_cli -v`
Expected: PASS.

- [ ] **Step 5: Stage (do NOT commit)**

```bash
git add glances/main_v5.py tests/test_main_v5.py
```
Suggested message: `feat(v5): add --percpu and --full-quicklook CLI flags (G2)`.

### Task 5b: `build_frame` hides TOP siblings in full-quicklook

**Files:**
- Modify: `glances/outputs/curses_renderer_v5.py` (`build_frame`, the registry loop ~line 716)
- Test: `tests/test_curses_renderer_v5.py` (append)

- [ ] **Step 1: Write the failing test (append to `tests/test_curses_renderer_v5.py`)**

```python
def test_full_quicklook_hides_top_siblings():
    from glances.outputs.curses_renderer_v5 import build_frame

    registry = [("quicklook", False), ("cpu", False), ("mem", False), ("network", True)]
    store = {
        "quicklook": {"cpu": 10.0, "_levels": {}},
        "cpu": {"total": 10.0, "_levels": {}},
        "mem": {"percent": 20.0, "_levels": {}},
        "network": {"data": []},
    }
    fields = {k: {} for k in store}

    frame = build_frame(store, fields, registry, [], view={"full_quicklook": True})
    # NOTE: PluginBlock's field is `name` (not `plugin_name`).
    top_names = [b.name for b in frame.top]
    assert "quicklook" in top_names
    assert "cpu" not in top_names
    assert "mem" not in top_names
    # Non-top plugins are unaffected.
    assert any(b.name == "network" for b in frame.left)


def test_no_full_quicklook_keeps_all_top():
    from glances.outputs.curses_renderer_v5 import build_frame

    registry = [("quicklook", False), ("cpu", False), ("mem", False)]
    store = {
        "quicklook": {"cpu": 10.0, "_levels": {}},
        "cpu": {"total": 10.0, "_levels": {}},
        "mem": {"percent": 20.0, "_levels": {}},
    }
    fields = {k: {} for k in store}
    frame = build_frame(store, fields, registry, [], view=None)
    top_names = [b.name for b in frame.top]
    assert {"quicklook", "cpu", "mem"} <= set(top_names)
```

> NOTE: confirm `PluginBlock` exposes `.plugin_name` (it is constructed in `build_frame`). If the attribute name differs, adapt the assertions to the real field.

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_curses_renderer_v5.py -k full_quicklook -v`
Expected: FAIL — siblings still in `frame.top`.

- [ ] **Step 3: Implement — skip hidden siblings**

Near the top of `glances/outputs/curses_renderer_v5.py` (with the other slot constants ~line 56), add:

```python
# In full-quicklook mode these TOP-slot plugins are hidden so quicklook
# takes the full width. EXACT v4 parity: `enable_fullquicklook`
# (glances/outputs/glances_curses.py:455) disables cpu/npu/mpp/gpu/mem/memswap
# only — `load` and `percpu` stay visible.
_FULL_QUICKLOOK_HIDDEN: frozenset[str] = frozenset(
    {"cpu", "npu", "mpp", "gpu", "mem", "memswap"}
)
```

Inside `build_frame`, at the very start of the `for plugin_name, is_collection in registry:` loop body, add:

```python
        if view and view.get("full_quicklook") and plugin_name in _FULL_QUICKLOOK_HIDDEN:
            continue
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_curses_renderer_v5.py -k full_quicklook -v`
Expected: PASS. Then run the whole renderer suite: `python -m pytest tests/test_curses_renderer_v5.py -q`.

- [ ] **Step 5: Stage (do NOT commit)**

```bash
git add glances/outputs/curses_renderer_v5.py tests/test_curses_renderer_v5.py
```
Suggested message: `feat(v5): hide TOP siblings in full-quicklook mode (G2)`.

### Task 5c: TUI `4` key toggle + view seeding

**Files:**
- Modify: `glances/outputs/glances_curses_v5.py` (`__init__` state, `_handle_key`, the `build_frame(..., view=...)` call site)
- Test: `tests/test_curses_v5.py` (append)

- [ ] **Step 1: Read the call site first**

Run: `grep -n "build_frame\|_handle_key\|self.args\|def __init__\|view" glances/outputs/glances_curses_v5.py | head -40`
Identify: (a) where `view` is currently built and passed to `build_frame`, (b) the `_handle_key` dispatch table, (c) whether `self.args` is stored.

- [ ] **Step 2: Write the failing test (append to `tests/test_curses_v5.py`)**

Match the existing construction pattern in that file (how other tests instantiate `TuiV5` / call `_handle_key`). Skeleton:

```python
def test_key_4_toggles_full_quicklook(make_tui):  # reuse the file's existing fixture/helper
    tui = make_tui()
    assert tui._full_quicklook is False
    tui._handle_key(ord("4"))
    assert tui._full_quicklook is True
    tui._handle_key(ord("4"))
    assert tui._full_quicklook is False


def test_view_carries_quicklook_flags(make_tui):
    tui = make_tui()
    tui._full_quicklook = True
    tui._percpu = True
    view = tui._build_view(max_x=120)  # adjust to the real view-builder name
    assert view["full_quicklook"] is True
    assert view["percpu"] is True
    assert isinstance(view["quicklook_width"], int)
```

> NOTE: `tests/test_curses_v5.py` already exists and constructs `TuiV5`. Reuse its existing fixture/helper rather than inventing `make_tui`. If view assembly is currently inline inside the paint loop, extract a small `_build_view(self, max_x)` method (preferred — testable) OR adapt the test to assert via the existing seam. Keep `1` key (help) and existing keys working.

- [ ] **Step 3: Run to verify failure**

Run: `python -m pytest tests/test_curses_v5.py -k quicklook -v`
Expected: FAIL — `_full_quicklook` attr / `_build_view` missing.

- [ ] **Step 4: Implement**

In `TuiV5.__init__`, seed state from args (so `--percpu`/`--full-quicklook` start active):

```python
        self._full_quicklook = bool(getattr(self.args, "full_quicklook", False))
        self._percpu = bool(getattr(self.args, "percpu", False))
```

In `_handle_key`, add a branch for `4` (mirror v4 `_handle_quicklook`):

```python
        if key == ord("4"):
            self._full_quicklook = not self._full_quicklook
            return "repaint"  # match the file's existing return convention
```

Add / extend the view builder used by the paint loop:

```python
    def _build_view(self, max_x: int) -> dict:
        """Assemble the per-cycle `view` dict passed to build_frame."""
        view = {
            "full_quicklook": self._full_quicklook,
            "percpu": self._percpu,
        }
        # Full mode: bars span (almost) the whole width; compact: a column.
        view["quicklook_width"] = max(20, max_x - 8) if self._full_quicklook else 38
        return view
```

Then make the `build_frame(...)` call pass `view=self._build_view(max_x)`. If a `view` dict is already assembled there, merge these keys into it instead of replacing.

- [ ] **Step 5: Run to verify pass**

Run: `python -m pytest tests/test_curses_v5.py -v`
Expected: PASS (new + existing).

- [ ] **Step 6: Full suite + lint**

Run: `python -m pytest tests/test_plugin_quicklook_v5.py tests/test_plugin_quicklook_render_curses_v5.py tests/test_curses_renderer_v5.py tests/test_curses_v5.py tests/test_main_v5.py -q && make lint && make format`
Expected: all pass, lint/format clean.

- [ ] **Step 7: Stage (do NOT commit)**

```bash
git add glances/outputs/glances_curses_v5.py tests/test_curses_v5.py
```
Suggested message: `feat(v5): wire 4-key full-quicklook toggle + view seeding (G2)`.

---

### Task 5d: wire the CLI flags into TuiV5 (no dead code)

Discovered during 5c: `TuiV5.__init__` has no `args` param, so the 5a flags were parsed but never consumed (forbidden dead code). Wiring:
- `TuiV5.__init__` gains `full_quicklook: bool = False, percpu: bool = False` params; `self._full_quicklook`/`self._percpu` seed from them (replacing the always-None `getattr(self, "args", None)` hack).
- `main_v5.assemble()` passes `full_quicklook=getattr(args, "full_quicklook", False)` and `percpu=getattr(args, "percpu", False)` at the `_TuiV5(...)` construction.
- Test in `tests/test_curses_v5.py`: `TuiV5(..., full_quicklook=True, percpu=True)` seeds both True; default → both False.

Also note (5c reality vs plan skeleton): the `4` key is registered in the data-driven `_HOTKEYS` table (auto-documented in the help overlay), and its `_handle_key` branch returns `"changed"` (not `"repaint"` — that string is the help-overlay path in this file).

## Task 6: documentation + memory

**Files:**
- Modify: `docs/architecture/tui-v4-rendering-patterns.md`
- (Do NOT touch `NEWS.rst` — project rule.)

- [ ] **Step 1: Add a quicklook section to the patterns doc**

Append a `## quicklook` section documenting: bars reuse `glances_bars.Bar`; `internal:True` fields (percpu/cpu_name/cpu_hz) reach the custom renderer; the `view` keys (`percpu`, `full_quicklook`, `quicklook_width`); the full-quicklook sibling-hiding in `build_frame`; and the explicit scope cuts (no GPU, no sparkline, no ZFS).

- [ ] **Step 2: Verify the doc references match the code**

Run: `grep -n "quicklook" docs/architecture/tui-v4-rendering-patterns.md`
Expected: the new section is present and names match the shipped symbols.

- [ ] **Step 3: Stage (do NOT commit)**

```bash
git add docs/architecture/tui-v4-rendering-patterns.md
```
Suggested message: `docs(v5): document quicklook TUI rendering pattern (G2)`.

- [ ] **Step 4: Update the project memory (separate from the repo)**

Update `project_v5_g1_trivials_done.md` (or add a `project_v5_g2_quicklook_done.md`) noting: G2 quicklook base shipped (model + renderer + full-quicklook), GPU/sparkline/ZFS deferred. This is a memory file, not a repo file — no git.

---

## Self-Review notes (author)

- **Spec coverage:** G2 = memswap (already done) + quicklook base (CPU+MEM+load+cores, no GPU). Tasks 1-4 cover the base; Task 5 adds full-quicklook (maintainer-requested); GPU explicitly deferred to G4A per spec §4.1.
- **`view` contract consistency:** keys `percpu`, `full_quicklook`, `quicklook_width` are produced in Task 5c (`_build_view`) and consumed in Task 2/4 (`render`) and Task 5b (`build_frame`). Names match across tasks.
- **No v4-plugin imports:** model uses `cpu_sampler_v5.sampler` + `psutil` only (audit rule: no v4 module leaks into v5).
- **Internal-field flow:** percpu/cpu_name/cpu_hz declared `internal:True, watched:False` — verified to reach the custom renderer while skipped by level computation + generic render.
- **Open implementer adaptations (flagged in-task, not placeholders):** the exact `main_v5` parser factory name (5a), `PluginBlock.plugin_name` attribute (5b), and `TuiV5` test fixture + view-builder seam (5c) must be matched to the real code — each task says how to find them.
```

