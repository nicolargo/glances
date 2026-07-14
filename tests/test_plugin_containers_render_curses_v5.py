#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the Glances v5 containers TUI renderer."""

from __future__ import annotations

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.containers.render_curses_v5 import render


def _payload(data, levels=None, disable_stats=None, max_name_size=20):
    return {
        "data": data,
        "_levels": levels or {},
        "disable_stats": disable_stats or [],
        "max_name_size": max_name_size,
    }


def _texts(row):
    return "".join(c.text for c in row.cells)


def test_empty_data_returns_empty():
    assert render(_payload([])) == []


def test_header_and_one_row():
    data = [
        {
            "name": "web",
            "engine": "docker",
            "status": "running",
            "uptime": "1h",
            "cpu_percent": 12.0,
            "memory_usage_no_cache": 200,
            "memory_limit": 1000,
            "ports": "",
        }
    ]
    rows = render(_payload(data), None, {"sort_key": None, "byte": False})
    assert len(rows) == 2  # header + 1
    header = _texts(rows[0])
    assert "CONTAINER" in header and "CPU%" in header and "Status" in header


def test_status_colour_running_is_ok():
    data = [{"name": "web", "engine": "docker", "status": "running"}]
    rows = render(_payload(data), None, {})
    # find the status cell (text startswith "running" padded)
    status_cells = [c for c in rows[1].cells if "running" in c.text]
    assert status_cells and status_cells[0].color == ColorRole.OK


def test_status_colour_exited_is_warning():
    data = [{"name": "web", "engine": "docker", "status": "exited"}]
    rows = render(_payload(data), None, {})
    cells = [c for c in rows[1].cells if "exited" in c.text]
    assert cells and cells[0].color == ColorRole.WARNING


def test_status_colour_dead_is_critical():
    data = [{"name": "web", "engine": "docker", "status": "dead"}]
    rows = render(_payload(data), None, {})
    cells = [c for c in rows[1].cells if "dead" in c.text]
    assert cells and cells[0].color == ColorRole.CRITICAL


def test_cpu_cell_coloured_by_level():
    data = [{"name": "web", "engine": "docker", "status": "running", "cpu_percent": 95.0}]
    levels = {"web": {"cpu_percent": {"level": "critical", "prominent": False}}}
    rows = render(_payload(data, levels), None, {})
    cpu_cells = [c for c in rows[1].cells if c.text.strip() == "95.0"]
    assert cpu_cells and cpu_cells[0].color == ColorRole.CRITICAL


def test_disable_stats_hides_column():
    data = [{"name": "web", "engine": "docker", "status": "running", "cpu_percent": 12.0}]
    rows = render(_payload(data, disable_stats=["cpu"]), None, {})
    assert "CPU%" not in _texts(rows[0])


def test_engine_column_only_when_multiple_engines():
    one = [{"name": "a", "engine": "docker", "status": "running"}]
    two = [
        {"name": "a", "engine": "docker", "status": "running"},
        {"name": "b", "engine": "podman", "status": "running"},
    ]
    assert "Engine" not in _texts(render(_payload(one), None, {})[0])
    assert "Engine" in _texts(render(_payload(two), None, {})[0])


def test_pod_column_only_when_pod_present():
    no_pod = [{"name": "a", "engine": "docker", "status": "running"}]
    with_pod = [{"name": "a", "engine": "podman", "status": "running", "pod_name": "p1", "pod_id": "abc"}]
    assert "Pod" not in _texts(render(_payload(no_pod), None, {})[0])
    assert "Pod" in _texts(render(_payload(with_pod), None, {})[0])


def test_sort_underline_on_cpu():
    data = [{"name": "web", "engine": "docker", "status": "running", "cpu_percent": 12.0}]
    rows = render(_payload(data), None, {"sort_key": "cpu_percent"})
    cpu_hdr = [c for c in rows[0].cells if "CPU%" in c.text]
    assert cpu_hdr and cpu_hdr[0].underline is True


def test_sort_underline_on_name():
    # Process sort key `name` underlines the CONTAINER (name) header. Guards the
    # header-label <-> _HEADER_SORT_KEY consistency (a label rename must update the map).
    data = [{"name": "web", "engine": "docker", "status": "running"}]
    rows = render(_payload(data), None, {"sort_key": "name"})
    name_hdr = [c for c in rows[0].cells if c.text.strip() == "CONTAINER"]
    assert name_hdr and name_hdr[0].underline is True


def test_sort_underline_on_mem_maps_to_memory_percent():
    # Process sort key `memory_percent` underlines the MEM header (processlist-aligned).
    data = [
        {"name": "web", "engine": "docker", "status": "running", "memory_usage_no_cache": 100, "memory_limit": 1000}
    ]
    rows = render(_payload(data), None, {"sort_key": "memory_percent"})
    mem_hdr = [c for c in rows[0].cells if c.text.strip() == "MEM"]
    assert mem_hdr and mem_hdr[0].underline is True


def test_net_bits_vs_bytes():
    data = [{"name": "web", "engine": "docker", "status": "running", "network_rx": 100, "network_tx": 0}]
    bits = render(_payload(data), None, {"byte": False})
    byts = render(_payload(data), None, {"byte": True})
    # bits multiply by 8 → different rendered Rx text
    assert _texts(bits[1]) != _texts(byts[1])
