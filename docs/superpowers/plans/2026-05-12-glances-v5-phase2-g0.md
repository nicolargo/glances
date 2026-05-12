# Glances v5 Phase 2 — G0 (TUI scaffold + Phase 1 plugin wiring) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a curses-based TUI v5 in a dedicated thread, driven entirely by `fields_description`, displaying the 5 Phase 1 plugins (cpu, mem, load, network, percpu) with default rendering close to v4.

**Architecture:** Three-file split for testability: (1) pure formatters keyed by `unit`, (2) pure renderer producing a layout structure from a store snapshot, (3) curses I/O thread running the loop. Wired into `main_v5.py` with a new `--no-tui` flag (TUI on by default in standalone). Visual parity validated by reading v4 `msg_curse()` upfront and capturing the patterns in a reference document.

**Tech Stack:** Python 3.10+, stdlib `curses` and `threading`, pytest + pytest-asyncio (asyncio_mode=auto), unittest.mock for curses isolation.

---

## File Structure

| Path | Responsibility | Action |
|---|---|---|
| `docs/architecture/tui-v4-rendering-patterns.md` | Reference: v4 `msg_curse()` patterns extracted from cpu/mem/load/network/percpu plugins | Create |
| `glances/outputs/curses_formatters_v5.py` | Pure unit-driven formatters (`bytes` → `4.0G`, `percent` → `72.0%`, etc.) | Create |
| `glances/outputs/curses_renderer_v5.py` | Pure renderer: store snapshot + registry → layout structure | Create |
| `glances/outputs/glances_curses_v5.py` | Curses I/O thread orchestration | Create |
| `glances/main_v5.py` | Add `--no-tui` flag, wire TuiV5 in `assemble()` / `serve()` | Modify |
| `tests/test_curses_formatters_v5.py` | Formatter unit tests | Create |
| `tests/test_curses_renderer_v5.py` | Renderer unit tests | Create |
| `tests/test_curses_v5.py` | Thread/IO smoke tests with mocked curses | Create |
| `tests/test_main_v5.py` | Extended: assert `--no-tui` and TUI lifecycle | Modify |
| `docs/architecture/glances-v5-architecture-decisions.md` | §1.4 fleshed out, §3.2 `format`/`column_width` documented | Modify |
| `.claude/skills/SKILL-plugin.md` | Extended with renderer hints + visual-parity guidance | Modify |

---

## Task 1: v4 rendering-pattern catalogue

**Files:**
- Create: `docs/architecture/tui-v4-rendering-patterns.md`

**Why:** Visual parity is the spec contract (§7 of the design). We must extract the v4 `msg_curse()` patterns *before* building the renderer, so the generic v5 renderer is designed against an explicit reference, not by reverse-engineering during PR review.

- [ ] **Step 1: Read each v4 plugin's `msg_curse()`**

Read these five files and locate `msg_curse(self, args=None, max_width=None)` in each:

```bash
# Open each in turn:
glances/plugins/cpu/__init__.py
glances/plugins/mem/__init__.py
glances/plugins/load/__init__.py
glances/plugins/network/__init__.py
glances/plugins/percpu/__init__.py
```

For each plugin record: column widths (`{:>10}`, `{:7.2f}`), alignment (`<` / `>`), format strings, label strings, separators (`'|'`, spaces), header line, footer line, conditional color logic (`get_alert(...)`, `'OK'`, `'CAREFUL'`, `'WARNING'`, `'CRITICAL'`, `'DEFAULT'`).

- [ ] **Step 2: Write the catalogue**

Create `docs/architecture/tui-v4-rendering-patterns.md`. Structure each plugin section as:

````markdown
## <plugin_name>

**Source:** `glances/plugins/<plugin_name>/__init__.py::msg_curse`

**Header line:** `MEM           used: 8G  total: 16G`  (concrete v4 example with realistic values)

**Field table:**

| field | label | format | alignment | width | color rule |
|---|---|---|---|---|---|
| percent | `MEM` | `{:.1f}%` | right | 6 | level → CAREFUL/WARNING/CRITICAL color, DEFAULT otherwise |
| total | `total:` | `auto_unit(bytes)` | right | 6 | DEFAULT |
| used | `used:` | `auto_unit(bytes)` | right | 6 | DEFAULT |
| free | `free:` | `auto_unit(bytes)` | right | 6 | DEFAULT |

**Layout notes:** two-column grid, `MEM` label is bold prominent, other rows DEFAULT.

**Conditional behaviour:** none / hidden when `args.disable_mem` / etc.
````

Keep it factual — record what v4 *does*, not what v5 *should*. The renderer design (Tasks 3–5) consumes this document.

- [ ] **Step 3: Commit**

```bash
git add docs/architecture/tui-v4-rendering-patterns.md
git commit -m "docs(v5): document v4 msg_curse() patterns for the 5 Phase 1 plugins"
```

---

## Task 2: Architecture decisions doc — §3.2 renderer hints

**Files:**
- Modify: `docs/architecture/glances-v5-architecture-decisions.md:115` (the `fields_description` table)

- [ ] **Step 1: Add two rows to the §3.2 table**

In the table that lists every `fields_description` key, append after `exportable`:

```markdown
| `format` | `str` | Optional. Explicit Python format string for the renderer (`"%5.1f%%"`, `"%>10s"`). Overrides the default unit-driven formatter. Pure formatting hint — does **not** influence threshold computation, export, or any non-rendering logic. |
| `column_width` | `int` | Optional. Fixed width (characters) for this field's column in the TUI. Overrides the auto-sizing computed from the label and observed max content width. Pure formatting hint. |
```

- [ ] **Step 2: Append a note under the table**

```markdown
**Renderer hints are not layout descriptors.** `format` and `column_width` describe *how a single field is formatted*, never *where it sits relative to other fields*. The plugin's overall layout (which fields appear, in which order, in which column) remains the renderer's responsibility (§1.4) — consistent with the §3.6 rejection of `view_layout`.
```

- [ ] **Step 3: Commit**

```bash
git add docs/architecture/glances-v5-architecture-decisions.md
git commit -m "docs(v5): document optional fields_description renderer hints (format, column_width)"
```

---

## Task 3: Formatters — tests first

**Files:**
- Test: `tests/test_curses_formatters_v5.py`
- Create: `glances/outputs/curses_formatters_v5.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_curses_formatters_v5.py`:

```python
"""Glances v5 — tests for unit-driven curses formatters."""

from __future__ import annotations

import pytest

from glances.outputs.curses_formatters_v5 import (
    FORMATTERS,
    format_bytes,
    format_bytespers,
    format_number,
    format_percent,
    format_seconds,
    format_string,
    format_value,
)


# ---------------------------------------------------------------- bytes


@pytest.mark.parametrize(
    "value, expected",
    [
        (0, "0B"),
        (1, "1B"),
        (1023, "1023B"),
        (1024, "1.0K"),
        (1_500_000, "1.4M"),
        (1_073_741_824, "1.0G"),
        (1_099_511_627_776, "1.0T"),
    ],
)
def test_format_bytes(value, expected):
    assert format_bytes(value) == expected


# ---------------------------------------------------------------- percent


@pytest.mark.parametrize(
    "value, expected",
    [
        (0, "0.0%"),
        (12.345, "12.3%"),
        (100, "100.0%"),
    ],
)
def test_format_percent(value, expected):
    assert format_percent(value) == expected


# ---------------------------------------------------------------- bytespers


def test_format_bytespers_appends_per_second():
    assert format_bytespers(1024).endswith("/s")
    assert format_bytespers(0) == "0B/s"


# ---------------------------------------------------------------- seconds


@pytest.mark.parametrize(
    "value, expected",
    [
        (0, "0s"),
        (45, "45s"),
        (90, "1m30s"),
        (3661, "1h01m"),
        (90061, "1d01h"),
    ],
)
def test_format_seconds(value, expected):
    assert format_seconds(value) == expected


# ---------------------------------------------------------------- passthrough


def test_format_string_passthrough():
    assert format_string("eth0") == "eth0"
    assert format_string(None) == ""


def test_format_number_integer_when_round():
    assert format_number(42) == "42"
    assert format_number(42.0) == "42"
    assert format_number(3.14) == "3.14"


# ---------------------------------------------------------------- dispatch


def test_format_value_dispatches_on_unit():
    assert format_value(0.5, schema={"unit": "percent"}) == "0.5%"
    assert format_value(1024, schema={"unit": "bytes"}) == "1.0K"
    assert format_value("eth0", schema={"unit": "string"}) == "eth0"


def test_format_value_honours_explicit_format_hint():
    """`format` in the schema overrides the unit-driven default."""
    assert format_value(0.5, schema={"unit": "percent", "format": "%.3f%%"}) == "0.500%"


def test_format_value_falls_back_to_str_for_unknown_unit():
    assert format_value(42, schema={"unit": "unknown_unit"}) == "42"


def test_format_value_handles_missing_value():
    """Absent value renders as empty string, not 'None'."""
    assert format_value(None, schema={"unit": "bytes"}) == ""


def test_formatters_registry_contract():
    """Every formatter in FORMATTERS takes a value and returns a str."""
    for unit, fn in FORMATTERS.items():
        result = fn(0)
        assert isinstance(result, str), f"Formatter for {unit!r} returned {type(result).__name__}"
```

- [ ] **Step 2: Run and confirm failure**

```bash
make test-v5 ARGS="tests/test_curses_formatters_v5.py"
```

Expected: `ImportError` (module does not exist yet) or all tests FAIL.

- [ ] **Step 3: Implement the formatters**

Create `glances/outputs/curses_formatters_v5.py`:

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit-driven formatters for the curses TUI renderer.

Every formatter takes a single raw value and returns a printable string.
The mapping `unit → formatter` is the contract between
`fields_description` and the renderer. A field whose `unit` is not in
`FORMATTERS` falls back to `str(value)`.

An optional `format` key in `fields_description` (§3.2 renderer hint)
overrides the unit-driven default with an explicit Python format string.
"""

from __future__ import annotations

from typing import Any, Callable

# ----------------------------------------------------------------- atoms


def _auto_unit(value: float, suffix: str = "") -> str:
    """K/M/G/T scaling à la `glances.tools.bytes2human` but minimal.

    Matches v4 visual output: one decimal for ≥ K, integer for < K.
    """
    abs_v = abs(value)
    for symbol, threshold in (
        ("T", 1_099_511_627_776),
        ("G", 1_073_741_824),
        ("M", 1_048_576),
        ("K", 1024),
    ):
        if abs_v >= threshold:
            return f"{value / threshold:.1f}{symbol}{suffix}"
    return f"{int(value)}B{suffix}"


def format_bytes(value: Any) -> str:
    try:
        return _auto_unit(float(value))
    except (TypeError, ValueError):
        return ""


def format_bytespers(value: Any) -> str:
    try:
        return _auto_unit(float(value), suffix="/s")
    except (TypeError, ValueError):
        return ""


def format_percent(value: Any) -> str:
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return ""


def format_seconds(value: Any) -> str:
    try:
        secs = int(float(value))
    except (TypeError, ValueError):
        return ""
    if secs < 60:
        return f"{secs}s"
    minutes, secs = divmod(secs, 60)
    if minutes < 60:
        return f"{minutes}m{secs:02d}s"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h{minutes:02d}m"
    days, hours = divmod(hours, 24)
    return f"{days}d{hours:02d}h"


def format_number(value: Any) -> str:
    if value is None:
        return ""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return str(value)
    if f.is_integer():
        return str(int(f))
    # Two decimals for non-integers, trimming trailing zeros.
    return f"{f:.2f}".rstrip("0").rstrip(".")


def format_string(value: Any) -> str:
    return "" if value is None else str(value)


def format_bool(value: Any) -> str:
    if value is None:
        return ""
    return "yes" if bool(value) else "no"


# ----------------------------------------------------------------- registry


FORMATTERS: dict[str, Callable[[Any], str]] = {
    "bytes": format_bytes,
    "bytespers": format_bytespers,
    "percent": format_percent,
    "seconds": format_seconds,
    "number": format_number,
    "string": format_string,
    "bool": format_bool,
}


# ----------------------------------------------------------------- dispatch


def format_value(value: Any, schema: dict[str, Any]) -> str:
    """Format `value` using the explicit `format` hint or the unit-default.

    Precedence:
        1. `schema["format"]` (an explicit Python format string)
        2. `FORMATTERS[schema["unit"]]`
        3. `str(value)`
    """
    if value is None:
        return ""
    explicit = schema.get("format")
    if explicit:
        try:
            return explicit % value
        except (TypeError, ValueError):
            return str(value)
    unit = schema.get("unit", "")
    formatter = FORMATTERS.get(unit)
    if formatter is not None:
        return formatter(value)
    return str(value)
```

- [ ] **Step 4: Run tests and verify pass**

```bash
make test-v5 ARGS="tests/test_curses_formatters_v5.py"
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add glances/outputs/curses_formatters_v5.py tests/test_curses_formatters_v5.py
git commit -m "feat(v5): add unit-driven curses formatters"
```

---

## Task 4: Renderer dataclasses + scalar plugin rendering — tests first

**Files:**
- Test: `tests/test_curses_renderer_v5.py`
- Create: `glances/outputs/curses_renderer_v5.py`

The renderer is a pure function tree: it takes a snapshot of the StatsStore (dict of `plugin_name → payload`), a registry mapping plugin names to display positions, and the alert history, and returns a `Frame` — a structured list of `Row`s of `Cell`s. The curses I/O layer (Task 6) consumes `Frame` and plots it.

This task covers the dataclasses and `render_scalar_plugin`. Collection plugins and the footer come in Task 5.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_curses_renderer_v5.py`:

```python
"""Glances v5 — tests for the pure curses renderer."""

from __future__ import annotations

import pytest

from glances.outputs.curses_renderer_v5 import (
    Cell,
    ColorRole,
    Row,
    render_scalar_plugin,
)


# ---------------------------------------------------------------- dataclasses


def test_cell_defaults_to_default_color():
    cell = Cell(text="42")
    assert cell.color == ColorRole.DEFAULT


def test_row_holds_cells():
    row = Row(cells=[Cell("A"), Cell("B")])
    assert [c.text for c in row.cells] == ["A", "B"]


# ---------------------------------------------------------------- scalar plugin


MEM_FIELDS = {
    "total": {"unit": "bytes", "label": "total"},
    "available": {"unit": "bytes", "label": "avail"},
    "percent": {
        "unit": "percent",
        "label": "MEM",
        "watched": True,
        "prominent": True,
    },
    "used": {"unit": "bytes", "label": "used"},
    "free": {"unit": "bytes", "label": "free"},
}


def _mem_payload(level: str = "ok") -> dict:
    return {
        "total": 16_000_000_000,
        "available": 8_000_000_000,
        "percent": 72.0,
        "used": 8_000_000_000,
        "free": 4_000_000_000,
        "_levels": {"percent": {"level": level, "prominent": True}},
    }


def test_render_scalar_returns_at_least_one_row():
    rows = render_scalar_plugin("mem", _mem_payload(), MEM_FIELDS)
    assert len(rows) >= 1


def test_render_scalar_header_includes_plugin_label():
    """The first row carries the plugin's prominent label ('MEM') in upper-case."""
    rows = render_scalar_plugin("mem", _mem_payload(), MEM_FIELDS)
    header = rows[0]
    joined = " ".join(c.text for c in header.cells)
    assert "MEM" in joined


def test_render_scalar_shows_percent_value():
    rows = render_scalar_plugin("mem", _mem_payload(), MEM_FIELDS)
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "72.0%" in flat


def test_render_scalar_formats_bytes_fields():
    rows = render_scalar_plugin("mem", _mem_payload(), MEM_FIELDS)
    flat = " ".join(c.text for row in rows for c in row.cells)
    # 16 GB total
    assert "14.9G" in flat or "15.9G" in flat  # 16_000_000_000 / 1024^3 ≈ 14.9


def test_render_scalar_applies_warning_color_on_watched_field():
    rows = render_scalar_plugin("mem", _mem_payload(level="warning"), MEM_FIELDS)
    percent_cells = [c for row in rows for c in row.cells if "%" in c.text]
    assert percent_cells
    assert percent_cells[0].color == ColorRole.WARNING


def test_render_scalar_applies_critical_color_with_prominent():
    rows = render_scalar_plugin("mem", _mem_payload(level="critical"), MEM_FIELDS)
    percent_cells = [c for row in rows for c in row.cells if "%" in c.text]
    assert percent_cells[0].color == ColorRole.CRITICAL
    # prominent=True triggers background-highlight rendering — exposed as
    # the `prominent` flag on the cell so the curses layer can pick the
    # right attribute (A_REVERSE vs plain colour).
    assert percent_cells[0].prominent is True


def test_render_scalar_handles_empty_payload():
    """Cycle-0: plugin registered but no data yet."""
    rows = render_scalar_plugin("mem", {}, MEM_FIELDS)
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "MEM" in flat  # header still rendered
    # No percent value — should not crash.


def test_render_scalar_honours_explicit_format_hint():
    fields = {
        "percent": {"unit": "percent", "label": "CPU", "format": "%.3f%%"},
    }
    rows = render_scalar_plugin("cpu", {"percent": 12.345}, fields)
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "12.345%" in flat
```

- [ ] **Step 2: Run and confirm failure**

```bash
make test-v5 ARGS="tests/test_curses_renderer_v5.py"
```

Expected: ImportError or assertion failures.

- [ ] **Step 3: Implement the dataclasses and scalar renderer**

Create `glances/outputs/curses_renderer_v5.py`:

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — pure curses renderer (no I/O).

The renderer is the layout brain of the TUI: it takes a snapshot of the
StatsStore (a `dict` of `plugin_name → payload`) plus the alert history
and produces a structured `Frame` of `Row`s of `Cell`s. The curses I/O
thread (glances_curses_v5.py) then plots the frame onto the terminal.

Keeping the renderer pure (no curses, no threading, no I/O) lets us
unit-test layout decisions exhaustively without driving a real terminal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from glances.outputs.curses_formatters_v5 import format_value


class ColorRole(Enum):
    """Renderer-internal color role. The curses I/O layer maps each role
    to a concrete curses color pair (§ glances_curses_v5)."""

    DEFAULT = "default"
    OK = "ok"
    CAREFUL = "careful"
    WARNING = "warning"
    CRITICAL = "critical"
    HEADER = "header"


# Map alert level (from `_levels`) to renderer color role.
_LEVEL_TO_ROLE: dict[str, ColorRole] = {
    "ok": ColorRole.OK,
    "careful": ColorRole.CAREFUL,
    "warning": ColorRole.WARNING,
    "critical": ColorRole.CRITICAL,
}


@dataclass
class Cell:
    """One renderable unit on a row."""

    text: str
    color: ColorRole = ColorRole.DEFAULT
    prominent: bool = False  # background highlight when True (cf. §3.3)


@dataclass
class Row:
    cells: list[Cell] = field(default_factory=list)


@dataclass
class Frame:
    """The complete TUI screen: ordered rows for left/right columns + footer."""

    left: list[Row] = field(default_factory=list)
    right: list[Row] = field(default_factory=list)
    footer: list[Row] = field(default_factory=list)


# ----------------------------------------------------------------- helpers


def _level_entry(payload: dict[str, Any], field_name: str) -> dict[str, Any]:
    levels = payload.get("_levels", {})
    if isinstance(levels, dict):
        entry = levels.get(field_name)
        if isinstance(entry, dict):
            return entry
    return {}


def _cell_for_field(
    field_name: str,
    value: Any,
    schema: dict[str, Any],
    payload: dict[str, Any],
) -> Cell:
    text = format_value(value, schema)
    entry = _level_entry(payload, field_name)
    level = entry.get("level")
    role = _LEVEL_TO_ROLE.get(level, ColorRole.DEFAULT)
    prominent = bool(entry.get("prominent")) if entry else False
    return Cell(text=text, color=role, prominent=prominent)


# ----------------------------------------------------------------- scalar


def render_scalar_plugin(
    plugin_name: str,
    payload: dict[str, Any],
    fields_desc: dict[str, dict[str, Any]],
) -> list[Row]:
    """Render a scalar plugin (`mem`, `cpu`, `load`).

    Layout: a header row carrying the plugin label, then one row per
    visible field showing `label: value`. The "primary" field (the only
    `watched: True` one or the first declared) is highlighted in the
    header alongside the plugin name.

    The header label is the plugin's most-prominent watched field's
    `label` upper-cased (e.g. `MEM` for the `percent` field of the `mem`
    plugin). Falls back to the plugin_name in upper case when no watched
    field is found.
    """
    header_label, primary_field = _resolve_header(plugin_name, fields_desc)
    header_cells: list[Cell] = [Cell(text=header_label, color=ColorRole.HEADER)]

    if primary_field and primary_field in payload:
        header_cells.append(
            _cell_for_field(primary_field, payload.get(primary_field), fields_desc[primary_field], payload)
        )

    rows: list[Row] = [Row(cells=header_cells)]

    for field_name, schema in fields_desc.items():
        if field_name == primary_field:
            continue
        if field_name not in payload:
            continue
        label = schema.get("label") or field_name
        value_cell = _cell_for_field(field_name, payload.get(field_name), schema, payload)
        rows.append(Row(cells=[Cell(text=f"{label}:"), value_cell]))

    return rows


def _resolve_header(plugin_name: str, fields_desc: dict[str, dict[str, Any]]) -> tuple[str, str | None]:
    """Pick (header label, primary field) for a scalar plugin.

    Heuristic: the first watched field wins; if none is watched, the
    plugin_name itself becomes the header and no primary field is shown
    inline.
    """
    for name, schema in fields_desc.items():
        if schema.get("watched"):
            label = (schema.get("label") or plugin_name).upper()
            return label, name
    return plugin_name.upper(), None
```

- [ ] **Step 4: Run and verify pass**

```bash
make test-v5 ARGS="tests/test_curses_renderer_v5.py"
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add glances/outputs/curses_renderer_v5.py tests/test_curses_renderer_v5.py
git commit -m "feat(v5): add curses renderer dataclasses and scalar plugin rendering"
```

---

## Task 5: Collection plugin rendering + alerts footer + Frame builder — tests first

**Files:**
- Test: `tests/test_curses_renderer_v5.py` (extend)
- Modify: `glances/outputs/curses_renderer_v5.py`

- [ ] **Step 1: Append failing tests**

Append to `tests/test_curses_renderer_v5.py`:

```python
# ---------------------------------------------------------------- collection plugin


NETWORK_FIELDS = {
    "interface_name": {"unit": "string", "label": "iface", "primary_key": True},
    "bytes_recv": {"unit": "bytespers", "label": "Rx", "rate": True, "watched": True, "prominent": True},
    "bytes_sent": {"unit": "bytespers", "label": "Tx", "rate": True, "watched": True, "prominent": True},
    "is_up": {"unit": "bool", "label": "up"},
}


def _network_payload() -> dict:
    return {
        "data": [
            {"interface_name": "eth0", "bytes_recv": 1200.0, "bytes_sent": 300.0, "is_up": True},
            {"interface_name": "lo", "bytes_recv": 0.0, "bytes_sent": 0.0, "is_up": True},
        ],
        "_levels": {
            "eth0": {
                "bytes_recv": {"level": "warning", "prominent": True},
                "bytes_sent": {"level": "ok", "prominent": True},
            },
            "lo": {
                "bytes_recv": {"level": "ok", "prominent": True},
                "bytes_sent": {"level": "ok", "prominent": True},
            },
        },
    }


def test_render_collection_returns_header_plus_one_row_per_item():
    from glances.outputs.curses_renderer_v5 import render_collection_plugin

    rows = render_collection_plugin("network", _network_payload(), NETWORK_FIELDS)
    # 1 header + 2 interfaces
    assert len(rows) == 3


def test_render_collection_header_uses_plugin_name_uppercase():
    from glances.outputs.curses_renderer_v5 import render_collection_plugin

    rows = render_collection_plugin("network", _network_payload(), NETWORK_FIELDS)
    header_text = " ".join(c.text for c in rows[0].cells)
    assert "NETWORK" in header_text


def test_render_collection_emits_per_item_level_colors():
    from glances.outputs.curses_renderer_v5 import render_collection_plugin

    rows = render_collection_plugin("network", _network_payload(), NETWORK_FIELDS)
    # Find the eth0 row and check Rx cell color.
    eth_row = next(r for r in rows if any("eth0" in c.text for c in r.cells))
    rx_cells = [c for c in eth_row.cells if c.text.endswith("/s") and c.color != ColorRole.DEFAULT]
    assert any(c.color == ColorRole.WARNING for c in rx_cells)


def test_render_collection_skips_filtered_items_handled_upstream():
    """The base class filters items before the renderer sees them."""
    from glances.outputs.curses_renderer_v5 import render_collection_plugin

    payload = {"data": [], "_levels": {}}
    rows = render_collection_plugin("network", payload, NETWORK_FIELDS)
    # Just the header, no item rows.
    assert len(rows) == 1


# ---------------------------------------------------------------- footer


def test_render_alert_footer_shows_recent_events():
    from glances.outputs.curses_renderer_v5 import render_alert_footer

    history = [
        {"ts": "2026-05-12T10:00:00+00:00", "plugin": "mem", "key": None, "field": "percent",
         "level": "warning", "previous_level": "ok", "value": 73.0, "prominent": True, "hostname": "h"},
        {"ts": "2026-05-12T10:01:00+00:00", "plugin": "network", "key": "eth0", "field": "bytes_recv",
         "level": "critical", "previous_level": "warning", "value": 9e7, "prominent": True, "hostname": "h"},
    ]
    rows = render_alert_footer(history, limit=10)
    assert len(rows) == 1 + 2  # header + 2 events
    flat = " ".join(c.text for row in rows for c in row.cells)
    assert "mem" in flat
    assert "eth0" in flat


def test_render_alert_footer_truncates_to_limit():
    from glances.outputs.curses_renderer_v5 import render_alert_footer

    history = [
        {"ts": f"2026-05-12T10:0{i}:00+00:00", "plugin": "mem", "key": None, "field": "percent",
         "level": "warning", "previous_level": "ok", "value": 73.0, "prominent": True, "hostname": "h"}
        for i in range(5)
    ]
    rows = render_alert_footer(history, limit=3)
    # 1 header + 3 events (the most recent 3).
    assert len(rows) == 4


def test_render_alert_footer_handles_empty_history():
    from glances.outputs.curses_renderer_v5 import render_alert_footer

    rows = render_alert_footer([], limit=10)
    # Just a header saying "no alerts" or similar — exact wording unspecified,
    # but it must produce at least one row and not crash.
    assert len(rows) >= 1


# ---------------------------------------------------------------- frame builder


def test_build_frame_arranges_scalars_left_collections_right():
    from glances.outputs.curses_renderer_v5 import build_frame

    store_snapshot = {
        "mem": _mem_payload(),
        "network": _network_payload(),
    }
    fields_by_plugin = {
        "mem": MEM_FIELDS,
        "network": NETWORK_FIELDS,
    }
    registry = [("mem", False), ("network", True)]  # (plugin_name, is_collection)

    frame = build_frame(store_snapshot, fields_by_plugin, registry, alerts_history=[])

    # mem is scalar → left column. network is collection → right column.
    assert frame.left
    assert frame.right
    assert any("MEM" in c.text for row in frame.left for c in row.cells)
    assert any("NETWORK" in c.text for row in frame.right for c in row.cells)


def test_build_frame_handles_missing_plugin_payload():
    """A plugin in the registry but absent from the store (cycle-0)."""
    from glances.outputs.curses_renderer_v5 import build_frame

    frame = build_frame(
        store_snapshot={},
        fields_by_plugin={"mem": MEM_FIELDS},
        registry=[("mem", False)],
        alerts_history=[],
    )
    # Header rendered, no value rows.
    flat = " ".join(c.text for row in frame.left for c in row.cells)
    assert "MEM" in flat
```

- [ ] **Step 2: Run and confirm failure**

```bash
make test-v5 ARGS="tests/test_curses_renderer_v5.py"
```

Expected: failures on the new tests.

- [ ] **Step 3: Implement collection rendering, footer, and Frame builder**

Append to `glances/outputs/curses_renderer_v5.py`:

```python
# ----------------------------------------------------------------- collection


def render_collection_plugin(
    plugin_name: str,
    payload: dict[str, Any],
    fields_desc: dict[str, dict[str, Any]],
) -> list[Row]:
    """Render a collection plugin (`network`, `fs`, …).

    Layout:
        Header row with the plugin name and column labels.
        One row per item, each cell formatted per `fields_desc`.

    The primary-key field is always the leftmost column. Other columns
    appear in `fields_desc` declaration order. Per-item `_levels` are
    looked up under `payload['_levels'][pk_value]`.
    """
    pk_field = _resolve_primary_key(fields_desc)
    # Column order: primary key first, then non-pk fields in declaration order.
    visible_fields = [name for name in fields_desc if name != pk_field]

    # Header row.
    header_cells: list[Cell] = [Cell(text=plugin_name.upper(), color=ColorRole.HEADER)]
    if pk_field:
        header_cells.append(Cell(text=fields_desc[pk_field].get("label", pk_field), color=ColorRole.HEADER))
    for name in visible_fields:
        header_cells.append(Cell(text=fields_desc[name].get("label", name), color=ColorRole.HEADER))
    rows: list[Row] = [Row(cells=header_cells)]

    # Item rows.
    items = payload.get("data", []) if isinstance(payload, dict) else []
    levels_index = payload.get("_levels", {}) if isinstance(payload, dict) else {}

    for item in items:
        if not isinstance(item, dict):
            continue
        pk_value = item.get(pk_field) if pk_field else None
        item_levels = levels_index.get(pk_value, {}) if isinstance(levels_index, dict) else {}
        # Synthesise a per-item payload so `_cell_for_field` can resolve levels.
        per_item_payload = {**item, "_levels": item_levels}

        cells: list[Cell] = [Cell(text="")]  # spacer under the plugin-name header column
        if pk_field:
            cells.append(Cell(text=format_value(item.get(pk_field), fields_desc[pk_field])))
        for name in visible_fields:
            cells.append(_cell_for_field(name, item.get(name), fields_desc[name], per_item_payload))
        rows.append(Row(cells=cells))

    return rows


def _resolve_primary_key(fields_desc: dict[str, dict[str, Any]]) -> str | None:
    for name, schema in fields_desc.items():
        if schema.get("primary_key"):
            return name
    return None


# ----------------------------------------------------------------- footer


def render_alert_footer(history: list[dict[str, Any]], limit: int = 10) -> list[Row]:
    """Render the alert history footer (vertical list, most recent at top).

    Header row: `ALERTS (n)`. Then up to `limit` event rows showing
    timestamp, plugin/key, field, transition (previous → new). When the
    history is empty, a single info row is shown.
    """
    rows: list[Row] = [Row(cells=[Cell(text=f"ALERTS ({len(history)})", color=ColorRole.HEADER)])]
    if not history:
        rows.append(Row(cells=[Cell(text="(no events)")]))
        return rows

    recent = list(reversed(history[-limit:]))
    for evt in recent:
        ts = str(evt.get("ts", "")).split("T")[-1][:8]  # HH:MM:SS
        plugin = str(evt.get("plugin", ""))
        key = evt.get("key")
        target = f"{plugin}[{key}]" if key is not None else plugin
        field_name = str(evt.get("field", ""))
        previous = str(evt.get("previous_level", ""))
        new_level = str(evt.get("level", ""))
        prominent = bool(evt.get("prominent", False))
        role = _LEVEL_TO_ROLE.get(new_level, ColorRole.DEFAULT)
        rows.append(
            Row(cells=[
                Cell(text=ts),
                Cell(text=target),
                Cell(text=field_name),
                Cell(text=f"{previous} → {new_level}", color=role, prominent=prominent),
            ])
        )
    return rows


# ----------------------------------------------------------------- frame


def build_frame(
    store_snapshot: dict[str, dict[str, Any]],
    fields_by_plugin: dict[str, dict[str, dict[str, Any]]],
    registry: list[tuple[str, bool]],
    alerts_history: list[dict[str, Any]],
    alerts_limit: int = 10,
) -> Frame:
    """Assemble a complete TUI Frame.

    Args:
        store_snapshot: `{plugin_name: payload}` — a shallow copy of the store.
        fields_by_plugin: `{plugin_name: fields_description}`.
        registry: ordered list of `(plugin_name, is_collection)` — controls
            which plugins are displayed and in which order.
        alerts_history: the deque output of `GlancesAlerts.get_history()`.
        alerts_limit: cap on the number of events rendered in the footer.

    Rules:
        - Scalar plugins → left column.
        - Collection plugins → right column.
        - Footer → alerts history.
        - A plugin in the registry with no payload (cycle-0) still gets its
          header rendered.
    """
    frame = Frame()
    for plugin_name, is_collection in registry:
        payload = store_snapshot.get(plugin_name) or {}
        fields_desc = fields_by_plugin.get(plugin_name, {})
        if is_collection:
            frame.right.extend(render_collection_plugin(plugin_name, payload, fields_desc))
            frame.right.append(Row(cells=[Cell(text="")]))  # spacer between plugins
        else:
            frame.left.extend(render_scalar_plugin(plugin_name, payload, fields_desc))
            frame.left.append(Row(cells=[Cell(text="")]))
    frame.footer = render_alert_footer(alerts_history, limit=alerts_limit)
    return frame
```

- [ ] **Step 4: Run all renderer tests**

```bash
make test-v5 ARGS="tests/test_curses_renderer_v5.py"
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add glances/outputs/curses_renderer_v5.py tests/test_curses_renderer_v5.py
git commit -m "feat(v5): add collection rendering, alerts footer, and Frame builder"
```

---

## Task 6: TuiV5 thread + curses I/O — tests first

**Files:**
- Test: `tests/test_curses_v5.py`
- Create: `glances/outputs/glances_curses_v5.py`

This task wires the renderer to a curses window in a dedicated thread. The thread reads the store lockless (architecture §1.3), builds a Frame each cycle, paints it, then sleeps `refresh_time` before the next paint. A `threading.Event` signals shutdown.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_curses_v5.py`:

```python
"""Glances v5 — smoke tests for the curses TUI thread.

The thread is fully exercised under a mocked `curses` module so the suite
runs headless. The visual layer (color attributes, addstr placement) is
checked through assertions on the mock; logic is tested via the pure
renderer in test_curses_renderer_v5.
"""

from __future__ import annotations

import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------- fixtures


@pytest.fixture
def fake_store():
    store = MagicMock()
    store.as_dict.return_value = {
        "mem": {
            "total": 16_000_000_000,
            "available": 8_000_000_000,
            "percent": 72.0,
            "_levels": {"percent": {"level": "warning", "prominent": True}},
        },
    }
    return store


@pytest.fixture
def fake_alerts():
    alerts = MagicMock()
    alerts.get_history.return_value = []
    return alerts


@pytest.fixture
def fake_config():
    cfg = MagicMock()
    cfg.get.side_effect = lambda section, key, default=None: default
    return cfg


# ---------------------------------------------------------------- lifecycle


def test_tui_v5_can_start_and_stop_without_curses(monkeypatch, fake_store, fake_alerts, fake_config):
    """The thread enters its loop and exits cleanly when stop() is called."""
    from glances.outputs import glances_curses_v5 as tui_mod

    # Replace `curses.wrapper(fn)` with a sentinel that just invokes fn(stdscr=fake).
    fake_stdscr = MagicMock()
    monkeypatch.setattr(tui_mod, "_safe_curses_wrapper", lambda fn: fn(fake_stdscr))

    fake_registry = [("mem", False)]
    fake_fields = {"mem": {
        "percent": {"unit": "percent", "label": "MEM", "watched": True, "prominent": True}
    }}

    tui = tui_mod.TuiV5(
        store=fake_store,
        alerts=fake_alerts,
        config=fake_config,
        registry=fake_registry,
        fields_by_plugin=fake_fields,
        refresh_interval=0.01,
    )

    tui.start()
    time.sleep(0.05)  # let the loop run a few iterations
    tui.stop()
    tui.join(timeout=1.0)
    assert not tui.is_alive()


def test_tui_v5_calls_addstr_for_rendered_cells(monkeypatch, fake_store, fake_alerts, fake_config):
    """The thread paints something onto stdscr each cycle."""
    from glances.outputs import glances_curses_v5 as tui_mod

    fake_stdscr = MagicMock()
    fake_stdscr.getmaxyx.return_value = (24, 80)
    fake_stdscr.getch.return_value = -1  # no keypress

    captured: list[tuple] = []

    def record_wrapper(fn):
        # Run the curses loop body inline, then bail out so the test ends.
        fn(fake_stdscr)

    monkeypatch.setattr(tui_mod, "_safe_curses_wrapper", record_wrapper)

    registry = [("mem", False)]
    fields = {"mem": {
        "percent": {"unit": "percent", "label": "MEM", "watched": True, "prominent": True}
    }}

    tui = tui_mod.TuiV5(
        store=fake_store, alerts=fake_alerts, config=fake_config,
        registry=registry, fields_by_plugin=fields, refresh_interval=0.01,
    )
    tui.start()
    time.sleep(0.05)
    tui.stop()
    tui.join(timeout=1.0)

    # At least one addstr call must have happened with text containing 'MEM'.
    addstr_calls = [c for c in fake_stdscr.addstr.call_args_list]
    assert addstr_calls, "addstr was never called"
    flat = " ".join(str(args) for args in addstr_calls)
    assert "MEM" in flat


def test_tui_v5_quit_on_q_key(monkeypatch, fake_store, fake_alerts, fake_config):
    """Pressing 'q' triggers stop()."""
    from glances.outputs import glances_curses_v5 as tui_mod

    fake_stdscr = MagicMock()
    fake_stdscr.getmaxyx.return_value = (24, 80)
    fake_stdscr.getch.side_effect = [ord("q"), -1, -1]

    monkeypatch.setattr(tui_mod, "_safe_curses_wrapper", lambda fn: fn(fake_stdscr))

    tui = tui_mod.TuiV5(
        store=fake_store, alerts=fake_alerts, config=fake_config,
        registry=[("mem", False)], fields_by_plugin={"mem": {}},
        refresh_interval=0.01,
    )
    tui.start()
    tui.join(timeout=1.0)
    assert not tui.is_alive()
    assert tui._stop_event.is_set()
```

- [ ] **Step 2: Run and confirm failure**

```bash
make test-v5 ARGS="tests/test_curses_v5.py"
```

Expected: ImportError on the module.

- [ ] **Step 3: Implement the TuiV5 thread**

Create `glances/outputs/glances_curses_v5.py`:

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — curses TUI thread.

A `threading.Thread` runs the curses event loop independently of the
asyncio scheduler (architecture §1.4). Each cycle:

    1. Build a Frame from a lockless store snapshot + alert history.
    2. Paint the Frame to stdscr via `_paint`.
    3. Poll a keypress (`q` / `ESC` → stop), refresh.
    4. Sleep `refresh_interval`.

A `threading.Event` is the shutdown channel; the main asyncio task sets
it in its `finally` clause to stop the thread cleanly.
"""

from __future__ import annotations

import curses
import logging
import threading
import time
from typing import Any

from glances.alerts_v5 import GlancesAlerts
from glances.config_v5 import GlancesConfigV5
from glances.outputs.curses_renderer_v5 import (
    Cell,
    ColorRole,
    Frame,
    build_frame,
)
from glances.stats_store_v5 import StatsStoreV5

logger = logging.getLogger(__name__)


# Map our renderer ColorRole → curses color pair index.
# Filled in `_init_colors` once curses is initialised.
_COLOR_PAIRS: dict[ColorRole, int] = {}


def _safe_curses_wrapper(fn):
    """`curses.wrapper` wrapper — separated so tests can monkeypatch it."""
    curses.wrapper(fn)


class TuiV5(threading.Thread):
    """Curses TUI v5 thread."""

    def __init__(
        self,
        store: StatsStoreV5,
        alerts: GlancesAlerts | None,
        config: GlancesConfigV5,
        registry: list[tuple[str, bool]],
        fields_by_plugin: dict[str, dict[str, dict[str, Any]]],
        refresh_interval: float = 1.0,
    ) -> None:
        super().__init__(name="glances-tui-v5", daemon=True)
        self.store = store
        self.alerts = alerts
        self.config = config
        self.registry = registry
        self.fields_by_plugin = fields_by_plugin
        self.refresh_interval = refresh_interval
        self._stop_event = threading.Event()

    # ----------------------------------------------------------- control

    def stop(self) -> None:
        """Signal the thread to exit at the next loop iteration."""
        self._stop_event.set()

    # ----------------------------------------------------------- run loop

    def run(self) -> None:
        try:
            _safe_curses_wrapper(self._loop)
        except Exception as e:  # pragma: no cover — defensive
            logger.warning("TUI v5 crashed: %s", e)

    def _loop(self, stdscr) -> None:
        _init_colors()
        # Non-blocking input so the loop can refresh on its own cadence.
        stdscr.nodelay(True)
        try:
            curses.curs_set(0)
        except curses.error:
            pass  # terminals without cursor support — ignore

        while not self._stop_event.is_set():
            frame = self._build_frame()
            self._paint(stdscr, frame)
            stdscr.refresh()

            key = stdscr.getch()
            if key in (ord("q"), 27):  # 27 = ESC
                self.stop()
                break

            # Sleep in small steps so stop() responds quickly.
            self._sleep_responsive(self.refresh_interval)

    def _sleep_responsive(self, total: float, step: float = 0.05) -> None:
        elapsed = 0.0
        while elapsed < total and not self._stop_event.is_set():
            time.sleep(step)
            elapsed += step

    # ----------------------------------------------------------- helpers

    def _build_frame(self) -> Frame:
        snapshot = self.store.as_dict()
        history = self.alerts.get_history() if self.alerts is not None else []
        return build_frame(
            store_snapshot=snapshot,
            fields_by_plugin=self.fields_by_plugin,
            registry=self.registry,
            alerts_history=history,
        )

    # ----------------------------------------------------------- paint

    def _paint(self, stdscr, frame: Frame) -> None:
        stdscr.erase()
        max_y, max_x = stdscr.getmaxyx()

        left_width = max_x // 2
        right_x = left_width
        right_width = max_x - left_width

        self._paint_column(stdscr, frame.left, 0, 0, left_width, max_y - len(frame.footer) - 1)
        self._paint_column(stdscr, frame.right, 0, right_x, right_width, max_y - len(frame.footer) - 1)
        self._paint_column(stdscr, frame.footer, max_y - len(frame.footer), 0, max_x, len(frame.footer))

    def _paint_column(self, stdscr, rows, y0: int, x0: int, width: int, height: int) -> None:
        for i, row in enumerate(rows[:height]):
            x = x0
            for cell in row.cells:
                if x >= x0 + width:
                    break
                text = cell.text[: x0 + width - x]
                attr = _attr_for(cell)
                try:
                    stdscr.addstr(y0 + i, x, text, attr)
                except curses.error:
                    # Drawing past the screen — silently skip the rest of the row.
                    break
                x += len(text) + 1  # one-space gap between cells


# ----------------------------------------------------------------- colors


def _init_colors() -> None:
    if not curses.has_colors():
        return
    curses.start_color()
    try:
        curses.use_default_colors()
    except curses.error:
        pass
    # Pair index 0 is reserved by curses for DEFAULT.
    pairs = [
        (ColorRole.OK, curses.COLOR_GREEN),
        (ColorRole.CAREFUL, curses.COLOR_BLUE),
        (ColorRole.WARNING, curses.COLOR_MAGENTA),
        (ColorRole.CRITICAL, curses.COLOR_RED),
        (ColorRole.HEADER, curses.COLOR_CYAN),
    ]
    for i, (role, color) in enumerate(pairs, start=1):
        try:
            curses.init_pair(i, color, -1)
        except curses.error:
            curses.init_pair(i, color, curses.COLOR_BLACK)
        _COLOR_PAIRS[role] = curses.color_pair(i)
    _COLOR_PAIRS[ColorRole.DEFAULT] = curses.color_pair(0)


def _attr_for(cell: Cell) -> int:
    attr = _COLOR_PAIRS.get(cell.color, 0)
    if cell.color == ColorRole.HEADER:
        attr |= curses.A_BOLD
    if cell.prominent and cell.color in (ColorRole.WARNING, ColorRole.CRITICAL):
        attr |= curses.A_REVERSE
    return attr
```

- [ ] **Step 4: Run and verify pass**

```bash
make test-v5 ARGS="tests/test_curses_v5.py"
```

Expected: all green. If the mocked `getch` behaviour causes intermittent failures (the thread can run faster than the side_effect list), keep `side_effect` lists at length 3+ — they're already sized for that.

- [ ] **Step 5: Commit**

```bash
git add glances/outputs/glances_curses_v5.py tests/test_curses_v5.py
git commit -m "feat(v5): add curses TUI thread driving the renderer"
```

---

## Task 7: Wire TuiV5 into main_v5 — tests first

**Files:**
- Test: `tests/test_main_v5.py` (extend)
- Modify: `glances/main_v5.py`

- [ ] **Step 1: Add failing tests**

Open `tests/test_main_v5.py` and append:

```python
# ---------------------------------------------------------------- TUI wiring


def test_parser_accepts_no_tui_flag():
    from glances.main_v5 import build_parser

    args = build_parser().parse_args(["--no-tui"])
    assert args.no_tui is True


def test_parser_tui_defaults_to_enabled():
    from glances.main_v5 import build_parser

    args = build_parser().parse_args([])
    assert args.no_tui is False


def test_assemble_builds_tui_when_enabled(monkeypatch):
    """assemble() returns a TuiV5 instance when --no-tui is not set."""
    import argparse

    from glances.main_v5 import assemble
    from glances.config_v5 import GlancesConfigV5

    cfg = GlancesConfigV5()
    args = argparse.Namespace(
        config_path=None, bind=None, port=None, api_doc=None,
        debug=False, set_password=False, no_tui=False,
    )
    app, scheduler, host, port, tui = assemble(args, cfg)
    assert tui is not None


def test_assemble_skips_tui_when_no_tui(monkeypatch):
    """assemble() returns None for the tui slot when --no-tui is set."""
    import argparse

    from glances.main_v5 import assemble
    from glances.config_v5 import GlancesConfigV5

    cfg = GlancesConfigV5()
    args = argparse.Namespace(
        config_path=None, bind=None, port=None, api_doc=None,
        debug=False, set_password=False, no_tui=True,
    )
    app, scheduler, host, port, tui = assemble(args, cfg)
    assert tui is None
```

- [ ] **Step 2: Run and confirm failure**

```bash
make test-v5 ARGS="tests/test_main_v5.py"
```

Expected: failures on the new tests (unknown argument `--no-tui`, `assemble` returns 4-tuple not 5-tuple).

- [ ] **Step 3: Update `build_parser`**

In `glances/main_v5.py`, after the `--debug` argument:

```python
    parser.add_argument(
        "--no-tui",
        dest="no_tui",
        action="store_true",
        help="Disable the curses TUI (REST API only). Useful for headless / server-mode deployments.",
    )
```

- [ ] **Step 4: Update `assemble()` to also return a TUI instance**

Modify the function signature and body. Replace the existing `assemble` with:

```python
def assemble(
    args: argparse.Namespace, config: GlancesConfigV5
) -> tuple[FastAPI, AsyncScheduler, str, int, "TuiV5 | None"]:
    """Wire every Phase 1 component into a runnable tuple.

    Also instantiates the curses TUI thread unless ``--no-tui`` is set.
    The TUI is started by `serve()`, not here.
    """
    store = StatsStoreV5()
    actions = discover_actions("glances.actions_v5")
    alerts = GlancesAlerts(config, actions=actions)

    plugins = discover_plugins(store, config)
    if not plugins:
        logger.warning(
            "No v5 plugins discovered. The server will start with an empty registry; "
            "plugins can be activated later via the REST API (issue #3548)."
        )
    else:
        logger.info(
            "Discovered %d v5 plugins: %s",
            len(plugins),
            ", ".join(p.plugin_name for p in plugins),
        )

    if args.api_doc is not None:
        config._merged.setdefault("outputs", {})["api_doc"] = bool(args.api_doc)

    app = build_app(config=config, store=store, alerts=alerts)
    for plugin in plugins:
        register_plugin(app, plugin)

    scheduler = AsyncScheduler(store, config, alerts=alerts)
    for plugin in plugins:
        scheduler.register(plugin)

    host = args.bind or config.get("outputs", "bind_address", _DEFAULT_BIND_ADDRESS)
    port = args.port or config.get("outputs", "port", _DEFAULT_PORT)

    tui: TuiV5 | None = None
    if not getattr(args, "no_tui", False):
        from glances.outputs.glances_curses_v5 import TuiV5  # local import — curses is platform-dependent

        registry = [(p.plugin_name, p.IS_COLLECTION) for p in plugins]
        fields_by_plugin = {p.plugin_name: p._fields for p in plugins}
        refresh = float(config.get("outputs", "tui_refresh_interval", 1.0))
        tui = TuiV5(
            store=store,
            alerts=alerts,
            config=config,
            registry=registry,
            fields_by_plugin=fields_by_plugin,
            refresh_interval=refresh,
        )

    return app, scheduler, host, int(port), tui
```

Also add the import at the top of the file (after the other glances imports):

```python
if TYPE_CHECKING:
    from fastapi import FastAPI
    from glances.outputs.glances_curses_v5 import TuiV5
```

- [ ] **Step 5: Update `serve()` to manage TUI lifecycle**

Replace the existing `serve()`:

```python
async def serve(
    app: FastAPI,
    scheduler: AsyncScheduler,
    host: str,
    port: int,
    tui: "TuiV5 | None" = None,
) -> None:
    """Run scheduler, uvicorn, and (optionally) the TUI thread concurrently."""
    scheduler_task: asyncio.Task[None] | None = None
    if scheduler._entries:  # type: ignore[attr-defined]
        scheduler_task = asyncio.create_task(scheduler.run_forever())

    if tui is not None:
        tui.start()

    uvi_config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(uvi_config)
    try:
        await server.serve()
    finally:
        if tui is not None:
            tui.stop()
            # Join in a thread executor — never block the event loop.
            await asyncio.to_thread(tui.join, 2.0)
        await scheduler.stop()
        if scheduler_task is not None:
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await scheduler_task
```

- [ ] **Step 6: Update `main()` to pass tui through**

Replace the `main` body's `assemble` and `serve` call:

```python
def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    setup_logging(args.debug)

    if args.set_password:
        return cli_set_password()

    config = GlancesConfigV5(cli_config_path=args.config_path)
    app, scheduler, host, port, tui = assemble(args, config)

    logger.info("Starting Glances v5 REST API on http://%s:%d", host, port)
    try:
        asyncio.run(serve(app, scheduler, host, port, tui))
    except KeyboardInterrupt:
        pass
    return 0
```

- [ ] **Step 7: Run main tests**

```bash
make test-v5 ARGS="tests/test_main_v5.py"
```

Expected: all green. If existing tests were calling `assemble` expecting a 4-tuple, the failures will surface here — update those callsites in the same commit to consume the 5-tuple.

- [ ] **Step 8: Run the full v5 test suite to catch regressions**

```bash
make test-v5
```

Expected: all green. Pay special attention to `test_main_v5.py` — older tests may need the new return-tuple shape.

- [ ] **Step 9: Commit**

```bash
git add glances/main_v5.py tests/test_main_v5.py
git commit -m "feat(v5): wire TuiV5 thread into main_v5 with --no-tui flag"
```

---

## Task 8: Manual smoke test

**Files:** None (operational verification).

- [ ] **Step 1: Start Glances v5 with TUI**

```bash
make run-v5
```

Expected:
- Terminal enters curses mode.
- Top-left: `MEM` block with percent + total/used/free/available values, percent colored per threshold.
- Top-left below `MEM`: `CPU` block with percent and breakdown.
- Top-left further down: `LOAD` block, with per-core load if `percpu` is registered.
- Top-right: `NETWORK` block with per-interface Rx/Tx rates.
- Bottom: `ALERTS (n)` footer (empty initially).

- [ ] **Step 2: Compare side-by-side with v4**

In a second terminal:

```bash
.venv/bin/glances
```

Capture both terminals (screenshot or `script` recording). Compare:
- Are field labels visually similar (MEM, CPU, LOAD, NET headers)?
- Are values in the same unit/precision?
- Are colors triggered at the same thresholds?

Note discrepancies — they are either (a) acceptable v5 evolution to be documented in `NEWS.rst`, or (b) regressions to be fixed in a follow-up PR.

- [ ] **Step 3: Test `q` and `Ctrl-C` shutdown**

- Start `make run-v5`, press `q` — terminal should restore cleanly, prompt returns.
- Start again, press `Ctrl-C` — terminal should restore cleanly, prompt returns.
- Start with `--no-tui`:
  ```bash
  python -m glances.main_v5 --no-tui
  ```
  Expected: no curses, REST API responds. Curl test:
  ```bash
  curl -s http://127.0.0.1:61208/api/5/mem | jq .percent
  ```

- [ ] **Step 4: Document any visible-output diff in PR description**

Capture both v4 and v5 screenshots, attach to the PR.

---

## Task 9: Architecture decisions doc — §1.4 details

**Files:**
- Modify: `docs/architecture/glances-v5-architecture-decisions.md` (§1.4 expansion)

- [ ] **Step 1: Expand §1.4**

Locate the current §1.4 block:

```markdown
### 1.4 Curses TUI integration

- The TUI runs in a **dedicated thread**, reading the StatsStore synchronously.
- Curses is not async-native; a thread avoids blocking the asyncio event loop.
- The thread reads the StatsStore without a lock (same lockless contract as other consumers).
```

Replace with the expanded version:

```markdown
### 1.4 Curses TUI integration

- The TUI runs in a **dedicated `threading.Thread`** spawned by `serve()` in
  `main_v5.py` after the scheduler and before `uvicorn.Server.serve()`. It
  reads the StatsStore synchronously and without a lock (same lockless
  contract as exporters and the REST API — §1.3).
- The thread is implemented in `glances/outputs/glances_curses_v5.py` and is
  split into three units:
  - `curses_formatters_v5.py` — pure unit-driven formatters keyed by the
    `unit` value declared in `fields_description` (§3.2).
  - `curses_renderer_v5.py` — pure renderer producing a structured `Frame`
    (`Row`s of `Cell`s) from a store snapshot + an alerts history. No
    curses, no threading — fully unit-testable in isolation.
  - `glances_curses_v5.py` — `TuiV5(threading.Thread)` owning the curses
    event loop, the color pair initialisation, and the `addstr` paint
    pipeline. Listens to `q` / `ESC` for shutdown; honours a
    `threading.Event` set by the asyncio task in its `finally` clause.
- **Layout** — two-column grid. Scalar plugins (cpu, mem, load, …) populate
  the left column; collection plugins (network, fs, …) populate the right
  column. Order within each column follows registry order
  (`[(plugin_name, is_collection), …]`), itself derived from discovery
  order at startup. The bottom of the screen carries the alerts footer
  (`ALERTS (n)` header + up to 10 most-recent events, configurable).
- **Color mapping** — renderer `ColorRole` (HEADER, OK, CAREFUL, WARNING,
  CRITICAL, DEFAULT) → curses color pairs. `prominent: True` on a
  WARNING/CRITICAL cell adds `A_REVERSE` for background highlight; on
  non-alert cells `prominent` only changes color. No 256-color advanced
  support in this iteration — base ANSI palette only.
- **Renderer hints** in `fields_description` (§3.2) — `format` and
  `column_width` give plugin authors a controlled way to override the
  unit-driven defaults without re-introducing the rejected `view_layout`
  mechanism (§3.6). They describe per-field formatting, never overall
  layout.
- **CLI control** — `--no-tui` disables the thread entirely (REST API only).
  Default behaviour in standalone mode is TUI on. Server mode uses
  `--no-tui` in practice.
- **Refresh cadence** — configurable via `[outputs] tui_refresh_interval`
  (default `1.0` second). Independent of plugin `refresh_time` (plugin
  cadence) — the TUI repaints from the store at its own rhythm.
- **Shutdown** — `q` or `ESC` keypress, or `Ctrl-C` propagating through
  uvicorn, sets the shared `threading.Event`. The TUI's main loop polls
  the event between curses cycles and exits gracefully, restoring the
  terminal via `curses.wrapper`.
```

- [ ] **Step 2: Commit**

```bash
git add docs/architecture/glances-v5-architecture-decisions.md
git commit -m "docs(v5): flesh out §1.4 curses TUI integration"
```

---

## Task 10: Update SKILL-plugin.md

**Files:**
- Modify: `.claude/skills/SKILL-plugin.md`

- [ ] **Step 1: Read the current SKILL**

```bash
cat .claude/skills/SKILL-plugin.md
```

- [ ] **Step 2: Append the renderer-hints section**

Append this section to the file (just before any "Examples" or end-of-file marker):

```markdown
## Renderer hints in `fields_description`

Two **optional** keys give plugin authors fine control over the TUI/WebUI
rendering without re-introducing the rejected `view_layout` mechanism
(§3.6 of the architecture document):

| Key | Type | Purpose |
|---|---|---|
| `format` | `str` | Explicit Python format string applied to the value (e.g. `"%5.1f%%"`). Overrides the default unit-driven formatter. |
| `column_width` | `int` | Fixed character width for the field's column in the TUI. Overrides the auto-sizing computed from label + observed max content width. |

Both are pure *formatting* hints — they describe how a single field is
displayed, never *where* it sits relative to others. The overall layout
(which fields appear, in which column, in which order) remains owned by
the renderer.

**When to use:**
- The unit-driven default does not match v4 (e.g. trailing space, three-digit
  padding) → declare `format`.
- The auto-sized column flickers because content length varies cycle-to-cycle
  → declare `column_width`.

**When NOT to use:** when you want a different *layout* (custom column order,
two-line rendering, sparkline). The renderer owns layout. If your need is
truly different, open an issue first — adding a renderer feature is a
deliberate decision, not a per-plugin escape hatch.

## Visual parity contract

Every plugin PR ships with a screenshot pair (v4 vs v5) in its description,
on the same data set. The reviewer arbitrates:

- Field labels visually similar?
- Values formatted with the same unit/precision?
- Threshold-driven coloration triggered at the same boundaries?

If the visual diff is non-trivial and the reviewer wants automation, the
PR author adds a text fixture under `tests/fixtures/tui_<plugin>_v5.txt`
and a `test_curses_<plugin>_v5.py` assertion that the renderer output
matches the fixture (line-by-line). This is opt-in per plugin.

The catalogue of v4 patterns lives in
`docs/architecture/tui-v4-rendering-patterns.md` — extend it whenever a
new plugin is migrated.

## Done-bar checklist (Phase 2)

Before requesting review on a plugin migration PR:

- [ ] `glances/plugins/<name>/model_v5.py` exists with a complete
      `fields_description` (description, unit, label, watched,
      watch_direction, prominent, default_thresholds, primary_key for
      collections, exportable, rate where applicable).
- [ ] `tests/test_plugin_<name>_v5.py` covers `_grab_stats`, the four
      `_transform` steps, `_levels`, the field schema, and `get_export`.
- [ ] `tests/test_plugin_<name>.py` (v4) still passes — no regression.
- [ ] `GET /api/5/<name>` and `GET /api/5/<name>/info` return the expected
      shapes (verified in `tests/test_routes_v5.py` or via curl in the
      PR description).
- [ ] TUI wiring done in the same PR — screenshot v4 vs v5 attached.
- [ ] Perf check (`tests/test_perf_v5.py`) shows no regression > 20%.
- [ ] `make lint && make format` clean.
- [ ] `NEWS.rst` updated if a visible-API change (datamodel, thresholds,
      config keys) is introduced.
```

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/SKILL-plugin.md
git commit -m "docs(v5): extend SKILL-plugin.md with renderer hints + done-bar"
```

---

## Task 11: Final sanity sweep

**Files:** None.

- [ ] **Step 1: Full test suite**

```bash
make test-v5
```

Expected: every v5 test green.

- [ ] **Step 2: v4 non-regression check**

```bash
make test
```

Expected: no new failures vs the baseline before G0. Identify any test that fails because of G0 changes and fix.

- [ ] **Step 3: Lint + format**

```bash
make lint && make format
```

Expected: clean.

- [ ] **Step 4: Headless probe**

```bash
python -m glances.main_v5 --no-tui --port 16208 &
sleep 1
curl -s http://127.0.0.1:16208/api/5/pluginslist
curl -s http://127.0.0.1:16208/api/5/mem | jq .
curl -s http://127.0.0.1:16208/api/5/network | jq '.data[0]'
kill %1
```

Expected: `pluginslist` lists cpu, load, mem, network, percpu; `/mem` returns a payload with `percent` + `_levels`; `/network` returns a list with at least one interface.

- [ ] **Step 5: TUI smoke**

```bash
make run-v5
```

Inspect manually. Quit with `q`. Confirm terminal restored.

- [ ] **Step 6: NEWS.rst entry**

Open `NEWS.rst` and add an entry under the active `5.0.0a*` heading (create the section if missing):

```rst
Glances version 5.0.0a2 (2026-05-12 — Phase 2 G0)
==================================================

ENHANCEMENTS

* v5: curses TUI v5 thread (lockless StatsStore reads, asyncio-friendly), driven entirely by ``fields_description``. Default layout: scalar plugins (cpu, mem, load) in the left column, collection plugins (network) in the right column, alerts footer at the bottom.
* v5: optional ``fields_description`` keys ``format`` and ``column_width`` give per-field rendering hints without revisiting the rejected ``view_layout`` (see architecture §3.2 / §3.6).
* v5: new ``--no-tui`` CLI flag for headless / server-mode deployments. TUI on by default in standalone.
```

Commit:

```bash
git add NEWS.rst
git commit -m "docs(v5): add NEWS.rst entry for Phase 2 G0 TUI scaffold"
```

- [ ] **Step 7: Final commit (if anything changed in the sweep)**

If the sweep surfaced lint/format auto-fixes:

```bash
git add -u
git commit -m "chore(v5): apply lint/format auto-fixes from G0 sweep"
```

Otherwise no commit needed.

---

## Wrap-up

Once every task is checked off:

1. Push the branch and open the PR.
2. Attach v4 vs v5 TUI screenshots in the PR description (Task 8).
3. Confirm CI green.
4. Request review.
5. After merge, update `MEMORY.md` with a project-memory note:

```
- [Phase 2 G0 done: TUI v5 scaffold + cpu/mem/load/network/percpu wired](project_v5_g0_tui_scaffold.md) — TUI generic renderer driven by fields_description, format/column_width as opt-in hints.
```
