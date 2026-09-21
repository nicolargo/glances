"""The browser cannot import Python, so the TUI's column widths exist twice.
This test is the only thing keeping the copies honest -- never edit one side
alone.
"""

from __future__ import annotations

import re
from pathlib import Path

from glances.outputs import curses_renderer_v5 as renderer
from glances.plugins.containers import render_curses_v5 as containers
from glances.plugins.processlist import render_curses_v5 as processlist
from glances.plugins.programlist import render_curses_v5 as programlist

_MODULE = Path("glances/outputs/static/js/v5/process_widths.js")


def _int_const(name: str) -> int:
    match = re.search(rf"export const {name}\s*=\s*(\d+)\s*;", _MODULE.read_text())
    assert match, f"{name} is not exported from {_MODULE}"
    return int(match.group(1))


def _width_map(name: str) -> dict[str, int]:
    body = re.search(rf"export const {name}\s*=\s*\{{(.*?)\}};", _MODULE.read_text(), re.S)
    assert body, f"{name} is not exported from {_MODULE}"
    return {k: int(v) for k, v in re.findall(r'"([^"]+)"\s*:\s*(\d+)', body.group(1))}


def test_the_processlist_widths_match_the_terminal_renderer():
    assert _width_map("PROCESS_COL_WIDTHS") == {
        "CPU%": processlist._W_CPU,
        "MEM%": processlist._W_MEM,
        "VIRT": processlist._W_VIRT,
        "RES": processlist._W_RES,
        "PID": processlist._W_PID_DEFAULT,
        "USER": processlist._W_USER,
        "THR": processlist._W_THR,
        "NI": processlist._W_NI,
        "S": processlist._W_STATUS,
        "TIME+": processlist._W_TIME,
        "R/s": processlist._W_IO,
        "W/s": processlist._W_IO,
    }


def test_the_command_floor_matches():
    assert _int_const("MIN_COMMAND_WIDTH") == processlist._MIN_COMMAND_WIDTH


def test_the_fixed_column_order_matches():
    """A <colgroup> is positional: a different order silently mis-sizes every
    column, and no width assertion would catch it.
    """
    body = re.search(r"export const FIXED_COL_KEYS\s*=\s*\[(.*?)\];", _MODULE.read_text(), re.S)
    assert body, "FIXED_COL_KEYS is not exported"
    assert re.findall(r'"([^"]+)"', body.group(1)) == processlist._FIXED_COL_KEYS


def test_the_programlist_nprocs_width_matches():
    assert _int_const("NPROCS_WIDTH") == programlist._W_NPROCS


def test_the_programlist_fixed_column_order_matches():
    """Same positional risk as `test_the_fixed_column_order_matches` above,
    for programlist's own copy: CPU% and NPROCS are both width 7, so a
    transposition of that adjacent pair mis-sizes every column while every
    width assertion (including the WebUI's own column-width test) stays
    green -- only the order, checked independently of any width, catches it.
    """
    body = re.search(r"export const PROGRAM_FIXED_COL_KEYS\s*=\s*\[(.*?)\];", _MODULE.read_text(), re.S)
    assert body, "PROGRAM_FIXED_COL_KEYS is not exported"
    assert re.findall(r'"([^"]+)"', body.group(1)) == programlist._FIXED_COL_KEYS


def test_the_alert_grid_geometry_matches():
    assert _width_map("ALERT_COL_WIDTHS") == {
        "GLYPH": renderer._ALERT_W_GLYPH,
        "TIME": renderer._ALERT_W_TIME,
        "DURATION": renderer._ALERT_W_DURATION,
        "LEVEL": renderer._ALERT_W_LEVEL,
    }
    assert _int_const("ALERT_MIN_TARGET") == renderer._ALERT_MIN_TARGET
    assert _int_const("ALERT_MIN_TOP") == renderer._ALERT_MIN_TOP
    assert _int_const("ALERT_W_WITH_TOP") == renderer._ALERT_W_WITH_TOP
    assert _int_const("ALERT_W_WITH_LEVEL") == renderer._ALERT_W_WITH_LEVEL
    assert _int_const("ALERT_W_WITH_DURATION") == renderer._ALERT_W_WITH_DURATION


def test_the_container_column_geometry_matches_the_terminal_renderer():
    """`_COL_GEOMETRY` is (cells, width) per key; the browser needs the two
    halves separately (one <col> per CELL, each `width / cells` wide), so the
    copy is two maps. Both are compared here -- a `diskio` silently reduced to
    one cell on the Python side would otherwise leave the browser painting two
    7-character columns where the terminal paints one 14-character one.
    """
    geometry = containers._COL_GEOMETRY
    assert _width_map("CONTAINER_COL_WIDTHS") == {key: width for key, (_, width) in geometry.items()}
    assert _width_map("CONTAINER_COL_CELLS") == {key: cells for key, (cells, _) in geometry.items()}


def test_the_container_command_floor_is_the_one_the_geometry_budgets():
    """The elastic tail contributes its FLOOR to the table's min-width, and
    for `command` that floor IS its `_COL_GEOMETRY` entry (the terminal paints
    the cell unbounded, :213, and budgets it at `_MIN_COMMAND_WIDTH`). Pinned
    separately from the map above: the two are equal by construction in the
    renderer, and nothing else would notice if they stopped being.
    """
    assert _width_map("CONTAINER_COL_WIDTHS")["command"] == containers._MIN_COMMAND_WIDTH


def test_the_container_column_order_matches():
    """Same positional risk as the processlist <colgroup> above. `name` is the
    one display column with no `_COL_GEOMETRY` entry (the terminal sizes it
    from the data, `name_w`), so it is removed before comparing; the rest must
    stay in the renderer's own order, which is also its header build order
    (`_build_header_row`).
    """
    body = re.search(r"export const CONTAINER_COL_KEYS\s*=\s*\[(.*?)\];", _MODULE.read_text(), re.S)
    assert body, "CONTAINER_COL_KEYS is not exported"
    keys = re.findall(r'"([^"]+)"', body.group(1))
    assert "name" in keys, f"the name column is missing entirely: {keys!r}"
    assert [key for key in keys if key != "name"] == list(containers._COL_GEOMETRY)


def test_the_container_name_cap_default_matches():
    """`[containers] max_name_size`'s fallback, for a payload that carries
    none. It is a literal in the renderer rather than a named constant, so it
    is read out of that source instead of being written twice here.
    """
    source = Path(containers.__file__).read_text()
    match = re.search(r'payload\.get\("max_name_size"\)\s*or\s*(\d+)', source)
    assert match, "the renderer's max_name_size fallback was not found"
    assert _int_const("CONTAINER_MAX_NAME_SIZE") == int(match.group(1))
