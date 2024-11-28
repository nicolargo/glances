#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""CPU percent stats shared between CPU and Quicklook plugins."""

from typing import Optional, TypedDict

import psutil

from glances.logger import logger
from glances.timer import Timer

__all__ = ["cpu_percent"]


class CpuInfo(TypedDict):
    cpu_name: str
    cpu_hz: Optional[float]
    cpu_hz_current: Optional[float]


class PerCpuPercentInfo(TypedDict):
    key: str
    cpu_number: int
    total: float
    user: float
    system: float
    idle: float
    nice: Optional[float]
    iowait: Optional[float]
    irq: Optional[float]
    softirq: Optional[float]
    steal: Optional[float]
    guest: Optional[float]
    guest_nice: Optional[float]
    dpc: Optional[float]
    interrupt: Optional[float]


class CpuPercent:
    """Get and store the CPU percent."""

    def __init__(self, cached_timer_cpu: int = 2):
        # cached_timer_cpu is the minimum time interval between stats updates
        # since last update is passed (will retrieve old cached info instead)
        self.cached_timer_cpu = cached_timer_cpu
        # psutil.cpu_freq() consumes lots of CPU
        # So refresh CPU frequency stats every refresh * 2
        self.cached_timer_cpu_info = cached_timer_cpu * 2

        # Get CPU name
        self.timer_cpu_info = Timer(0)
        self.cpu_info: CpuInfo = {'cpu_name': self.__get_cpu_name(), 'cpu_hz_current': None, 'cpu_hz': None}

        # Warning from PsUtil documentation
        # The first time this function is called with interval = 0.0 or None
        # it will return a meaningless 0.0 value which you are supposed to ignore.
        self.timer_cpu = Timer(0)
        self.cpu_percent = self._compute_cpu()
        self.timer_percpu = Timer(0)
        self.percpu_percent = self._compute_percpu()

    def get_key(self):
        """Return the key of the per CPU list."""
        return 'cpu_number'

    def get_info(self) -> CpuInfo:
        """Get additional information about the CPU"""
        # Never update more than 1 time per cached_timer_cpu_info
        if self.timer_cpu_info.finished() and hasattr(psutil, 'cpu_freq'):
            # Get the CPU freq current/max
            try:
                cpu_freq = psutil.cpu_freq()
            except Exception as e:
                logger.debug(f'Can not grab CPU information ({e})')
            else:
                if hasattr(cpu_freq, 'current'):
                    self.cpu_info['cpu_hz_current'] = cpu_freq.current
                else:
                    self.cpu_info['cpu_hz_current'] = None
                if hasattr(cpu_freq, 'max'):
                    self.cpu_info['cpu_hz'] = cpu_freq.max
                else:
                    self.cpu_info['cpu_hz'] = None
                # Reset timer for cache
                self.timer_cpu_info.reset(duration=self.cached_timer_cpu_info)
        return self.cpu_info

    @staticmethod
    def __get_cpu_name() -> str:
        # Get the CPU name once from the /proc/cpuinfo file
        # Read the first line with the "model name" ("Model" for Raspberry Pi)
        try:
            cpuinfo_lines = open('/proc/cpuinfo').readlines()
        except (FileNotFoundError, PermissionError):
            logger.debug("No permission to read '/proc/cpuinfo'")
            return 'CPU'

        for line in cpuinfo_lines:
            if line.startswith('model name') or line.startswith('Model') or line.startswith('cpu model'):
                return line.split(':')[1].strip()

        return 'CPU'

    def get_cpu(self) -> float:
        """Update and/or return the CPU using the psutil library."""
        # Never update more than 1 time per cached_timer_cpu
        if self.timer_cpu.finished():
            # Reset timer for cache
            self.timer_cpu.reset(duration=self.cached_timer_cpu)
            # Update the stats
            self.cpu_percent = self._compute_cpu()
        return self.cpu_percent

    @staticmethod
    def _compute_cpu() -> float:
        return psutil.cpu_percent(interval=0.0)

    def get_percpu(self) -> list[PerCpuPercentInfo]:
        """Update and/or return the per CPU list using the psutil library."""
        # Never update more than 1 time per cached_timer_cpu
        if self.timer_percpu.finished():
            # Reset timer for cache
            self.timer_percpu.reset(duration=self.cached_timer_cpu)
            # Update stats
            self.percpu_percent = self._compute_percpu()
        return self.percpu_percent

    def _compute_percpu(self) -> list[PerCpuPercentInfo]:
        psutil_percpu = enumerate(psutil.cpu_times_percent(interval=0.0, percpu=True))
        return [
            {
                'key': self.get_key(),
                'cpu_number': cpu_number,
                'total': round(100 - cpu_times.idle, 1),
                'user': cpu_times.user,
                'system': cpu_times.system,
                'idle': cpu_times.idle,
                'nice': cpu_times.nice if hasattr(cpu_times, 'nice') else None,
                'iowait': cpu_times.iowait if hasattr(cpu_times, 'iowait') else None,
                'irq': cpu_times.irq if hasattr(cpu_times, 'irq') else None,
                'softirq': cpu_times.softirq if hasattr(cpu_times, 'softirq') else None,
                'steal': cpu_times.steal if hasattr(cpu_times, 'steal') else None,
                'guest': cpu_times.guest if hasattr(cpu_times, 'guest') else None,
                'guest_nice': cpu_times.steal if hasattr(cpu_times, 'guest_nice') else None,
                'dpc': cpu_times.dpc if hasattr(cpu_times, 'dpc') else None,
                'interrupt': cpu_times.interrupt if hasattr(cpu_times, 'interrupt') else None,
            }
            for cpu_number, cpu_times in psutil_percpu
        ]


# CpuPercent instance shared between plugins
cpu_percent = CpuPercent()
