#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — tests for the smart curses renderer."""

from __future__ import annotations

from glances.globals import auto_unit
from glances.plugins.smart.render_curses_v5 import (
    _LEFT_SIDEBAR_MAX_WIDTH,
    _NAME_COL_WIDTH,
    _VALUE_COL_WIDTH,
    render,
)


def _attr(name, key=None, raw=0, value=100):
    return {"name": name, "key": key if key is not None else name, "raw": raw, "value": value}


def _payload(devices, levels=None):
    return {"data": devices, "_levels": levels or {}}


def _flat(rows):
    return "\n".join(" ".join(c.text for c in r.cells) for r in rows)


def test_empty_returns_header_only():
    rows = render(_payload([]))
    assert "SMART disks" in _flat(rows)
    assert len(rows) == 1  # header only


def test_header_device_and_attributes():
    dev = {"name": "/dev/sda Samsung SSD 850", "attributes": [_attr("Power_On_Hours", raw=12345)]}
    rows = render(_payload([dev]))
    flat = _flat(rows)
    assert "SMART disks" in flat
    assert "/dev/sda Samsung SSD 850" in flat
    # underscores rendered as spaces
    assert "Power On Hours" in flat
    assert "12345" in flat


def test_large_value_key_uses_auto_unit():
    dev = {"name": "/dev/nvme0 NVMe", "attributes": [_attr("Bytes written", key="bytesWritten", raw=1500000)]}
    rows = render(_payload([dev]))
    flat = _flat(rows)
    expected = auto_unit(1500000)  # e.g. '1.4M'
    assert expected in flat
    assert "1500000" not in flat  # raw not shown for a LARGE_VALUE_KEYS attribute


def test_none_raw_renders_blank_value():
    dev = {"name": "/dev/sda", "attributes": [_attr("Some_Attr", raw=None)]}
    rows = render(_payload([dev]))
    # attribute row present, value cell is blank (not the string 'None').
    assert "None" not in _flat(rows)


def test_row_fits_left_sidebar_budget():
    """name col + 1 separator + value col must fit the 34-char left sidebar."""
    assert _NAME_COL_WIDTH + 1 + _VALUE_COL_WIDTH <= _LEFT_SIDEBAR_MAX_WIDTH
    dev = {"name": "/dev/sda Samsung SSD 850 EVO extra long", "attributes": [_attr("Power_On_Hours", raw=12345)]}
    rows = render(_payload([dev]))
    for r in rows:
        # every attribute row is exactly [name_cell, value_cell]; the device
        # and header rows are single cells clamped to the block width.
        if len(r.cells) == 2:
            assert len(r.cells[0].text) + 1 + len(r.cells[1].text) <= _LEFT_SIDEBAR_MAX_WIDTH
        else:
            assert len(r.cells[0].text) <= _LEFT_SIDEBAR_MAX_WIDTH


def test_only_the_device_row_is_marked():
    """smart emits one row per attribute; the counter must count DEVICES."""
    dev = {"name": "/dev/sda", "attributes": [_attr("Power_On_Hours"), _attr("Temperature")]}
    rows = render(_payload([dev, {"name": "/dev/sdb", "attributes": [_attr("Reallocated")]}]))
    assert rows[0].item_start is False  # header
    assert sum(r.item_start for r in rows) == 2
    assert len(rows) == 6  # header + (sda + 2 attrs) + (sdb + 1 attr)
