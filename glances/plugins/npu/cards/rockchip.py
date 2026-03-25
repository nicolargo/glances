#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""ROCKCHIP Extension unit for Glances' NPU plugin.

WARNING: access to /sys/kernel/debug/ requires root privileges or specific permissions.
/sys/kernel/debug/rknpu/
├── load            # Load per core
├── version         # Driver version
└── mm              # SRAM

/sys/class/devfreq/
└── fdab0000.npu/
    ├── cur_freq    # Ex: "1000000000" (1 GHz in Hz)
    ├── max_freq    # Ex: "1000000000"
    └── min_freq    # Ex: "300000000"

/proc/device-tree/
└── model           # Ex: "Orange Pi 5 Plus"

Current limitation:
- Only one ROCKCHIP NPU is supported
- Load, Memory, temperature and power stats are not yet implemented
"""

import glob
import os
import re

from glances.logger import logger
from glances.plugins.npu.cards.npu import NPUStats


class RockchipNPU:
    """NPU card class."""

    def __init__(self, npu_root_folder: str = '/'):
        """Init ROCKCHIP NPU card class."""
        self.npu_root_folder = npu_root_folder

        debug_paths = glob.glob(os.path.join(self.npu_root_folder, 'sys/kernel/debug/rknpu'))
        self.debug_folder = debug_paths[0] if debug_paths else None

        device_paths = glob.glob(os.path.join(self.npu_root_folder, 'proc/device-tree/'))
        self.device_folder = device_paths[0] if device_paths else None

        freq_paths = glob.glob(os.path.join(self.npu_root_folder, 'sys/class/devfreq/*npu*'))
        self.freq_folder = freq_paths[0] if freq_paths else None

        logger.debug(f"ROCKCHIP NPU debug folder: {self.debug_folder}")
        logger.debug(f"ROCKCHIP NPU device folder: {self.device_folder}")
        logger.debug(f"ROCKCHIP NPU freq folder: {self.freq_folder}")

    def is_available(self) -> bool:
        """Check if ROCKCHIP NPU is available."""
        return self.debug_folder is not None and self.device_folder is not None and self.freq_folder is not None

    def disable(self):
        """Disable ROCKCHIP GPU class."""
        self.debug_folder = None
        self.device_folder = None
        self.freq_folder = None

    def exit(self):
        """Close ROCKCHIP GPU class."""
        pass

    def get_device_stats(self) -> dict | None:
        """Get ROCKCHIP GPU stats."""
        if not self.is_available():
            return None

        stats = NPUStats()

        stats.npu_id = 'rockship_1'
        stats.name = self._get_npu_name()
        stats.freq_current = self._read_file(os.path.join(self.freq_folder, 'cur_freq'), as_int=True)
        stats.freq_max = self._read_file(os.path.join(self.freq_folder, 'max_freq'), as_int=True)
        stats.freq = int(stats.freq_current / stats.freq_max * 100)
        stats.load = self.parse_rknpu_load(self._read_file(os.path.join(self.debug_folder, 'load')))

        # Return stats as a dictionary
        return stats.__dict__

    def _read_file(self, path: str, as_int: bool = False) -> int | None:
        """Safely read integer from file"""
        try:
            if os.path.exists(path):
                with open(path) as f:
                    if as_int:
                        return int(f.read().strip())
                    return f.read().strip('\x00').strip()
        except (OSError, ValueError) as e:
            logger.error(f"NPU - Error reading file {path}: {e}")
        except (PermissionError, FileNotFoundError) as e:
            logger.debug(f"NPU - Permission error reading file {path}: {e}")
        return None

    def _get_device_name(self, device_id: str) -> str:
        """Map ROCKCHIP device ID to product name"""
        return device_id

    def _get_npu_name(self) -> str:
        """Get NPU name from the device-tree compatible string.

        Reads the NPU's own compatible property (e.g. 'rockchip,rv1126b-rknpu')
        and formats it as a human-readable name (e.g. 'Rockchip RV1126B RKNPU').
        Falls back to the board model or a generic name.
        """
        # Try the NPU's own device-tree compatible string first
        compatible_path = os.path.join(self.freq_folder, 'device', 'of_node', 'compatible')
        compatible = self._read_file(compatible_path)
        if compatible:
            # e.g. "rockchip,rv1126b-rknpu" -> "Rockchip RV1126B RKNPU"
            parts = compatible.split(',', 1)
            if len(parts) == 2:
                vendor = parts[0].capitalize()
                # "rv1126b-rknpu" -> "RV1126B RKNPU"
                device = parts[1].replace('-', ' ').upper()
                return f"{vendor} {device}"

        # Fall back to board model
        model = self._read_file(os.path.join(self.device_folder, 'model'))
        return model if model else "Rockchip NPU"

    def parse_rknpu_load(self, content: str) -> int | None:
        """
        Parse the content of the rknpu load file.
        Return average load across all cores.
        0% means idle, 100% means full load.

        Supports two formats:
        - Multi-core (e.g. RK3588): "NPU load: Core0: 45%, Core1: 32%, Core2: 0%,"
        - Single-core (e.g. RV1126B): "NPU load:  0%"
        """
        if not content:
            return None

        # Multi-core format: "Core0: 45%, Core1: 32%, Core2: 0%,"
        load = []
        pattern = r'Core(\d+):\s*(\d+)%'
        matches = re.findall(pattern, content)
        for _, utilization in matches:
            load.append(int(utilization))

        if load:
            return int(sum(load) / len(load))

        # Single-core format: "NPU load:  0%"
        single_match = re.search(r'NPU load:\s*(\d+)%', content)
        if single_match:
            return int(single_match.group(1))

        return None


# End of file
