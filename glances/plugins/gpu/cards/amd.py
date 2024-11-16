#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""AMD Extension unit for Glances' GPU plugin.

The class grabs the stats from the /sys/class/drm/ directory.

See: https://wiki.archlinux.org/title/AMDGPU#Manually
"""

# Example
# test-data/plugins/gpu/amd/
# └── sys
#     ├── class
#     │   └── drm
#     │       └── card0
#     │           └── device
#     │               ├── gpu_busy_percent
#     │               ├── hwmon
#     │               │   └── hwmon0
#     │               │       └── temp1_input
#     │               ├── mem_info_vram_total
#     │               ├── mem_info_vram_used
#     │               ├── pp_dpm_mclk
#     │               └── pp_dpm_sclk
#     └── kernel
#         └── debug
#             └── dri
#                 └── 0
#                     └── amdgpu_pm_info

import os
import re
from typing import Optional

DRM_ROOT_FOLDER: str = '/sys/class/drm'
CARD_REGEX: str = r"^card\d$"
DEVICE_FOLDER: str = 'device'
GPU_PROC_PERCENT: str = 'gpu_busy_percent'
GPU_MEM_TOTAL: str = 'mem_info_vram_total'
GPU_MEM_USED: str = 'mem_info_vram_used'
HWMON_REGEXP: str = r"^hwmon\d$"
GPU_TEMPERATURE_REGEXP: str = r"^temp\d_input"


class AmdGPU:
    """GPU card class."""

    def __init__(self, drm_root_folder: str = DRM_ROOT_FOLDER):
        """Init AMD  GPU card class."""
        self.drm_root_folder = drm_root_folder
        self.device_folders = get_device_list(drm_root_folder)

    def exit(self):
        """Close AMD GPU class."""

    def get_device_stats(self):
        """Get AMD GPU stats."""
        stats = []

        for index, device in enumerate(self.device_folders):
            device_stats = {}
            # Dictionary key is the GPU_ID
            device_stats['key'] = 'gpu_id'
            # GPU id (for multiple GPU, start at 0)
            device_stats['gpu_id'] = f'amd{index}'
            # GPU name
            device_stats['name'] = get_device_name(device)
            # Memory consumption in % (not available on all GPU)
            device_stats['mem'] = get_mem(device)
            # Processor consumption in %
            device_stats['proc'] = get_proc(device)
            # Processor temperature in °C
            device_stats['temperature'] = get_temperature(device)
            # Fan speed in %
            device_stats['fan_speed'] = get_fan_speed(device)
            stats.append(device_stats)

        return stats


def get_device_list(drm_root_folder: str) -> list:
    """Return a list of path to the device stats."""
    ret = []
    for root, dirs, _ in os.walk(drm_root_folder):
        for d in dirs:
            if (
                re.match(CARD_REGEX, d)
                and DEVICE_FOLDER in os.listdir(os.path.join(root, d))
                and os.path.isfile(os.path.join(root, d, DEVICE_FOLDER, GPU_PROC_PERCENT))
            ):
                # If the GPU busy file is present then take the card into account
                ret.append(os.path.join(root, d, DEVICE_FOLDER))
    return ret


def get_device_name(device_folder: str) -> str:
    """Return the GPU name."""
    return 'AMD GPU'


def get_mem(device_folder: str) -> Optional[int]:
    """Return the memory consumption in %."""
    mem_info_vram_total = os.path.join(device_folder, GPU_MEM_TOTAL)
    mem_info_vram_used = os.path.join(device_folder, GPU_MEM_USED)
    if os.path.isfile(mem_info_vram_total) and os.path.isfile(mem_info_vram_used):
        with open(mem_info_vram_total) as f:
            mem_info_vram_total = int(f.read())
        with open(mem_info_vram_used) as f:
            mem_info_vram_used = int(f.read())
        if mem_info_vram_total > 0:
            return round(mem_info_vram_used / mem_info_vram_total * 100)
    return None


def get_proc(device_folder: str) -> Optional[int]:
    """Return the processor consumption in %."""
    gpu_busy_percent = os.path.join(device_folder, GPU_PROC_PERCENT)
    if os.path.isfile(gpu_busy_percent):
        with open(gpu_busy_percent) as f:
            return int(f.read())
    return None


def get_temperature(device_folder: str) -> Optional[int]:
    """Return the processor temperature in °C (mean of all HWMON)"""
    temp_input = []
    for root, dirs, _ in os.walk(device_folder):
        for d in dirs:
            if re.match(HWMON_REGEXP, d):
                for _, _, files in os.walk(os.path.join(root, d)):
                    for f in files:
                        if re.match(GPU_TEMPERATURE_REGEXP, f):
                            with open(os.path.join(root, d, f)) as f:
                                temp_input.append(int(f.read()))
    if temp_input:
        return round(sum(temp_input) / len(temp_input) / 1000)
    return None


def get_fan_speed(device_folder: str) -> Optional[int]:
    """Return the fan speed in %."""
    return None
