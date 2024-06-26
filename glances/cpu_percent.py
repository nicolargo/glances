#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""CPU percent stats shared between CPU and Quicklook plugins."""

import psutil

from glances.logger import logger
from glances.timer import Timer


class CpuPercent:
    """Get and store the CPU percent."""

    def __init__(self, cached_timer_cpu=2):
        # cached_timer_cpu is the minimum time interval between stats updates
        # since last update is passed (will retrieve old cached info instead)
        self.cached_timer_cpu = cached_timer_cpu
        # psutil.cpu_freq() consumes lots of CPU
        # So refresh CPU frequency stats every refresh * 2
        self.cached_timer_cpu_info = cached_timer_cpu * 2

        # Get CPU name
        self.timer_cpu_info = Timer(0)
        self.cpu_info = {'cpu_name': self.__get_cpu_name(), 'cpu_hz_current': None, 'cpu_hz': None}

        # Warning from PsUtil documentation
        # The first time this function is called with interval = 0.0 or None
        # it will return a meaningless 0.0 value which you are supposed to ignore.
        self.timer_cpu = Timer(0)
        self.cpu_percent = self.get_cpu()
        self.timer_percpu = Timer(0)
        self.percpu_percent = self.get_percpu()

    def get_key(self):
        """Return the key of the per CPU list."""
        return 'cpu_number'

    def get_info(self):
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

    def __get_cpu_name(self):
        # Get the CPU name once from the /proc/cpuinfo file
        # Read the first line with the "model name" ("Model" for Raspberry Pi)
        ret = None
        try:
            cpuinfo_file = open('/proc/cpuinfo').readlines()
        except (FileNotFoundError, PermissionError):
            pass
        else:
            for line in cpuinfo_file:
                if line.startswith('model name') or line.startswith('Model') or line.startswith('cpu model'):
                    ret = line.split(':')[1].strip()
                    break
        return ret if ret else 'CPU'

    def get_cpu(self):
        """Update and/or return the CPU using the psutil library."""
        # Never update more than 1 time per cached_timer_cpu
        if self.timer_cpu.finished():
            # Reset timer for cache
            self.timer_cpu.reset(duration=self.cached_timer_cpu)
            # Update the stats
            self.cpu_percent = psutil.cpu_percent(interval=0.0)
        return self.cpu_percent

    def get_percpu(self):
        """Update and/or return the per CPU list using the psutil library."""
        # Never update more than 1 time per cached_timer_cpu
        if self.timer_percpu.finished():
            # Reset timer for cache
            self.timer_percpu.reset(duration=self.cached_timer_cpu)
            # Get stats
            percpu_percent = []
            psutil_percpu = enumerate(psutil.cpu_times_percent(interval=0.0, percpu=True))
            for cpu_number, cputimes in psutil_percpu:
                cpu = {
                    'key': self.get_key(),
                    'cpu_number': cpu_number,
                    'total': round(100 - cputimes.idle, 1),
                    'user': cputimes.user,
                    'system': cputimes.system,
                    'idle': cputimes.idle,
                }
                # The following stats are for API purposes only
                if hasattr(cputimes, 'nice'):
                    cpu['nice'] = cputimes.nice
                if hasattr(cputimes, 'iowait'):
                    cpu['iowait'] = cputimes.iowait
                if hasattr(cputimes, 'irq'):
                    cpu['irq'] = cputimes.irq
                if hasattr(cputimes, 'softirq'):
                    cpu['softirq'] = cputimes.softirq
                if hasattr(cputimes, 'steal'):
                    cpu['steal'] = cputimes.steal
                if hasattr(cputimes, 'guest'):
                    cpu['guest'] = cputimes.guest
                if hasattr(cputimes, 'guest_nice'):
                    cpu['guest_nice'] = cputimes.guest_nice
                # Append new CPU to the list
                percpu_percent.append(cpu)
            # Update stats
            self.percpu_percent = percpu_percent
        return self.percpu_percent


# CpuPercent instance shared between plugins
cpu_percent = CpuPercent()
