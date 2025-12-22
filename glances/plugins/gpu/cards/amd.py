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
# tests-data/plugins/gpu/amd/
# └── sys
#     ├── class
#     │   └── drm
#     │       └── card0
#     │           └── device
#     │               ├── device
#     │               ├── gpu_busy_percent
#     │               ├── hwmon
#     │               │   └── hwmon0
#     │               │       ├── in1_input
#     │               │       └── temp1_input
#     │               ├── mem_info_gtt_total
#     │               ├── mem_info_gtt_used
#     │               ├── mem_info_vram_total
#     │               ├── mem_info_vram_used
#     │               ├── pp_dpm_mclk
#     │               ├── pp_dpm_sclk
#     │               └── revision
#     └── kernel
#         └── debug
#             └── dri
#                 └── 0
#                     └── amdgpu_pm_info

import functools
import glob
import os
import re

DRM_ROOT_FOLDER: str = '/sys/class/drm'
DEVICE_FOLDER_PATTERN: str = 'card[0-9]/device'
AMDGPU_IDS_FILE: str = '/usr/share/libdrm/amdgpu.ids'
PCI_DEVICE_ID: str = 'device'
PCI_REVISION_ID: str = 'revision'
GPU_PROC_PERCENT: str = 'gpu_busy_percent'
GPU_MEM_TOTAL: str = 'mem_info_vram_total'
GPU_MEM_USED: str = 'mem_info_vram_used'
GTT_MEM_TOTAL: str = 'mem_info_gtt_total'
GTT_MEM_USED: str = 'mem_info_gtt_used'
HWMON_NORTHBRIDGE_VOLTAGE_PATTERN: str = 'hwmon/hwmon[0-9]/in1_input'
HWMON_TEMPERATURE_PATTERN = 'hwmon/hwmon[0-9]/temp[0-9]_input'


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


def get_device_list(drm_root_folder: str) -> list[str]:
    """Return a list of path to the device stats."""
    ret = []
    for device_folder in glob.glob(DEVICE_FOLDER_PATTERN, root_dir=drm_root_folder):
        if os.path.isfile(os.path.join(drm_root_folder, device_folder, GPU_PROC_PERCENT)):
            # If the GPU busy file is present then take the card into account
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

    # Table source: https://cgit.freedesktop.org/drm/libdrm/tree/data/amdgpu.ids
    device_id = read_file(device_folder, PCI_DEVICE_ID)
    revision_id = read_file(device_folder, PCI_REVISION_ID)
    amdgpu_ids = read_file(AMDGPU_IDS_FILE)
    if device_id and revision_id and amdgpu_ids:
        # Strip leading "0x" and convert to uppercase hexadecimal
        device_id = device_id[2:].upper()
        revision_id = revision_id[2:].upper()
        # Syntax:
        # device_id,	revision_id,	product_name        <-- single tab after comma
        pattern = re.compile(f'^{device_id},\\s{revision_id},\\s(?P<product_name>.+)$', re.MULTILINE)
        if match := pattern.search(amdgpu_ids):
            return match.group('product_name').removeprefix('AMD ').removesuffix(' Graphics')

    return 'AMD GPU'


def get_mem(device_folder: str) -> int | None:
    """Return the memory consumption in %."""
    mem_info_total = read_file(device_folder, GPU_MEM_TOTAL)
    mem_info_used = read_file(device_folder, GPU_MEM_USED)
    if mem_info_total and mem_info_used:
        mem_info_total = int(mem_info_total)
        mem_info_used = int(mem_info_used)
        # Detect integrated GPU by looking for APU-only Northbridge voltage.
        # See https://docs.kernel.org/gpu/amdgpu/thermal.html
        if glob.glob(HWMON_NORTHBRIDGE_VOLTAGE_PATTERN, root_dir=device_folder):
            mem_info_gtt_total = read_file(device_folder, GTT_MEM_TOTAL)
            mem_info_gtt_used = read_file(device_folder, GTT_MEM_USED)
            if mem_info_gtt_total and mem_info_gtt_used:
                # Integrated GPU allocates static VRAM and dynamic GTT from the same system memory.
                mem_info_total += int(mem_info_gtt_total)
                mem_info_used += int(mem_info_gtt_used)
        if mem_info_total > 0:
            return round(mem_info_used / mem_info_total * 100)
    return None


def get_proc(device_folder: str) -> int | None:
    """Return the processor consumption in %."""
    if gpu_busy_percent := read_file(device_folder, GPU_PROC_PERCENT):
        return int(gpu_busy_percent)
    return None


def get_temperature(device_folder: str) -> int | None:
    """Return the processor temperature in °C (mean of all HWMON)"""
    temp_input = []
    for temp_file in glob.glob(HWMON_TEMPERATURE_PATTERN, root_dir=device_folder):
        if a_temp_input := read_file(device_folder, temp_file):
            temp_input.append(int(a_temp_input))
        else:
            return None
    if temp_input:
        return round(sum(temp_input) / len(temp_input) / 1000)
    return None


def get_fan_speed(device_folder: str) -> int | None:
    """Return the fan speed in %."""
    return None
