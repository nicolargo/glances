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


def _many(n):
    return [
        {
            "name": f"ctr{i}",
            "status": "running",
            "cpu_percent": 1.0,
            "memory_usage_no_cache": 1024,
            "memory_limit": 4096,
        }
        for i in range(n)
    ]


def test_row_budget_truncates_the_container_list():
    rows = render(_payload(_many(25)), {}, view={"row_budget": {"containers": 7}})
    assert len(rows) == 1 + 7


def test_truncated_list_shows_a_counter_in_the_name_header():
    rows = render(_payload(_many(25)), {}, view={"row_budget": {"containers": 7}})
    assert "CONTAINER 7/25" in _texts(rows[0])


def test_untruncated_list_keeps_the_bare_header_label():
    rows = render(_payload(_many(5)), {}, view={"row_budget": {"containers": 10}})
    header = _texts(rows[0])
    assert "CONTAINER" in header
    assert "/" not in header.split("Status")[0]


def test_zero_budget_hides_the_block_entirely():
    assert render(_payload(_many(25)), {}, view={"row_budget": {"containers": 0}}) == []


def test_without_row_budget_all_containers_are_rendered():
    """Non-régression : appel direct sans view → sortie inchangée."""
    rows = render(_payload(_many(25)), {})
    assert len(rows) == 1 + 25


def test_counter_widens_the_name_column_so_data_rows_stay_aligned():
    """Un compteur plus long que le nom le plus long ne doit pas décaler les
    colonnes suivantes : la cellule de nom garde la même largeur en en-tête
    et en données."""
    data = [{"name": "a", "status": "running"} for _ in range(25)]
    rows = render(_payload(data), {}, view={"row_budget": {"containers": 7}})
    assert rows[0].cells[0].text.startswith("CONTAINER 7/25")
    assert len(rows[0].cells[0].text) == len(rows[1].cells[0].text)


def test_sort_underline_survives_the_truncation_counter():
    rows = render(
        _payload(_many(25)),
        {},
        view={"row_budget": {"containers": 7}, "sort_key": "name"},
    )
    assert rows[0].cells[0].underline is True


# --------------------------------------------------------- responsive columns
#
# Largeur naturelle de la ligne pour `_rich()` (un seul moteur, pas de pod) :
# name_w vaut 9 — le nom "web" est plus court que le libellé "CONTAINER", qui
# fixe donc le plancher de la colonne. L'échelle des seuils est alors :
#
#     toutes colonnes                113
#     - command  (8 + 1 sép.)        104
#     - ports    (16 + 1)             87
#     - /MAX     (8 + 1)              78
#     - diskio   (14 + 2)             62
#     - networkio(14 + 2)             46
#     - uptime   (10 + 1)             35
#     - status   (10 + 1)             24  <- plancher CONTAINER + CPU% + MEM
#
# Chaque test vise une largeur strictement à l'intérieur d'un palier.


def _labels(row):
    """En-têtes de colonnes, dépadées, dans l'ordre d'affichage."""
    return [c.text.strip() for c in row.cells]


def _rich(name="web", engine="docker", **extra):
    c = {
        "name": name,
        "engine": engine,
        "status": "running",
        "uptime": "1h",
        "cpu_percent": 12.0,
        "memory_usage_no_cache": 200,
        "memory_limit": 1000,
        "io_rx": 1024,
        "io_wx": 2048,
        "network_rx": 512,
        "network_tx": 256,
        "ports": "8080",
        "command": "/usr/bin/glances",
    }
    c.update(extra)
    return c


def test_no_right_width_keeps_all_columns():
    """Non-régression : sans `right_width` (export, REST, appels directs), la
    sortie est strictement celle d'avant les colonnes responsives."""
    rows = render(_payload([_rich()]), {}, view={})
    assert _labels(rows[0]) == [
        "CONTAINER",
        "Status",
        "Uptime",
        "CPU%",
        "MEM",
        "/MAX",
        "IOR/s",
        "IOW/s",
        "Rx/s",
        "Tx/s",
        "Ports",
        "Command",
    ]


def test_wide_right_width_keeps_all_columns():
    rows = render(_payload([_rich()]), {}, view={"right_width": 200})
    assert "Command" in _labels(rows[0])
    assert "Ports" in _labels(rows[0])


def test_command_is_dropped_first():
    rows = render(_payload([_rich()]), {}, view={"right_width": 110})
    labels = _labels(rows[0])
    assert "Command" not in labels
    assert "Ports" in labels


def test_ports_is_dropped_after_command():
    rows = render(_payload([_rich()]), {}, view={"right_width": 95})
    labels = _labels(rows[0])
    assert "Ports" not in labels
    assert "/MAX" in labels


def test_mem_max_is_dropped_but_mem_is_kept():
    rows = render(_payload([_rich()]), {}, view={"right_width": 80})
    labels = _labels(rows[0])
    assert "/MAX" not in labels
    assert "MEM" in labels
    assert "IOR/s" in labels


def test_diskio_columns_drop_as_a_pair():
    rows = render(_payload([_rich()]), {}, view={"right_width": 70})
    labels = _labels(rows[0])
    assert "IOR/s" not in labels and "IOW/s" not in labels
    assert "Rx/s" in labels and "Tx/s" in labels


def test_networkio_columns_drop_as_a_pair():
    rows = render(_payload([_rich()]), {}, view={"right_width": 50})
    labels = _labels(rows[0])
    assert "Rx/s" not in labels and "Tx/s" not in labels
    assert "Uptime" in labels


def test_uptime_is_dropped_before_status():
    rows = render(_payload([_rich()]), {}, view={"right_width": 40})
    labels = _labels(rows[0])
    assert "Uptime" not in labels
    assert "Status" in labels


def test_identity_columns_survive_the_narrowest_width():
    rows = render(_payload([_rich()]), {}, view={"right_width": 10})
    assert _labels(rows[0]) == ["CONTAINER", "CPU%", "MEM"]


def test_pod_is_dropped_before_engine():
    """Ligne naturelle = 133 (113 + Engine 7 + Pod 13) ; à 90 on a droppé
    command/ports//MAX (98) puis Pod (85), Engine survit."""
    data = [
        _rich(name="web", engine="docker", pod_id="pod1", pod_name="p"),
        _rich(name="db", engine="podman", pod_id="pod1", pod_name="p"),
    ]
    rows = render(_payload(data), {}, view={"right_width": 90})
    labels = _labels(rows[0])
    assert "Pod" not in labels
    assert "Engine" in labels


def test_column_disabled_by_config_frees_room_for_a_lower_priority_one():
    """`disable_stats` retire la colonne du calcul de largeur : à 100 colonnes,
    Ports désactivé ramène la ligne à 96 et laisse Command, droppée sinon."""
    control = render(_payload([_rich()]), {}, view={"right_width": 100})
    assert "Command" not in _labels(control[0])
    rows = render(_payload([_rich()], disable_stats=["ports"]), {}, view={"right_width": 100})
    assert "Command" in _labels(rows[0])


def test_header_and_data_rows_stay_cell_aligned_after_drops():
    rows = render(_payload([_rich()]), {}, view={"right_width": 70})
    assert len(rows[0].cells) == len(rows[1].cells)
    for header_cell, data_cell in zip(rows[0].cells, rows[1].cells):
        assert len(header_cell.text) == len(data_cell.text)
