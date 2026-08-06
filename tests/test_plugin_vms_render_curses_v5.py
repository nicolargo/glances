#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the Glances v5 vms TUI renderer."""

from __future__ import annotations

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.vms.render_curses_v5 import render


def _payload(items, max_name_size=20):
    return {"data": items, "max_name_size": max_name_size}


def _flat(rows):
    return "".join(c.text for row in rows for c in row.cells)


def _vm(**over):
    base = {
        "name": "vm-a",
        "status": "running",
        "cpu_count": 2,
        "cpu_time": None,
        "memory_usage": 1024,
        "memory_total": 4096,
        "load_1min": None,
        "engine": "multipass",
        "release": "24.04",
    }
    base.update(over)
    return base


def test_empty_returns_nothing():
    assert render(_payload([])) == []


def test_header_and_row_no_title():
    # No title row (consistency with containers): rows[0] is the column header.
    rows = render(_payload([_vm()]))
    assert "VMs" not in _flat([rows[0]])  # first row is the header, not a "VMs …" title
    header = _flat([rows[0]])
    assert "Name" in header
    assert "Status" in header
    assert "Core" in header
    assert "CPU%" in header
    assert "MEM" in header
    assert "MAX" in header
    assert "Release" in header
    data = _flat([rows[1]])
    assert "vm-a" in data
    assert "running" in data


def test_engine_column_hidden_single_engine():
    items = [_vm(name="vm-a", engine="virsh"), _vm(name="vm-b", engine="virsh")]
    rows = render(_payload(items))
    assert "Engine" not in _flat([rows[0]])


def test_engine_column_shown_multi_engine():
    items = [_vm(name="vm-a", engine="multipass"), _vm(name="vm-b", engine="virsh")]
    rows = render(_payload(items))
    assert "Engine" in _flat([rows[0]])


def test_load_columns_hidden_when_load_none():
    rows = render(_payload([_vm(load_1min=None)]))
    assert "LOAD 1/5/15min" not in _flat([rows[0]])


def test_load_columns_shown_when_load_present():
    rows = render(_payload([_vm(load_1min=0.5, load_5min=0.4, load_15min=0.3)]))
    assert "LOAD 1/5/15min" in _flat([rows[0]])
    assert "0.5" in _flat([rows[1]])


def test_status_colour_running_ok():
    rows = render(_payload([_vm(status="running")]))
    status_cell = [c for c in rows[1].cells if "running" in c.text][0]
    assert status_cell.color == ColorRole.OK


def test_status_colour_starting_warning():
    rows = render(_payload([_vm(status="starting")]))
    status_cell = [c for c in rows[1].cells if "starting" in c.text][0]
    assert status_cell.color == ColorRole.WARNING


def test_status_colour_other_default():
    rows = render(_payload([_vm(status="stopped")]))
    status_cell = [c for c in rows[1].cells if "stopped" in c.text][0]
    assert status_cell.color == ColorRole.DEFAULT


def test_cpu_time_absent_shows_dash():
    vm = _vm()
    del vm["cpu_time"]
    rows = render(_payload([vm]))
    # Core cell has cpu_count=2; CPU% cell should be the dash placeholder.
    dash_cells = [c for c in rows[1].cells if c.text.strip() == "-"]
    assert dash_cells


def test_name_truncated_to_max_name_size():
    rows = render(_payload([_vm(name="a-very-long-vm-name")], max_name_size=5))
    name_cell = rows[1].cells[0] if "Engine" not in _flat([rows[0]]) else rows[1].cells[1]
    assert len(name_cell.text.strip()) <= 5


def test_sort_underline_name():
    rows = render(_payload([_vm()]), view={"sort_key": "name"})
    header = rows[0].cells
    name_cell = next(c for c in header if c.text.strip() == "Name")
    cpu_cell = next(c for c in header if c.text.strip() == "CPU%")
    assert name_cell.underline is True
    assert cpu_cell.underline is False


def test_sort_underline_cpu():
    rows = render(_payload([_vm()]), view={"sort_key": "cpu_percent"})
    header = rows[0].cells
    cpu_cell = next(c for c in header if c.text.strip() == "CPU%")
    name_cell = next(c for c in header if c.text.strip() == "Name")
    assert cpu_cell.underline is True
    assert name_cell.underline is False


def test_sort_underline_mem():
    rows = render(_payload([_vm()]), view={"sort_key": "memory_percent"})
    header = rows[0].cells
    mem_cell = next(c for c in header if "MEM" in c.text and "MAX" in c.text)
    assert mem_cell.underline is True


def test_no_view_no_underline():
    rows = render(_payload([_vm()]))
    header = rows[0].cells
    assert all(c.underline is False for c in header)


def _many_vms(n):
    return [_vm(name=f"vm{i}") for i in range(n)]


def test_row_budget_truncates_the_vm_list():
    rows = render(_payload(_many_vms(12)), {}, view={"row_budget": {"vms": 3}})
    assert len(rows) == 1 + 3


def test_truncated_list_shows_a_counter_in_the_name_header():
    rows = render(_payload(_many_vms(12)), {}, view={"row_budget": {"vms": 3}})
    assert "Name 3/12" in _flat([rows[0]])


def test_untruncated_list_keeps_the_bare_header_label():
    rows = render(_payload(_many_vms(2)), {}, view={"row_budget": {"vms": 10}})
    assert "/" not in _flat([rows[0]]).split("Status")[0]


def test_zero_budget_hides_the_block_entirely():
    assert render(_payload(_many_vms(12)), {}, view={"row_budget": {"vms": 0}}) == []


def test_without_row_budget_all_vms_are_rendered():
    rows = render(_payload(_many_vms(12)), {})
    assert len(rows) == 1 + 12


def test_counter_widens_the_name_column_so_data_rows_stay_aligned():
    rows = render(_payload([_vm(name="a") for _ in range(12)]), {}, view={"row_budget": {"vms": 3}})
    name_index = 0  # pas de colonne Engine avec un seul moteur
    assert len(rows[0].cells[name_index].text) == len(rows[1].cells[name_index].text)


def test_sort_underline_survives_the_truncation_counter():
    rows = render(
        _payload(_many_vms(12)),
        {},
        view={"row_budget": {"vms": 3}, "sort_key": "name"},
    )
    assert rows[0].cells[0].underline is True
