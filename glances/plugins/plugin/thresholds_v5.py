#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 threshold engine — pure functional `_levels` computation.

Two evaluation modes, both consumed by ``GlancesPluginBase``:

- **Numeric** (default): ``compute_level(value, thresholds, direction)``
  compares ``value`` against numeric ``careful`` / ``warning`` /
  ``critical`` thresholds. Used by every quantitative field (cpu %,
  mem %, byte rates, etc.).
- **Categorical**: ``compute_level_categorical(value, mapping)`` matches
  a discrete value against per-level value-sets. Used for fields whose
  alert semantics are membership-based (e.g. process ``status``: ``Z``
  / ``D`` are critical, ``R`` / ``W`` are ok). Driven by config keys
  like ``status_critical=Z,D``.

`GlancesAlerts` (Phase 1.4) reads ``_levels`` from the store but **never
recomputes thresholds** — this module is the single source of truth for
level computation.

See architecture decisions §3.3.
"""

from __future__ import annotations

from typing import Any, Literal

Level = Literal["ok", "careful", "warning", "critical"]
Direction = Literal["high", "low"]

LEVELS: tuple[Level, ...] = ("ok", "careful", "warning", "critical")

# Walked from most severe to least severe so the first match wins.
_BOUNDARY_KEYS_DESCENDING: tuple[Level, ...] = ("critical", "warning", "careful")
# For categorical thresholds, ``ok`` is a configurable bucket too — a
# value explicitly listed in ``<field>_ok=`` is matched as ok even when
# higher-severity buckets exist. The walk order still goes most-severe
# first so that membership in a higher bucket wins on conflict.
_CATEGORICAL_KEYS_DESCENDING: tuple[Level, ...] = ("critical", "warning", "careful", "ok")

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


# --------------------------------------------------------------- categorical


def _parse_csv_tokens(raw: Any) -> list[str]:
    """Split a config value (``"R,W,P,I"`` or ``"-1, -2, -3"``) into tokens.

    Whitespace is stripped per-token. Empty tokens are dropped. Returns
    an empty list if ``raw`` is missing or not a string.
    """
    if raw is None:
        return []
    if isinstance(raw, (list, tuple, set)):
        return [str(t).strip() for t in raw if str(t).strip()]
    text = str(raw).strip()
    if not text:
        return []
    return [t.strip() for t in text.split(",") if t.strip()]


def compute_level_categorical(
    value: Any,
    mapping: dict[str, set[str]],
) -> Level | None:
    """Return the alert level whose value-set contains ``value``, or
    ``None`` when ``value`` belongs to **no** configured bucket.

    Args:
        value: A discrete value (string letter, integer-as-string, etc.).
        mapping: ``{"critical": {...}, "warning": {...}, ...}`` — per-level
            value-sets. Levels with no entry (absent or empty set) match
            no value.

    Behaviour:
        - The walk order is **most-severe-first** so a value that appears
          in two buckets (a user misconfiguration) escalates to the
          higher one rather than being silently downgraded.
        - A value not in any configured set returns ``None``. Callers
          (typically ``base_v5._compute_levels_for_item``) interpret
          this as "no level entry" — the cell stays default-coloured in
          the TUI and the alert pipeline sees no event for that field.
          This matches v4 ``get_alert`` which returns ``'DEFAULT'`` for
          unmatched categorical values rather than ``'OK'``.
    """
    if value is None:
        return None
    token = str(value).strip()
    for level in _CATEGORICAL_KEYS_DESCENDING:
        bucket = mapping.get(level)
        if bucket and token in bucket:
            return level
    return None


def read_thresholds_categorical(
    config: Any,
    section: str,
    field: str | None = None,
    pk_value: str | None = None,
) -> dict[str, set[str]]:
    """Read ``<field>_<level>=<csv>`` keys into per-level value-sets.

    Three key patterns mirror ``read_thresholds`` (most-specific wins):

    1. ``<pk_value>_<field>_<level>``
    2. ``<field>_<level>``
    3. ``<level>`` (bare, only when ``field`` is None — categorical
       fields cannot inherit a bare ``<level>`` key because the value
       sets are field-specific by nature).

    Empty / missing keys produce an empty set for that level. Levels
    that resolve to an empty set are dropped from the returned mapping
    so ``compute_level_categorical`` can short-circuit cheaply.
    """
    out: dict[str, set[str]] = {}
    for level in _CATEGORICAL_KEYS_DESCENDING:
        keys: tuple[str, ...]
        if field is not None and pk_value is not None:
            keys = (f"{pk_value}_{field}_{level}", f"{field}_{level}")
        elif field is not None:
            keys = (f"{field}_{level}",)
        else:
            keys = (level,)
        bucket: set[str] = set()
        for key in keys:
            # Empty-string default so ``config.get`` infers str coercion;
            # ``config.get(default=None)`` raises because NoneType has no
            # registered coercion path (cf. GlancesConfigV5._coerce).
            raw = config.get(section, key, "")
            tokens = _parse_csv_tokens(raw)
            if tokens:
                bucket.update(tokens)
                break
        if bucket:
            out[level] = bucket
    return out
