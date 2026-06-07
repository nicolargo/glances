#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""
Tegra (NVIDIA Jetson) sysfs fallback for Glances' NVIDIA GPU card.

On NVIDIA Jetson (Tegra) platforms the integrated GPU *is* enumerated by NVML
(the ``nvidia-l4t-nvml`` library): ``nvmlDeviceGetName`` returns a name such as
``Orin (nvgpu)``. However the per-metric NVML queries
(``nvmlDeviceGetUtilizationRates``, ``nvmlDeviceGetMemoryInfo``,
``nvmlDeviceGetTemperature``, ``nvmlDeviceGetFanSpeed``) all return
``NVML_ERROR_NOT_SUPPORTED`` because the integrated GPU does not implement the
discrete-GPU telemetry interface. As a result the GPU plugin would only ever
display ``N/A``.

The same metrics are exposed through Tegra sysfs nodes, which this module reads
as a fallback so the GPU plugin shows real numbers on Jetson.

Sources (verified on JetPack 7 / Orin):
- GPU utilization: ``/sys/devices/platform/gpu.0/load`` -- per-mille (0..1000),
  i.e. ``77`` means 7.7 %. Cross-checked against ``tegrastats`` ``GR3D_FREQ``.
- GPU temperature: the ``/sys/class/thermal/thermal_zone*`` whose ``type`` is
  ``gpu-thermal``, ``temp`` node in milli-degrees Celsius. Cross-checked against
  ``tegrastats`` ``gpu@`` reading.

Memory is intentionally not reported: the Tegra GPU shares system RAM (there is
no dedicated VRAM), so it is already accounted for by the Glances MEM plugin and
NVML reports it as not supported.

See:
- https://docs.nvidia.com/jetson/archives/ (Jetson Linux / tegrastats)
"""

# Example test fixture layout:
# tests-data/plugins/gpu/tegra/
# └── sys
#     ├── devices/platform/gpu.0/load
#     └── class/thermal/
#         ├── thermal_zone0/{type,temp}   (cpu-thermal)
#         └── thermal_zone1/{type,temp}   (gpu-thermal)

import glob
import os

GPU_DEVICE_FOLDER: str = '/sys/devices/platform/gpu.0'
THERMAL_ROOT: str = '/sys/class/thermal'
GPU_LOAD_FILE: str = 'load'
GPU_THERMAL_TYPE: str = 'gpu-thermal'
THERMAL_ZONE_PATTERN: str = 'thermal_zone[0-9]*'


def read_file(*path_segments: str) -> str | None:
    """Return content of file or None if not accessible."""
    path = os.path.join(*path_segments)
    if os.path.isfile(path):
        try:
            with open(path) as f:
                return f.read().strip()
        except (PermissionError, OSError):
            # File exists but is not readable (e.g. Snap strict confinement)
            return None
    return None


def is_tegra(name: str | None = None, gpu_device_folder: str = GPU_DEVICE_FOLDER) -> bool:
    """
    Return True if this looks like a Tegra (Jetson) integrated GPU.

    Detection is based on the NVML device name (``nvgpu`` appears in names such
    as ``Orin (nvgpu)``) and falls back to the presence of the Tegra GPU sysfs
    node, so the fallback never triggers on discrete NVIDIA GPUs.
    """
    if name and 'nvgpu' in name.lower():
        return True
    return os.path.isdir(gpu_device_folder)


def get_proc(gpu_device_folder: str = GPU_DEVICE_FOLDER) -> int | None:
    """
    Return the GPU utilization in % from the Tegra ``load`` node.

    The node is expressed in per-mille (0..1000); divide by 10 to get a percent.
    """
    raw = read_file(gpu_device_folder, GPU_LOAD_FILE)
    if raw is None:
        return None
    try:
        permille = int(raw)
    except ValueError:
        return None
    return max(0, min(100, round(permille / 10)))


def get_temperature(thermal_root: str = THERMAL_ROOT) -> int | None:
    """Return the GPU temperature in °C from the ``gpu-thermal`` thermal zone."""
    for type_file in sorted(glob.glob(os.path.join(THERMAL_ZONE_PATTERN, 'type'), root_dir=thermal_root)):
        if read_file(thermal_root, type_file) != GPU_THERMAL_TYPE:
            continue
        raw = read_file(thermal_root, os.path.dirname(type_file), 'temp')
        if raw is None:
            return None
        try:
            return round(int(raw) / 1000)
        except ValueError:
            return None
    return None
