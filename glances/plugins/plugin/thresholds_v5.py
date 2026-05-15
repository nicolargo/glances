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
    pk_value: str | None = None,
    defaults: dict[str, float] | None = None,
    strict: bool = False,
) -> dict[str, float]:
    """Read thresholds from a config section, layered over `defaults`.

    Three key patterns are supported, walked from most specific to least
    specific — the first non-absent key wins for each level:

    1. ``<pk_value>_<field>_<level>``  — per-item, per-field (e.g.
       ``wlan0_bytes_recv_warning``). Requires both ``field`` and
       ``pk_value`` to be provided.
    2. ``<field>_<level>``             — per-field, all items (e.g.
       ``bytes_recv_warning``). Requires ``field``.
    3. ``<level>``                     — applies to any watched field
       (e.g. ``warning``). **Skipped when** ``strict=True``.

    Per-level defaults (from the field schema's ``default_thresholds``)
    are used when none of the three keys are configured. Layering is
    per-key — the user can override only one level and keep the others
    at their declared defaults.

    A negative value in the config is treated as "absent" so users can
    explicitly disable a level by setting ``careful=-1``.

    ``strict=True`` opts a field out of the bare-``<level>`` fallback.
    Used by opt-in alert fields (cf. ``memswap.sin``/``sout``) where
    legacy bare keys in the plugin section — common in user XDG
    glances.conf files inherited from earlier versions — must not
    inadvertently trigger unrelated alerts. The field-prefixed key
    (``<field>_<level>``) and the pk-field-level key for collections
    continue to work normally.
    """
    out: dict[str, float] = dict(defaults) if defaults else {}

    for level in _BOUNDARY_KEYS_DESCENDING:
        keys: tuple[str, ...]
        if field is not None and pk_value is not None:
            if strict:
                keys = (f"{pk_value}_{field}_{level}", f"{field}_{level}")
            else:
                keys = (f"{pk_value}_{field}_{level}", f"{field}_{level}", level)
        elif field is not None:
            if strict:
                keys = (f"{field}_{level}",)
            else:
                keys = (f"{field}_{level}", level)
        else:
            # No field given — strict has no field-prefix to fall back to;
            # the bare key is the only option. Keep the same behaviour.
            keys = (level,)
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
