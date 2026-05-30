#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the processlist plugin.

Mirror of v4 ``processlist.msg_curse``. Renders a header row + top-N
processes (engine pre-sorts by ``cpu_percent`` descending).

Reference layout:

    CPU%  MEM%  VIRT   RES      PID USER       THR  NI S  TIME+    R/s  W/s  Command
    78.4   3.1  120M  32.1M   12345 alice        4   0 S  0:12     0B   0B   python myscript.py
     0.5   0.2   2.4M  1.0M     512 root         2   0 S  3:42     0B   0B   sshd
    ...

Columns:
- ``CPU%`` / ``MEM%`` — watched, coloured by ``_levels``.
- ``VIRT`` / ``RES``  — psutil ``memory_info.vms`` / ``memory_info.rss``,
  human-readable bytes.
- ``PID``             — right-aligned, width follows widest PID in payload.
- ``USER``            — truncated with a trailing ``+`` marker.
- ``THR``             — number of threads.
- ``NI``              — nice value (categorical alert when configured).
- ``S``               — single-letter status (categorical alert when configured).
- ``TIME+``           — cumulative CPU time (``cpu_times.user + cpu_times.system``).
  Format mirrors v4: ``MM:SS`` under 1h, ``Hh{MM:SS}`` between 1h and 99h,
  ``<hours>h`` past 100h. Unknown → ``?``.
- ``R/s`` / ``W/s``   — IO rates from ``io_counters[0..3]`` / ``time_since_update``
  (engine pattern: ``[r_new, w_new, r_old, w_old, io_tag]``). ``io_tag == 0``
  (access denied or first cycle) → ``?``.
- ``Command``         — v4 ``split_cmdline`` pattern: command name in **bold**,
  arguments in default colour. Falls back to ``[name]`` for kernel threads.

Status / nice cells inherit the ``_levels`` colour when configured
(``status_critical=Z,D`` / ``nice_warning=…`` in ``[processlist]``).

Limit: top 20 processes (engine returns the full sorted list).
"""

from __future__ import annotations

import os
from typing import Any

from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row, title_role

# Column widths (v4 parity — see ``processlist.layout_header``/``layout_stat``).
_W_CPU = 5
_W_MEM = 5
_W_VIRT = 5
_W_RES = 5
_W_USER = 10
_W_THR = 3
_W_NI = 2
_W_STATUS = 1
_W_TIME = 8
_W_IO = 5
_W_PID_DEFAULT = 7
_MAX_ROWS = 20

# Header label → engine sort key. The active sort column's header is
# underlined (v4 'SORT' decoration). Columns with no sort key (VIRT, RES,
# PID, THR, NI, S) are never marked. ``R/s`` and ``W/s`` both map to
# ``io_counters`` so the IO sort underlines the pair.
_HEADER_SORT_KEY: dict[str, str] = {
    "CPU%": "cpu_percent",
    "MEM%": "memory_percent",
    "USER": "username",
    "TIME+": "cpu_times",
    "R/s": "io_counters",
    "W/s": "io_counters",
    "Command": "name",
}


# ----------------------------------------------------------- value formatting


def _format_percent(value: Any, width: int) -> str:
    try:
        return f"{float(value):>{width}.1f}"
    except (TypeError, ValueError):
        return "?".rjust(width)


def _format_int(value: Any, width: int, *, signed: bool = False) -> str:
    try:
        ival = int(value)
    except (TypeError, ValueError):
        return "?".rjust(width)
    formatted = f"{ival:>+{width}d}" if signed else f"{ival:>{width}d}"
    return formatted[-width:].rjust(width)


def _format_username(value: Any) -> str:
    text = str(value) if value is not None else "?"
    if len(text) > _W_USER:
        return text[: _W_USER - 1] + "+"
    return text.ljust(_W_USER)


def _format_cpu_time(item: dict[str, Any], width: int) -> str:
    """Render ``cpu_times.user + cpu_times.system`` as v4-style TIME+.

    Same rules as v4 ``_get_process_curses_cpu_times``:
    - ``hours > 99``           → ``{hours}h`` (left-padded to width).
    - ``0 < hours < 100``      → ``{H}h{MM:SS}``  (e.g. ``1h05:30``).
    - ``hours == 0``           → ``{M}:{SS}``    (e.g. ``5:30``).
    - Missing / unparsable     → ``?``.
    """
    raw = item.get("cpu_times")
    user = system = None
    if isinstance(raw, dict):
        user = raw.get("user")
        system = raw.get("system")
    elif isinstance(raw, (tuple, list)) and len(raw) >= 2:
        user, system = raw[0], raw[1]
    try:
        total = float(user) + float(system)
    except (TypeError, ValueError):
        return "?".rjust(width)
    if total < 0:
        return "?".rjust(width)
    total_int = int(total)
    minutes, seconds = divmod(total_int, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 99:
        text = f"{hours}h"
    elif hours > 0:
        text = f"{hours}h{minutes:02d}:{seconds:02d}"
    else:
        text = f"{minutes}:{seconds:02d}"
    return text.rjust(width)


def _format_bytes(value: Any, width: int) -> str:
    """Render a byte count as a fixed-width human-readable string (K/M/G/T)."""
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "?".rjust(width)
    if n < 0:
        return "?".rjust(width)
    for suffix, scale in (("T", 1024**4), ("G", 1024**3), ("M", 1024**2), ("K", 1024)):
        if n >= scale:
            v = n / scale
            return (f"{v:.1f}{suffix}" if v < 100 else f"{int(v)}{suffix}").rjust(width)
    return f"{int(n)}B".rjust(width)


# ----------------------------------------------------------- domain accessors


def _memory_info_field(item: dict[str, Any], field: str) -> Any:
    raw = item.get("memory_info")
    if isinstance(raw, dict):
        return raw.get(field)
    return None


def _io_rate(item: dict[str, Any], read: bool) -> tuple[Any, bool]:
    """Return (rate_value_or_None, is_unknown).

    Engine convention: ``io_counters = [r_new, w_new, r_old, w_old, io_tag]``.
    ``io_tag == 0`` means access denied **or** first observation for the
    pid — caller renders ``?``.
    """
    raw = item.get("io_counters")
    if not isinstance(raw, list) or len(raw) < 5:
        return (None, True)
    io_tag = raw[4]
    if io_tag != 1:
        return (None, True)
    elapsed = item.get("time_since_update")
    try:
        elapsed_f = float(elapsed)
    except (TypeError, ValueError):
        return (None, True)
    if elapsed_f <= 0:
        return (None, True)
    new_idx, old_idx = (0, 2) if read else (1, 3)
    try:
        delta = float(raw[new_idx]) - float(raw[old_idx])
    except (TypeError, ValueError):
        return (None, True)
    if delta < 0:
        delta = 0.0
    return (delta / elapsed_f, False)


def _split_cmdline(item: dict[str, Any]) -> tuple[str, str, str]:
    """v4 parity ``split_cmdline`` — returns (path, cmd, args).

    - cmdline missing or empty → (``""``, ``name`` if known else ``""``, ``""``).
    - cmdline[0] starts with the bare process name (psutil's ``name``) →
      treat cmdline[0] as the command (no path split).
    - Else ``os.path.split(cmdline[0])`` separates ``path`` and ``cmd``.
    - Arguments are ``" ".join(cmdline[1:])``.
    """
    cmdline = item.get("cmdline")
    name = str(item.get("name") or "")
    if not isinstance(cmdline, list) or not cmdline:
        return ("", name, "")
    head = str(cmdline[0])
    if name and head.startswith(name):
        path, cmd = "", head
    else:
        path, cmd = os.path.split(head)
    args = " ".join(str(t) for t in cmdline[1:] if t is not None)
    return (path, cmd, args)


# ----------------------------------------------------------- cell builders


def _percent_cell(value: Any, level_entry: dict[str, Any] | None, width: int) -> Cell:
    text = _format_percent(value, width)
    if isinstance(level_entry, dict):
        role = _LEVEL_TO_ROLE.get(level_entry.get("level"), ColorRole.DEFAULT)
        return Cell(text=text, color=role, prominent=bool(level_entry.get("prominent")))
    return Cell(text=text)


def _level_text_cell(text: str, level_entry: dict[str, Any] | None) -> Cell:
    if isinstance(level_entry, dict):
        role = _LEVEL_TO_ROLE.get(level_entry.get("level"), ColorRole.DEFAULT)
        return Cell(text=text, color=role, prominent=bool(level_entry.get("prominent")))
    return Cell(text=text)


def _io_cell(value: Any, is_unknown: bool, width: int) -> Cell:
    if is_unknown:
        return Cell(text="?".rjust(width))
    return Cell(text=_format_bytes(value, width))


def _command_cells(item: dict[str, Any], short_name: bool = True) -> list[Cell]:
    """Render the command as bold cmd + plain args.

    - ``short_name=True`` (default, v4 short view): the ``/path/to/``
      prefix of ``cmdline[0]`` is stripped via ``split_cmdline`` — only
      the executable name (bold) + arguments are shown.
    - ``short_name=False`` (v4 ``/`` hotkey full view): when the stripped
      path is a real directory, it is prepended as a plain ``path + os.sep``
      cell before the bold cmd (mirrors v4 ``_get_process_curses_cmdline``,
      including the ``os.path.isdir`` guard so a bogus path is not shown).

    Empty / missing cmdline falls back to the kernel-thread convention
    ``[name]`` (no bold) — kthreads have no cmdline in ``/proc``.
    """
    cmdline = item.get("cmdline")
    if not isinstance(cmdline, list) or not cmdline:
        name = str(item.get("name") or "")
        return [Cell(text=f"[{name}]" if name else "")]
    path, cmd, args = _split_cmdline(item)
    cells: list[Cell] = []
    if not short_name and path and os.path.isdir(path):
        # Plain path prefix, with the bold command glued flush after it so
        # it reads "/usr/bin/python3" (no space between path and exe name).
        cells.append(Cell(text=path + os.sep))
        cells.append(Cell(text=cmd, bold=True, glue=True))
    else:
        cells.append(Cell(text=cmd, bold=True))
    if args:
        # No leading space: the painter already inserts one separator space
        # between this cell and the command (single space, not double).
        cells.append(Cell(text=args))
    return cells


def _pid_width(items: list[dict[str, Any]]) -> int:
    width = len(str(max((int(i.get("pid") or 0) for i in items), default=0)))
    return max(width, 4)


# ----------------------------------------------------------- entry point


def render(
    payload: dict[str, Any],
    fields_desc: dict[str, dict[str, Any]],
    view: dict[str, Any] | None = None,
) -> list[Row]:
    """Render the processlist plugin's process table.

    ``view`` (optional, supplied by the TUI) carries the active engine
    ``sort_key`` — used to underline the sorted column header (v4 'SORT'
    decoration). Absent ``view`` (export / tests) → no column is marked.
    """
    sort_key = (view or {}).get("sort_key")
    short_name = (view or {}).get("process_short_name", True)

    def _header(label: str, width: int, *, ljust: bool = False, color: ColorRole = ColorRole.HEADER) -> Cell:
        text = label.ljust(width) if ljust else label.rjust(width)
        return Cell(
            text=text,
            color=color,
            bold=True,
            underline=_HEADER_SORT_KEY.get(label) == sort_key if sort_key else False,
        )

    pid_width = _W_PID_DEFAULT
    items: list[dict[str, Any]] = []

    if isinstance(payload, dict):
        raw_items = payload.get("data")
        if isinstance(raw_items, list):
            items = [i for i in raw_items if isinstance(i, dict)]
            if items:
                pid_width = _pid_width(items)

    raw_levels = payload.get("_levels") if isinstance(payload, dict) else None
    levels_index = raw_levels if isinstance(raw_levels, dict) else {}

    title_color = title_role(payload) if items else ColorRole.HEADER

    header_cells = [
        _header("CPU%", _W_CPU, color=title_color),
        _header("MEM%", _W_MEM),
        _header("VIRT", _W_VIRT),
        _header("RES", _W_RES),
        _header("PID", pid_width),
        _header("USER", _W_USER, ljust=True),
        _header("THR", _W_THR),
        _header("NI", _W_NI),
        _header("S", _W_STATUS),
        _header("TIME+", _W_TIME),
        _header("R/s", _W_IO),
        _header("W/s", _W_IO),
        _header("Command", len("Command")),
    ]
    rows: list[Row] = [Row(cells=header_cells)]

    for item in items[:_MAX_ROWS]:
        pid = item.get("pid")
        pid_levels = levels_index.get(pid) if isinstance(levels_index, dict) else None
        pid_levels = pid_levels if isinstance(pid_levels, dict) else {}

        r_rate, r_unknown = _io_rate(item, read=True)
        w_rate, w_unknown = _io_rate(item, read=False)
        status_letter = str(item.get("status") or "?")[:1].rjust(_W_STATUS)
        nice_text = _format_int(item.get("nice"), _W_NI, signed=False)

        fixed_cells = [
            _percent_cell(item.get("cpu_percent"), pid_levels.get("cpu_percent"), _W_CPU),
            _percent_cell(item.get("memory_percent"), pid_levels.get("memory_percent"), _W_MEM),
            Cell(text=_format_bytes(_memory_info_field(item, "vms"), _W_VIRT)),
            Cell(text=_format_bytes(_memory_info_field(item, "rss"), _W_RES)),
            Cell(text=_format_int(pid, pid_width)),
            Cell(text=_format_username(item.get("username"))),
            Cell(text=_format_int(item.get("num_threads"), _W_THR)),
            _level_text_cell(nice_text, pid_levels.get("nice")),
            _level_text_cell(status_letter, pid_levels.get("status")),
            Cell(text=_format_cpu_time(item, _W_TIME)),
            _io_cell(r_rate, r_unknown, _W_IO),
            _io_cell(w_rate, w_unknown, _W_IO),
        ]
        rows.append(Row(cells=fixed_cells + _command_cells(item, short_name)))

    return rows
