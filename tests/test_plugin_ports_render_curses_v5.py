#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the Glances v5 ports TUI renderer."""

from __future__ import annotations

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.ports.render_curses_v5 import (
    _NAME_MAX_WIDTH,
    _STATUS_COL_WIDTH,
    render,
)


def _payload(data, levels=None):
    return {"data": data, "time_since_update": 2.0, "_levels": levels or {}}


def _texts(row):
    return "".join(c.text for c in row.cells)


def _status_text(row):
    return row.cells[-1].text.strip()


def test_empty_data_returns_empty():
    assert render(_payload([])) == []


def test_missing_data_key_returns_empty():
    assert render({}) == []


# --- NO TITLE ROW guard ---------------------------------------------------


def test_no_title_row_deliberate_do_not_fix():
    """`ports` sits directly under `network` in LEFT_SLOT; the two belong to the
    same functional domain and read as one continuous block. The absent title is
    that continuity, NOT an oversight (design §5.3). This test exists so a future
    reviewer cannot silently "align ports with the other LEFT plugins"."""
    data = [
        {"indice": "port_1", "host": "h", "port": 80, "description": "Home Box", "status": 0.012, "rtt_warning": None},
        {
            "indice": "web_1",
            "url": "http://x",
            "description": "My Blog",
            "status": 200,
            "elapsed": 0.1,
            "rtt_warning": None,
        },
    ]
    rows = render(_payload(data))
    # Exactly one row per item — no title, no column header.
    assert len(rows) == len(data)
    assert "PORTS" not in _texts(rows[0]).upper()
    for row in rows:
        for cell in row.cells:
            assert cell.color is not ColorRole.HEADER
            assert cell.bold is False


# --- port-kind status strings --------------------------------------------


def test_port_status_scanning():
    data = [{"indice": "port_1", "host": "h", "port": 80, "description": "Home Box", "status": None}]
    assert _status_text(render(_payload(data))[0]) == "Scanning"


def test_port_status_open_when_status_is_true():
    data = [{"indice": "port_1", "host": "h", "port": 80, "description": "Home Box", "status": True}]
    assert _status_text(render(_payload(data))[0]) == "Open"


def test_port_status_timeout_when_status_is_false():
    data = [{"indice": "port_1", "host": "h", "port": 80, "description": "Home Box", "status": False}]
    assert _status_text(render(_payload(data))[0]) == "Timeout"


def test_port_status_timeout_when_status_is_zero():
    data = [{"indice": "port_1", "host": "h", "port": 80, "description": "Home Box", "status": 0}]
    assert _status_text(render(_payload(data))[0]) == "Timeout"


def test_port_status_rtt_in_milliseconds():
    # v4 stores the RTT in seconds and displays milliseconds, rounded to 0 dp.
    data = [{"indice": "port_1", "host": "h", "port": 80, "description": "Home Box", "status": 0.0123}]
    assert _status_text(render(_payload(data))[0]) == "12ms"


def test_port_status_none_host():
    # `get_default_gateway()` can return None → v4 prints the literal "None".
    data = [{"indice": "port_0", "host": None, "port": 0, "description": "DefaultGateway", "status": None}]
    assert _status_text(render(_payload(data))[0]) == "None"


# --- web-kind status strings ---------------------------------------------


def test_web_status_code():
    data = [{"indice": "web_1", "url": "http://x", "description": "My Blog", "status": 404, "elapsed": 0.1}]
    assert _status_text(render(_payload(data))[0]) == "Code 404"


def test_web_status_scanning():
    data = [{"indice": "web_1", "url": "http://x", "description": "My Blog", "status": None, "elapsed": 0}]
    assert _status_text(render(_payload(data))[0]) == "Scanning"


def test_web_status_error_string():
    data = [{"indice": "web_1", "url": "http://x", "description": "My Blog", "status": "Error", "elapsed": 0}]
    assert _status_text(render(_payload(data))[0]) == "Error"


# --- layout ---------------------------------------------------------------


def test_description_is_left_aligned_and_padded():
    data = [{"indice": "port_1", "host": "h", "port": 80, "description": "Box", "status": 0}]
    name_cell = render(_payload(data))[0].cells[0]
    assert name_cell.text == "Box".ljust(_NAME_MAX_WIDTH)


def test_long_description_is_truncated():
    long_name = "A" * 80
    data = [{"indice": "port_1", "host": "h", "port": 80, "description": long_name, "status": 0}]
    name_cell = render(_payload(data))[0].cells[0]
    assert name_cell.text == "A" * _NAME_MAX_WIDTH
    assert len(name_cell.text) == _NAME_MAX_WIDTH


def test_status_is_right_aligned_on_nine_and_glued():
    data = [{"indice": "port_1", "host": "h", "port": 80, "description": "Box", "status": 0}]
    status_cell = render(_payload(data))[0].cells[-1]
    assert status_cell.text == "Timeout".rjust(_STATUS_COL_WIDTH)
    # glue=True → the painter adds NO separating space (v4 concatenates directly),
    # so the block spans exactly 25 + 9 = 34 = the left-sidebar budget.
    assert status_cell.glue is True


def test_block_fits_the_left_sidebar_budget():
    from glances.outputs.curses_renderer_v5 import PluginBlock

    data = [{"indice": "web_1", "url": "http://x", "description": "X" * 80, "status": 404, "elapsed": 0.1}]
    block = PluginBlock(name="ports", rows=render(_payload(data)))
    assert block.width == 34


def test_missing_description_renders_blank_padding():
    data = [{"indice": "port_1", "host": "h", "port": 80, "status": 0}]
    assert render(_payload(data))[0].cells[0].text == " " * _NAME_MAX_WIDTH


def test_item_with_neither_host_nor_url_is_skipped():
    data = [{"indice": "weird_1", "description": "?", "status": None}]
    assert render(_payload(data)) == []


# --- colours --------------------------------------------------------------


def test_port_status_cell_coloured_from_levels():
    data = [{"indice": "port_1", "host": "h", "port": 80, "description": "Box", "status": 0}]
    levels = {"port_1": {"status": {"level": "critical", "prominent": False}}}
    cell = render(_payload(data, levels))[0].cells[-1]
    assert cell.color == ColorRole.CRITICAL
    assert cell.prominent is False


def test_web_status_cell_coloured_from_levels():
    data = [{"indice": "web_1", "url": "http://x", "description": "Blog", "status": 200, "elapsed": 9.0}]
    levels = {"web_1": {"status": {"level": "warning", "prominent": False}}}
    assert render(_payload(data, levels))[0].cells[-1].color == ColorRole.WARNING


def test_careful_level_colours_the_scanning_cell():
    data = [{"indice": "port_1", "host": "h", "port": 80, "description": "Box", "status": None}]
    levels = {"port_1": {"status": {"level": "careful", "prominent": False}}}
    assert render(_payload(data, levels))[0].cells[-1].color == ColorRole.CAREFUL


def test_no_level_entry_falls_back_to_default_colour():
    data = [{"indice": "port_1", "host": "h", "port": 80, "description": "Box", "status": 0.01}]
    assert render(_payload(data))[0].cells[-1].color == ColorRole.DEFAULT


def test_malformed_level_entry_falls_back_to_default_colour():
    # Guards against `AttributeError` if `_levels[indice]` is not a dict.
    data = [{"indice": "port_1", "host": "h", "port": 80, "description": "Box", "status": 0.01}]
    levels = {"port_1": "not-a-dict"}
    assert render(_payload(data, levels))[0].cells[-1].color == ColorRole.DEFAULT


def test_status_prominent_forwarded_when_levels_carry_it():
    data = [{"indice": "port_1", "host": "h", "port": 80, "description": "Box", "status": 0}]
    levels = {"port_1": {"status": {"level": "critical", "prominent": True}}}
    cell = render(_payload(data, levels))[0].cells[-1]
    assert cell.prominent is True


def test_status_prominent_not_set_when_levels_lack_it():
    data = [{"indice": "port_1", "host": "h", "port": 80, "description": "Box", "status": 0}]
    levels = {"port_1": {"status": {"level": "critical"}}}
    cell = render(_payload(data, levels))[0].cells[-1]
    assert cell.prominent is False


def test_both_kinds_render_in_one_block():
    data = [
        {"indice": "port_1", "host": "h", "port": 80, "description": "Home Box", "status": 0},
        {"indice": "web_1", "url": "http://x", "description": "My Blog", "status": 200, "elapsed": 0.1},
    ]
    levels = {
        "port_1": {"status": {"level": "critical", "prominent": False}},
        "web_1": {"status": {"level": "warning", "prominent": False}},
    }
    rows = render(_payload(data, levels))
    assert len(rows) == 2
    assert _status_text(rows[0]) == "Timeout"
    assert rows[0].cells[-1].color == ColorRole.CRITICAL
    assert _status_text(rows[1]) == "Code 200"
    assert rows[1].cells[-1].color == ColorRole.WARNING
