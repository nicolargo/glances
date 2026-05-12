"""Glances v5 — tests for unit-driven curses formatters."""

from __future__ import annotations

import pytest

from glances.outputs.curses_formatters_v5 import (
    FORMATTERS,
    format_bytes,
    format_bytespers,
    format_number,
    format_percent,
    format_seconds,
    format_string,
    format_value,
)

# ---------------------------------------------------------------- bytes


@pytest.mark.parametrize(
    "value, expected",
    [
        (0, "0B"),
        (1, "1B"),
        (1023, "1023B"),
        (1024, "1.0K"),
        (1_500_000, "1.4M"),
        (1_073_741_824, "1.0G"),
        (1_099_511_627_776, "1.0T"),
    ],
)
def test_format_bytes(value, expected):
    assert format_bytes(value) == expected


# ---------------------------------------------------------------- percent


@pytest.mark.parametrize(
    "value, expected",
    [
        (0, "0.0%"),
        (12.345, "12.3%"),
        (100, "100.0%"),
    ],
)
def test_format_percent(value, expected):
    assert format_percent(value) == expected


# ---------------------------------------------------------------- bytespers


def test_format_bytespers_appends_per_second():
    assert format_bytespers(1024).endswith("/s")
    assert format_bytespers(0) == "0B/s"


# ---------------------------------------------------------------- seconds


@pytest.mark.parametrize(
    "value, expected",
    [
        (0, "0s"),
        (45, "45s"),
        (90, "1m30s"),
        (3661, "1h01m"),
        (90061, "1d01h"),
    ],
)
def test_format_seconds(value, expected):
    assert format_seconds(value) == expected


# ---------------------------------------------------------------- passthrough


def test_format_string_passthrough():
    assert format_string("eth0") == "eth0"
    assert format_string(None) == ""


def test_format_number_integer_when_round():
    assert format_number(42) == "42"
    assert format_number(42.0) == "42"
    assert format_number(3.14) == "3.14"


# ---------------------------------------------------------------- dispatch


def test_format_value_dispatches_on_unit():
    assert format_value(0.5, schema={"unit": "percent"}) == "0.5%"
    assert format_value(1024, schema={"unit": "bytes"}) == "1.0K"
    assert format_value("eth0", schema={"unit": "string"}) == "eth0"


def test_format_value_honours_explicit_format_hint():
    """`format` in the schema overrides the unit-driven default."""
    assert format_value(0.5, schema={"unit": "percent", "format": "%.3f%%"}) == "0.500%"


def test_format_value_falls_back_to_str_for_unknown_unit():
    assert format_value(42, schema={"unit": "unknown_unit"}) == "42"


def test_format_value_handles_missing_value():
    """Absent value renders as empty string, not 'None'."""
    assert format_value(None, schema={"unit": "bytes"}) == ""


def test_formatters_registry_contract():
    """Every formatter in FORMATTERS takes a value and returns a str."""
    for unit, fn in FORMATTERS.items():
        result = fn(0)
        assert isinstance(result, str), f"Formatter for {unit!r} returned {type(result).__name__}"
