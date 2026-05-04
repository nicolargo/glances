#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 threshold engine — pure functional `_levels` computation.

`f(value, thresholds, direction) -> "ok" | "careful" | "warning" | "critical"`

Consumed by `GlancesPluginBase._derived_parameters()` to populate the
`_levels` dict written to the StatsStore. `GlancesAlerts` (Phase 1.4)
reads `_levels` from the store but **never recomputes thresholds** —
this module is the single source of truth for level computation.

See architecture decisions §3.3.
"""

from __future__ import annotations

from typing import Any, Literal

Level = Literal["ok", "careful", "warning", "critical"]
Direction = Literal["high", "low"]

LEVELS: tuple[Level, ...] = ("ok", "careful", "warning", "critical")

# Walked from most severe to least severe so the first match wins.
_BOUNDARY_KEYS_DESCENDING: tuple[Level, ...] = ("critical", "warning", "careful")

_ABSENT = -1.0


def compute_level(
    value: float | int | None,
    thresholds: dict[str, float],
    direction: Direction = "high",
) -> Level:
    """Return the alert level for `value` against the configured thresholds.

    Args:
        value: The metric value. None is treated as "ok" (cannot evaluate).
        thresholds: Mapping with keys among "careful" / "warning" / "critical".
            Missing keys are treated as no threshold for that level.
        direction:
            "high" — alert when `value >= threshold` (e.g. mem percent used).
            "low"  — alert when `value <= threshold` (e.g. fs free percent).

    Returns:
        One of "ok" / "careful" / "warning" / "critical".
    """
    if value is None:
        return "ok"

    for level in _BOUNDARY_KEYS_DESCENDING:
        threshold = thresholds.get(level)
        if threshold is None:
            continue
        if direction == "high" and value >= threshold:
            return level
        if direction == "low" and value <= threshold:
            return level
    return "ok"


def read_thresholds(
    config: Any,
    section: str,
    field: str | None = None,
    defaults: dict[str, float] | None = None,
) -> dict[str, float]:
    """Read thresholds from a config section, layered over `defaults`.

    Two key patterns are supported:

    - `[section] careful=N, warning=N, critical=N` — single-watched-field plugin.
    - `[section] <field>_careful=N, <field>_warning=N, ...` — multi-field plugin.

    When `field` is provided, field-prefixed keys are tried first, with
    fallback to bare keys. When `field` is None, only bare keys are read.

    Per-level defaults (from the field schema's `default_thresholds`) are
    used when neither the field-prefixed nor the bare key is configured.
    Layering is per-key — the user can override only one level and keep
    the others at their defaults.

    A negative value in the config is treated as "absent" so users can
    explicitly disable a level by setting `careful=-1`.
    """
    out: dict[str, float] = dict(defaults) if defaults else {}

    for level in _BOUNDARY_KEYS_DESCENDING:
        keys = (f"{field}_{level}", level) if field is not None else (level,)
        for key in keys:
            value = config.get(section, key, _ABSENT)
            if value is None:
                continue
            try:
                fvalue = float(value)
            except (TypeError, ValueError):
                continue
            if fvalue >= 0:
                out[level] = fvalue
                break

    return out
