#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — tests for the npu curses renderer."""

from __future__ import annotations

from glances.plugins.npu.render_curses_v5 import render


def _payload(npus, levels=None):
    return {"data": npus, "_levels": levels or {}}


def _npu(npu_id="intel_1", name="Intel NPU", load=45, freq=50, fc=1_000_000_000, fm=2_000_000_000, mem=None, temp=None):
    return {
        "npu_id": npu_id,
        "name": name,
        "load": load,
        "freq": freq,
        "freq_current": fc,
        "freq_max": fm,
        "mem": mem,
        "temperature": temp,
    }


def _flat(rows):
    return "\n".join(" ".join(c.text for c in r.cells) for r in rows)


def test_empty_returns_no_rows():
    assert render(_payload([])) == []


def test_header_uses_first_npu_name():
    rows = render(_payload([_npu(name="Meteor Lake NPU")]))
    assert "Meteor Lake NPU" in _flat(rows)


def test_load_line_shown_when_load_present():
    rows = render(_payload([_npu(load=45)]))
    flat = _flat(rows)
    assert "45" in flat  # load %
    assert "Hz" in flat  # freq range


def test_freq_fallback_when_load_none():
    rows = render(_payload([_npu(load=None, freq=60)]))
    assert "60" in _flat(rows)


def test_mem_and_temperature_rows():
    rows = render(_payload([_npu(mem=30, temp=55)]))
    flat = _flat(rows)
    assert "mem" in flat and "30" in flat
    assert "temperature" in flat and "55" in flat


def test_only_first_npu_rendered():
    rows = render(_payload([_npu("intel_1", "First"), _npu("amd_1", "Second")]))
    flat = _flat(rows)
    assert "First" in flat
    assert "Second" not in flat


def test_temperature_fahrenheit_when_view_flag_set():
    """view["fahrenheit"] converts the temperature row (v5 enhancement; v4 npu is Celsius-only)."""
    rows = render(_payload([_npu(temp=100)]), None, view={"fahrenheit": True})
    flat = _flat(rows)
    assert "212" in flat  # 100C -> 212F
    assert "F" in flat
