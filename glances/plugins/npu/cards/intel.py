#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Intel Extension unit for Glances' NPU plugin.

/sys/class/accel/
└── accel0/
    ├── device -> ../../../0000:00:0b.0/
    │   ├── vendor                    # "0x8086" (Intel)
    │   ├── device                    # Ex: "0x7d1d" (Meteor Lake)
    │   ├── npu_current_frequency_mhz # Ex: "1400"
    │   ├── npu_max_frequency_mhz    # Ex: "1400"
    │   └── hwmon/
    │       └── hwmon2/
    │           ├── temp1_input       # Ex: "45000" (45°C in milli-Celsius)
    │           └── power1_input      # Ex: "2500000" (2.5W in micro-Watts)
    └── dev                           # "261:0"

Current limitation:
- Only one Intel NPU is supported
- Load and Memory stats are not yet implemented
"""

import glob
import os

from glances.logger import logger
from glances.plugins.npu.cards.npu import NPUStats


class IntelNPU:
    """NPU card class."""

    def __init__(self, npu_root_folder: str = '/'):
        """Init Intel NPU card class."""
        self.npu_root_folder = npu_root_folder

        device_paths = glob.glob(os.path.join(self.npu_root_folder, 'sys/class/accel/accel*/device'))
        self.device_folder = device_paths[0] if device_paths else None

        logger.debug(f"Intel NPU device folder: {self.device_folder}")

    def is_available(self) -> bool:
        """Check if Intel NPU is available."""
        return self.device_folder is not None

    def disable(self):
        """Disable Intel GPU class."""
        self.device_folder = None

    def exit(self):
        """Close Intel GPU class."""
        pass

    def get_device_stats(self) -> dict | None:
        """Get Intel GPU stats."""
        if not self.is_available():
            return None

        stats = NPUStats()

        stats.npu_id = 'intel_1'
        stats.freq_current = (
            self._read_file(os.path.join(self.device_folder, 'npu_current_frequency_mhz'), as_int=True) * 1000000
        )  # Convert MHz to Hz
        stats.freq_max = (
            self._read_file(os.path.join(self.device_folder, 'npu_max_frequency_mhz'), as_int=True) * 1000000
        )  # Convert MHz to Hz
        stats.freq = int(stats.freq_current / stats.freq_max * 100)
        stats.name = self._get_device_name(self._read_file(os.path.join(self.device_folder, 'device')))

        # Temperature
        temp_files = glob.glob(os.path.join(self.device_folder, 'hwmon/hwmon*/temp*_input'))
        if temp_files:
            temp_value = self._read_file(temp_files[0], as_int=True)
            if temp_value:
                stats.temperature = temp_value / 1000.0  # Convert milli-Celsius to Celsius

        # Power
        power_files = glob.glob(os.path.join(self.device_folder, 'hwmon/hwmon*/power*_input'))
        if power_files:
            power_value = self._read_file(power_files[0], as_int=True)
            if power_value:
                stats.power = power_value / 1000000.0  # Convert micro-Watts to Watts

        # Return stats as a dictionary
        return stats.__dict__

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
        """Map Intel device ID to product name"""
        device_map = {
            '0x7d1d': 'Intel NPU (Meteor Lake)',
            '0xa75d': 'Intel NPU (Lunar Lake)',
            '0x643e': 'Intel NPU (Arrow Lake)',
        }
        return device_map.get(device_id, 'Intel NPU')


# End of file
