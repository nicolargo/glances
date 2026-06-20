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
- ``view["quicklook_width"]``-> int : inner bar size (full-width mode only)
- ``view["quicklook_freq_only"]`` -> bool: header shows "Frequency" instead
  of the CPU name (cascade step d); compact bars shrink to match

In compact mode (not ``full_quicklook``) with a header present, every bar
row is justified to the header line's painter-width.
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row
from glances.outputs.glances_bars import Bar

# Default inner-bar size (the `Bar` width, i.e. the number of cells the
# `||||      45.0%` string occupies) when the TUI does not pass one in
# `view` (e.g. unit tests, or the very first cycle, or when there is no
# header to justify against). v4 capped the quicklook column at 48 — keep
# the inner bar comfortably under that.
_DEFAULT_BAR_WIDTH = 38

# Label cell is `f"{label:<4} "` -> always 5 painter columns (4 + trailing
# space). The flush brackets add 2 columns ("[" + "]"). So a bar row's
# painter-width is always `_LABEL_WIDTH + _BRACKETS_WIDTH + bar_size`.
_LABEL_WIDTH = 5
_BRACKETS_WIDTH = 2

# Floor for the justified bar-row total painter-width. Keeps the inner bar
# usable even when the header (CPU name + freq) is very short. 5 (label) +
# 2 (brackets) + 8 (bar) = 15.
_MIN_BAR_TOTAL = _LABEL_WIDTH + _BRACKETS_WIDTH + 8

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


def _hz_to_ghz(hz: Any) -> float:
    return float(hz) / 1_000_000_000.0


def _header_row(payload: dict[str, Any], freq_only: bool = False) -> Row | None:
    """CPU name + frequency line (v4 `msg_curse` lines 211-228).

    Shown only when a current frequency is available. Mirrors v4:
    ``<name> <cur>/<max>GHz`` (or just ``<cur>GHz`` when max is unknown).
    When ``freq_only`` (cascade step d), the literal ``"Frequency"`` label
    replaces the CPU name to shrink the block.
    """
    cur = payload.get("cpu_hz_current")
    if cur is None:
        return None
    mx = payload.get("cpu_hz")
    if mx is not None:
        freq = f" {_hz_to_ghz(cur):.2f}/{_hz_to_ghz(mx):.2f}GHz"
    else:
        freq = f" {_hz_to_ghz(cur):.2f}GHz"
    name = "Frequency" if freq_only else (payload.get("cpu_name") or "Frequency")
    return Row(cells=[Cell(text=name, color=ColorRole.HEADER), Cell(text=freq)])


def _painter_width(row: Row) -> int:
    """Width the painter draws a row at: total text + one separator before
    every non-glue cell after the first (mirrors the TUI painter)."""
    return sum(len(c.text) for c in row.cells) + sum(1 for i, c in enumerate(row.cells) if i > 0 and not c.glue)


def render(
    payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]], view: dict[str, Any] | None = None
) -> list[Row]:
    """Render the quicklook plugin's TUI block — mirrors v4 `quicklook.msg_curse`."""
    if not payload:
        return [Row(cells=[Cell(text="CPU", color=ColorRole.HEADER, bold=True)])]

    view = view or {}
    full = bool(view.get("full_quicklook"))
    freq_only = bool(view.get("quicklook_freq_only"))

    rows: list[Row] = []

    header = _header_row(payload, freq_only=freq_only)
    if header is not None:
        rows.append(header)

    if full:
        # Full-width mode keeps the explicit `quicklook_width` (inner bar size).
        width = _bar_width(view)
    elif header is not None:
        # Compact mode with a header: justify every bar row to the header's
        # painter-width (floored so the bar stays usable on tiny headers).
        target = max(_painter_width(header), _MIN_BAR_TOTAL)
        width = target - _LABEL_WIDTH - _BRACKETS_WIDTH
    else:
        # Compact mode, no header to justify against -> today's default.
        width = _DEFAULT_BAR_WIDTH

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
