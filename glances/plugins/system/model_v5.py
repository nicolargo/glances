#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — system plugin (scalar host/OS metadata).

Migrated from `glances/plugins/system/__init__.py`. Local-only: SNMP is
dropped in v5 (architecture §10). The ``[system] system_info_msg`` config
key overrides the human-readable name, exactly like v4.
"""

from __future__ import annotations

import asyncio
import logging
import os
import platform
import re
from typing import Any, ClassVar

from glances.config_v5 import GlancesConfigV5
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.stats_store_v5 import StatsStoreV5

logger = logging.getLogger(__name__)


def _linux_os_release() -> str:
    """Read a human distro name from /etc/os-release (NAME + VERSION_ID)."""
    pretty_name = ""
    ashtray: dict[str, str] = {}
    keys = ["NAME", "VERSION_ID"]
    try:
        with open(os.path.join("/etc", "os-release")) as f:
            for line in f:
                for key in keys:
                    if line.startswith(key):
                        ashtray[key] = re.sub(r'^"|"$', "", line.strip().split("=")[1])
    except OSError:
        return pretty_name
    if "NAME" in ashtray:
        pretty_name = ashtray["NAME"]
    if "VERSION_ID" in ashtray:
        pretty_name += f" {ashtray['VERSION_ID']}"
    return pretty_name


def _linux_distro() -> str:
    """Best-effort Linux distribution string (platform.linux_distribution was
    removed in Python 3.8 — fall back to /etc/os-release)."""
    legacy = getattr(platform, "linux_distribution", None)
    if callable(legacy):
        try:
            parts = legacy()
            if parts and parts[0]:
                return " ".join(parts[:2])
        except Exception:
            pass
    return _linux_os_release()


class PluginModel(GlancesPluginBase[dict]):
    """Host / operating-system metadata plugin (scalar)."""

    plugin_name: ClassVar[str] = "system"
    IS_COLLECTION: ClassVar[bool] = False

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "os_name": {"description": "Operating system name.", "unit": "string"},
        "hostname": {"description": "Hostname.", "unit": "string"},
        "platform": {"description": "Platform (32 or 64 bits).", "unit": "string"},
        "linux_distro": {"description": "Linux distribution.", "unit": "string"},
        "os_version": {"description": "Operating system version.", "unit": "string"},
        "hr_name": {"description": "Human readable operating system name.", "unit": "string"},
    }

    def __init__(self, store: StatsStoreV5, config: GlancesConfigV5) -> None:
        super().__init__(store, config)
        # Optional operator override for the human-readable name (v4 parity).
        self._info_msg = self.config.get("system", "system_info_msg", "")

    async def _grab_stats(self) -> dict:
        return await asyncio.to_thread(self._collect)

    def _collect(self) -> dict[str, Any]:
        stats: dict[str, Any] = {
            "os_name": platform.system(),
            "hostname": platform.node(),
            "platform": platform.architecture()[0],
            "linux_distro": "",
            "os_version": "",
        }
        os_name = stats["os_name"]
        if os_name == "Linux":
            stats["linux_distro"] = _linux_distro()
            stats["os_version"] = platform.release()
        elif os_name.endswith("BSD") or os_name == "SunOS":
            stats["os_version"] = platform.release()
        elif os_name == "Darwin":
            stats["os_version"] = platform.mac_ver()[0]
        elif os_name == "Windows":
            win = platform.win32_ver()
            stats["os_version"] = " ".join(win[::2])
        stats["hr_name"] = self._human_name(stats)
        return stats

    def _human_name(self, stats: dict[str, Any]) -> str:
        if self._info_msg:
            try:
                return self._info_msg.format(**stats)
            except (KeyError, IndexError) as e:
                logger.debug("system: invalid system_info_msg (%s)", e)
        if stats["os_name"] == "Linux":
            return "{linux_distro} {platform} / {os_name} {os_version}".format(**stats)
        return "{os_name} {os_version} {platform}".format(**stats)
