#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — tests for the gpu curses renderer."""

from __future__ import annotations

from glances.plugins.gpu.render_curses_v5 import render


def _payload(cards, levels=None):
    return {"data": cards, "_levels": levels or {}}


def _card(gpu_id="nvidia0", name="GeForce RTX", mem=40, proc=30, temp=55):
    return {"gpu_id": gpu_id, "name": name, "mem": mem, "proc": proc, "temperature": temp}


def _flat(rows):
    return "\n".join(" ".join(c.text for c in r.cells) for r in rows)


def test_empty_payload_returns_no_rows():
    assert render(_payload([])) == []


def test_single_gpu_summary_three_metric_rows():
    rows = render(_payload([_card()]))
    flat = _flat(rows)
    # Header (name) + proc/mem/temperature labels.
    assert "GeForce RTX" in flat
    assert "proc:" in flat
    assert "mem:" in flat
    assert "temperature:" in flat
    assert "30" in flat and "40" in flat and "55" in flat


def test_header_two_same_name():
    rows = render(_payload([_card("nvidia0", "Tesla"), _card("nvidia1", "Tesla")]))
    assert "2 Tesla" in _flat(rows)


def test_header_two_different_names():
    rows = render(_payload([_card("nvidia0", "Tesla"), _card("amd0", "Radeon")]))
    assert "2 GPUs" in _flat(rows)


def test_multi_mode_one_row_per_gpu():
    cards = [_card("nvidia0", "Tesla", proc=30, mem=40), _card("amd0", "Radeon", proc=10, mem=20)]
    rows = render(_payload(cards))
    flat = _flat(rows)
    # Multi rows use the name[:9] id and show proc + mem.
    assert "Tesla" in flat and "Radeon" in flat
    assert "mem" in flat


def test_meangpu_forces_summary_for_multi():
    cards = [_card("nvidia0", "Tesla", proc=20), _card("nvidia1", "Tesla", proc=40)]
    rows = render(_payload(cards), {}, view={"meangpu": True})
    flat = _flat(rows)
    assert "proc mean:" in flat
    assert "30" in flat  # mean of 20 and 40


def test_fahrenheit_temperature():
    rows = render(_payload([_card(temp=100)]), {}, view={"fahrenheit": True})
    flat = _flat(rows)
    assert "212" in flat  # 100C -> 212F
    assert "F" in flat


def test_none_values_render_na():
    rows = render(_payload([_card(mem=None, proc=None, temp=None)]))
    assert "N/A" in _flat(rows)


def test_multi_mode_none_values_render_na():
    # #3631: an unavailable metric must be displayed as N/A, not hidden — hiding
    # it drops a cell and misaligns the rows of heterogeneous cards.
    cards = [_card("nvidia0", "Tesla", proc=30, mem=40), _card("intel0", "Intel", proc=None, mem=None)]
    rows = render(_payload(cards))
    assert "N/A" in _flat(rows)
    # Every card row carries the same cell count: name + proc + mem.
    assert [len(r.cells) for r in rows[1:]] == [3, 3]
