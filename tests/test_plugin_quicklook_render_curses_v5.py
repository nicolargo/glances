#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the v5 quicklook curses renderer."""

from __future__ import annotations

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.quicklook.render_curses_v5 import render

FIELDS = {
    "cpu": {"unit": "percent"},
    "mem": {"unit": "percent"},
    "load": {"unit": "percent"},
}


def _text(row):
    return "".join(c.text for c in row.cells)


def _payload(**over):
    base = {
        "cpu": 20.0,
        "mem": 42.0,
        "swap": 10.0,
        "load": 25.0,
        "_levels": {
            "cpu": {"level": "ok", "prominent": True},
            "mem": {"level": "ok", "prominent": True},
            "load": {"level": "ok", "prominent": True},
        },
    }
    base.update(over)
    return base


def test_empty_payload_returns_title_only():
    rows = render({}, FIELDS)
    assert len(rows) == 1
    assert "CPU" in _text(rows[0])


def test_compact_has_cpu_mem_load_rows():
    rows = render(_payload(), FIELDS)
    text = "\n".join(_text(r) for r in rows)
    assert "CPU" in text
    assert "MEM" in text
    assert "LOAD" in text
    # The percent value is rendered by the Bar (e.g. "20.0%").
    assert "20.0%" in text
    assert "42.0%" in text


def test_bar_brackets_present():
    rows = render(_payload(), FIELDS)
    text = "\n".join(_text(r) for r in rows)
    assert "[" in text and "]" in text


def test_level_colors_value_cell():
    rows = render(
        _payload(_levels={"cpu": {"level": "critical", "prominent": True}}),
        FIELDS,
    )
    # The CPU bar cell carries the CRITICAL role.
    crit = [c for r in rows for c in r.cells if c.color == ColorRole.CRITICAL]
    assert crit, "expected at least one CRITICAL-coloured cell for cpu"


def test_header_shows_name_and_frequency():
    p = _payload(cpu_name="Test CPU", cpu_hz_current=2_000_000_000, cpu_hz=3_000_000_000)
    rows = render(p, FIELDS)
    head = _text(rows[0])
    assert "Test CPU" in head
    assert "2.00" in head and "3.00" in head and "GHz" in head


def test_header_absent_when_no_freq():
    rows = render(_payload(), FIELDS)
    # First row is a bar row (CPU), not a frequency header.
    assert "GHz" not in _text(rows[0])


def _percpu_payload(n):
    cores = [{"cpu_number": i, "total": float(i * 7 % 100)} for i in range(n)]
    return _payload(percpu=cores)


def test_percpu_view_shows_per_core_bars():
    rows = render(_percpu_payload(2), FIELDS, view={"percpu": True})
    text = "\n".join(_text(r) for r in rows)
    assert "CPU0" in text and "CPU1" in text
    assert "MEM" in text and "LOAD" in text  # other bars still present


def test_percpu_view_caps_and_adds_star_row():
    rows = render(_percpu_payload(8), FIELDS, view={"percpu": True})
    text = "\n".join(_text(r) for r in rows)
    # Max 4 cores shown + a CPU* mean row (payload carries no freq header).
    assert "CPU*" in text
    assert text.count("CPU") == 5  # 4 cores + CPU*


def test_percpu_star_row_averages_overflow_cores():
    # totals = i*7 for i in 0..7 -> [0,7,14,21,28,35,42,49]; top-4 displayed,
    # overflow = [21,14,7,0] -> mean 10.5 (v4 Bar-path parity).
    rows = render(_percpu_payload(8), FIELDS, view={"percpu": True})
    star = [r for r in rows if "CPU*" in _text(r)]
    assert len(star) == 1
    assert "10.5%" in _text(star[0])


def test_no_percpu_view_shows_single_cpu_bar():
    rows = render(_percpu_payload(8), FIELDS)  # no view → compact
    text = "\n".join(_text(r) for r in rows)
    assert "CPU0" not in text
    assert "CPU " in text  # single aggregate CPU bar


def test_bar_cells_are_glued_for_flush_brackets():
    rows = render(_payload(), FIELDS)
    cpu_row = next(r for r in rows if r.cells and r.cells[0].text.startswith("CPU "))
    # cells = [label, "[", bar, "]"]; the bracket+bar trio must be glue=True so
    # the painter draws them flush (v4 parity, no spurious inner spaces).
    assert len(cpu_row.cells) >= 4
    assert cpu_row.cells[0].glue is False  # label keeps its normal separator
    assert all(c.glue for c in cpu_row.cells[1:])  # [, bar, ] glued


def _painter_width(row):
    """Painter width = total text + one separator before each non-glue cell after the first."""
    return sum(len(c.text) for c in row.cells) + sum(1 for i, c in enumerate(row.cells) if i > 0 and not c.glue)


def test_freq_only_header_uses_frequency_label():
    p = _payload(cpu_name="A Very Long CPU Brand Name X", cpu_hz_current=2_000_000_000, cpu_hz=3_000_000_000)
    rows = render(p, FIELDS, view={"quicklook_freq_only": True})
    head = _text(rows[0])
    assert "A Very Long CPU Brand Name X" not in head
    assert head.startswith("Frequency")
    assert "GHz" in head


def test_bars_justify_to_header_width():
    # With a header present, every bar row width == header row width (justified).
    p = _payload(cpu_name="Chip", cpu_hz_current=2_000_000_000, cpu_hz=3_000_000_000)
    rows = render(p, FIELDS)
    header_w = _painter_width(rows[0])
    bar_ws = [_painter_width(r) for r in rows[1:]]
    assert bar_ws and all(bw == header_w for bw in bar_ws)


def test_freq_only_is_narrower_than_named():
    p = _payload(cpu_name="A Very Long CPU Brand Name X", cpu_hz_current=2_000_000_000, cpu_hz=3_000_000_000)
    named = render(p, FIELDS)
    freq = render(p, FIELDS, view={"quicklook_freq_only": True})

    def block_w(rows):
        return max(_painter_width(r) for r in rows)

    assert block_w(freq) < block_w(named)
