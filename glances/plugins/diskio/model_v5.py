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
- ``read_count`` / ``write_count`` are kept exportable for IOPS-style
  consumers but flagged ``internal=True`` so the generic renderer
  skips them.
- ``read_time``/``write_time`` and the derived ``read_latency`` /
  ``write_latency`` of v4 are not ported — deferred to a later phase
  with the ``--diskio-latency`` mode.

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
            # Useful for IOPS-style export downstream but not rendered in
            # the default TUI (which shows byte rates only — v4 parity).
            "internal": True,
        },
        "write_count": {
            "description": "Write operations per second (rate of psutil write_count counter).",
            "unit": "number",
            "rate": True,
            "internal": True,
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
            out.append(
                {
                    "disk_name": disk_name,
                    "read_count": counters.read_count,
                    "write_count": counters.write_count,
                    "read_bytes": counters.read_bytes,
                    "write_bytes": counters.write_bytes,
                }
            )
        return out
