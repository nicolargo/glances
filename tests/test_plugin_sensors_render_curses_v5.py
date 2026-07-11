#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — tests for the sensors curses renderer."""

from __future__ import annotations

from glances.plugins.sensors.render_curses_v5 import render


def _payload(rows, levels=None):
    return {"data": rows, "_levels": levels or {}}


def _flat(rows):
    return "\n".join(" ".join(c.text for c in r.cells) for r in rows)


def _sensor(label, value, unit="C", type="temperature_core", status=None):
    row = {"label": label, "value": value, "unit": unit, "type": type}
    if status is not None:
        row["status"] = status
    return row


def test_empty_returns_header_only():
    rows = render(_payload([]))
    assert "SENSORS" in _flat(rows)
    assert len(rows) == 1  # header only


def test_header_and_one_row():
    rows = render(_payload([_sensor("Core 0", 42)]))
    flat = _flat(rows)
    assert "SENSORS" in flat
    assert "Core 0" in flat
    assert "42" in flat


def test_long_label_truncated():
    rows = render(_payload([_sensor("A" * 40, 42)]))
    # No cell text exceeds the name column width (20) + value column (14).
    for r in rows:
        for c in r.cells:
            assert len(c.text) <= 20


def test_string_sentinel_rendered():
    rows = render(_payload([_sensor("sdc", "ERR", type="temperature_hdd")]))
    assert "ERR" in _flat(rows)


def test_fahrenheit_converts_temperature_only(view=None):
    rows = render(
        _payload([_sensor("Core 0", 100)]),
        None,
        view={"fahrenheit": True},
    )
    flat = _flat(rows)
    assert "212" in flat  # 100C -> 212F
    assert "F" in flat


def test_fahrenheit_skips_fan():
    rows = render(
        _payload([_sensor("fan1", 1200, unit="R", type="fan_speed")]),
        None,
        view={"fahrenheit": True},
    )
    flat = _flat(rows)
    assert "1200" in flat  # unchanged, not converted
    assert "2192" not in flat  # would be 1200*1.8+32 if wrongly converted


def test_battery_trend_arrow():
    rows = render(_payload([_sensor("Battery", 80, unit="%", type="battery", status="Discharging")]))
    flat = _flat(rows)
    # ARROW_DOWN unicode or its ascii fallback 'v'
    assert "↓" in flat or "v" in flat


def test_empty_battery_skipped():
    rows = render(_payload([_sensor("Battery", [], unit="%", type="battery")]))
    flat = _flat(rows)
    assert "Battery" not in flat  # empty-value battery row omitted


def test_level_colour_applied():
    levels = {"Core 0": {"value": {"level": "critical", "prominent": True}}}
    rows = render(_payload([_sensor("Core 0", 95)], levels))
    # find the value cell and assert it is coloured critical + prominent
    value_cells = [c for r in rows for c in r.cells if "95" in c.text]
    assert value_cells and value_cells[0].color.value == "critical"
    assert value_cells[0].prominent is True  # prominent flag propagated


def test_none_value_row_skipped():
    """A non-battery row with a None (non-numeric, non-sentinel) value is
    dropped rather than crashing or rendering an empty value."""
    rows = render(_payload([_sensor("Core 0", None)]))
    assert "Core 0" not in _flat(rows)


def test_fahrenheit_skips_battery():
    rows = render(
        _payload([_sensor("Battery", 80, unit="%", type="battery", status="Charging")]),
        None,
        view={"fahrenheit": True},
    )
    flat = _flat(rows)
    assert "80" in flat  # battery % unchanged
    assert "F" not in flat  # not converted to Fahrenheit
