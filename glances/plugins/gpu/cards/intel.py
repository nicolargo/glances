#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Intel Extension unit for Glances' GPU plugin.

Processor load is computed from the per-client engine time counters
exposed by the i915/xe drivers in /proc/*/fdinfo (``drm-engine-*``,
cumulative nanoseconds). The value is the delta of the summed counters
over the refresh interval, i.e. real engine busy time -- not the
frequency ratio. When no fdinfo data is available (no GPU client, first
call after startup, or /proc not readable), the legacy frequency ratio
(``gt_act_freq_mhz / gt_max_freq_mhz``) is used as a fallback.

Memory, temperature and fan speed are not exposed for Intel GPUs.

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
import time

from glances.globals import LINUX
from glances.logger import logger

# Memory denominator/% helpers shared with the ARM backend: on integrated
# GPUs there is no dedicated VRAM, buffers live in system RAM, so the only
# honest denominator is CmaTotal/MemTotal (never drm-total-memory, see #3611).
from glances.plugins.gpu.cards.arm import compute_mem_percent, get_mem_capacity_bytes

DRM_ROOT_FOLDER: str = '/sys/class/drm'
PROC_ROOT_FOLDER: str = '/proc'
DEVICE_FOLDER_PATTERN: str = 'card[0-9]'
INTELGPU_IDS_FILE: str = '/usr/share/misc/pci.ids'
PCI_DEVICE_VENDOR: str = 'device/vendor'
PCI_DEVICE_ID: str = 'device/device'
PCI_ACT_FRQ_MHZ: str = 'gt_act_freq_mhz'
PCI_MAX_FRQ_MHZ: str = 'gt_max_freq_mhz'

# DRM drivers exposing the standardised drm-engine-* fdinfo counters.
SUPPORTED_DRIVERS: set[str] = {'i915', 'xe'}

MEM_UNITS: dict[str, int] = {
    'KiB': 1024,
    'KB': 1000,
    'MiB': 1024 * 1024,
    'MB': 1000 * 1000,
    'GiB': 1024 * 1024 * 1024,
    'GB': 1000 * 1000 * 1000,
}


class IntelGPU:
    """Intel GPU card class."""

    def __init__(
        self,
        drm_root_folder: str = DRM_ROOT_FOLDER,
        proc_root_folder: str = PROC_ROOT_FOLDER,
    ):
        """Init Intel GPU card class."""
        self.drm_root_folder = drm_root_folder
        self.proc_root_folder = proc_root_folder
        self.device_folders: list[tuple[str, str | None, str | None]] = []
        if LINUX and os.path.isdir(drm_root_folder):
            self.device_folders = get_device_list(drm_root_folder)
        # State for delta-based proc% computation
        self._last_sample: dict[str, tuple[int, int]] = {}
        # Denominator for GPU mem% -- static system property, read once.
        # Integrated GPUs allocate buffers from system RAM (see #3611).
        self._mem_capacity_bytes = get_mem_capacity_bytes(os.path.join(proc_root_folder, 'meminfo'))

    def exit(self):
        """Close Intel GPU class."""

    def get_device_stats(self):
        """Get Intel GPU stats."""
        if not self.device_folders:
            return []

        per_device = aggregate_fdinfo(self.proc_root_folder, self.device_folders)

        stats = []

        for index, (device, _driver, _pdev) in enumerate(self.device_folders):
            snapshot = per_device.get(device)
            device_stats = {}
            # Dictionary key is the GPU_ID
            device_stats['key'] = 'gpu_id'
            # GPU id (for multiple GPU, start at 0)
            device_stats['gpu_id'] = f'intel{index}'
            # GPU name
            device_stats['name'] = get_device_name(device)
            # Memory consumption in %: GPU-resident buffers (shared system
            # RAM on integrated GPUs) over CmaTotal/MemTotal. None when no
            # client holds GPU buffers.
            device_stats['mem'] = compute_mem_percent(snapshot, self._mem_capacity_bytes)
            # Processor consumption in %: real engine busy time,
            # frequency ratio as fallback (see module docstring)
            device_stats['proc'] = self._compute_proc_percent(device, snapshot)
            if device_stats['proc'] is None:
                device_stats['proc'] = get_proc(device)
            # Processor temperature in °C
            device_stats['temperature'] = get_temperature(device)
            # Fan speed in %
            device_stats['fan_speed'] = get_fan_speed(device)
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
        # Engines can run in parallel, so the summed busy time can exceed
        # the elapsed wall-clock time -- clamp to 100, as in the ARM backend.
        return max(0, min(100, round(delta_busy / delta_t * 100)))


def get_device_list(drm_root_folder: str) -> list[tuple[str, str | None, str | None]]:
    """Return list of (device_folder, driver, pdev) tuples for Intel GPUs."""
    ret = []
    for card in sorted(glob.glob(DEVICE_FOLDER_PATTERN, root_dir=drm_root_folder)):
        card_path = os.path.join(drm_root_folder, card)
        driver = _resolve_driver(card_path)
        if driver is not None and driver not in SUPPORTED_DRIVERS:
            # Another vendor's card (nvidia, amdgpu...) -- not ours.
            continue
        if driver is None and not os.path.isfile(os.path.join(card_path, PCI_ACT_FRQ_MHZ)):
            # Legacy layout without a driver link: only take the card into
            # account if the GPU frequency file is present.
            continue
        ret.append((card_path, driver, _resolve_pdev(card_path)))
    return ret


def _resolve_driver(card_path: str) -> str | None:
    """Return the DRM driver name (e.g. 'i915') or None if not resolvable."""
    driver_link = os.path.join(card_path, 'device', 'driver')
    if not os.path.islink(driver_link):
        return None
    try:
        return os.path.basename(os.readlink(driver_link))
    except OSError:
        return None


def _resolve_pdev(card_path: str) -> str | None:
    """Resolve the parent device identifier (pdev) from a DRM card path.

    On real sysfs, ``card0/device`` is a symlink to the PCI device
    (``/sys/devices/pci0000:00/0000:00:02.0``). We match the basename to
    what fdinfo reports as ``drm-pdev:``. When it cannot be resolved to a
    usable identifier, return None and fall back to driver-only matching.
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


def read_file(*path_segments: str) -> str | None:
    """Return content of file or None if not accessible."""
    path = os.path.join(*path_segments)
    if os.path.isfile(path):
        try:
            with open(path) as f:
                return f.read().strip()
        except (PermissionError, OSError):
            # File exists but is not readable (e.g. Snap strict confinement)
            # Graceful degradation: caller will use a default value instead
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


def get_proc(device_folder: str) -> int | None:
    """Return the processor consumption in % (frequency ratio, fallback)."""
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


def parse_fdinfo(text: str) -> dict | None:
    """Parse the content of a /proc/*/fdinfo/* file.

    Returns a dict with keys:
        - driver: str
        - pdev:   str | None
        - engine_total_ns: int (sum of all drm-engine-* time counters,
          excluding drm-engine-capacity-* which is a count, not a time)
        - mem_total_bytes: int (sum of all drm-total-* region counters)
        - mem_used_bytes:  int (sum of all drm-resident-* region counters)

    Only totals and resident memory are counted: shared/active/purgeable
    are subsets and would double-count.

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
        elif key.startswith('drm-engine-') and not key.startswith('drm-engine-capacity'):
            parts = value.split()
            if not parts:
                continue
            try:
                number = int(parts[0])
            except ValueError:
                continue
            if len(parts) >= 2 and parts[1] != 'ns':
                continue
            engine_total_ns += number
        elif key.startswith('drm-total-'):
            parsed = _parse_memory(value)
            if parsed is not None:
                mem_total_bytes += parsed
        elif key.startswith('drm-resident-'):
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
    device_folders: list[tuple[str, str | None, str | None]],
) -> dict[str, dict]:
    """Scan /proc/*/fdinfo/* and aggregate engine time per device folder.

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
        if driver is None:
            continue
        drivers_count[driver] = drivers_count.get(driver, 0) + 1
        single_device_per_driver[driver] = device
    for driver, count in drivers_count.items():
        if count > 1:
            single_device_per_driver.pop(driver, None)

    per_device: dict[str, dict] = {}

    for _pid, record in _iter_fdinfo_records(proc_root):
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
            target, {'engine_total_ns': 0, 'mem_total_bytes': 0, 'mem_used_bytes': 0}
        )
        bucket['engine_total_ns'] += record['engine_total_ns']
        bucket['mem_total_bytes'] += record['mem_total_bytes']
        bucket['mem_used_bytes'] += record['mem_used_bytes']

    return per_device


def _iter_fdinfo_records(proc_root: str):
    """Yield (pid, record) for every DRM fdinfo entry below proc_root.

    Only records of supported Intel drivers are returned; anything else
    (non-DRM fds, other vendors, unreadable files) is skipped silently.
    """
    try:
        pids = os.listdir(proc_root)
    except OSError as e:
        logger.debug(f'Intel GPU: cannot list {proc_root}: {e}')
        return

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
            if record is None or record['driver'] not in SUPPORTED_DRIVERS:
                continue
            yield int(pid), record


# Previous per-PID sample for delta-based percent computation:
# {pid: (monotonic_ns, engine_total_ns)}
_pid_last_sample: dict[int, tuple[int, int]] = {}


def intel_gpu_present(drm_root_folder: str = DRM_ROOT_FOLDER) -> bool:
    """Return True if at least one Intel GPU card is detected.

    Evaluated on every call (cheap sysfs glob) so a GPU bound away for
    passthrough -- where /sys/class/drm/card* disappears -- hides the
    per-process column instead of showing stale zeros.
    """
    if not LINUX or not os.path.isdir(drm_root_folder):
        return False
    return bool(get_device_list(drm_root_folder))


def get_per_pid_gpu_percent(proc_root: str = PROC_ROOT_FOLDER) -> dict[int, int]:
    """Return {pid: GPU busy %} for Intel GPU clients.

    Computed from the delta of the summed drm-engine-* fdinfo counters
    over the time since the previous call -- the same source nvtop uses.
    PIDs without measurable activity (first sighting, idle, counter reset
    after PID reuse) report 0. Stale PIDs are pruned on every call.
    """
    now_ns = time.monotonic_ns()
    per_pid_ns: dict[int, int] = {}
    for pid, record in _iter_fdinfo_records(proc_root):
        per_pid_ns[pid] = per_pid_ns.get(pid, 0) + record['engine_total_ns']

    result: dict[int, int] = {}
    for pid, busy_ns in per_pid_ns.items():
        prev = _pid_last_sample.get(pid)
        _pid_last_sample[pid] = (now_ns, busy_ns)
        if prev is None:
            continue
        delta_t = now_ns - prev[0]
        delta_busy = busy_ns - prev[1]
        if delta_t <= 0 or delta_busy < 0:
            continue
        # Engines can run in parallel -- clamp to 100.
        result[pid] = max(0, min(100, round(delta_busy / delta_t * 100)))

    # Prune PIDs that no longer hold GPU file descriptors.
    for pid in [pid for pid in _pid_last_sample if pid not in per_pid_ns]:
        _pid_last_sample.pop(pid, None)

    return result


def get_per_pid_gpu_mem_bytes(proc_root: str = PROC_ROOT_FOLDER) -> dict[int, int]:
    """Return {pid: GPU-resident memory in bytes} for Intel GPU clients.

    Point-in-time gauge (no delta): summed drm-resident-* region counters
    per PID. Shared buffers may be counted once per holder, as in nvtop.
    """
    per_pid_mem: dict[int, int] = {}
    for pid, record in _iter_fdinfo_records(proc_root):
        per_pid_mem[pid] = per_pid_mem.get(pid, 0) + record['mem_used_bytes']
    return per_pid_mem
