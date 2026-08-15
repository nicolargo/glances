#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Rockchip MPP (Media Process Platform) extension for Glances' MPP plugin.

Reads hardware encoder/decoder/jpeg engine stats from:

/proc/mpp_service/
├── load                # Per-engine load & utilization (requires load_interval)
├── load_interval       # Polling interval in ms (must be set > 0 first)
├── sessions-summary    # Active sessions with PID, device, memory, codec info
├── supports-device     # Available HW devices (RKVDEC, RKVENC, RKJPEGD)
├── rkvdec0/            # Decoder node
├── rkvenc0/            # Encoder node
│   └── sessions-info   # Per-session codec detail table
└── jpegd/              # JPEG decoder node

Tested on: Rockchip RV1126B-P
"""

import os
import re

from glances.logger import logger
from glances.plugins.mpp.cards.mpp import MPPStats

# Map device-tree address prefixes to engine types
_ENGINE_TYPES = {
    'rkvenc': 'enc',
    'rkvdec': 'dec',
    'jpegd': 'jpeg',
}

# Desired load_interval in milliseconds
_LOAD_INTERVAL_MS = 1000


class RockchipMPP:
    """Rockchip MPP card class."""

    def __init__(self, mpp_root_folder: str = '/'):
        """Init Rockchip MPP card class."""
        self.mpp_root_folder = mpp_root_folder
        self.proc_path = os.path.join(self.mpp_root_folder, 'proc', 'mpp_service')
        self._available = os.path.isdir(self.proc_path)
        self._load_interval_set = False

        logger.debug(f"Rockchip MPP proc path: {self.proc_path} (available: {self._available})")

    def is_available(self) -> bool:
        """Check if Rockchip MPP service is available."""
        return self._available

    def disable(self):
        """Disable Rockchip MPP class."""
        self._available = False

    def exit(self):
        """Close Rockchip MPP class."""

    def _ensure_load_interval(self):
        """Set load_interval if not already set, so /proc/mpp_service/load returns data."""
        if self._load_interval_set:
            return
        interval_path = os.path.join(self.proc_path, 'load_interval')
        try:
            with open(interval_path) as f:
                current = int(f.read().strip())
            if current == 0:
                with open(interval_path, 'w') as f:
                    f.write(str(_LOAD_INTERVAL_MS))
                logger.debug(f"Rockchip MPP: set load_interval to {_LOAD_INTERVAL_MS}ms")
            self._load_interval_set = True
        except (OSError, ValueError) as e:
            logger.debug(f"Rockchip MPP: could not set load_interval: {e}")

    def _read_file(self, path: str) -> str | None:
        """Safely read a file and return its content stripped."""
        try:
            if os.path.exists(path):
                with open(path) as f:
                    return f.read().strip('\x00').strip()
        except (OSError, PermissionError) as e:
            logger.debug(f"MPP - Error reading {path}: {e}")
        return None

    def get_stats(self) -> list[dict]:
        """Get stats for all MPP engines.

        Returns a list of dicts (one per engine).
        """
        if not self._available:
            return []

        self._ensure_load_interval()

        # Parse per-engine load
        engines = self._parse_load()

        # Count active sessions per engine
        self._count_sessions(engines)

        return [e.__dict__ for e in engines.values()]

    def _parse_load(self) -> dict[str, MPPStats]:
        """Parse /proc/mpp_service/load.

        Example content:
            21f40000.rkvenc           load:  24.80% utilization:  24.39%
            22140100.rkvdec           load:  28.23% utilization:  13.38%
            22170000.jpegd            load:   0.00% utilization:   0.00%

        Returns a dict keyed by engine device name (e.g. 'rkvenc', 'rkvdec', 'jpegd').
        """
        engines: dict[str, MPPStats] = {}
        content = self._read_file(os.path.join(self.proc_path, 'load'))
        if not content:
            return engines

        pattern = r'(\S+)\.(\w+)\s+load:\s*([\d.]+)%\s+utilization:\s*([\d.]+)%'
        for match in re.finditer(pattern, content):
            _, dev_name, load_str, util_str = match.groups()

            stats = MPPStats()
            stats.engine_id = f'rockchip_{dev_name}'
            stats.name = dev_name.upper()
            stats.type = _ENGINE_TYPES.get(dev_name, dev_name)
            stats.load = float(load_str)
            stats.utilization = float(util_str)

            engines[dev_name] = stats

        return engines

    def _count_sessions(self, engines: dict[str, MPPStats]):
        """Count active sessions per engine from sessions-summary.

        Example relevant lines:
            session: pid=388 index=69
             device: 22140100.rkvdec
        """
        content = self._read_file(os.path.join(self.proc_path, 'sessions-summary'))
        if not content:
            return

        # Count "device: <addr>.<name>" lines
        pattern = r'device:\s*\S+\.(\w+)'
        for match in re.finditer(pattern, content):
            dev_name = match.group(1)
            if dev_name in engines:
                engines[dev_name].sessions += 1
