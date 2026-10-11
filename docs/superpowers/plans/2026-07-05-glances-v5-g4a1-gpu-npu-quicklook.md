# Glances v5 G4A-1: gpu + npu + quicklook GPU addendum + cascade step (g) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the v4 `gpu` and `npu` plugins to v5 (top-row collections reusing the v4 hardware grabbers), add the GPU averages to the v5 quicklook via the stats store, and extend the responsive top-row cascade with a final `hide_gpu` step.

**Architecture:** `gpu`/`npu` are v5 `GlancesPluginBase[list]` collections. Each instantiates the existing v4 card backends (`glances/plugins/gpu/cards/*`, `glances/plugins/npu/cards/*`) once in `__init__`, then collects them each cycle via `asyncio.to_thread`. Custom curses renderers mirror v4 `msg_curse()`. Quicklook reads `self.store.get("gpu")` to compute `gpu_mem`/`gpu_proc` means (no global mutable channel). The cascade gains a measured `hide_gpu` last-resort step.

**Tech Stack:** Python, asyncio, pytest. Reused v4 grabbers (pynvml/sysfs). Curses TUI v5 (`Frame`/`PluginBlock`/`Row`/`Cell`), `glances.outputs.glances_bars.Bar`.

## Global Constraints

- Run tests with `.venv/bin/python -m pytest` (the `python` wrapper hook fails). Lint with `.venv/bin/python -m ruff check` and `.venv/bin/python -m ruff format`.
- v5 plugin constructor is `PluginModel(store, config)` — NOT v4's `config=/args=`.
- Collections: `IS_COLLECTION = True`, `_primary_key` via the `primary_key: True` field flag. `_grab_stats` returns `list[dict]`. Payload delivered to the renderer is `{"data": [...], "_levels": {pk: {field: {"level":..., "prominent":...}}}, ...}`.
- Watched percent fields use `"watched": True, "watch_direction": "high", "default_thresholds": {"careful": .., "warning": .., "critical": ..}`. Non-rendered support fields use `"internal": True` (and `"watched": False` when they must also stay out of level-compute).
- Mirror v4 `msg_curse()` exactly (read it first). Divergent "clean generic" layouts are regressions.
- NEVER commit/push/PR — the `git commit` steps below are written for completeness per the plan format, but in THIS repo the maintainer commits personally: stage only (`git add`) and STOP at the end of each task unless told otherwise. NEVER add a `Co-Authored-By` trailer. NEVER touch `NEWS.rst`.
- No dead code: every field, flag, and branch must be reachable and used.

---

### Task 1: `gpu` plugin model

**Files:**
- Create: `glances/plugins/gpu/model_v5.py`
- Test: `tests/test_plugin_gpu_v5.py`

**Interfaces:**
- Consumes: `GlancesPluginBase` (`glances/plugins/plugin/base_v5.py`), the v4 card classes `NvidiaGPU`, `AmdGPU`, `IntelGPU`, `ArmGPU` (each exposes `get_device_stats() -> list[dict]` and `exit()`).
- Produces: `PluginModel` with `plugin_name="gpu"`, `IS_COLLECTION=True`, primary key `gpu_id`, watched fields `proc`/`mem`/`temperature`. `_grab_stats()` returns `list[dict]` with keys `gpu_id, name, mem, proc, temperature, fan_speed`. Instance attr `self._backends: list` (mutable — tests replace it).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_plugin_gpu_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `gpu` plugin (collection)."""

from __future__ import annotations

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.gpu.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    return GlancesConfigV5()


class _FakeBackend:
    def __init__(self, cards):
        self._cards = cards

    def get_device_stats(self):
        return self._cards

    def exit(self):
        pass


class _BoomBackend:
    def get_device_stats(self):
        raise OSError("no device")

    def exit(self):
        pass


def _card(gpu_id="nvidia0", name="GeForce", mem=40, proc=30, temp=55):
    return {
        "key": "gpu_id",
        "gpu_id": gpu_id,
        "name": name,
        "mem": mem,
        "proc": proc,
        "temperature": temp,
        "fan_speed": 20,
    }


def test_plugin_identity(store, config):
    p = PluginModel(store, config)
    assert p.plugin_name == "gpu"
    assert p.IS_COLLECTION is True
    assert p._primary_key == "gpu_id"


def test_fields_watched_and_internal():
    fd = PluginModel.fields_description
    for key in ("proc", "mem", "temperature"):
        assert fd[key]["watched"] is True
        assert fd[key]["watch_direction"] == "high"
        assert set(fd[key]["default_thresholds"]) == {"careful", "warning", "critical"}
    assert fd["gpu_id"].get("primary_key") is True
    assert fd["name"].get("internal") is True
    assert fd["fan_speed"].get("internal") is True
    assert fd["fan_speed"].get("watched", False) is False


def test_gpu_temperature_thresholds_mirror_v4():
    t = PluginModel.fields_description["temperature"]["default_thresholds"]
    assert t == {"careful": 60.0, "warning": 70.0, "critical": 80.0}


@pytest.mark.asyncio
async def test_grab_stats_concatenates_backends(store, config):
    p = PluginModel(store, config)
    p._backends = [
        _FakeBackend([_card("nvidia0", "A")]),
        _FakeBackend([_card("amd0", "B")]),
    ]
    out = await p._grab_stats()
    assert [c["gpu_id"] for c in out] == ["nvidia0", "amd0"]


@pytest.mark.asyncio
async def test_grab_stats_survives_backend_failure(store, config):
    p = PluginModel(store, config)
    p._backends = [_BoomBackend(), _FakeBackend([_card("amd0", "B")])]
    out = await p._grab_stats()
    assert [c["gpu_id"] for c in out] == ["amd0"]


@pytest.mark.asyncio
async def test_grab_stats_empty_when_no_backend(store, config):
    p = PluginModel(store, config)
    p._backends = []
    assert await p._grab_stats() == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_plugin_gpu_v5.py -q`
Expected: FAIL — `ModuleNotFoundError: glances.plugins.gpu.model_v5`.

- [ ] **Step 3: Write the model**

Create `glances/plugins/gpu/model_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — GPU plugin (collection, per-card).

Migrated from `glances/plugins/gpu/__init__.py`. Reuses the v4 hardware
card backends (`glances/plugins/gpu/cards/{nvidia,amd,intel,arm}.py`) as
pure collectors — each is instantiated once (guarded; a backend whose
init raises is simply left out) and polled every cycle inside
`asyncio.to_thread`. One backend failing never drops the others.

The v4 `__init__.py` side effect of writing GPU means into the global
`glances.gpu_percent` module is intentionally NOT ported — the v5
quicklook reads this plugin's published cards from the stats store
instead (see quicklook/model_v5.py).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

from glances.plugins.plugin.base_v5 import GlancesPluginBase

logger = logging.getLogger(__name__)

_PERCENT_THRESHOLDS = {"careful": 70.0, "warning": 80.0, "critical": 90.0}
# GPU temperature ladder — exact v4 conf/glances.conf [gpu] defaults.
_TEMP_THRESHOLDS = {"careful": 60.0, "warning": 70.0, "critical": 80.0}


def _build_backends() -> list:
    """Instantiate every available v4 GPU card backend, guarded.

    A backend whose constructor raises (driver/library absent) is skipped.
    Import is local so a missing optional dependency (e.g. pynvml) cannot
    break module import for machines without that vendor.
    """
    backends: list = []
    from glances.plugins.gpu.cards.amd import AmdGPU
    from glances.plugins.gpu.cards.arm import ArmGPU
    from glances.plugins.gpu.cards.intel import IntelGPU
    from glances.plugins.gpu.cards.nvidia import NvidiaGPU

    for cls in (NvidiaGPU, AmdGPU, IntelGPU, ArmGPU):
        try:
            backends.append(cls())
        except Exception as exc:  # noqa: BLE001 — any driver/lib error → skip vendor
            logger.debug("gpu: %s init failed: %s", cls.__name__, exc)
    return backends


class PluginModel(GlancesPluginBase[list]):
    """Per-GPU plugin (collection)."""

    plugin_name: ClassVar[str] = "gpu"
    IS_COLLECTION: ClassVar[bool] = True

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "gpu_id": {
            "description": "GPU identifier (e.g. nvidia0).",
            "unit": "string",
            "primary_key": True,
        },
        "name": {
            "description": "GPU product name.",
            "unit": "string",
            "internal": True,
        },
        "proc": {
            "description": "GPU processor consumption.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": True,
            "default_thresholds": _PERCENT_THRESHOLDS,
        },
        "mem": {
            "description": "GPU memory consumption.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": True,
            "default_thresholds": _PERCENT_THRESHOLDS,
        },
        "temperature": {
            "description": "GPU temperature.",
            "unit": "celsius",
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "default_thresholds": _TEMP_THRESHOLDS,
        },
        "fan_speed": {
            "description": "GPU fan speed.",
            "unit": "percent",
            "internal": True,
            "watched": False,
        },
    }

    def __init__(self, store: Any, config: Any) -> None:
        super().__init__(store, config)
        self._backends = _build_backends()

    def _collect(self) -> list:
        out: list[dict[str, Any]] = []
        for backend in self._backends:
            try:
                cards = backend.get_device_stats()
            except Exception as exc:  # noqa: BLE001 — one bad GPU must not drop others
                logger.debug("gpu: %s collect failed: %s", type(backend).__name__, exc)
                continue
            if cards:
                out.extend(cards)
        return out

    async def _grab_stats(self) -> list:
        return await asyncio.to_thread(self._collect)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_plugin_gpu_v5.py -q`
Expected: PASS (6 tests).

- [ ] **Step 5: Lint + stage**

```bash
.venv/bin/python -m ruff check glances/plugins/gpu/model_v5.py tests/test_plugin_gpu_v5.py
.venv/bin/python -m ruff format glances/plugins/gpu/model_v5.py tests/test_plugin_gpu_v5.py
git add glances/plugins/gpu/model_v5.py tests/test_plugin_gpu_v5.py
```
(Do not commit — maintainer commits.)

---

### Task 2: `gpu` curses renderer

**Files:**
- Create: `glances/plugins/gpu/render_curses_v5.py`
- Test: `tests/test_plugin_gpu_render_curses_v5.py`

**Interfaces:**
- Consumes: the gpu payload `{"data": [card, ...], "_levels": {gpu_id: {field: {"level":...}}}}`; helpers `Cell, ColorRole, Row, _LEVEL_TO_ROLE, title_role` from `glances.outputs.curses_renderer_v5`; `to_fahrenheit` from `glances.globals`.
- Produces: `render(payload, fields_desc, view=None) -> list[Row]`. Honours `view["meangpu"]` (force summary) and `view["fahrenheit"]` (°F on temperature). Auto-detected as view-accepting by `_accepts_view`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_plugin_gpu_render_curses_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — tests for the gpu curses renderer."""

from __future__ import annotations

from glances.plugins.gpu.render_curses_v5 import render


def _payload(cards, levels=None):
    return {"data": cards, "_levels": levels or {}}


def _card(gpu_id="nvidia0", name="GeForce RTX", mem=40, proc=30, temp=55):
    return {"gpu_id": gpu_id, "name": name, "mem": mem, "proc": proc, "temperature": temp}


def _flat(rows):
    return "\n".join(" ".join(c.text for c in r.cells) for r in rows)


def test_empty_payload_returns_no_rows():
    assert render(_payload([])) == []


def test_single_gpu_summary_three_metric_rows():
    rows = render(_payload([_card()]))
    flat = _flat(rows)
    # Header (name) + proc/mem/temperature labels.
    assert "GeForce RTX" in flat
    assert "proc:" in flat
    assert "mem:" in flat
    assert "temperature:" in flat
    assert "30" in flat and "40" in flat and "55" in flat


def test_header_two_same_name():
    rows = render(_payload([_card("nvidia0", "Tesla"), _card("nvidia1", "Tesla")]))
    assert "2 Tesla" in _flat(rows)


def test_header_two_different_names():
    rows = render(_payload([_card("nvidia0", "Tesla"), _card("amd0", "Radeon")]))
    assert "2 GPUs" in _flat(rows)


def test_multi_mode_one_row_per_gpu():
    cards = [_card("nvidia0", "Tesla", proc=30, mem=40), _card("amd0", "Radeon", proc=10, mem=20)]
    rows = render(_payload(cards))
    flat = _flat(rows)
    # Multi rows use the name[:9] id and show proc + mem.
    assert "Tesla" in flat and "Radeon" in flat
    assert "mem" in flat


def test_meangpu_forces_summary_for_multi():
    cards = [_card("nvidia0", "Tesla", proc=20), _card("nvidia1", "Tesla", proc=40)]
    rows = render(_payload(cards), {}, view={"meangpu": True})
    flat = _flat(rows)
    assert "proc mean:" in flat
    assert "30" in flat  # mean of 20 and 40


def test_fahrenheit_temperature():
    rows = render(_payload([_card(temp=100)]), {}, view={"fahrenheit": True})
    flat = _flat(rows)
    assert "212" in flat  # 100C -> 212F
    assert "F" in flat


def test_none_values_render_na():
    rows = render(_payload([_card(mem=None, proc=None, temp=None)]))
    assert "N/A" in _flat(rows)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_plugin_gpu_render_curses_v5.py -q`
Expected: FAIL — module missing.

- [ ] **Step 3: Write the renderer**

Create `glances/plugins/gpu/render_curses_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the gpu plugin.

Mirrors v4 `gpu.msg_curse()`:

    GeForce RTX 3080         <- header (name / "N NAME" / "N GPUs")
    proc:              30%   <- summary mode (1 GPU or view["meangpu"])
    mem:               40%
    temperature:       55C

Multi mode (>1 GPU, not meangpu): one row per GPU — `name[:9]  proc  mem N`.
"""

from __future__ import annotations

from typing import Any

from glances.globals import to_fahrenheit
from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row, title_role

_HEADER_MAX = 17


def _format_value(value: Any, unit: str = "%") -> str:
    if value is None:
        return "{:>4}".format("N/A")
    return f"{value:>3.0f}{unit}"


def _mean(cards: list[dict[str, Any]], key: str) -> float | None:
    vals = [c[key] for c in cards if isinstance(c, dict) and c.get(key) is not None]
    if not vals:
        return None
    return sum(vals) / len(vals)


def _build_header(cards: list[dict[str, Any]]) -> str:
    first = cards[0].get("name") or "GPU"
    same = all((c.get("name") or "GPU") == first for c in cards)
    n = len(cards)
    if n > 1:
        header = f"{n} {first}" if same else f"{n} GPUs"
    else:
        header = first
    return header[:_HEADER_MAX]


def _level_role(levels: dict[str, Any], gpu_id: Any, field: str) -> ColorRole:
    entry = levels.get(gpu_id, {})
    level = entry.get(field, {}).get("level") if isinstance(entry, dict) else None
    return _LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT)


def _summary_rows(cards: list[dict[str, Any]], levels: dict[str, Any], fahrenheit: bool) -> list[Row]:
    is_multi = len(cards) > 1
    first_id = cards[0].get("gpu_id")
    rows: list[Row] = []
    for key, label, label_mean in (("proc", "proc:", "proc mean:"), ("mem", "mem:", "mem mean:")):
        rows.append(
            Row(
                cells=[
                    Cell(text=f"{label_mean if is_multi else label:<13}"),
                    Cell(text=_format_value(_mean(cards, key)), color=_level_role(levels, first_id, key)),
                ]
            )
        )
    temp = _mean(cards, "temperature")
    if temp is not None and fahrenheit:
        temp = to_fahrenheit(temp)
    unit = "F" if fahrenheit else "C"
    temp_label = "temp mean:" if is_multi else "temperature:"
    rows.append(
        Row(
            cells=[
                Cell(text=f"{temp_label:<13}"),
                Cell(text=_format_value(temp, unit), color=_level_role(levels, first_id, "temperature")),
            ]
        )
    )
    return rows


def _multi_rows(cards: list[dict[str, Any]], levels: dict[str, Any]) -> list[Row]:
    rows: list[Row] = []
    for card in cards:
        gpu_id = card.get("gpu_id")
        cells = [Cell(text="{:<7}".format(str(card.get("name") or "")[0:9]))]
        if card.get("proc") is not None:
            cells.append(Cell(text=f" {_format_value(card.get('proc'))}", color=_level_role(levels, gpu_id, "proc")))
        if card.get("mem") is not None:
            cells.append(Cell(text=f" mem {_format_value(card.get('mem'))}", color=_level_role(levels, gpu_id, "mem")))
        rows.append(Row(cells=cells))
    return rows


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]] | None = None, view=None) -> list[Row]:
    if not isinstance(payload, dict):
        return []
    cards = payload.get("data")
    if not isinstance(cards, list) or not cards:
        return []
    levels = payload.get("_levels") if isinstance(payload.get("_levels"), dict) else {}
    view = view or {}

    header = Row(cells=[Cell(text=_build_header(cards), color=title_role(payload), bold=True)])
    rows: list[Row] = [header]

    if len(cards) == 1 or view.get("meangpu"):
        rows.extend(_summary_rows(cards, levels, bool(view.get("fahrenheit"))))
    else:
        rows.extend(_multi_rows(cards, levels))
    return rows
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_plugin_gpu_render_curses_v5.py -q`
Expected: PASS (8 tests).

- [ ] **Step 5: Lint + stage**

```bash
.venv/bin/python -m ruff check glances/plugins/gpu/render_curses_v5.py tests/test_plugin_gpu_render_curses_v5.py
.venv/bin/python -m ruff format glances/plugins/gpu/render_curses_v5.py tests/test_plugin_gpu_render_curses_v5.py
git add glances/plugins/gpu/render_curses_v5.py tests/test_plugin_gpu_render_curses_v5.py
```

---

### Task 3: `--meangpu` / `--fahrenheit` CLI flags + view seeding

**Files:**
- Modify: `glances/main_v5.py` (`build_parser` add flags; `assemble` pass through)
- Modify: `glances/outputs/glances_curses_v5.py` (`TuiV5.__init__` accept `meangpu`/`fahrenheit`; `_build_view` seed `view["meangpu"]`/`view["fahrenheit"]`)
- Test: `tests/test_main_v5.py` (flags parse), `tests/test_curses_v5.py` (view seeding)

**Interfaces:**
- Consumes: existing `--percpu`/`--full-quicklook` wiring in `main_v5.py` and `TuiV5` (mirror it).
- Produces: `view["meangpu"]: bool`, `view["fahrenheit"]: bool` consumed by the gpu renderer (Task 2) and later sensors (G4A-2).

- [ ] **Step 1: Write the failing tests**

Read `glances/main_v5.py` around the existing `--percpu` flag (line ~146) and `assemble` (line ~399) and `glances/outputs/glances_curses_v5.py` `__init__` (line ~166) + `_build_view` (line ~576). Add to `tests/test_main_v5.py`:

```python
def test_meangpu_and_fahrenheit_flags_parse():
    from glances.main_v5 import build_parser

    args = build_parser().parse_args(["--meangpu", "--fahrenheit"])
    assert args.meangpu is True
    assert args.fahrenheit is True


def test_meangpu_fahrenheit_default_false():
    from glances.main_v5 import build_parser

    args = build_parser().parse_args([])
    assert getattr(args, "meangpu", False) is False
    assert getattr(args, "fahrenheit", False) is False
```

Add to `tests/test_curses_v5.py` (mirror the existing view-seeding tests; use the same `TuiV5` construction helper already used there — read the file to match the fixture/constructor style):

```python
def test_build_view_seeds_meangpu_and_fahrenheit():
    tui = _make_tui(meangpu=True, fahrenheit=True)  # _make_tui: existing helper in this file
    view = tui._build_view(200)
    assert view["meangpu"] is True
    assert view["fahrenheit"] is True


def test_build_view_meangpu_fahrenheit_default_false():
    tui = _make_tui()
    view = tui._build_view(200)
    assert view["meangpu"] is False
    assert view["fahrenheit"] is False
```

If `tests/test_curses_v5.py` has no `_make_tui` helper, construct `TuiV5(...)` exactly as the existing tests in that file do, passing `meangpu=`/`fahrenheit=` (added in Step 3).

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_main_v5.py -q -k "meangpu or fahrenheit"` and `.venv/bin/python -m pytest tests/test_curses_v5.py -q -k "meangpu or fahrenheit"`
Expected: FAIL — unknown args / unexpected kwargs.

- [ ] **Step 3: Implement**

In `glances/main_v5.py`, next to the existing `--percpu` argument, add:

```python
    parser.add_argument(
        "--meangpu",
        dest="meangpu",
        action="store_true",
        default=False,
        help="Show a single mean GPU summary instead of per-GPU lines",
    )
    parser.add_argument(
        "--fahrenheit",
        dest="fahrenheit",
        action="store_true",
        default=False,
        help="Display temperatures in Fahrenheit (default: Celsius)",
    )
```

In `assemble(...)`, where `TuiV5(... full_quicklook=..., percpu=...)` is built (line ~399), add:

```python
meangpu = (getattr(args, "meangpu", False),)
fahrenheit = (getattr(args, "fahrenheit", False),)
```

In `glances/outputs/glances_curses_v5.py`, extend `TuiV5.__init__` signature (mirror the `full_quicklook`/`percpu` params at line ~166) with `meangpu: bool = False, fahrenheit: bool = False`, and store:

```python
        self._meangpu = bool(meangpu)
        self._fahrenheit = bool(fahrenheit)
```

In `_build_view` (near line ~585 where `view["full_quicklook"]`/`view["percpu"]` are set), add:

```python
        view["meangpu"] = self._meangpu
        view["fahrenheit"] = self._fahrenheit
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_main_v5.py tests/test_curses_v5.py -q`
Expected: PASS (no regressions).

- [ ] **Step 5: Lint + stage**

```bash
.venv/bin/python -m ruff check glances/main_v5.py glances/outputs/glances_curses_v5.py tests/test_main_v5.py tests/test_curses_v5.py
git add glances/main_v5.py glances/outputs/glances_curses_v5.py tests/test_main_v5.py tests/test_curses_v5.py
```

---

### Task 4: `npu` plugin model

**Files:**
- Create: `glances/plugins/npu/model_v5.py`
- Test: `tests/test_plugin_npu_v5.py`

**Interfaces:**
- Consumes: `GlancesPluginBase`; v4 card classes `AmdNPU`, `IntelNPU`, `RockchipNPU` (each: `is_available() -> bool`, `get_device_stats() -> dict | None`, `disable()`, `exit()`; constructor takes `npu_root_folder="/"`).
- Produces: `PluginModel` `plugin_name="npu"`, `IS_COLLECTION=True`, primary key `npu_id`, watched `load`/`freq`/`mem`. `_grab_stats()` returns `list[dict]`. Instance attr `self._backends`. **Default-disabled** helper `_is_enabled()` reading config `[npu] disable` (v4 default True).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_plugin_npu_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the `npu` plugin (collection)."""

from __future__ import annotations

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.plugins.npu.model_v5 import PluginModel
from glances.stats_store_v5 import StatsStoreV5


@pytest.fixture
def store() -> StatsStoreV5:
    return StatsStoreV5()


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    return GlancesConfigV5()


class _FakeCard:
    def __init__(self, stats, available=True):
        self._stats = stats
        self._available = available
        self.disabled = False

    def is_available(self):
        return self._available

    def get_device_stats(self):
        return self._stats

    def disable(self):
        self.disabled = True
        self._available = False

    def exit(self):
        pass


class _BoomCard(_FakeCard):
    def get_device_stats(self):
        raise OSError("boom")


def _npu(npu_id="intel_1", name="NPU", load=45, freq=50):
    return {"npu_id": npu_id, "name": name, "load": load, "freq": freq, "mem": None}


def test_plugin_identity(store, config):
    p = PluginModel(store, config)
    assert p.plugin_name == "npu"
    assert p.IS_COLLECTION is True
    assert p._primary_key == "npu_id"


def test_fields_watched():
    fd = PluginModel.fields_description
    for key in ("load", "freq", "mem"):
        assert fd[key]["watched"] is True
    assert fd["npu_id"].get("primary_key") is True
    for key in ("freq_current", "freq_max", "temperature", "power", "name"):
        assert fd[key].get("internal") is True


@pytest.mark.asyncio
async def test_grab_stats_collects_available_cards(store, config):
    p = PluginModel(store, config)
    p._backends = [_FakeCard(_npu("intel_1")), _FakeCard(_npu("amd_1"), available=False)]
    out = await p._grab_stats()
    assert [c["npu_id"] for c in out] == ["intel_1"]


@pytest.mark.asyncio
async def test_grab_stats_disables_card_on_error(store, config):
    p = PluginModel(store, config)
    boom = _BoomCard(_npu("rockship_1"))
    p._backends = [boom]
    out = await p._grab_stats()
    assert out == []
    assert boom.disabled is True


def test_npu_disabled_by_default(store, config):
    # Mirror v4 [npu] disable=True — no user config present here.
    p = PluginModel(store, config)
    assert p._is_enabled() is False


@pytest.mark.asyncio
async def test_grab_stats_empty_when_disabled(store, config):
    p = PluginModel(store, config)
    p._backends = [_FakeCard(_npu("intel_1"))]
    # default disabled -> collects nothing even with an available card
    assert await p._grab_stats() == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_plugin_npu_v5.py -q`
Expected: FAIL — module missing.

- [ ] **Step 3: Write the model**

Create `glances/plugins/npu/model_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — NPU plugin (collection, per-card).

Migrated from `glances/plugins/npu/__init__.py`. Reuses the v4 hardware
card backends (`glances/plugins/npu/cards/{amd,intel,rockchip}.py`) as
pure collectors. Each card exposes an availability model
(`is_available()`, `get_device_stats()`, `disable()`); a card that
raises during collection is disabled for the rest of the run (v4 parity).

**Default-disabled**: v4 ships `[npu] disable=True`. This plugin mirrors
that — with no explicit `[npu] disable=False` in the user config it
collects and publishes nothing. The plugin is still discovered so it can
be enabled without code changes.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

from glances.plugins.plugin.base_v5 import GlancesPluginBase

logger = logging.getLogger(__name__)

_PERCENT_THRESHOLDS = {"careful": 50.0, "warning": 70.0, "critical": 90.0}


def _build_backends() -> list:
    backends: list = []
    from glances.plugins.npu.cards.amd import AmdNPU
    from glances.plugins.npu.cards.intel import IntelNPU
    from glances.plugins.npu.cards.rockchip import RockchipNPU

    for cls in (AmdNPU, IntelNPU, RockchipNPU):
        try:
            backends.append(cls())
        except Exception as exc:  # noqa: BLE001
            logger.debug("npu: %s init failed: %s", cls.__name__, exc)
    return backends


class PluginModel(GlancesPluginBase[list]):
    """Per-NPU plugin (collection)."""

    plugin_name: ClassVar[str] = "npu"
    IS_COLLECTION: ClassVar[bool] = True

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "npu_id": {
            "description": "NPU identifier (e.g. intel_1).",
            "unit": "string",
            "primary_key": True,
        },
        "name": {"description": "NPU product name.", "unit": "string", "internal": True},
        "load": {
            "description": "NPU load.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": True,
            "default_thresholds": _PERCENT_THRESHOLDS,
        },
        "freq": {
            "description": "NPU frequency (current/max).",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "default_thresholds": _PERCENT_THRESHOLDS,
        },
        "mem": {
            "description": "NPU memory consumption.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "default_thresholds": _PERCENT_THRESHOLDS,
        },
        "freq_current": {"description": "NPU current frequency (Hz).", "unit": "hertz", "internal": True},
        "freq_max": {"description": "NPU maximum frequency (Hz).", "unit": "hertz", "internal": True},
        "temperature": {"description": "NPU temperature.", "unit": "celsius", "internal": True},
        "power": {"description": "NPU power draw.", "unit": "watt", "internal": True},
    }

    def __init__(self, store: Any, config: Any) -> None:
        super().__init__(store, config)
        self._backends = _build_backends()

    def _is_enabled(self) -> bool:
        """Return True only if the user explicitly set [npu] disable=False.

        Mirrors v4's `[npu] disable=True` default — NPU is off unless the
        operator opts in.
        """
        raw = self.config.get("npu", "disable", "True")
        return str(raw).strip().lower() in ("false", "0", "no")

    def _collect(self) -> list:
        out: list[dict[str, Any]] = []
        for backend in self._backends:
            if not backend.is_available():
                continue
            try:
                stats = backend.get_device_stats()
            except Exception as exc:  # noqa: BLE001 — disable the faulty card, keep others
                logger.debug("npu: %s collect failed, disabling: %s", type(backend).__name__, exc)
                backend.disable()
                continue
            if stats:
                out.append(stats)
        return out

    async def _grab_stats(self) -> list:
        if not self._is_enabled():
            return []
        return await asyncio.to_thread(self._collect)
```

Note: confirm `GlancesConfigV5.get(section, key, default)` signature by reading `glances/config_v5.py` (the alerts engine uses `config.get(plugin, key, default)` — same shape). Adjust the `_is_enabled` call if the real signature differs.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_plugin_npu_v5.py -q`
Expected: PASS (7 tests).

- [ ] **Step 5: Lint + stage**

```bash
.venv/bin/python -m ruff check glances/plugins/npu/model_v5.py tests/test_plugin_npu_v5.py
.venv/bin/python -m ruff format glances/plugins/npu/model_v5.py tests/test_plugin_npu_v5.py
git add glances/plugins/npu/model_v5.py tests/test_plugin_npu_v5.py
```

---

### Task 5: `npu` renderer + TOP_SLOT insertion

**Files:**
- Create: `glances/plugins/npu/render_curses_v5.py`
- Modify: `glances/outputs/curses_renderer_v5.py` (`TOP_SLOT` — insert `"npu"`)
- Test: `tests/test_plugin_npu_render_curses_v5.py`, `tests/test_curses_renderer_v5.py` (slot order)

**Interfaces:**
- Consumes: npu payload `{"data": [npu, ...], "_levels": {npu_id: {...}}}`; `Cell, ColorRole, Row, _LEVEL_TO_ROLE, title_role` from curses_renderer_v5; `to_fahrenheit` from globals.
- Produces: `render(payload, fields_desc, view=None) -> list[Row]`. Renders first NPU only (v4 parity).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_plugin_npu_render_curses_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — tests for the npu curses renderer."""

from __future__ import annotations

from glances.plugins.npu.render_curses_v5 import render


def _payload(npus, levels=None):
    return {"data": npus, "_levels": levels or {}}


def _npu(npu_id="intel_1", name="Intel NPU", load=45, freq=50, fc=1_000_000_000, fm=2_000_000_000, mem=None, temp=None):
    return {
        "npu_id": npu_id,
        "name": name,
        "load": load,
        "freq": freq,
        "freq_current": fc,
        "freq_max": fm,
        "mem": mem,
        "temperature": temp,
    }


def _flat(rows):
    return "\n".join(" ".join(c.text for c in r.cells) for r in rows)


def test_empty_returns_no_rows():
    assert render(_payload([])) == []


def test_header_uses_first_npu_name():
    rows = render(_payload([_npu(name="Meteor Lake NPU")]))
    assert "Meteor Lake NPU" in _flat(rows)


def test_load_line_shown_when_load_present():
    rows = render(_payload([_npu(load=45)]))
    flat = _flat(rows)
    assert "45" in flat  # load %
    assert "Hz" in flat  # freq range


def test_freq_fallback_when_load_none():
    rows = render(_payload([_npu(load=None, freq=60)]))
    assert "60" in _flat(rows)


def test_mem_and_temperature_rows():
    rows = render(_payload([_npu(mem=30, temp=55)]))
    flat = _flat(rows)
    assert "mem" in flat and "30" in flat
    assert "temperature" in flat and "55" in flat


def test_only_first_npu_rendered():
    rows = render(_payload([_npu("intel_1", "First"), _npu("amd_1", "Second")]))
    flat = _flat(rows)
    assert "First" in flat
    assert "Second" not in flat
```

Add to `tests/test_curses_renderer_v5.py`:

```python
def test_top_slot_has_npu_after_percpu_before_gpu():
    from glances.outputs.curses_renderer_v5 import TOP_SLOT

    assert "npu" in TOP_SLOT
    assert TOP_SLOT.index("percpu") < TOP_SLOT.index("npu") < TOP_SLOT.index("gpu")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_plugin_npu_render_curses_v5.py tests/test_curses_renderer_v5.py -q -k "npu or top_slot"`
Expected: FAIL — module missing + `npu` not in TOP_SLOT.

- [ ] **Step 3: Write the renderer + insert into TOP_SLOT**

Create `glances/plugins/npu/render_curses_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the npu plugin.

Mirrors v4 `npu.msg_curse()` — renders the FIRST NPU only:

    Intel NPU             <- header (name[:17])
    45%        1.0G/2.0GHz  <- load% (or freq% if load is None) + freq range
    mem:              N/A%
    temperature:       55C
"""

from __future__ import annotations

from typing import Any

from glances.globals import to_fahrenheit
from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row, title_role

_HEADER_MAX = 17
_RANGE_WIDTH = 14


def _format_value(value: Any, unit: str) -> str:
    if value is None:
        return "{:>5}".format("N/A")
    return f"{value:>4.0f}{unit}"


def _auto_hz(hz: Any) -> str:
    try:
        v = float(hz)
    except (TypeError, ValueError):
        return "?"
    for symbol, threshold in (("G", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(v) >= threshold:
            return f"{v / threshold:.1f}{symbol}"
    return f"{int(v)}"


def _level_role(levels: dict[str, Any], npu_id: Any, field: str) -> ColorRole:
    entry = levels.get(npu_id, {})
    level = entry.get(field, {}).get("level") if isinstance(entry, dict) else None
    return _LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT)


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]] | None = None, view=None) -> list[Row]:
    if not isinstance(payload, dict):
        return []
    npus = payload.get("data")
    if not isinstance(npus, list) or not npus:
        return []
    npu = npus[0]
    if not isinstance(npu, dict):
        return []
    levels = payload.get("_levels") if isinstance(payload.get("_levels"), dict) else {}
    view = view or {}
    npu_id = npu.get("npu_id")

    rows: list[Row] = [
        Row(cells=[Cell(text=str(npu.get("name") or "NPU")[:_HEADER_MAX], color=title_role(payload), bold=True)])
    ]

    # Row 2: load% (or freq% fallback) + right-justified current/max freq range.
    if npu.get("load") is not None:
        pct_cell = Cell(text=f"{npu['load']:>3.0f}%", color=_level_role(levels, npu_id, "load"))
    else:
        freq = npu.get("freq")
        pct_cell = Cell(
            text=("{:>4}".format("N/A") if freq is None else f"{freq:>3.0f}%"),
            color=_level_role(levels, npu_id, "freq"),
        )
    freq_range = f"{_auto_hz(npu.get('freq_current'))}/{_auto_hz(npu.get('freq_max'))}Hz"
    rows.append(Row(cells=[pct_cell, Cell(text=freq_range.rjust(_RANGE_WIDTH))]))

    # Row 3: mem.
    rows.append(
        Row(
            cells=[
                Cell(text="{:<12}".format("mem:")),
                Cell(text=_format_value(npu.get("mem"), "%"), color=_level_role(levels, npu_id, "mem")),
            ]
        )
    )

    # Row 4: temperature (never watched in v4 — default colour).
    temp = npu.get("temperature")
    if temp is not None and view.get("fahrenheit"):
        temp = to_fahrenheit(temp)
    unit = "F" if view.get("fahrenheit") else "C"
    rows.append(Row(cells=[Cell(text="{:<12}".format("temperature:")), Cell(text=_format_value(temp, unit))]))

    return rows
```

In `glances/outputs/curses_renderer_v5.py`, change `TOP_SLOT` (currently `("quicklook", "cpu", "percpu", "gpu", "mem", "memswap", "load")`) to insert `"npu"` after `"percpu"`:

```python
TOP_SLOT: tuple[str, ...] = ("quicklook", "cpu", "percpu", "npu", "gpu", "mem", "memswap", "load")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_plugin_npu_render_curses_v5.py tests/test_curses_renderer_v5.py -q`
Expected: PASS.

- [ ] **Step 5: Lint + stage**

```bash
.venv/bin/python -m ruff check glances/plugins/npu/render_curses_v5.py glances/outputs/curses_renderer_v5.py tests/test_plugin_npu_render_curses_v5.py tests/test_curses_renderer_v5.py
.venv/bin/python -m ruff format glances/plugins/npu/render_curses_v5.py
git add glances/plugins/npu/render_curses_v5.py glances/outputs/curses_renderer_v5.py tests/test_plugin_npu_render_curses_v5.py tests/test_curses_renderer_v5.py
```

---

### Task 6: quicklook GPU addendum (store-read + bars)

**Files:**
- Modify: `glances/plugins/quicklook/model_v5.py` (add `gpu_mem`/`gpu_proc` fields + store read in `_grab_stats`)
- Modify: `glances/plugins/quicklook/render_curses_v5.py` (`_BAR_KEYS` + label map)
- Test: extend `tests/test_plugin_quicklook_v5.py`, `tests/test_plugin_quicklook_render_curses_v5.py`

**Interfaces:**
- Consumes: `self.store.get("gpu")` → `list[dict]` of gpu cards (or `None`), each with numeric `mem`/`proc` (may be `None`).
- Produces: `gpu_mem`/`gpu_proc` percent keys in the quicklook payload when a GPU publishes usable data; absent otherwise. Rendered as bottom bars labelled `GMEM`/`GPU`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_plugin_quicklook_v5.py`:

```python
@pytest.mark.asyncio
async def test_gpu_means_from_store(store, config, monkeypatch):
    """quicklook computes gpu_mem/gpu_proc as the mean of the gpu plugin's cards."""
    await store.set(
        "gpu",
        [
            {"gpu_id": "n0", "mem": 40, "proc": 20},
            {"gpu_id": "n1", "mem": 60, "proc": 40},
        ],
    )
    p = PluginModel(store, config)

    import glances.plugins.quicklook.model_v5 as mod

    monkeypatch.setattr(mod, "_collect_sync", lambda: {})

    class _S:
        cpu_count = 1

        async def get_aggregate(self):
            class _A:
                idle = 100.0

            return _A()

        async def get_per_core(self):
            return []

    monkeypatch.setattr(mod, "sampler", _S())

    stats = await p._grab_stats()
    assert stats["gpu_mem"] == 50.0
    assert stats["gpu_proc"] == 30.0


@pytest.mark.asyncio
async def test_no_gpu_keys_when_store_empty(store, config, monkeypatch):
    p = PluginModel(store, config)
    import glances.plugins.quicklook.model_v5 as mod

    monkeypatch.setattr(mod, "_collect_sync", lambda: {})

    class _S:
        cpu_count = 1

        async def get_aggregate(self):
            class _A:
                idle = 100.0

            return _A()

        async def get_per_core(self):
            return []

    monkeypatch.setattr(mod, "sampler", _S())

    stats = await p._grab_stats()
    assert "gpu_mem" not in stats
    assert "gpu_proc" not in stats


@pytest.mark.asyncio
async def test_no_gpu_keys_when_all_none(store, config, monkeypatch):
    await store.set("gpu", [{"gpu_id": "n0", "mem": None, "proc": None}])
    p = PluginModel(store, config)
    import glances.plugins.quicklook.model_v5 as mod

    monkeypatch.setattr(mod, "_collect_sync", lambda: {})

    class _S:
        cpu_count = 1

        async def get_aggregate(self):
            class _A:
                idle = 100.0

            return _A()

        async def get_per_core(self):
            return []

    monkeypatch.setattr(mod, "sampler", _S())

    stats = await p._grab_stats()
    assert "gpu_mem" not in stats
    assert "gpu_proc" not in stats


def test_gpu_fields_declared_watched():
    fd = PluginModel.fields_description
    for key in ("gpu_mem", "gpu_proc"):
        assert fd[key]["watched"] is True
        assert fd[key]["unit"] == "percent"
```

Add to `tests/test_plugin_quicklook_render_curses_v5.py` (match the file's existing payload/helper style):

```python
def test_gpu_bars_render_when_present():
    payload = {
        "cpu": 10.0,
        "mem": 20.0,
        "load": 5.0,
        "gpu_mem": 50.0,
        "gpu_proc": 30.0,
        "_levels": {},
    }
    rows = render(payload, {}, view=None)
    flat = "\n".join(" ".join(c.text for c in r.cells) for r in rows)
    assert "GMEM" in flat
    assert "GPU" in flat


def test_no_gpu_bars_when_absent():
    payload = {"cpu": 10.0, "mem": 20.0, "load": 5.0, "_levels": {}}
    rows = render(payload, {}, view=None)
    flat = "\n".join(" ".join(c.text for c in r.cells) for r in rows)
    assert "GMEM" not in flat
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_plugin_quicklook_v5.py tests/test_plugin_quicklook_render_curses_v5.py -q -k "gpu"`
Expected: FAIL.

- [ ] **Step 3: Implement the model change**

In `glances/plugins/quicklook/model_v5.py`, add the two fields to `fields_description` (after `load`), reusing the existing `_PERCENT_THRESHOLDS`:

```python
        "gpu_mem": {
            "description": "Average GPU memory consumption.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": True,
            "default_thresholds": _PERCENT_THRESHOLDS,
        },
        "gpu_proc": {
            "description": "Average GPU processor consumption.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            "prominent": True,
            "default_thresholds": _PERCENT_THRESHOLDS,
        },
```

At the END of `_grab_stats` (just before `return out`), fold in the GPU means read from the store:

```python
        self._add_gpu_means(out)
        return out
```

And add the helper method to `PluginModel`:

```python
    def _add_gpu_means(self, out: dict[str, Any]) -> None:
        """Average the gpu plugin's per-card proc/mem into gpu_proc/gpu_mem.

        Cross-plugin read via the stats store — the gpu plugin publishes
        its card list, quicklook averages it (replaces v4's global
        `glances.gpu_percent` mutable channel). Keys are omitted entirely
        when no GPU is present or every card reports None, so the renderer
        draws no GPU bar (auto-show only when a GPU is detected).
        """
        cards = self.store.get("gpu")
        if not isinstance(cards, list) or not cards:
            return
        for src, dst in (("mem", "gpu_mem"), ("proc", "gpu_proc")):
            vals = [c[src] for c in cards if isinstance(c, dict) and c.get(src) is not None]
            if vals:
                out[dst] = round(sum(vals) / len(vals), 1)
```

- [ ] **Step 4: Implement the renderer change**

In `glances/plugins/quicklook/render_curses_v5.py`:

- Extend the bar-key tuple and add a label map right after it:

```python
# Stats shown as bars, in v4 order. GPU means appended (auto-shown when the
# gpu plugin publishes cards — see quicklook/model_v5._add_gpu_means).
_BAR_KEYS = ("cpu", "mem", "load", "gpu_mem", "gpu_proc")

# 4-char display labels (the bar label cell is padded to 4). Keeps the
# grid aligned — raw upper-cased keys "GPU_MEM"/"GPU_PROC" (7 chars) would
# break it.
_BAR_LABEL = {"gpu_mem": "GMEM", "gpu_proc": "GPU"}
```

- In `render`, change the bar label at the `_bar_cells(...)` call (currently `_bar_cells(key.upper(), ...)`) to use the map:

```python
        rows.append(Row(cells=_bar_cells(_BAR_LABEL.get(key, key.upper()), payload[key], _role_for(payload, key), width)))
```

(The existing `if key not in payload or payload.get(key) is None: continue` guard already suppresses GPU bars when the keys are absent — no extra branch needed.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_plugin_quicklook_v5.py tests/test_plugin_quicklook_render_curses_v5.py -q`
Expected: PASS (including the pre-existing quicklook tests — GPU bars must be byte-absent by default).

- [ ] **Step 6: Lint + stage**

```bash
.venv/bin/python -m ruff check glances/plugins/quicklook/model_v5.py glances/plugins/quicklook/render_curses_v5.py tests/test_plugin_quicklook_v5.py tests/test_plugin_quicklook_render_curses_v5.py
git add glances/plugins/quicklook/model_v5.py glances/plugins/quicklook/render_curses_v5.py tests/test_plugin_quicklook_v5.py tests/test_plugin_quicklook_render_curses_v5.py
```

---

### Task 7: cascade step (g) `hide_gpu` + build_frame guard + docs

**Files:**
- Modify: `glances/outputs/glances_curses_v5.py` (`_DEGRADE_STEPS` — append `("hide_gpu", True)`; remove the `TODO(G4A — gpu)` marker)
- Modify: `glances/outputs/curses_renderer_v5.py` (`build_frame` — skip the gpu block when `view["hide_gpu"]`)
- Modify: `docs/architecture/tui-v4-rendering-patterns.md` (cascade table — add step g)
- Test: extend `tests/test_curses_v5.py`

**Interfaces:**
- Consumes: the existing measure-driven cascade (`_build_fitted_frame`, `_DEGRADE_STEPS`, `_frame_for_view`) and `build_frame`'s existing `hide_quicklook`/`hide_memswap` guards.
- Produces: `hide_gpu` as the last cascade step; `build_frame` drops the gpu top block when set.

- [ ] **Step 1: Write the failing test**

Read `tests/test_curses_v5.py` for the existing cascade tests (they build a `TuiV5`, register plugins incl. `gpu`, and shrink `max_x`). Add a test that at a width where steps (a)–(f) are insufficient, the gpu block disappears, and that `hide_gpu` is strictly last. Match the file's existing harness (fixtures/registration helpers) — mirror the closest existing cascade test:

```python
def test_hide_gpu_is_last_cascade_step():
    from glances.outputs.glances_curses_v5 import _DEGRADE_STEPS

    keys = [k for k, _ in _DEGRADE_STEPS]
    assert keys[-1] == "hide_gpu"
    # Ordering contract: gpu hidden only after quicklook + memswap.
    assert keys.index("hide_memswap") < keys.index("hide_gpu")


def test_build_frame_hides_gpu_when_flagged():
    from glances.outputs.curses_renderer_v5 import build_frame

    # build_frame(store_snapshot, fields_by_plugin, registry, alerts_history, ..., view=None)
    registry = [("gpu", True)]
    snapshot = {
        "gpu": {
            "data": [{"gpu_id": "n0", "name": "X", "mem": 10, "proc": 5, "temperature": 40}],
            "_levels": {},
        }
    }
    fields = {"gpu": {}}
    shown = build_frame(snapshot, fields, registry, [], view={"hide_gpu": False})
    hidden = build_frame(snapshot, fields, registry, [], view={"hide_gpu": True})
    assert "gpu" in [b.name for b in shown.top]
    assert "gpu" not in [b.name for b in hidden.top]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_curses_v5.py -q -k "hide_gpu"`
Expected: FAIL — `hide_gpu` not in `_DEGRADE_STEPS`; build_frame ignores it.

- [ ] **Step 3: Implement**

In `glances/outputs/glances_curses_v5.py`, `_DEGRADE_STEPS` is a **list** of `(key, value)` tuples with per-step comments (steps a–f), followed by the `TODO(G4A — gpu)` marker. Append step (g) and delete the TODO comment block:

```python
_DEGRADE_STEPS: list[tuple[str, Any]] = [
    ("mem_cols", 1),  # (a) hide MEM 2nd column
    ("cpu_cols", 2),  # (b) hide CPU 3rd column
    ("cpu_cols", 1),  # (c) hide CPU 2nd column
    ("quicklook_freq_only", True),  # (d) "Frequency" header + shrink quicklook
    ("hide_quicklook", True),  # (e) hide quicklook block
    ("hide_memswap", True),  # (f) hide swap block
    ("hide_gpu", True),  # (g) hide gpu block (last resort)
]
```

(Preserve the exact existing values/comments for a–f — copy from the current source; only append `("hide_gpu", True)` and remove the TODO comment lines.)

In `glances/outputs/curses_renderer_v5.py` `build_frame` (the loop `for plugin_name, is_collection in registry:`), add after the existing `hide_memswap` guard (line ~762) — mirroring it exactly:

```python
        if view and view.get("hide_gpu") and plugin_name == "gpu":
            continue
```

In `docs/architecture/tui-v4-rendering-patterns.md`, add row **(g)** to the top-row cascade table: `g) hide the gpu plugin (last resort)`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_curses_v5.py tests/test_curses_renderer_v5.py -q`
Expected: PASS.

- [ ] **Step 5: Full suite + lint + stage**

```bash
.venv/bin/python -m pytest tests/ -q
.venv/bin/python -m ruff check glances/outputs/glances_curses_v5.py glances/outputs/curses_renderer_v5.py tests/test_curses_v5.py
git add glances/outputs/glances_curses_v5.py glances/outputs/curses_renderer_v5.py docs/architecture/tui-v4-rendering-patterns.md tests/test_curses_v5.py
```

---

## Post-plan verification

- [ ] Run the full suite: `.venv/bin/python -m pytest tests/ -q` — all green.
- [ ] `.venv/bin/python -m ruff check glances/ tests/` — clean.
- [ ] Manual smoke (maintainer): `make run-v5` on a machine with a GPU — verify the gpu block in the top row (summary vs multi), the quicklook GMEM/GPU bars, `--meangpu`, `--fahrenheit`, and the responsive cascade dropping gpu last at very narrow widths. On a no-GPU machine, verify no gpu block and no quicklook GPU bars (regression guard).
- [ ] Update memory `project_v5_g2_quicklook_done.md` (or a new `project_v5_g4a1_done.md`) noting G4A-1 complete and G4A-2 (sensors) next.

## Out of scope (explicit)

- `sensors` (→ G4A-2), `mpp` (→ G6).
- Rewriting hardware backends (reuse v4).
- A `[quicklook] list` config key (auto-show chosen).
- `NEWS.rst` (release-time only), sparklines (no v5 history store).
