#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — tests for the raid curses renderer."""

from __future__ import annotations

from glances.plugins.raid.render_curses_v5 import (
    _AVAIL_COL_WIDTH,
    _LEFT_SIDEBAR_MAX_WIDTH,
    _NAME_MAX_WIDTH,
    _USED_COL_WIDTH,
    render,
)


def _payload(rows, levels=None):
    return {"data": rows, "_levels": levels or {}}


def _flat(rows):
    return "\n".join(" ".join(c.text for c in r.cells) for r in rows)


def _array(name, type_="raid1", status="active", used=2, available=2, components=None, config="UU"):
    return {
        "name": name,
        "type": type_,
        "status": status,
        "used": used,
        "available": available,
        "components": components or {},
        "config": config,
    }


def test_empty_returns_header_only():
    rows = render(_payload([]))
    assert "RAID disks" in _flat(rows)
    assert len(rows) == 1  # header only


def test_header_labels():
    flat = _flat(render(_payload([])))
    assert "RAID disks" in flat
    assert "Used" in flat
    assert "Avail" in flat


def test_active_row_shows_used_and_available():
    rows = render(_payload([_array("md0", "raid1", "active", used=2, available=2)]))
    flat = _flat(rows)
    # Full name = "<TYPE> <name>".
    assert "RAID1 md0" in flat
    # Used=2, Avail=2 appear on the data row.
    data = rows[1]
    assert data.cells[1].text.strip() == "2"
    assert data.cells[2].text.strip() == "2"


def test_raid0_shows_component_count_and_dash():
    rows = render(
        _payload([_array("md9", "raid0", "active", used=None, available=None, components={"sda1": "0", "sdb1": "1"})])
    )
    data = rows[1]
    assert data.cells[1].text.strip() == "2"  # len(components)
    assert data.cells[2].text.strip() == "-"  # no "available" for raid0


def test_unknown_type_renders_uppercase_unknown():
    rows = render(_payload([_array("md0", type_=None, status="active", used=2, available=2)]))
    assert "UNKNOWN md0" in _flat(rows)


def test_width_budget():
    """name + 1 separator + used + 1 separator + avail must fit the 34-char
    left sidebar, or the painter clips the rightmost column."""
    assert _NAME_MAX_WIDTH + 1 + _USED_COL_WIDTH + 1 + _AVAIL_COL_WIDTH <= _LEFT_SIDEBAR_MAX_WIDTH


def test_level_colour_applied():
    levels = {"md0": {"status": {"level": "warning", "prominent": False}}}
    rows = render(_payload([_array("md0", "raid5", "active", used=3, available=4)], levels))
    data = rows[1]
    assert data.cells[1].color.value == "warning"
    assert data.cells[2].color.value == "warning"
    assert data.cells[1].prominent is False


def test_inactive_emits_status_and_component_sub_lines():
    rows = render(
        _payload(
            [_array("md0", "raid1", "inactive", used=2, available=2, components={"sda1": "0", "sdb1": "1"})],
            levels={"md0": {"status": {"level": "critical", "prominent": False}}},
        )
    )
    flat = _flat(rows)
    assert "Status inactive" in flat
    # Components sorted -> sda1 (├─) then sdb1 (└─).
    assert "├─ disk 0: sda1" in flat
    assert "└─ disk 1: sdb1" in flat


def test_inactive_status_line_coloured():
    rows = render(
        _payload(
            [_array("md0", "raid1", "inactive", used=2, available=2, components={"sda1": "0"})],
            levels={"md0": {"status": {"level": "critical", "prominent": False}}},
        )
    )
    status_cells = [c for r in rows for c in r.cells if "Status inactive" in c.text]
    assert status_cells and status_cells[0].color.value == "critical"


def test_degraded_emits_mode_and_layout_lines():
    rows = render(
        _payload(
            [_array("md0", "raid5", "active", used=3, available=4, config="U_")],
            levels={"md0": {"status": {"level": "warning", "prominent": False}}},
        )
    )
    flat = _flat(rows)
    assert "Degraded mode" in flat
    # config "U_".replace("_", "A") -> "UA".
    assert "UA" in flat


def test_degraded_layout_omitted_when_config_too_long():
    rows = render(
        _payload(
            [_array("md0", "raid5", "active", used=3, available=4, config="U" * 20)],
            levels={"md0": {"status": {"level": "warning", "prominent": False}}},
        )
    )
    flat = _flat(rows)
    assert "Degraded mode" in flat
    assert ("U" * 20) not in flat  # layout line suppressed when len(config) >= 17


def test_healthy_array_has_no_sub_lines():
    rows = render(_payload([_array("md0", "raid1", "active", used=2, available=2)]))
    flat = _flat(rows)
    assert "Degraded mode" not in flat
    assert "Status" not in flat
