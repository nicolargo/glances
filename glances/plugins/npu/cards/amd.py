#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""AMD Extension unit for Glances' NPU plugin.

/sys/bus/pci/drivers/amdxdna/
└── 0000:c4:00.1/
    ├── vendor                 # "0x1022" (AMD)
    ├── device                 # Ex: "0x1714" (Strix Point)
    ├── accel/
    │   └── accel0/
    │       └── dev
    └── ...

/sys/class/devfreq/
└── *xdna*/                   # or *npu* or /sys/devices/platform/*.npu/devfreq/*
    ├── cur_freq              # Ex: "800000000" (800 MHz in Hz)
    ├── max_freq              # Ex: "1500000000" (1.5 GHz in Hz)
    ├── min_freq              # Ex: "400000000" (400 MHz in Hz)
    └── available_frequencies

Current limitation:
- Only one AMD NPU is supported
- Load, Memory, temperature and power stats are not yet implemented
"""

import glob
import os

from glances.logger import logger
from glances.plugins.npu.cards.npu import NPUStats


class AmdNPU:
    """NPU card class."""

    def __init__(self, npu_root_folder: str = '/'):
        """Init AMD NPU card class."""
        self.npu_root_folder = npu_root_folder

        device_paths = glob.glob(os.path.join(self.npu_root_folder, 'sys/bus/pci/drivers/amdxdna/*/accel/accel*'))
        self.device_folder = device_paths[0] if device_paths else None

        self.freq_folder = self._find_devfreq_path()

        logger.debug(f"AMD NPU device folder: {self.device_folder}")
        logger.debug(f"AMD NPU freq folder: {self.freq_folder}")

    def is_available(self) -> bool:
        """Check if AMD NPU is available."""
        return self.device_folder is not None and self.freq_folder is not None

    def disable(self):
        """Disable AMD GPU class."""
        self.device_folder = None
        self.freq_folder = None

    def exit(self):
        """Close AMD GPU class."""
        pass

    def get_device_stats(self) -> dict | None:
        """Get AMD GPU stats."""
        if not self.is_available():
            return None

        stats = NPUStats()

        stats.npu_id = 'amd_1'
        stats.freq_current = self._read_file(os.path.join(self.freq_folder, 'cur_freq'), as_int=True)
        stats.freq_max = self._read_file(os.path.join(self.freq_folder, 'max_freq'), as_int=True)
        stats.freq = int(stats.freq_current / stats.freq_max * 100)
        stats.name = self._get_device_name(self._read_file(os.path.join(self.device_folder, '../../device')))

        # Return stats as a dictionary
        return stats.__dict__

    def _find_devfreq_path(self) -> str | None:
        """Find AMD NPU devfreq path"""
        # AMD NPU typically at specific address
        patterns = [
            os.path.join(self.npu_root_folder, 'sys/class/devfreq/*npu*'),
            os.path.join(self.npu_root_folder, 'sys/class/devfreq/*xdna*'),
            os.path.join(self.npu_root_folder, 'sys/devices/platform/*.npu/devfreq/*'),
        ]

        for pattern in patterns:
            paths = glob.glob(pattern)
            if paths:
                return paths[0]
        return None

    def _read_file(self, path: str, as_int: bool = False) -> int | None:
        """Safely read integer from file"""
        try:
            if os.path.exists(path):
                with open(path) as f:
                    if as_int:
                        return int(f.read().strip())
                    return f.read().strip()
        except (OSError, ValueError) as e:
            logger.error(f"NPU - Error reading file {path}: {e}")
        return None

    def _get_device_name(self, device_id: str) -> str:
        """Map AMD device ID to product name"""
        device_map = {
            '0x1502': 'AMD NPU (Phoenix)',
            '0x17f0': 'AMD NPU (Hawk Point)',
            '0x1714': 'AMD NPU (Strix Point)',
        }
        return device_map.get(device_id, 'AMD NPU')


# End of file
