#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Intel Extension unit for Glances' GPU plugin.

The class grabs the stats from the /sys/class/drm/ directory.

See: https://github.com/nicolargo/glances/issues/994
"""

# Example
# /sys/class/drm/card0
# ├── gt_act_freq_mhz
# ├── gt_boost_freq_mhz
# ├── gt_cur_freq_mhz
# ├── gt_max_freq_mhz
# ├── gt_min_freq_mhz
# ├── gt_RP0_freq_mhz
# ├── gt_RP1_freq_mhz
# ├── gt_RPn_freq_mhz

import functools
import glob
import os
import re

DRM_ROOT_FOLDER: str = '/sys/class/drm'
DEVICE_FOLDER_PATTERN: str = 'card[0-9]'
INTELGPU_IDS_FILE: str = '/usr/share/misc/pci.ids'
PCI_DEVICE_VENDOR: str = 'device/vendor'
PCI_DEVICE_ID: str = 'device/device'
PCI_ACT_FRQ_MHZ: str = 'gt_act_freq_mhz'
PCI_MAX_FRQ_MHZ: str = 'gt_max_freq_mhz'


class IntelGPU:
    """Intel GPU card class."""

    def __init__(self, drm_root_folder: str = DRM_ROOT_FOLDER):
        """Init Intel GPU card class."""
        self.drm_root_folder = drm_root_folder
        self.device_folders = get_device_list(drm_root_folder)

    def exit(self):
        """Close Intel GPU class."""

    def get_device_stats(self):
        """Get Intel GPU stats."""
        stats = []

        for index, device in enumerate(self.device_folders):
            device_stats = {}
            # Dictionary key is the GPU_ID
            device_stats['key'] = 'gpu_id'
            # GPU id (for multiple GPU, start at 0)
            device_stats['gpu_id'] = f'intel{index}'
            # GPU name
            device_stats['name'] = get_device_name(device)
            # Memory consumption in % (not available on all GPU)
            device_stats['mem'] = get_mem(device)
            # Processor consumption in % of frequency
            device_stats['proc'] = get_proc(device)
            # Processor temperature in °C
            device_stats['temperature'] = get_temperature(device)
            # Fan speed in %
            device_stats['fan_speed'] = get_fan_speed(device)
            stats.append(device_stats)

        return stats


def get_device_list(drm_root_folder: str) -> list[str]:
    """Return a list of path to the device stats."""
    ret = []
    for device_folder in glob.glob(DEVICE_FOLDER_PATTERN, root_dir=drm_root_folder):
        if os.path.isfile(os.path.join(drm_root_folder, device_folder, PCI_ACT_FRQ_MHZ)):
            # If the GPU act freq file is present then take the card into account
            ret.append(os.path.join(drm_root_folder, device_folder))
    return ret


def read_file(*path_segments: str) -> str | None:
    """Return content of file."""
    path = os.path.join(*path_segments)
    if os.path.isfile(path):
        with open(path) as f:
            try:
                return f.read().strip()
            except PermissionError:
                # Catch exception (see issue #3125)
                return None
    return None


@functools.cache
def get_device_name(device_folder: str) -> str:
    """Return the GPU name."""
    device_vendor = read_file(device_folder, PCI_DEVICE_VENDOR)
    device_id = read_file(device_folder, PCI_DEVICE_ID)
    intelgpu_ids = read_file(INTELGPU_IDS_FILE)

    if device_vendor and device_id and intelgpu_ids:
        device_vendor = device_vendor.strip()[2:].lower()
        device_id = device_id.strip()[2:].lower()

        pattern = rf'^{device_vendor}[ \t]+.+\n(?:(?![0-9a-f]{{4}}).+\n)*?\t{device_id}[ \t]+(.+)$'
        match = re.search(pattern, intelgpu_ids, re.MULTILINE)
        if match:
            name = match.group(1)
            bracket_match = re.search(r'\[(.+)\]', name)
            return bracket_match.group(1) if bracket_match else name

    return 'Intel GPU'


def get_mem(device_folder: str) -> int | None:
    """Return the memory consumption in %."""
    return None


def get_proc(device_folder: str) -> int | None:
    """Return the processor consumption in %."""
    act_freq = read_file(device_folder, PCI_ACT_FRQ_MHZ)
    max_freq = read_file(device_folder, PCI_MAX_FRQ_MHZ)
    if act_freq and max_freq:
        return round(int(act_freq) / int(max_freq) * 100)
    return None


def get_temperature(device_folder: str) -> int | None:
    """Return the processor temperature in °C (mean of all HWMON)"""
    return None


def get_fan_speed(device_folder: str) -> int | None:
    """Return the fan speed in %."""
    return None
