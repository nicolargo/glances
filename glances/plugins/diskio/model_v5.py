#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — disk I/O plugin (collection, per-device).

Migrated from `glances/plugins/diskio/__init__.py`. Collection plugin
keyed on ``disk_name``. Read/write byte counters are converted to
bytes/sec rates by the base class (``rate: True``).

V5 scope (G4-diskio):
- ``read_bytes`` / ``write_bytes`` are opt-in alerts: ``watched=True``
  but **no default thresholds** — sustained disk traffic is host-
  specific, alerts only fire when the user sets per-disk or per-field
  keys in ``[diskio]`` (e.g. ``read_bytes_warning=50_000_000``).
- ``read_count`` / ``write_count`` are flagged ``internal=True`` so the
  generic renderer skips them; the ``B`` hotkey's IOPS mode renders them
  explicitly, and exporters have always had them.
- ``read_time`` / ``write_time`` (cumulative ms, turned into ms/s by the
  base class) are ``internal``; the derived ``read_latency`` /
  ``write_latency`` (mean ms per operation, v4 ``update_latency``) are
  what the ``L`` hotkey / ``--diskio-latency`` mode renders. Both latencies
  are opt-in alerts under v4's own keys (``[diskio] rx_latency_*`` /
  ``tx_latency_*``, per disk ``<disk>_rx_latency_*``) via ``threshold_field``.

SNMP support is **not ported to v5** (architecture §10).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

import psutil

from glances.plugins.plugin.base_v5 import GlancesPluginBase

logger = logging.getLogger(__name__)


class PluginModel(GlancesPluginBase[list]):
    """Per-disk I/O plugin (collection)."""

    plugin_name: ClassVar[str] = "diskio"
    IS_COLLECTION: ClassVar[bool] = True

    # `hide_zero` display filter (design §5.1) — v4 `diskio/__init__.py:98`
    # (`read_bytes_rate_per_sec` / `write_bytes_rate_per_sec` there; v5 keeps
    # the base field names since `rate: True` replaces the value in place).
    HIDE_ZERO_FIELDS: ClassVar[list[str]] = ["read_bytes", "write_bytes"]

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "disk_name": {
            "description": "Disk name (e.g. sda, nvme0n1).",
            "unit": "string",
            "primary_key": True,
        },
        "read_count": {
            "description": "Read operations per second (rate of psutil read_count counter).",
            "unit": "number",
            "rate": True,
            # `internal` keeps it out of the GENERIC renderer's default
            # columns (which show byte rates — v4 parity); the `B` hotkey's
            # IOPS mode renders it explicitly, and exporters have always had
            # it. `short_name` is v4's header for that mode
            # (`diskio/__init__.py:242`).
            "internal": True,
            "short_name": "IOR/s",
        },
        "write_count": {
            "description": "Write operations per second (rate of psutil write_count counter).",
            "unit": "number",
            "rate": True,
            # See `read_count` above.
            "internal": True,
            "short_name": "IOW/s",
        },
        "read_time": {
            "description": "Time spent reading, in milliseconds per second (rate of psutil read_time counter).",
            "unit": "number",
            "rate": True,
            # Only the input of `read_latency` below; exporters keep it.
            "internal": True,
        },
        "write_time": {
            "description": "Time spent writing, in milliseconds per second (rate of psutil write_time counter).",
            "unit": "number",
            "rate": True,
            "internal": True,
        },
        "read_latency": {
            "description": "Mean time spent reading per operation, in milliseconds.",
            "unit": "number",
            # Not a column of the default mode: the `L` hotkey renders it.
            "internal": True,
            # v4's header for that mode (`diskio/__init__.py:247`).
            "short_name": "ms/opR",
            # Opt-in, like the byte rates: no default thresholds (v4 has none
            # either), and v4's key names kept -- `rx_latency_careful`,
            # `dm-0_rx_latency_warning` -- through `threshold_field`, so the
            # shipped glances.conf examples work as written.
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "strict_thresholds": True,
            "threshold_field": "rx_latency",
        },
        "write_latency": {
            "description": "Mean time spent writing per operation, in milliseconds.",
            "unit": "number",
            "internal": True,
            "short_name": "ms/opW",
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "strict_thresholds": True,
            "threshold_field": "tx_latency",
        },
        "read_bytes": {
            "description": "Bytes read per second (rate of psutil read_bytes counter).",
            # Column label, TUI header and WebUI alike (field_label, prefer_short).
            "short_name": "R/s",
            "unit": "bytespers",
            "rate": True,
            # Opt-in alerts. No default thresholds — disk traffic is
            # host-specific (a database server may stream MB/s by design).
            # ``strict_thresholds=True`` opts the field out of the
            # bare-``<level>`` fallback in ``read_thresholds`` so a legacy
            # ``[diskio] careful=50`` in a user XDG glances.conf cannot
            # silently trigger spurious alerts (cf. memswap.sin/sout).
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "strict_thresholds": True,
        },
        "write_bytes": {
            "description": "Bytes written per second (rate of psutil write_bytes counter).",
            "short_name": "W/s",
            "unit": "bytespers",
            "rate": True,
            "watched": True,
            "watch_direction": "high",
            "prominent": False,
            "strict_thresholds": True,
        },
    }

    def _expand_parameters(self) -> None:
        """Derive the per-operation latencies from this cycle's rates.

        v4 ``update_latency``: ``int(time_rate / count_rate)`` ms, 0 when no
        operation happened. Runs after ``_transform_gauge`` (the rates exist)
        and before ``_derived_parameters`` (the levels see the latency).
        ``None`` while a rate is not known yet -- cycle 1, a new disk, or a
        platform whose psutil has no ``read_time``.
        """
        super()._expand_parameters()
        if not isinstance(self._stats, list):
            return
        for item in self._stats:
            if not isinstance(item, dict):
                continue
            for latency, time_key, count_key in (
                ("read_latency", "read_time", "read_count"),
                ("write_latency", "write_time", "write_count"),
            ):
                spent, ops = item.get(time_key), item.get(count_key)
                if spent is None or ops is None:
                    item[latency] = None
                else:
                    item[latency] = int(spent / ops) if ops > 0 else 0

    async def _grab_stats(self) -> list:
        try:
            iomap = await asyncio.to_thread(psutil.disk_io_counters, perdisk=True)
        except (OSError, RuntimeError) as exc:
            logger.debug("diskio: psutil.disk_io_counters() failed: %s", exc)
            return []
        if not iomap:
            return []

        out: list[dict[str, Any]] = []
        for disk_name, counters in iomap.items():
            entry: dict[str, Any] = {
                "disk_name": disk_name,
                "read_count": counters.read_count,
                "write_count": counters.write_count,
                "read_bytes": counters.read_bytes,
                "write_bytes": counters.write_bytes,
            }
            # Not every platform's psutil reports the time counters.
            for name in ("read_time", "write_time"):
                if hasattr(counters, name):
                    entry[name] = getattr(counters, name)
            out.append(entry)
        return out
