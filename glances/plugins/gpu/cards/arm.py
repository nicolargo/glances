#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""ARM GPU Extension for Glances' GPU plugin.

Reads DRM devices from /sys/class/drm and per-client stats from
/proc/*/fdinfo via the standardised drm-driver fdinfo format
(requires Linux kernel >= 6.0).

Supported drivers: msm (Adreno), panfrost, panthor, v3d, lima, etnaviv.

See:
- https://www.kernel.org/doc/html/latest/gpu/drm-usage-stats.html
- https://docs.kernel.org/gpu/panfrost.html
"""

# Example test fixture layout:
# tests-data/plugins/gpu/arm/
# ├── sys/class/drm/
# │   └── card0/
# │       └── device/
# │           ├── driver                       (symlink to drivers/<name>)
# │           └── hwmon/hwmon0/temp1_input
# └── proc/
#     └── 1234/fdinfo/7

import functools
import glob
import os
import time

from glances.globals import LINUX
from glances.logger import logger

DRM_ROOT_FOLDER: str = '/sys/class/drm'
PROC_ROOT_FOLDER: str = '/proc'
DEVICE_FOLDER_PATTERN: str = 'card[0-9]'
HWMON_TEMPERATURE_PATTERN: str = 'hwmon/hwmon[0-9]/temp[0-9]_input'

SUPPORTED_DRIVERS: set[str] = {'msm', 'panfrost', 'panthor', 'v3d', 'lima', 'etnaviv'}

DRIVER_NAMES: dict[str, str] = {
    'msm': 'Adreno (msm)',
    'panfrost': 'Mali (Panfrost)',
    'panthor': 'Mali (Panthor)',
    'v3d': 'VideoCore (v3d)',
    'lima': 'Mali (Lima)',
    'etnaviv': 'Vivante (Etnaviv)',
}

MEM_UNITS: dict[str, int] = {
    'KiB': 1024,
    'KB': 1000,
    'MiB': 1024 * 1024,
    'MB': 1000 * 1000,
    'GiB': 1024 * 1024 * 1024,
    'GB': 1000 * 1000 * 1000,
}


class ArmGPU:
    """ARM GPU card class (msm, panfrost, panthor, v3d, lima, etnaviv)."""

    def __init__(
        self,
        drm_root_folder: str = DRM_ROOT_FOLDER,
        proc_root_folder: str = PROC_ROOT_FOLDER,
    ):
        """Init ARM GPU card class."""
        self.drm_root_folder = drm_root_folder
        self.proc_root_folder = proc_root_folder
        self.device_folders: list[tuple[str, str, str | None]] = []
        if LINUX and os.path.isdir(drm_root_folder):
            self.device_folders = get_device_list(drm_root_folder)
        # State for delta-based proc% computation
        self._last_sample: dict[str, tuple[int, int]] = {}

    def exit(self):
        """Close ARM GPU class."""

    def get_device_stats(self) -> list[dict]:
        """Get ARM GPU stats."""
        if not self.device_folders:
            return []

        per_device = aggregate_fdinfo(self.proc_root_folder, self.device_folders)

        stats = []
        for index, (device, driver, _pdev) in enumerate(self.device_folders):
            snapshot = per_device.get(device)
            device_stats = {
                'key': 'gpu_id',
                'gpu_id': f'arm{index}',
                'name': get_device_name(driver),
                'mem': compute_mem_percent(snapshot),
                'proc': self._compute_proc_percent(device, snapshot),
                'temperature': get_temperature(device),
                'fan_speed': None,
            }
            stats.append(device_stats)

        return stats

    def _compute_proc_percent(self, device: str, snapshot: dict | None) -> int | None:
        """Compute the GPU busy % based on delta of cumulative engine ns counters."""
        if snapshot is None:
            return None
        busy_ns = snapshot.get('engine_total_ns', 0)
        now_ns = time.monotonic_ns()
        prev = self._last_sample.get(device)
        self._last_sample[device] = (now_ns, busy_ns)
        if prev is None:
            return None
        delta_t = now_ns - prev[0]
        delta_busy = busy_ns - prev[1]
        if delta_t <= 0 or delta_busy < 0:
            return None
        return max(0, min(100, round(delta_busy / delta_t * 100)))


def read_file(*path_segments: str) -> str | None:
    """Return content of file or None if not accessible."""
    path = os.path.join(*path_segments)
    if os.path.isfile(path):
        try:
            with open(path) as f:
                return f.read().strip()
        except (PermissionError, OSError):
            return None
    return None


def get_device_list(drm_root_folder: str) -> list[tuple[str, str, str | None]]:
    """Return list of (device_folder, driver, pdev) tuples for ARM GPUs."""
    ret = []
    for card in sorted(glob.glob(DEVICE_FOLDER_PATTERN, root_dir=drm_root_folder)):
        card_path = os.path.join(drm_root_folder, card)
        driver_link = os.path.join(card_path, 'device', 'driver')
        if not os.path.islink(driver_link):
            continue
        try:
            driver = os.path.basename(os.readlink(driver_link))
        except OSError:
            continue
        if driver not in SUPPORTED_DRIVERS:
            continue
        pdev = _resolve_pdev(card_path)
        ret.append((card_path, driver, pdev))
    return ret


def _resolve_pdev(card_path: str) -> str | None:
    """Resolve the parent device identifier (pdev) from a DRM card path.

    On real sysfs, ``card0/device`` is a symlink to either a PCI device
    (``/sys/devices/pci0000:00/0000:00:02.0``) or a platform device
    (``/sys/devices/platform/fe9b0000.gpu``). We match the basename to what
    fdinfo reports as ``drm-pdev:``. When it cannot be resolved to a usable
    identifier, return None and fall back to driver-only matching.
    """
    device_link = os.path.join(card_path, 'device')
    try:
        resolved = os.path.realpath(device_link)
    except OSError:
        return None
    pdev = os.path.basename(resolved)
    if pdev in ('device', '', card_path):
        return None
    return pdev


@functools.cache
def get_device_name(driver: str) -> str:
    """Return the friendly GPU name based on driver."""
    return DRIVER_NAMES.get(driver, 'ARM GPU')


def get_temperature(device_folder: str) -> int | None:
    """Return the GPU temperature in °C (mean of all HWMON probes)."""
    temp_input = []
    device_path = os.path.join(device_folder, 'device')
    search_root = device_path if os.path.isdir(device_path) else device_folder
    for temp_file in glob.glob(HWMON_TEMPERATURE_PATTERN, root_dir=search_root):
        value = read_file(search_root, temp_file)
        if value is None:
            return None
        try:
            temp_input.append(int(value))
        except ValueError:
            return None
    if temp_input:
        return round(sum(temp_input) / len(temp_input) / 1000)
    return None


def parse_fdinfo(text: str) -> dict | None:
    """Parse the content of a /proc/*/fdinfo/* file.

    Returns a dict with keys:
        - driver: str
        - pdev:   str | None
        - engine_total_ns: int (sum of all drm-engine-* counters)
        - mem_total_bytes: int
        - mem_used_bytes:  int

    Returns None if the text does not look like a DRM fdinfo entry.
    """
    if not text or 'drm-driver:' not in text:
        return None

    driver: str | None = None
    pdev: str | None = None
    engine_total_ns = 0
    mem_total_bytes = 0
    mem_used_bytes = 0

    for raw_line in text.splitlines():
        if ':' not in raw_line:
            continue
        key, _, value = raw_line.partition(':')
        key = key.strip()
        value = value.strip()
        if not key.startswith('drm-'):
            continue
        if key == 'drm-driver':
            driver = value
        elif key == 'drm-pdev':
            pdev = value
        elif key.startswith('drm-engine-') and key != 'drm-engine-capacity':
            parsed = _parse_scalar(value, expected_unit='ns')
            if parsed is not None:
                engine_total_ns += parsed
        elif key == 'drm-total-memory' or key.startswith('drm-total-memory-'):
            parsed = _parse_memory(value)
            if parsed is not None:
                mem_total_bytes += parsed
        elif key == 'drm-resident-memory' or key.startswith('drm-resident-memory-'):
            parsed = _parse_memory(value)
            if parsed is not None:
                mem_used_bytes += parsed
        elif key.startswith('drm-memory-'):
            parsed = _parse_memory(value)
            if parsed is not None:
                mem_used_bytes += parsed

    if driver is None:
        return None

    return {
        'driver': driver,
        'pdev': pdev,
        'engine_total_ns': engine_total_ns,
        'mem_total_bytes': mem_total_bytes,
        'mem_used_bytes': mem_used_bytes,
    }


def _parse_scalar(value: str, expected_unit: str | None = None) -> int | None:
    """Parse '<number> [unit]' → int. Returns None on parse error."""
    parts = value.split()
    if not parts:
        return None
    try:
        number = int(parts[0])
    except ValueError:
        return None
    if expected_unit is not None and len(parts) >= 2 and parts[1] != expected_unit:
        return None
    return number


def _parse_memory(value: str) -> int | None:
    """Parse '<number> <unit>' → bytes. Default unit: KiB (matches kernel doc)."""
    parts = value.split()
    if not parts:
        return None
    try:
        number = int(parts[0])
    except ValueError:
        return None
    unit = parts[1] if len(parts) >= 2 else 'KiB'
    multiplier = MEM_UNITS.get(unit)
    if multiplier is None:
        return None
    return number * multiplier


def aggregate_fdinfo(
    proc_root: str,
    device_folders: list[tuple[str, str, str | None]],
) -> dict[str, dict]:
    """Scan /proc/*/fdinfo/* and aggregate DRM stats per device folder.

    Matching strategy:
    - If fdinfo has a ``drm-pdev`` and a device matches it, attribute to that
      device.
    - Else, if exactly one device uses that driver, attribute to it.
    - Else, skip the record.
    """
    if not device_folders or not os.path.isdir(proc_root):
        return {}

    pdev_to_device: dict[str, str] = {}
    drivers_count: dict[str, int] = {}
    single_device_per_driver: dict[str, str] = {}
    for device, driver, pdev in device_folders:
        if pdev:
            pdev_to_device[pdev] = device
        drivers_count[driver] = drivers_count.get(driver, 0) + 1
        single_device_per_driver[driver] = device
    for driver, count in drivers_count.items():
        if count > 1:
            single_device_per_driver.pop(driver, None)

    per_device: dict[str, dict] = {}

    try:
        pids = os.listdir(proc_root)
    except OSError as e:
        logger.debug(f'ARM GPU: cannot list {proc_root}: {e}')
        return {}

    for pid in pids:
        if not pid.isdigit():
            continue
        fdinfo_dir = os.path.join(proc_root, pid, 'fdinfo')
        try:
            fds = os.listdir(fdinfo_dir)
        except (FileNotFoundError, PermissionError, NotADirectoryError):
            continue
        except OSError:
            continue
        for fd in fds:
            fd_path = os.path.join(fdinfo_dir, fd)
            try:
                with open(fd_path) as f:
                    text = f.read()
            except (FileNotFoundError, PermissionError, OSError):
                continue
            record = parse_fdinfo(text)
            if record is None:
                continue
            if record['driver'] not in SUPPORTED_DRIVERS:
                continue

            target = None
            if record['pdev'] and record['pdev'] in pdev_to_device:
                target = pdev_to_device[record['pdev']]
            elif record['driver'] in single_device_per_driver:
                target = single_device_per_driver[record['driver']]
            if target is None:
                continue

            bucket = per_device.setdefault(
                target,
                {'engine_total_ns': 0, 'mem_total_bytes': 0, 'mem_used_bytes': 0},
            )
            bucket['engine_total_ns'] += record['engine_total_ns']
            bucket['mem_total_bytes'] += record['mem_total_bytes']
            bucket['mem_used_bytes'] += record['mem_used_bytes']

    return per_device


def compute_mem_percent(snapshot: dict | None) -> int | None:
    """Return memory usage in % from a per-device fdinfo snapshot."""
    if snapshot is None:
        return None
    total = snapshot.get('mem_total_bytes', 0)
    used = snapshot.get('mem_used_bytes', 0)
    if total <= 0:
        return None
    return max(0, min(100, round(used / total * 100)))
