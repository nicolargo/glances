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
from glances.plugins.gpu.cards.arm import _parse_meminfo, _parse_memory

DRM_ROOT_FOLDER: str = '/sys/class/drm'
PROC_ROOT_FOLDER: str = '/proc'
DRM_DEV_PREFIX: str = '/dev/dri/'
DEVICE_FOLDER_PATTERN: str = 'card[0-9]'
INTELGPU_IDS_FILE: str = '/usr/share/misc/pci.ids'
PCI_DEVICE_VENDOR: str = 'device/vendor'
PCI_DEVICE_ID: str = 'device/device'
HWMON_PATTERN: str = 'device/hwmon/hwmon*'
HWMON_TEMP_PATTERN: str = 'temp*_input'
PCI_ACT_FRQ_MHZ: str = 'gt_act_freq_mhz'
PCI_MAX_FRQ_MHZ: str = 'gt_max_freq_mhz'
PCI_RESOURCE: str = 'device/resource'
# Lines 1-6 of the resource file are BAR0-5; line 7 is the expansion ROM.
PCI_BAR_COUNT: int = 6
# Resource flags, see include/linux/ioport.h.
IORESOURCE_MEM: int = 0x200
IORESOURCE_PREFETCH: int = 0x2000

# DRM drivers exposing the standardised drm-engine-* fdinfo counters.
SUPPORTED_DRIVERS: set[str] = {'i915', 'xe'}


class IntelGPU:
    """Intel GPU card class."""

    # True when the card temperature is also shown by the sensors plugin
    # (psutil.sensors_temperatures()). Source here: the i915/xe driver's hwmon node.
    TEMPERATURE_IN_SENSORS = True

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
            # Memory consumption in % (not available on all GPU)
            device_stats['mem'] = get_mem(device, snapshot, os.path.join(self.proc_root_folder, 'meminfo'))
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
            # No trustworthy scan: a later delta must not use this stale baseline.
            self._last_sample.pop(device, None)
            return None
        busy_ns = snapshot.get('engine_total_ns', 0)
        now_ns = time.monotonic_ns()
        prev = self._last_sample.get(device)
        self._last_sample[device] = (now_ns, busy_ns)
        if prev is None:
            return None
        delta_t = now_ns - prev[0]
        if delta_t <= 0:
            return None
        # The sum drops when a client exits (its counters vanish); report idle
        # rather than the frequency ratio, which is not a load figure.
        delta_busy = max(0, busy_ns - prev[1])
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


def get_mem(device_folder: str, snapshot: dict | None, meminfo_path: str = '/proc/meminfo') -> int | None:
    """
    Return the memory consumption in %, or None when it cannot be trusted.

    A card holding resident local memory (VRAM) is discrete: report it over
    the local aperture. Otherwise report system memory over MemTotal, which
    is right for an integrated GPU and reads ~0% for an idle discrete one.
    """
    if snapshot is None:
        return None
    local = snapshot.get('mem_local_bytes', 0)
    if local > 0:
        capacity = get_local_mem_capacity(device_folder)
        used = local
    else:
        capacity = get_system_mem_capacity(meminfo_path)
        used = snapshot.get('mem_system_bytes', 0)
    # Without resizable BAR the aperture is smaller than VRAM: no valid
    # percentage exists, and one above 100 would be wrong.
    if not capacity or used > capacity:
        return None
    return round(used / capacity * 100)


def get_system_mem_capacity(meminfo_path: str = '/proc/meminfo') -> int | None:
    """
    Return MemTotal in bytes, or None if unreadable.

    Not arm.get_mem_capacity_bytes: it prefers CmaTotal, the ARM DMA pool,
    which is not where Intel GPU buffers come from.
    """
    text = read_file(meminfo_path)
    if text is None:
        return None
    return _parse_meminfo(text).get('MemTotal') or None


def get_local_mem_capacity(device_folder: str) -> int | None:
    """
    Return the size in bytes of the card's local memory aperture, or None.

    It is the largest prefetchable memory BAR. That equals the VRAM size only
    with resizable BAR enabled; otherwise it is smaller, and the caller must
    not report a percentage above 100.
    """
    text = read_file(device_folder, PCI_RESOURCE)
    if text is None:
        return None
    largest = 0
    for line in text.splitlines()[:PCI_BAR_COUNT]:
        try:
            start, end, flags = (int(field, 16) for field in line.split()[:3])
        except ValueError:
            continue
        if flags & IORESOURCE_MEM and flags & IORESOURCE_PREFETCH and end > start:
            largest = max(largest, end - start + 1)
    return largest or None


def get_proc(device_folder: str) -> int | None:
    """Return the processor consumption in % (frequency ratio, fallback)."""
    act_freq = read_file(device_folder, PCI_ACT_FRQ_MHZ)
    max_freq = read_file(device_folder, PCI_MAX_FRQ_MHZ)
    if act_freq and max_freq:
        return round(int(act_freq) / int(max_freq) * 100)
    return None


def get_temperature(device_folder: str) -> int | None:
    """Return the processor temperature in °C (mean of all HWMON).

    Discrete GPUs (e.g. Arc) expose temp*_input (millidegrees C) under
    <card>/device/hwmon/hwmon*/. Integrated GPUs usually have no hwmon node
    there: None is returned and the temperature is simply not displayed.
    """
    temps = []
    for hwmon in glob.glob(HWMON_PATTERN, root_dir=device_folder):
        hwmon_folder = os.path.join(device_folder, hwmon)
        for temp_file in glob.glob(HWMON_TEMP_PATTERN, root_dir=hwmon_folder):
            value = read_file(hwmon_folder, temp_file)
            try:
                temps.append(int(value) / 1000)
            except (TypeError, ValueError):
                continue
    if temps:
        return round(sum(temps) / len(temps))
    return None


def get_fan_speed(device_folder: str) -> int | None:
    """Return the fan speed in %."""
    return None


def parse_fdinfo(text: str) -> dict | None:
    """Parse the content of a /proc/*/fdinfo/* file.

    Returns a dict with keys:
        - driver: str
        - pdev:   str | None
        - client_id: str | None (``drm-client-id``; one DRM client is visible
          through every fd that shares it, after dup() or fork())
        - engine_total_ns: int (sum of all drm-engine-* time counters,
          excluding drm-engine-capacity-* which is a count, not a time)
        - mem_system_bytes: int (sum of drm-resident-system* regions: host RAM)
        - mem_local_bytes: int (sum of drm-resident-local* / -vram* regions:
          the card's own memory, discrete GPUs only)

    Only resident counters are used: shared/active/purgeable are subsets of
    it, and stolen-* regions are a separate reserved pool.

    Returns None if the text does not look like a DRM fdinfo entry.
    """
    if not text or 'drm-driver:' not in text:
        return None

    driver: str | None = None
    pdev: str | None = None
    client_id: str | None = None
    engine_total_ns = 0
    resident = {'system': 0, 'local': 0}

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
        elif key == 'drm-client-id':
            client_id = value
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
        elif key.startswith('drm-resident-'):
            region = _memory_region(key.removeprefix('drm-resident-'))
            parsed = _parse_memory(value)
            if region and parsed is not None:
                resident[region] += parsed

    if driver is None:
        return None

    return {
        'driver': driver,
        'pdev': pdev,
        'client_id': client_id,
        'engine_total_ns': engine_total_ns,
        'mem_system_bytes': resident['system'],
        'mem_local_bytes': resident['local'],
    }


def _memory_region(name: str) -> str | None:
    """Map an fdinfo region name (``system0``, ``local0``, ``vram0``) to a class."""
    if name.startswith('system'):
        return 'system'
    if name.startswith(('local', 'vram')):
        return 'local'
    # stolen-*, or a region we do not know about.
    return None


def _empty_bucket() -> dict[str, int]:
    """Return the per-device accumulator used by aggregate_fdinfo."""
    return {'engine_total_ns': 0, 'mem_system_bytes': 0, 'mem_local_bytes': 0}


def _build_device_lookup(
    device_folders: list[tuple[str, str | None, str | None]],
) -> tuple[dict[str, str], dict[str, str]]:
    """Return ({pdev: device}, {driver: device}) for fdinfo attribution.

    The driver map only holds drivers bound to exactly one device: with
    several, a record lacking a usable pdev is ambiguous.
    """
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
    return pdev_to_device, single_device_per_driver


def _attribute_record(
    record: dict,
    pdev_to_device: dict[str, str],
    single_device_per_driver: dict[str, str],
) -> str | None:
    """Return the device folder an fdinfo record belongs to, or None."""
    if record['pdev'] and record['pdev'] in pdev_to_device:
        return pdev_to_device[record['pdev']]
    return single_device_per_driver.get(record['driver'])


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

    When every process could be inspected, each device gets an entry (zero
    engine time if it has no client), so an idle GPU reads 0 rather than
    unknown. If any process was unreadable the view is partial: devices
    without a visible client are left out and the caller falls back.
    """
    if not device_folders or not os.path.isdir(proc_root):
        return {}

    pdev_to_device, single_device_per_driver = _build_device_lookup(device_folders)
    per_device: dict[str, dict] = {}
    # Clients already counted: the same client shows up on several fds.
    seen_clients: set[tuple[str, str | None, str]] = set()

    try:
        pids = os.listdir(proc_root)
    except OSError as e:
        logger.debug(f'Intel GPU: cannot list {proc_root}: {e}')
        return {}

    complete = True
    for pid in pids:
        if not pid.isdigit():
            continue
        fd_dir = os.path.join(proc_root, pid, 'fd')
        try:
            fds = os.listdir(fd_dir)
        except PermissionError:
            complete = False
            continue
        except OSError:
            # Process exited mid-scan, or not a process directory.
            continue
        for fd in fds:
            # Only DRM fds carry engine counters: one readlink is far cheaper
            # than opening and reading the fdinfo of every fd on the system.
            try:
                if not os.readlink(os.path.join(fd_dir, fd)).startswith(DRM_DEV_PREFIX):
                    continue
            except OSError:
                # fd closed mid-scan.
                continue
            fd_path = os.path.join(proc_root, pid, 'fdinfo', fd)
            try:
                with open(fd_path) as f:
                    text = f.read()
            except PermissionError:
                complete = False
                continue
            except OSError:
                continue
            record = parse_fdinfo(text)
            if record is None:
                continue
            if record['driver'] not in SUPPORTED_DRIVERS:
                continue

            target = _attribute_record(record, pdev_to_device, single_device_per_driver)
            if target is None:
                continue
            if record['client_id'] is not None:
                client_key = (record['driver'], record['pdev'], record['client_id'])
                if client_key in seen_clients:
                    continue
                seen_clients.add(client_key)

            bucket = per_device.setdefault(target, _empty_bucket())
            for key in bucket:
                bucket[key] += record[key]

    if complete:
        for device, _driver, _pdev in device_folders:
            per_device.setdefault(device, _empty_bucket())

    return per_device
