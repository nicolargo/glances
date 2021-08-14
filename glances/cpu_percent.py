# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2021 Nicolargo <nicolas@nicolargo.com>
#
# Glances is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Glances is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""CPU percent stats shared between CPU and Quicklook plugins."""

from glances.logger import logger
from glances.timer import Timer

import psutil


class CpuPercent(object):

    """Get and store the CPU percent."""

    def __init__(self, cached_timer_cpu=3):
        self.cpu_info = {}
        self.cpu_percent = 0
        self.percpu_percent = []

        # Get CPU name
        self.__get_cpu_name()

        # cached_timer_cpu is the minimum time interval between stats updates
        # since last update is passed (will retrieve old cached info instead)
        self.cached_timer_cpu = cached_timer_cpu
        self.timer_cpu = Timer(0)
        self.timer_percpu = Timer(0)

        # psutil.cpu_freq() consumes lots of CPU
        # So refresh the stats every refresh*2 (6 seconds)
        self.cached_timer_cpu_info = cached_timer_cpu * 2
        self.timer_cpu_info = Timer(0)

    def get_key(self):
        """Return the key of the per CPU list."""
        return 'cpu_number'

    def get(self, percpu=False):
        """Update and/or return the CPU using the psutil library.
        If percpu, return the percpu stats"""
        if percpu:
            return self.__get_percpu()
        else:
            return self.__get_cpu()

    def get_info(self):
        """Get additional informations about the CPU"""
        # Never update more than 1 time per cached_timer_cpu_info
        if self.timer_cpu_info.finished() and hasattr(psutil, 'cpu_freq'):
            # Get the CPU freq current/max
            cpu_freq = psutil.cpu_freq()
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
        # @TODO: Multisystem...
        try:
            self.cpu_info['cpu_name'] = open('/proc/cpuinfo', 'r').readlines()[4].split(':')[1].strip()
        except:
            self.cpu_info['cpu_name'] = 'CPU'
        return self.cpu_info['cpu_name']

    def __get_cpu(self):
        """Update and/or return the CPU using the psutil library."""
        # Never update more than 1 time per cached_timer_cpu
        if self.timer_cpu.finished():
            self.cpu_percent = psutil.cpu_percent(interval=0.0)
            # Reset timer for cache
            self.timer_cpu.reset(duration=self.cached_timer_cpu)
        return self.cpu_percent

    def __get_percpu(self):
        """Update and/or return the per CPU list using the psutil library."""
        # Never update more than 1 time per cached_timer_cpu
        if self.timer_percpu.finished():
            self.percpu_percent = []
            for cpu_number, cputimes in enumerate(psutil.cpu_times_percent(interval=0.0,
                                                                           percpu=True)):
                cpu = {'key': self.get_key(),
                       'cpu_number': cpu_number,
                       'total': round(100 - cputimes.idle, 1),
                       'user': cputimes.user,
                       'system': cputimes.system,
                       'idle': cputimes.idle}
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
                self.percpu_percent.append(cpu)
                # Reset timer for cache
                self.timer_percpu.reset(duration=self.cached_timer_cpu)
        return self.percpu_percent


# CpuPercent instance shared between plugins
cpu_percent = CpuPercent()
