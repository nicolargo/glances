#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the cpu plugin.

Replicates v4's `cpu.msg_curse()` (see
`glances/plugins/cpu/__init__.py::msg_curse`): a 4-line block laid out
as a 3-column grid of (label, value) pairs, with line 1 carrying the
plugin title and total CPU usage.

Reference layout (Linux, all fields available):

    CPU      4.5%      idle   95.5%       ctx_sw   6.7K
      user   3.8%       irq    0.0%   interrupts   3.0K
    system   0.7%      nice    0.0%       sw_int   1.8K
    iowait   0.0%     steal    0.0%        guest   0.0%

Columns 1/2/3 carry per-line label+value pairs. The set of fields per
column is OS-dependent (see v4 `msg_curse`):
- Linux:   user/system/iowait | irq/nice/steal | interrupts/sw_int/guest
- Windows: idle/core/dpc       | irq/nice/steal | interrupts/sw_int/syscalls

The renderer is pure: takes a payload dict + fields_description, returns
the curses-renderer-internal `Row`s. No curses, no threading.
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import Cell, ColorRole, Row, _cell_for_field, field_label, title_role


def _stat_cells(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]], key: str, label: str) -> list[Cell]:
    """Return a (label, value) pair for a single stat.

    If the field is absent from the payload, the value is rendered as
    a single dash. Color/prominence comes from `_levels`.
    """
    label_cell = Cell(text=label)
    if key not in payload or payload.get(key) is None:
        return [label_cell, Cell(text="-")]
    schema = fields_desc.get(key, {})
    return [label_cell, _cell_for_field(key, payload[key], schema, payload)]


def _ctx_sw_value_cell(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]], key: str) -> Cell:
    """Render a counter rate (ctx_switches, interrupts, ...) as a short
    K/M-scaled number (matches v4's `auto_unit + min_symbol` for these
    fields). Falls back to the unit-driven formatter otherwise.
    """
    if key not in payload or payload.get(key) is None:
        return Cell(text="-")
    schema = fields_desc.get(key, {})
    # Use the unit-driven formatter; for `unit: number` this is a plain
    # integer. To match v4 we want K/M scaling — force a one-decimal
    # K-symbol via an explicit format only when value >= 1024.
    value = float(payload[key])
    if value >= 1024:
        # Tiny inline auto-unit (K/M only, matches v4 cpu cosmetics).
        if value >= 1_048_576:
            text = f"{value / 1_048_576:.1f}M"
        else:
            text = f"{value / 1024:.1f}K"
        # Reuse the level coloring from _cell_for_field by overriding text.
        cell = _cell_for_field(key, payload[key], schema, payload)
        return Cell(text=text, color=cell.color, prominent=cell.prominent)
    # Small values: integer.
    cell = _cell_for_field(key, payload[key], schema, payload)
    return Cell(text=f"{int(value)}", color=cell.color, prominent=cell.prominent)


# Value cells need a stable floor — their content can shrink
# cycle-to-cycle (e.g. "5.0%" vs "100.0%"). Label cells don't — labels
# come from the schema (``short_name`` → ``label`` → field name) and
# are constant strings, so the auto-size is naturally stable.
_CPU_VALUE_WIDTH = 6


def _align_grid(rows: list[list[Cell]]) -> list[Row]:
    """Per-column alignment for a 6-cell grid (3 label/value pairs).

    Value columns are floored at ``_CPU_VALUE_WIDTH`` so they don't
    jiggle when their content shrinks. Label columns auto-size to the
    widest observed text.
    """
    if not rows:
        return []
    ncols = max(len(r) for r in rows)
    widths = [0] * ncols
    for r in rows:
        for i, c in enumerate(r):
            widths[i] = max(widths[i], len(c.text))
    for i in range(ncols):
        if i % 2 == 1:  # value column
            widths[i] = max(widths[i], _CPU_VALUE_WIDTH)

    aligned: list[Row] = []
    for r in rows:
        new_cells: list[Cell] = []
        for i, c in enumerate(r):
            if i % 2 == 0:
                text = c.text.ljust(widths[i])
            else:
                text = c.text.rjust(widths[i])
            new_cells.append(Cell(text=text, color=c.color, prominent=c.prominent, bold=c.bold))
        aligned.append(Row(cells=new_cells))
    return aligned


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]]) -> list[Row]:
    """Render the cpu plugin's TUI block — mirrors v4 `cpu.msg_curse`.

    Args:
        payload: the cpu plugin's StatsStore payload (current cycle).
        fields_desc: the plugin's `fields_description` schema (with the
            base-class metadata fields merged in).

    Returns:
        A list of `Row`s ready for the curses painter.
    """
    # Cycle-0 / no data yet: show just the title.
    if not payload:
        return [Row(cells=[Cell(text="CPU", color=ColorRole.HEADER, bold=True)])]

    # `idle_tag` (Windows): no `user` field → display idle/core/dpc instead.
    idle_tag = "user" not in payload

    # Line 1: title + total% + (idle label/value) + (ctx_sw label/value)
    # Title colour reflects the worst prominent alert level in the payload
    # (HEADER/white when nothing is escalated, careful/warning/critical
    # colour otherwise — always bold).
    line1_cells: list[Cell] = [
        Cell(text="CPU", color=title_role(payload), bold=True),
        _cell_for_field("total", payload.get("total"), fields_desc.get("total", {}), payload),
    ]
    if not idle_tag and payload.get("idle") is not None:
        line1_cells += [
            Cell(text="idle"),
            _cell_for_field("idle", payload.get("idle"), fields_desc.get("idle", {}), payload),
        ]
    else:
        # Keep the slot so column alignment lines up; placeholders.
        line1_cells += [Cell(text=""), Cell(text="")]
    if "ctx_switches" in payload:
        line1_cells += [
            Cell(text=field_label(fields_desc.get("ctx_switches", {}), "ctx_switches", prefer_short=True)),
            _ctx_sw_value_cell(payload, fields_desc, "ctx_switches"),
        ]
    else:
        line1_cells += [Cell(text=""), Cell(text="")]

    def _kl(key: str) -> tuple[str, str]:
        """(key, short-label) — pulls short_name → label → key from schema."""
        return (key, field_label(fields_desc.get(key, {}), key, prefer_short=True))

    # Lines 2–4: 3-column grid.
    if not idle_tag:
        col1_keys_labels = [_kl("user"), _kl("system"), _kl("iowait")]
    else:
        col1_keys_labels = [_kl("idle"), _kl("core"), _kl("dpc")]

    col2_keys_labels = [_kl("irq"), _kl("nice"), _kl("steal")]

    # Col 3 — variants matching v4:
    #   line 2: interrupts
    #   line 3: soft_interrupts (Linux) or ctx_switches (Windows)
    #   line 4: guest (Linux) or syscalls (non-Linux/non-macOS)
    col3_keys_labels: list[tuple[str, str]] = [_kl("interrupts")]
    if "soft_interrupts" in payload:
        col3_keys_labels.append(_kl("soft_interrupts"))
    else:
        col3_keys_labels.append(_kl("ctx_switches"))
    if "guest" in payload:
        col3_keys_labels.append(_kl("guest"))
    elif "syscalls" in payload:
        col3_keys_labels.append(_kl("syscalls"))
    else:
        col3_keys_labels.append(("", ""))

    # Rate-style values in col 3 → K-scaling (interrupts, sw_int).
    rate_col3_keys = {"interrupts", "soft_interrupts", "ctx_switches", "syscalls"}

    def _col3_cell(key: str) -> Cell:
        if not key:
            return Cell(text="")
        if key in rate_col3_keys:
            return _ctx_sw_value_cell(payload, fields_desc, key)
        if key in payload and payload.get(key) is not None:
            return _cell_for_field(key, payload[key], fields_desc.get(key, {}), payload)
        return Cell(text="-")

    grid_rows: list[list[Cell]] = [line1_cells]
    for i in range(3):
        c1_key, c1_label = col1_keys_labels[i]
        c2_key, c2_label = col2_keys_labels[i]
        c3_key, c3_label = col3_keys_labels[i]
        # Skip line 4 col 3 entirely if no key applies.
        row = []
        row += _stat_cells(payload, fields_desc, c1_key, c1_label) if c1_key else [Cell(text=""), Cell(text="")]
        row += _stat_cells(payload, fields_desc, c2_key, c2_label) if c2_key else [Cell(text=""), Cell(text="")]
        row += [Cell(text=c3_label), _col3_cell(c3_key)] if c3_key else [Cell(text=""), Cell(text="")]
        grid_rows.append(row)

    return _align_grid(grid_rows)
