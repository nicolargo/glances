#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit-driven formatters for the curses TUI renderer.

Every formatter takes a single raw value and returns a printable string.
The mapping `unit → formatter` is the contract between
`fields_description` and the renderer. A field whose `unit` is not in
`FORMATTERS` falls back to `str(value)`.

An optional `format` key in `fields_description` (§3.2 renderer hint)
overrides the unit-driven default with an explicit Python format string.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

# ----------------------------------------------------------------- atoms


def _auto_unit(value: float, suffix: str = "") -> str:
    """K/M/G/T scaling à la `glances.tools.bytes2human` but minimal.

    Matches v4 visual output: one decimal for ≥ K, integer for < K.
    """
    abs_v = abs(value)
    for symbol, threshold in (
        ("T", 1_099_511_627_776),
        ("G", 1_073_741_824),
        ("M", 1_048_576),
        ("K", 1024),
    ):
        if abs_v >= threshold:
            return f"{value / threshold:.1f}{symbol}{suffix}"
    return f"{int(value)}B{suffix}"


def format_bytes(value: Any) -> str:
    try:
        return _auto_unit(float(value))
    except (TypeError, ValueError):
        return ""


def format_bytespers(value: Any) -> str:
    try:
        return _auto_unit(float(value), suffix="/s")
    except (TypeError, ValueError):
        return ""


def format_percent(value: Any) -> str:
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return ""


def format_seconds(value: Any) -> str:
    try:
        secs = int(float(value))
    except (TypeError, ValueError):
        return ""
    if secs < 60:
        return f"{secs}s"
    minutes, secs = divmod(secs, 60)
    if minutes < 60:
        return f"{minutes}m{secs:02d}s"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h{minutes:02d}m"
    days, hours = divmod(hours, 24)
    return f"{days}d{hours:02d}h"


def format_number(value: Any) -> str:
    if value is None:
        return ""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return str(value)
    if f.is_integer():
        return str(int(f))
    return f"{f:.2f}".rstrip("0").rstrip(".")


def format_string(value: Any) -> str:
    return "" if value is None else str(value)


def format_bool(value: Any) -> str:
    if value is None:
        return ""
    return "yes" if bool(value) else "no"


# ----------------------------------------------------------------- registry


FORMATTERS: dict[str, Callable[[Any], str]] = {
    "bytes": format_bytes,
    "bytespers": format_bytespers,
    "percent": format_percent,
    "seconds": format_seconds,
    "number": format_number,
    "string": format_string,
    "bool": format_bool,
}


# ----------------------------------------------------------------- dispatch


def format_value(value: Any, schema: dict[str, Any]) -> str:
    """Format `value` using the explicit `format` hint or the unit-default.

    Precedence:
        1. `schema["format"]` (an explicit Python format string)
        2. `FORMATTERS[schema["unit"]]`
        3. `str(value)`
    """
    if value is None:
        return ""
    explicit = schema.get("format")
    if explicit:
        try:
            return explicit % value
        except (TypeError, ValueError):
            return str(value)
    unit = schema.get("unit", "")
    formatter = FORMATTERS.get(unit)
    if formatter is not None:
        return formatter(value)
    return str(value)
