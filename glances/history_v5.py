#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — the stats history store.

Bounded, in-memory time series of the fields a plugin declares with
``history: True`` in its ``fields_description`` (v4 ``items_history_list``).
Design: ``docs/superpowers/specs/2026-09-26-glances-v5-history-store-design.md``.

Layout, per plugin (design §5.3):

- ONE time axis (``timestamps``, wall-clock epoch seconds): every series of a
  plugin is sampled in the same cycle, so the timestamp is stored once.
- One ``deque(maxlen=size)`` per series, ALIGNED with that axis: index ``i``
  of every series belongs to ``timestamps[i]``. A series first seen late is
  left-padded with ``None``; a known series absent from a cycle gets ``None``.
- ``series[field][item]``: ``item`` is the primary-key value (a string) for a
  collection plugin and ``None`` for a scalar one. Nesting instead of a flat
  ``"<item>_<field>"`` key is what v4 got wrong: any separator collides with
  some real item name (``/`` in mount points, ``_`` in interface names).
- A series whose every point is ``None`` has fully aged out and is dropped —
  v4 kept a vanished interface's series until restart.

``record()`` is synchronous and never awaits, so a reader on the same event
loop never sees half a cycle. The lock covers readers on other threads.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import Any

logger = logging.getLogger(__name__)

# The shipped glances.conf value ("~1h with the default refresh rate"), and
# the default v4's own disable check uses (`main.py:892`). v4's code default
# of 28800 is deliberately not carried over (design §5.4).
DEFAULT_HISTORY_SIZE = 1200


def resolve_history_size(config: Any, disable_history: bool = False) -> int:
    """`[global] history_size`, or 0 when history is off.

    0 (from the key or from ``--disable-history``) means "no store at all".
    A negative or non-integer value falls back to the default, with a
    WARNING: a window quietly reverting to its default is hard to notice.
    """
    if disable_history:
        return 0
    # A str default reads the raw value: an int default would make
    # `config.get` coerce, and raise on a typo instead of letting us warn.
    raw = config.get("global", "history_size", "")
    if raw in ("", None):
        return DEFAULT_HISTORY_SIZE
    try:
        size = int(raw)
    except (TypeError, ValueError):
        size = -1
    if size < 0:
        logger.warning(
            "Invalid [global] history_size %r (expected an integer >= 0); using %d",
            raw,
            DEFAULT_HISTORY_SIZE,
        )
        return DEFAULT_HISTORY_SIZE
    return size


def _is_number(value: Any) -> bool:
    # `bool` is an `int` subclass, and is not a measurement.
    return value is None or (isinstance(value, (int, float)) and not isinstance(value, bool))


class _PluginHistory:
    """One plugin's time axis and its aligned series."""

    __slots__ = ("idle", "series", "timestamps")

    def __init__(self, size: int) -> None:
        self.timestamps: deque[float] = deque(maxlen=size)
        self.series: dict[str, dict[str | None, deque[float | None]]] = {}
        # Consecutive cycles without a value, per (field, item).
        self.idle: dict[tuple[str, str | None], int] = {}


class HistoryStoreV5:
    """Ring buffers of every historised field, one time axis per plugin."""

    def __init__(self, size: int = DEFAULT_HISTORY_SIZE) -> None:
        if size <= 0:
            raise ValueError("HistoryStoreV5 needs a positive size; history is disabled by not creating one")
        self.size = size
        self._plugins: dict[str, _PluginHistory] = {}
        self._lock = threading.Lock()

    def record(
        self,
        plugin_name: str,
        stats: dict[str, Any] | list[dict[str, Any]],
        fields: list[str],
        primary_key: str | None = None,
        now: float | None = None,
    ) -> None:
        """Append one cycle of `stats` (a plugin's published, post-transform
        values). `now` is injectable for tests; wall clock otherwise."""
        values = self._extract(plugin_name, stats, fields, primary_key)
        with self._lock:
            hist = self._plugins.get(plugin_name)
            if hist is None:
                hist = self._plugins[plugin_name] = _PluginHistory(self.size)
            hist.timestamps.append(time.time() if now is None else now)
            length = len(hist.timestamps)

            # Known series: append this cycle's value, or None if absent.
            for field, items in hist.series.items():
                for item in list(items):
                    key = (field, item)
                    value = values.pop(key, None)
                    items[item].append(value)
                    idle = 0 if value is not None else hist.idle.get(key, 0) + 1
                    if idle >= self.size:
                        # Every point it holds is None: fully aged out.
                        del items[item]
                        hist.idle.pop(key, None)
                    else:
                        hist.idle[key] = idle
            # New series: left-pad so index i still belongs to timestamps[i].
            for (field, item), value in values.items():
                if value is None:
                    continue
                series = deque([None] * (length - 1), maxlen=self.size)
                series.append(value)
                hist.series.setdefault(field, {})[item] = series
                hist.idle[(field, item)] = 0
            for field in [f for f, items in hist.series.items() if not items]:
                del hist.series[field]

    @staticmethod
    def _extract(
        plugin_name: str,
        stats: dict[str, Any] | list[dict[str, Any]],
        fields: list[str],
        primary_key: str | None,
    ) -> dict[tuple[str, str | None], float | None]:
        """{(field, item): value} for the numbers in `stats`."""
        rows: list[tuple[str | None, dict[str, Any]]]
        if isinstance(stats, list):
            if primary_key is None:
                return {}
            rows = [
                (str(row[primary_key]), row)
                for row in stats
                if isinstance(row, dict) and row.get(primary_key) is not None
            ]
        elif isinstance(stats, dict):
            rows = [(None, stats)]
        else:
            return {}
        out: dict[tuple[str, str | None], float | None] = {}
        for item, row in rows:
            for field in fields:
                if field not in row:
                    continue
                value = row[field]
                if not _is_number(value):
                    logger.debug("history: %s.%s is not a number (%r) — not recorded", plugin_name, field, value)
                    continue
                out[(field, item)] = value
        return out

    def get(self, plugin_name: str, nb: int = 0) -> dict[str, Any]:
        """Columnar copy of one plugin's history, the last `nb` points (0 = all).

        ``{"timestamps": [...], "series": {field: [...]}}`` for a scalar
        plugin, ``{field: {item: [...]}}`` under ``series`` for a collection.
        Empty (not an error) for a plugin that has recorded nothing.
        """
        with self._lock:
            hist = self._plugins.get(plugin_name)
            if hist is None:
                return {"timestamps": [], "series": {}}
            start = len(hist.timestamps) - nb if 0 < nb < len(hist.timestamps) else 0
            series: dict[str, Any] = {}
            for field, items in hist.series.items():
                sliced = {item: list(values)[start:] for item, values in items.items()}
                series[field] = sliced[None] if list(sliced) == [None] else sliced
            return {"timestamps": list(hist.timestamps)[start:], "series": series}
