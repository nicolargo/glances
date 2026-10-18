# Glances v5 — G6C `irq` port Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the v4 `irq` plugin (per-IRQ-line interrupt rates from `/proc/interrupts`) to the v5 asyncio architecture, replacing v4's hand-rolled rate arithmetic with the base class's `rate: True` machinery.

**Architecture:** `model_v5.py` is a collection plugin (`IS_COLLECTION = True`, primary key `irq_line`, `DISABLED_BY_DEFAULT = True`). `_grab_stats()` parses `/proc/interrupts` in a worker thread and returns the **cumulative** interrupt count per line; the base's `_transform_gauge()` converts it to a per-second rate. Sorting and the top-5 cap move to `_expand_parameters()`, which runs after rates and before levels — so `_derived_parameters()` stays untouched and the plugin keeps reporting correctly through `/api/5/irq/limits`. A `render_curses_v5.py` mirrors v4's two-column `IRQ / Rate/s` table in the left sidebar, where `irq` is already registered.

**Tech Stack:** Python, `asyncio.to_thread`, `glances/plugins/plugin/base_v5.py`, pytest

**Spec:** `docs/superpowers/specs/2026-08-04-glances-v5-g6c-design.md` §3

## Global Constraints

- **Never commit, push, or open a PR.** Every task ends with `git add` only. The maintainer commits personally. Never add a `Co-Authored-By` trailer.
- **Do not touch `NEWS.rst`.**
- Run `make pre-commit` before staging each task — not just `make lint && make format`. Treat a failure as blocking. Note: gitleaks scans the **git index**, so `git add` before re-running it.
- Full v5 suite must stay green: `make test-v5`.
- Every new file carries the standard SPDX header used by sibling v5 modules (see `glances/plugins/npu/model_v5.py:1-7`).
- New modules and tests start with `from __future__ import annotations`.
- `DISABLED_BY_DEFAULT = True` — v4 ships `[irq] disable=True`. Do not change the default.
- Linux-only. On any other platform the plugin must publish an empty collection without raising and without log spam.

---

### Task 1: `model_v5.py` — parse, rate, sort, cap

**Files:**
- Create: `glances/plugins/irq/model_v5.py`
- Test: `tests/test_plugin_irq_v5.py`

**Interfaces:**
- Produces: `glances.plugins.irq.model_v5.PluginModel`, a `GlancesPluginBase[list]` with `plugin_name = "irq"`. Published item shape: `{"irq_line": str, "irq_rate": float}`. `irq_rate` is **absent** on an item's first appearance (the base strips rate fields with no previous sample).
- Consumes: `GlancesPluginBase._transform_gauge()` (rate machinery), `_expand_parameters()` (post-rate hook).

**Two deliberate divergences from v4** — both must be preserved and both are covered by tests below:

1. **v4's rate is a raw delta, not a rate.** `glances/plugins/irq/__init__.py:~200` reads
   `int(current - lasts[x] if lasts.get(x) else 0 // time_since_update)`. Python precedence binds this as `(current - lasts[x]) if lasts.get(x) else (0 // time_since_update)` — the division only ever applies to the literal `0`. So v4 publishes a per-cycle delta under a field documented as `numberpersecond`. v5 declares `rate: True` and the base divides by `time_since_update`, which fixes the bug. Values will differ from v4; that is intended.
2. **First cycle has no `irq_rate` key at all.** v4 emits `0`; the v5 base strips a rate field when there is no previous sample, so consumers see the field as absent rather than a misleading zero.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_plugin_irq_v5.py`:

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Unit tests for the v5 ``irq`` plugin model.

See docs/superpowers/specs/2026-08-04-glances-v5-g6c-design.md §3
"""

from __future__ import annotations

import asyncio

import pytest

from glances.plugins.irq.model_v5 import PluginModel, parse_interrupts

# Two CPUs. `1:` is numeric so v4 appends the alias (`1_i8042`);
# `LOC:` is not numeric so it stays as-is.
PROC_INTERRUPTS = """\
           CPU0       CPU1
  1:      44487        341   IO-APIC   1-edge      i8042
  8:         10          0   IO-APIC   8-edge      rtc0
LOC:   33549868   22394684   Local timer interrupts
FIQ:                          usb_fiq
"""


def test_parse_builds_human_names_and_sums_cpu_columns():
    rows = parse_interrupts(PROC_INTERRUPTS)
    by_line = {r["irq_line"]: r["irq_rate"] for r in rows}
    assert by_line["1_i8042"] == 44487 + 341
    assert by_line["8_rtc0"] == 10
    assert by_line["LOC"] == 33549868 + 22394684


def test_parse_tolerates_non_numeric_columns():
    """Raspberry Pi / Raspbian emit lines with no counter columns (v4 #1007)."""
    rows = parse_interrupts(PROC_INTERRUPTS)
    assert {"irq_line": "FIQ", "irq_rate": 0} in rows


def test_parse_empty_input_returns_empty_list():
    assert parse_interrupts("") == []


def test_grab_stats_returns_cumulative_counters(store_with, config_with):
    plugin = PluginModel(store_with(), config_with({}))
    plugin._read_proc = lambda: PROC_INTERRUPTS
    stats = asyncio.run(plugin._grab_stats())
    assert {r["irq_line"] for r in stats} == {"1_i8042", "8_rtc0", "LOC", "FIQ"}
    # Raw cumulative values — the base class turns them into rates.
    assert next(r for r in stats if r["irq_line"] == "8_rtc0")["irq_rate"] == 10


def test_first_cycle_publishes_items_without_a_rate_field(store_with, config_with):
    store = store_with()
    plugin = PluginModel(store, config_with({}))
    plugin._read_proc = lambda: PROC_INTERRUPTS
    asyncio.run(plugin.update())
    items = store.get("irq")["data"]
    assert items, "items must be published on cycle 1"
    assert all("irq_rate" not in i for i in items), "no previous sample yet"


def test_second_cycle_computes_a_per_second_rate(store_with, config_with):
    store = store_with()
    plugin = PluginModel(store, config_with({}))
    plugin._read_proc = lambda: PROC_INTERRUPTS
    asyncio.run(plugin.update())
    # +2000 interrupts on rtc0 for the second sample.
    bumped = PROC_INTERRUPTS.replace("  8:         10          0", "  8:       2010          0")
    plugin._read_proc = lambda: bumped
    asyncio.run(plugin.update())
    rtc0 = next(i for i in store.get("irq")["data"] if i["irq_line"] == "8_rtc0")
    # Rate is delta / elapsed; elapsed is tiny in a test, so just assert the
    # delta was divided by something positive rather than published raw.
    assert rtc0["irq_rate"] > 0
    assert rtc0["irq_rate"] != 2000, "a raw delta means the rate machinery was bypassed"


def test_sorted_by_rate_descending_and_capped_at_five(store_with, config_with):
    store = store_with()
    plugin = PluginModel(store, config_with({}))
    first = "           CPU0\n" + "".join(f"{i}:  0  IO-APIC {i}-edge dev{i}\n" for i in range(1, 9))
    plugin._read_proc = lambda: first
    asyncio.run(plugin.update())
    # Give each line a distinct increment so the ordering is unambiguous.
    second = "           CPU0\n" + "".join(f"{i}:  {i * 100}  IO-APIC {i}-edge dev{i}\n" for i in range(1, 9))
    plugin._read_proc = lambda: second
    asyncio.run(plugin.update())
    items = store.get("irq")["data"]
    assert len(items) == 5, "v4 caps the collection at the top 5"
    rates = [i["irq_rate"] for i in items]
    assert rates == sorted(rates, reverse=True)
    # The five busiest lines are 8..4.
    assert [i["irq_line"] for i in items] == [f"{n}_dev{n}" for n in (8, 7, 6, 5, 4)]


def test_missing_proc_file_yields_empty_collection(store_with, config_with):
    store = store_with()
    plugin = PluginModel(store, config_with({}))

    def _boom():
        raise FileNotFoundError("/proc/interrupts")

    plugin._read_proc = _boom
    asyncio.run(plugin.update())
    assert store.get("irq")["data"] == []


def test_non_linux_yields_empty_collection(store_with, config_with, monkeypatch):
    monkeypatch.setattr("glances.plugins.irq.model_v5.LINUX", False)
    store = store_with()
    plugin = PluginModel(store, config_with({}))
    asyncio.run(plugin.update())
    assert store.get("irq")["data"] == []


@pytest.mark.parametrize("attr,expected", [("plugin_name", "irq"), ("IS_COLLECTION", True), ("EMITS_ALERTS", False)])
def test_class_flags(attr, expected):
    assert getattr(PluginModel, attr) == expected


def test_disabled_by_default():
    assert PluginModel.DISABLED_BY_DEFAULT is True
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_plugin_irq_v5.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glances.plugins.irq.model_v5'`

- [ ] **Step 3: Write the implementation**

Create `glances/plugins/irq/model_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — IRQ plugin (collection, per interrupt line).

Migrated from `glances/plugins/irq/__init__.py`. Linux-only: reads
`/proc/interrupts` and publishes the busiest five interrupt lines.

**Rate handling differs from v4 on purpose.** v4 computed the rate by hand
and shipped a precedence bug (`a - b if b else 0 // elapsed` binds as
`(a - b) if b else (0 // elapsed)`), so the division never applied and the
published `irq_rate` was a per-cycle *delta* despite its
`numberpersecond` unit. Here `_grab_stats` returns the **cumulative**
counter and `rate: True` lets the base class divide by
`time_since_update`. Values therefore differ from v4 — the v5 ones are
the ones the field name always claimed.

**Default-disabled**: v4 ships `[irq] disable=True`.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

from glances.globals import LINUX
from glances.plugins.plugin.base_v5 import GlancesPluginBase

logger = logging.getLogger(__name__)

IRQ_FILE = "/proc/interrupts"

# v4 keeps only the busiest lines; the cap lives at the data layer so the
# REST payload and the TUI agree on what "top" means.
_TOP_N = 5


def parse_interrupts(content: str) -> list[dict[str, Any]]:
    """Parse `/proc/interrupts` content into cumulative per-line counters.

    The first line is the CPU header; its column count tells us how many
    numeric columns each following line carries. Everything after those
    columns is the controller/device description.

        1:      44487        341   IO-APIC   1-edge      i8042
        LOC: 33549868   22394684   Local timer interrupts
    """
    lines = content.splitlines()
    if not lines:
        return []

    cpu_number = len(lines[0].split())
    out: list[dict[str, Any]] = []
    for line in lines[1:]:
        parts = line.split()
        if not parts:
            continue
        irq_line = parts[0].replace(":", "")
        if irq_line.isdigit():
            # Numeric lines are meaningless on their own — v4 appends the
            # device alias from the last column.
            irq_line += f"_{parts[-1]}"
        try:
            total = sum(map(int, parts[1 : cpu_number + 1]))
        except ValueError:
            # Some platforms emit lines with no counter columns (v4 #1007).
            total = 0
        out.append({"irq_line": irq_line, "irq_rate": total})
    return out


class PluginModel(GlancesPluginBase[list]):
    """Per-interrupt-line plugin (collection)."""

    plugin_name: ClassVar[str] = "irq"
    IS_COLLECTION: ClassVar[bool] = True
    EMITS_ALERTS: ClassVar[bool] = False
    # Mirrors v4 `[irq] disable=True`.
    DISABLED_BY_DEFAULT: ClassVar[bool] = True

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "irq_line": {
            "description": "IRQ line name, suffixed with the device alias when numeric.",
            "unit": "string",
            "primary_key": True,
        },
        "irq_rate": {
            "description": "Interrupts per second on this line.",
            "unit": "numberpersecond",
            "rate": True,
        },
    }

    def _read_proc(self) -> str:
        """Read `/proc/interrupts`. Seam for tests."""
        # The `open()` itself is inside the caller's try (Snap strict
        # confinement blocks at open, not at read).
        with open(IRQ_FILE) as f:
            return f.read()

    def _collect(self) -> list:
        if not LINUX:
            return []
        try:
            content = self._read_proc()
        except OSError as exc:
            # Missing on OpenVZ containers (v4 #947); also unreadable under
            # some confinements. Debug level: this is expected, not a fault.
            logger.debug("irq: cannot read %s: %s", IRQ_FILE, exc)
            return []
        return parse_interrupts(content)

    async def _grab_stats(self) -> list:
        return await asyncio.to_thread(self._collect)

    def _expand_parameters(self) -> None:
        """Sort by rate and keep the top N.

        Runs after `_transform_gauge` (so `irq_rate` is a real rate, not a
        counter) and before `_derived_parameters` — which stays untouched,
        keeping the plugin visible to `/api/5/irq/limits`.

        Items on their first appearance carry no `irq_rate` at all, so they
        sort last rather than raising.
        """
        if not isinstance(self._stats, list):
            return
        self._stats.sort(key=lambda item: item.get("irq_rate", 0.0), reverse=True)
        del self._stats[_TOP_N:]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_plugin_irq_v5.py -v`
Expected: PASS (11 tests)

- [ ] **Step 5: Run the full v5 suite**

Run: `make test-v5`
Expected: no new failures.

- [ ] **Step 6: Pre-commit, then stage**

```bash
git add glances/plugins/irq/model_v5.py tests/test_plugin_irq_v5.py
make pre-commit
```

If a hook rewrites a file, `git add` again and re-run. Do **not** commit.

---

### Task 2: `render_curses_v5.py` — left-sidebar table

**Files:**
- Create: `glances/plugins/irq/render_curses_v5.py`
- Test: `tests/test_plugin_irq_v5.py` (append)

**Interfaces:**
- Consumes: the payload published by Task 1 — `{"data": [{"irq_line": str, "irq_rate": float}, ...], "_levels": {...}}`.
- Produces: `render(payload, fields_desc)` returning `list[Row]`. Discovered automatically by `curses_renderer_v5` via the module path `glances.plugins.irq.render_curses_v5` — **no registration step**. `irq` is already listed in `LEFT_SLOT` (`glances/outputs/curses_renderer_v5.py:69`), so the layout needs no change either.

v4 reference (`glances/plugins/irq/__init__.py::msg_curse`): a `IRQ` title cell padded to `max_width - 7`, a right-aligned `Rate/s` header of width 9, then one line per IRQ with the same two columns.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_plugin_irq_v5.py`:

```python
from glances.plugins.irq.render_curses_v5 import render

_FIELDS = PluginModel.fields_description


def test_render_empty_payload_returns_no_rows():
    assert render({}, _FIELDS) == []
    assert render({"data": []}, _FIELDS) == []


def test_render_emits_a_header_then_one_row_per_irq():
    payload = {"data": [{"irq_line": "1_i8042", "irq_rate": 12.0}, {"irq_line": "LOC", "irq_rate": 3.0}]}
    rows = render(payload, _FIELDS)
    assert len(rows) == 3  # header + 2
    header = "".join(c.text for c in rows[0].cells)
    assert "IRQ" in header and "Rate/s" in header
    assert "1_i8042" in "".join(c.text for c in rows[1].cells)
    assert "LOC" in "".join(c.text for c in rows[2].cells)


def test_render_tolerates_an_item_without_a_rate():
    """Cycle-1 items carry no `irq_rate`; the renderer must not raise."""
    rows = render({"data": [{"irq_line": "1_i8042"}]}, _FIELDS)
    assert len(rows) == 2
    assert "1_i8042" in "".join(c.text for c in rows[1].cells)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_plugin_irq_v5.py -k render -v`
Expected: FAIL — `ModuleNotFoundError: ...render_curses_v5`

- [ ] **Step 3: Write the renderer**

Create `glances/plugins/irq/render_curses_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the irq plugin (left sidebar).

Mirrors v4 `irq.msg_curse()`: a two-column table, IRQ line name on the
left and interrupts-per-second right-aligned.

    IRQ                Rate/s
    1_i8042                12
    LOC                     3
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import Cell, ColorRole, Row

_RATE_WIDTH = 9


def _rate_text(value: Any) -> str:
    # A rate field is absent on an item's first cycle (no previous sample).
    if value is None:
        return "{:>{w}}".format("-", w=_RATE_WIDTH)
    return "{:>{w}}".format(f"{value:.0f}", w=_RATE_WIDTH)


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]]) -> list[Row]:
    if not isinstance(payload, dict):
        return []
    items = payload.get("data")
    if not isinstance(items, list) or not items:
        return []

    rows: list[Row] = [
        Row(
            cells=[
                Cell(text="IRQ", color=ColorRole.HEADER, bold=True),
                Cell(text="{:>{w}}".format("Rate/s", w=_RATE_WIDTH)),
            ]
        )
    ]
    for item in items:
        if not isinstance(item, dict):
            continue
        rows.append(
            Row(
                cells=[
                    Cell(text=str(item.get("irq_line", ""))),
                    Cell(text=_rate_text(item.get("irq_rate"))),
                ]
            )
        )
    return rows
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_plugin_irq_v5.py -v`
Expected: PASS (14 tests)

- [ ] **Step 5: Run the full v5 suite**

Run: `make test-v5`
Expected: no new failures.

- [ ] **Step 6: Pre-commit, then stage**

```bash
git add glances/plugins/irq/render_curses_v5.py tests/test_plugin_irq_v5.py
make pre-commit
```

Do **not** commit. Report that both tasks are staged.

---

## Manual smoke test (maintainer)

With `[irq] disable=False` in the config, on Linux:

```bash
python -m glances.main_v5 -s &
curl -s http://127.0.0.1:61208/api/5/irq          # 5 items max, rates present from cycle 2
curl -s http://127.0.0.1:61208/api/5/irq/limits   # {} — no thresholds on this plugin
python -m glances.main_v5                          # IRQ table in the left sidebar
```
