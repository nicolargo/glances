#
# This file is part of Glances.
#
# Intel GPU support added (poorly) 2025 by <computerdork@verion.net>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Intel GPU card for Glances."""

import glob
import json
import os
import re
import subprocess
import time
from collections import defaultdict

from glances.logger import logger


class IntelGPU:
    """Intel GPU card (Arc, Xe) using xpumcli + fdinfo."""

    def __init__(self, config=None):
        """Init Intel GPU detection."""
        self.ready = False
        self.device_count = 0
        self.pci_to_id = {}
        self.fdinfo_last = {}
        self.config = config

        # Parse ignore_devices from config
        self.ignore_devices = set()
        if config:
            try:
                ignore_str = config.get_value('gpu', 'ignore_devices', default='')
                if ignore_str:
                    self.ignore_devices = {int(x.strip()) for x in ignore_str.split(',') if x.strip()}
                    logger.debug(f"Intel GPU ignoring devices: {self.ignore_devices}")
            except Exception as e:
                logger.debug(f"Error parsing ignore_devices: {e}")

        # Detect which command is available: xpu-smi (newer) or xpumcli (older)
        self.xpumcli_cmd = None
        for cmd in ['xpu-smi', 'xpumcli']:
            try:
                result = subprocess.run([cmd, '--version'], capture_output=True, timeout=2)
                if result.returncode == 0:
                    self.xpumcli_cmd = cmd
                    logger.debug(f"Found Intel GPU tool: {cmd}")
                    break
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

        if not self.xpumcli_cmd:
            logger.debug("Neither xpu-smi nor xpumcli found, Intel GPU support disabled")
            return

        # Get Intel GPU device list
        try:
            result = subprocess.run([self.xpumcli_cmd, 'discovery', '-j'], capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                data = json.loads(result.stdout)
                devices = data.get('device_list', [])
                self.device_count = len(devices)

                # Build PCI address mapping
                for device in devices:
                    device_id = device.get('device_id')
                    pci_addr = device.get('pci_bdf_address', '').lower()
                    if device_id is not None and pci_addr:
                        self.pci_to_id[pci_addr] = device_id

                if self.device_count > 0:
                    self.ready = True
                    logger.debug(f"Intel GPU support initialized: {self.device_count} device(s)")
        except Exception as e:
            logger.debug(f"Intel GPU initialization failed: {e}")

    def get_device_stats(self):
        """Get Intel GPU stats.

        Returns list of dicts with GPU stats.
        """
        if not self.ready:
            return []

        stats = []

        # Get GPU utilization from fdinfo
        intel_util = self._get_fdinfo_utilization()

        # Query each Intel GPU
        for xpu_device_id in range(self.device_count):
            # Skip ignored devices
            if xpu_device_id in self.ignore_devices:
                logger.debug(f"Skipping ignored Intel GPU device {xpu_device_id}")
                continue

            try:
                result = subprocess.run(
                    [self.xpumcli_cmd, 'stats', '-j', '-d', str(xpu_device_id)],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode != 0:
                    continue

                data = json.loads(result.stdout)
                device_level = data.get('device_level', [])

                device_stats = {
                    'key': 'gpu_id',
                    'gpu_id': f'intel{xpu_device_id}',
                    'name': self._get_device_name(xpu_device_id),
                    'mem': self._extract_metric(device_level, 'XPUM_STATS_MEMORY_UTILIZATION'),
                    'proc': intel_util.get(xpu_device_id, 0.0),
                    'temperature': self._extract_metric(device_level, 'XPUM_STATS_MEMORY_TEMPERATURE'),
                    'fan_speed': None,  # Not available
                }

                # Set None for invalid values
                if device_stats['mem'] <= 0:
                    device_stats['mem'] = None
                if device_stats['temperature'] <= 0:
                    device_stats['temperature'] = None

                stats.append(device_stats)

            except Exception as e:
                logger.debug(f"Error getting Intel GPU {xpu_device_id} stats: {e}")
                continue

        return stats

    def _get_device_name(self, device_id):
        """Get Intel GPU device name."""
        try:
            result = subprocess.run([self.xpumcli_cmd, 'discovery', '-j'], capture_output=True, text=True, timeout=5)

            if result.returncode == 0:
                data = json.loads(result.stdout)
                for device in data.get('device_list', []):
                    if device.get('device_id') == device_id:
                        name = device.get('device_name', 'Intel GPU')
                        # Clean up name
                        name = name.replace('Intel(R) ', '').replace('Graphics ', '')
                        if not name or name == 'Graphics':
                            # Fallback to PCI device ID
                            pci_id = device.get('pci_device_id', '')
                            if pci_id.startswith('0x'):
                                name = pci_id[2:]
                            else:
                                name = 'Intel GPU'
                        return name
        except Exception:
            pass
        return 'Intel GPU'

    def _extract_metric(self, device_level, metric_type):
        """Extract metric from xpumcli device_level array."""
        for metric in device_level:
            if metric.get('metrics_type') == metric_type:
                return metric.get('value', 0)
        return 0

    def _get_fdinfo_utilization(self):
        """Get Intel GPU utilization from /proc/*/fdinfo/*.

        Returns dict of {device_id: utilization_percent}

        Requires root/CAP_SYS_PTRACE to see all processes.
        """
        current_time = time.time()

        # Find all processes with GPU access
        pci_to_cycles = defaultdict(lambda: defaultdict(int))

        for proc_dir in glob.glob('/proc/[0-9]*'):
            try:
                fdinfo_dir = os.path.join(proc_dir, 'fdinfo')

                if not os.path.exists(fdinfo_dir):
                    continue

                for fdinfo_file in os.listdir(fdinfo_dir):
                    fdinfo_path = os.path.join(fdinfo_dir, fdinfo_file)

                    try:
                        with open(fdinfo_path) as f:
                            content = f.read()

                        # Check for Intel GPU
                        pci_match = re.search(r'drm-pdev:\s*([0-9a-f:\.]+)', content)
                        if not pci_match or 'drm-cycles-' not in content:
                            continue

                        pci_addr = pci_match.group(1).lower()

                        # Only process Intel GPUs we know about
                        if pci_addr not in self.pci_to_id:
                            continue

                        # Parse engine cycles
                        cycles_pattern = re.compile(r'drm-cycles-(\w+):\s+(\d+)')
                        total_cycles_pattern = re.compile(r'drm-total-cycles-(\w+):\s+(\d+)')

                        for match in cycles_pattern.finditer(content):
                            engine = match.group(1)
                            value = int(match.group(2))
                            pci_to_cycles[pci_addr][engine + '_cycles'] += value

                        for match in total_cycles_pattern.finditer(content):
                            engine = match.group(1)
                            value = int(match.group(2))
                            key = engine + '_total'
                            pci_to_cycles[pci_addr][key] = max(pci_to_cycles[pci_addr][key], value)

                    except (OSError, PermissionError):
                        continue
            except (ValueError, OSError, PermissionError):
                continue

        # Calculate utilization
        utilization = {}

        for pci_addr, cycles in pci_to_cycles.items():
            device_id = self.pci_to_id.get(pci_addr)
            if device_id is None:
                continue

            # Check if we have a previous measurement
            if pci_addr not in self.fdinfo_last:
                # First measurement - store baseline
                self.fdinfo_last[pci_addr] = {'cycles': dict(cycles), 'time': current_time}
                utilization[device_id] = 0.0
                continue

            last = self.fdinfo_last[pci_addr]
            time_delta = current_time - last['time']

            if time_delta < 0.1:
                utilization[device_id] = 0.0
                continue

            # Calculate max utilization across all engines
            max_util = 0.0
            engines = {k.replace('_cycles', '').replace('_total', '') for k in cycles.keys()}

            for engine in engines:
                curr_cycles = cycles.get(engine + '_cycles', 0)
                curr_total = cycles.get(engine + '_total', 0)
                prev_cycles = last['cycles'].get(engine + '_cycles', 0)
                prev_total = last['cycles'].get(engine + '_total', 0)

                delta_cycles = curr_cycles - prev_cycles
                delta_total = curr_total - prev_total

                if delta_total > 0:
                    engine_util = (delta_cycles / delta_total) * 100.0
                    max_util = max(max_util, engine_util)

            utilization[device_id] = min(100.0, max(0.0, max_util))

            # Update last measurement
            self.fdinfo_last[pci_addr] = {'cycles': dict(cycles), 'time': current_time}

        # Fill in 0% for devices with no activity
        for device_id in range(self.device_count):
            if device_id not in utilization:
                utilization[device_id] = 0.0

        return utilization

    def exit(self):
        """Cleanup (Intel GPU is stateless)."""
        pass
