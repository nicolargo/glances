#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — File system plugin (collection, per-mountpoint).

Migrated from `glances/plugins/fs/__init__.py`. Collection plugin keyed
on ``mnt_point``.

V4-aligned watched fields:
- ``percent`` — prominent True, default thresholds 50/70/90 (same ladder
  as ``mem``).

Filesystems whose mountpoint matches the configured ``hide=`` / ``show=``
regex patterns are filtered out by the base class
(``GlancesPluginBase._filter_collection``).

SNMP support is **not ported to v5** (architecture §10).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar

import psutil

from glances.plugins.plugin.base_v5 import GlancesPluginBase

logger = logging.getLogger(__name__)

# Filesystems are usually fine until close to full — the ladder here is
# looser than mem's 50/70/90 to avoid noisy "careful" warnings on disks
# that routinely sit at 60-70% on healthy hosts.
_DEFAULT_PERCENT_THRESHOLDS = {"careful": 70.0, "warning": 80.0, "critical": 90.0}


class PluginModel(GlancesPluginBase[list]):
    """Per-filesystem plugin (collection)."""

    plugin_name: ClassVar[str] = "fs"
    IS_COLLECTION: ClassVar[bool] = True
    # `[fs] show=/dev/sdb.*` filters on the device too (v4, docs/aoa/fs.rst).
    FILTER_EXTRA_FIELDS: ClassVar[tuple[str, ...]] = ("device_name",)
    # Filesystem usage changes slowly, but not THAT slowly: a build filling a
    # disk must not sit on stale data for a minute. `statvfs` is cheap
    # (~0.003% of a core at this cadence), so 30s is the right trade.
    DEFAULT_REFRESH_TIME: ClassVar[float | None] = 30.0

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "mnt_point": {
            "description": "Mount point.",
            "unit": "string",
            "primary_key": True,
        },
        "device_name": {
            "description": "Device name backing the filesystem (e.g. /dev/sda1).",
            "unit": "string",
        },
        "fs_type": {
            "description": "File system type (e.g. ext4, xfs, btrfs).",
            "unit": "string",
            # Kept in export payloads (useful for downstream consumers),
            # but not surfaced in the TUI by the generic renderer.
            "internal": True,
        },
        "options": {
            "description": "Mount options string (comma-separated).",
            "unit": "string",
            "internal": True,
        },
        "size": {
            "description": "Total size of the filesystem in bytes.",
            # Column labels, TUI header and WebUI alike (field_label, prefer_short).
            "short_name": "Total",
            "unit": "bytes",
        },
        "used": {
            "description": "Used size in bytes.",
            "short_name": "Used",
            "unit": "bytes",
        },
        "free": {
            "description": "Free size in bytes.",
            "short_name": "Free",
            "unit": "bytes",
        },
        "percent": {
            "description": "Filesystem usage as a percentage of total size.",
            "unit": "percent",
            "watched": True,
            "watch_direction": "high",
            # Explicit False — colour the Used value but do not reverse-video
            # the cell. The framework defaults missing ``prominent`` to True.
            "prominent": False,
            "default_thresholds": _DEFAULT_PERCENT_THRESHOLDS,
        },
    }

    def __init__(self, store: Any, config: Any) -> None:
        super().__init__(store, config)
        # `[fs] allow`: extra filesystem types (logical mounts) included on
        # top of the built-in list (design §5.3, v4 `fs/__init__.py:160-170`,
        # issue #448). Absent by default — behaviour is unchanged.
        self.allow: list[str] = self.config.get(self.plugin_name, "allow", [])
        # `[fs] free_space`: switches the TUI block from used to free space
        # (design §5.4, v4 `main.py:644` CLI / `main.py:832` config
        # fallback). The CLI flag is merged into this config key by
        # `main_v5.assemble()` before plugin construction. Published as
        # metadata (see `_add_metadata`) — the renderer has no other way to
        # reach the config.
        self.free_space: bool = self.config.get(self.plugin_name, "free_space", False)

    def _add_metadata(self) -> None:
        super()._add_metadata()
        self._metadata["free_space"] = self.free_space

    async def _grab_stats(self) -> list:
        # Snap-heavy hosts routinely expose 70+ mountpoints (one per
        # installed snap revision). Calling
        # ``await asyncio.to_thread(psutil.disk_usage, mnt)`` per partition
        # produces N+1 thread-pool submissions + epoll wakes per cycle,
        # which dominates idle-CPU on machines with many snaps installed.
        # Coalesce the whole walk inside a single worker thread so the
        # asyncio loop sees exactly one wake per fs cycle.
        try:
            return await asyncio.to_thread(self._collect_sync, self.allow)
        except (PermissionError, OSError) as exc:
            logger.debug("fs: collection failed: %s", exc)
            return []

    @staticmethod
    def _collect_sync(allow: list[str]) -> list[dict[str, Any]]:
        """Synchronous collector — runs in a single worker thread."""
        try:
            partitions = psutil.disk_partitions(all=False)
        except (PermissionError, OSError) as exc:
            logger.debug("fs: psutil.disk_partitions() failed: %s", exc)
            return []

        if allow:
            # Avoid the extra psutil call unless mounts need to be allowed
            # (v4 `fs/__init__.py:162-163`).
            try:
                all_mounted = psutil.disk_partitions(all=True)
            except (PermissionError, OSError) as exc:
                logger.debug("fs: psutil.disk_partitions(all=True) failed: %s", exc)
                all_mounted = []
            # Discard duplicates (issue #2299): only add mountpoints not
            # already tracked, matching any allowed fs type by substring
            # (v4 parity: ``fstype.find(fs_type) >= 0``).
            tracked_mnt_points = {p.mountpoint for p in partitions}
            for part in all_mounted:
                if part.mountpoint in tracked_mnt_points:
                    continue
                if any(fs_type in part.fstype for fs_type in allow):
                    partitions.append(part)

        out: list[dict[str, Any]] = []
        for part in partitions:
            try:
                usage = psutil.disk_usage(part.mountpoint)
            except (OSError, PermissionError) as exc:
                # Disk ejected, broken NFS mount, transient FS error — drop
                # this partition from the cycle without aborting the whole
                # update.
                logger.debug("fs: disk_usage(%s) failed: %s", part.mountpoint, exc)
                continue
            # v4 issue #1065: non-breaking space in mountpoint can break
            # serialisation downstream — normalise to a plain space.
            mnt = str(part.mountpoint).replace(" ", " ")
            out.append(
                {
                    "mnt_point": mnt,
                    "device_name": part.device,
                    "fs_type": part.fstype,
                    "options": part.opts,
                    "size": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent,
                }
            )
        return out
