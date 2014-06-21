# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2014 Nicolargo <nicolas@nicolargo.com>
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

from glances.core.glances_globals import is_bsd, is_mac, is_windows
from glances.core.glances_timer import Timer, getTimeSinceLastUpdate

import psutil


class GlancesProcesses(object):

    """Get processed stats using the psutil library."""

    def __init__(self, cache_timeout=60):
        """Init the class to collect stats about processes."""
        # Add internals caches because PSUtil do not cache all the stats
        # See: https://code.google.com/p/psutil/issues/detail?id=462
        self.username_cache = {}
        self.cmdline_cache = {}

        # The internals caches will be cleaned each 'cache_timeout' seconds
        self.cache_timeout = cache_timeout
        self.cache_timer = Timer(self.cache_timeout)

        # Init the io dict
        # key = pid
        # value = [ read_bytes_old, write_bytes_old ]
        self.io_old = {}

        # Init stats
        self.processsort = 'cpu_percent'
        self.processlist = []
        self.processcount = {'total': 0, 'running': 0, 'sleeping': 0, 'thread': 0}

        # Tag to enable/disable the processes stats (to reduce the Glances CPU comsumption)
        # Default is to enable the processes stats
        self.disable_tag = False

    def enable(self):
        """Enable process stats."""
        self.disable_tag = False
        self.update()

    def disable(self):
        """Disable process stats."""
        self.disable_tag = True

    def __get_process_stats(self, proc):
        """Get process stats."""
        procstat = {}

        # Process ID
        procstat['pid'] = proc.pid

        # Process name (cached by PSUtil)
        try:
            procstat['name'] = proc.name()
        except psutil.AccessDenied:
            procstat['name'] = ""

        # Process username (cached with internal cache)
        try:
            self.username_cache[procstat['pid']]
        except:
            try:
                self.username_cache[procstat['pid']] = proc.username()
            except (KeyError, psutil.AccessDenied):
                try:
                    self.username_cache[procstat['pid']] = proc.uids().real
                except (KeyError, AttributeError, psutil.AccessDenied):
                    self.username_cache[procstat['pid']] = "?"
        procstat['username'] = self.username_cache[procstat['pid']]

        # Process command line (cached with internal cache)
        try:
            self.cmdline_cache[procstat['pid']]
        except:
            self.cmdline_cache[procstat['pid']] = ' '.join(proc.cmdline())
        procstat['cmdline'] = self.cmdline_cache[procstat['pid']]

        # Process status
        procstat['status'] = str(proc.status())[:1].upper()

        # Process nice
        try:
            procstat['nice'] = proc.nice()
        except psutil.AccessDenied:
            procstat['nice'] = None

        # Process memory
        procstat['memory_info'] = proc.memory_info()
        procstat['memory_percent'] = proc.memory_percent()

        # Process CPU
        procstat['cpu_times'] = proc.cpu_times()
        procstat['cpu_percent'] = proc.cpu_percent(interval=0)

        # Process network connections (TCP and UDP) (Experimental)
        # !!! High CPU consumption
        # try:
        #     procstat['tcp'] = len(proc.connections(kind="tcp"))
        #     procstat['udp'] = len(proc.connections(kind="udp"))
        # except:
        #     procstat['tcp'] = 0
        #     procstat['udp'] = 0

        # Process IO
        # procstat['io_counters'] is a list:
        # [read_bytes, write_bytes, read_bytes_old, write_bytes_old, io_tag]
        # If io_tag = 0 > Access denied (display "?")
        # If io_tag = 1 > No access denied (display the IO rate)
        # Note Disk IO stat not available on Mac OS
        if not is_mac:
            try:
                # Get the process IO counters
                proc_io = proc.io_counters()
                io_new = [proc_io.read_bytes, proc_io.write_bytes]
            except psutil.AccessDenied:
                # Access denied to process IO (no root account)
                # Put 0 in all values (for sort) and io_tag = 0 (for display)
                procstat['io_counters'] = [0, 0] + [0, 0]
                io_tag = 0
            else:
                # For IO rate computation
                # Append saved IO r/w bytes
                try:
                    procstat['io_counters'] = io_new + self.io_old[procstat['pid']]
                except KeyError:
                    procstat['io_counters'] = io_new + [0, 0]
                # then save the IO r/w bytes
                self.io_old[procstat['pid']] = io_new
                io_tag = 1

            # Append the IO tag (for display)
            procstat['io_counters'] += [io_tag]

        return procstat

    def update(self):
        """Update the processes stats."""
        # Reset the stats
        self.processlist = []
        self.processcount = {'total': 0, 'running': 0, 'sleeping': 0, 'thread': 0}

        # Do not process if disable tag is set
        if self.disable_tag:
            return

        # Get the time since last update
        time_since_update = getTimeSinceLastUpdate('process_disk')

        # For each existing process...
        for proc in psutil.process_iter():
            try:
                # Get stats using the PSUtil
                procstat = self.__get_process_stats(proc)
                # Add a specific time_since_update stats for bitrate
                procstat['time_since_update'] = time_since_update
                # ignore the 'idle' process on Windows and *BSD
                # ignore the 'kernel_task' process on OS X
                # waiting for upstream patch from psutil
                if (is_bsd and procstat['name'] == 'idle' or
                        is_windows and procstat['name'] == 'System Idle Process' or
                        is_mac and procstat['name'] == 'kernel_task'):
                    continue
                # Update processcount (global statistics)
                try:
                    self.processcount[str(proc.status())] += 1
                except KeyError:
                    # Key did not exist, create it
                    self.processcount[str(proc.status())] = 1
                else:
                    self.processcount['total'] += 1
                # Update thread number (global statistics)
                try:
                    self.processcount['thread'] += proc.num_threads()
                except:
                    pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            else:
                # Update processlist
                self.processlist.append(procstat)

        # Clean internals caches if timeout is reached
        if self.cache_timer.finished():
            self.username_cache = {}
            self.cmdline_cache = {}
            # Restart the timer
            self.cache_timer.reset()

    def getcount(self):
        """Get the number of processes."""
        return self.processcount

    def getlist(self, sortedby=None):
        """Get the processlist."""
        return self.processlist

    def getsortkey(self):
        """Get the current sort key for automatic sort."""
        return self.processsort

    def setsortkey(self, sortedby):
        """Set the current sort key for automatic sort."""
        self.processsort = sortedby
        return self.processsort

    def getsortlist(self, sortedby=None):
        """Get the sorted processlist."""
        if sortedby is None:
            # No need to sort...
            return self.processlist

        sortedreverse = True
        if sortedby == 'name':
            sortedreverse = False

        if sortedby == 'io_counters':
            # Specific case for io_counters
            # Sum of io_r + io_w
            try:
                # Sort process by IO rate (sum IO read + IO write)
                listsorted = sorted(self.processlist,
                                    key=lambda process: process[sortedby][0] -
                                    process[sortedby][2] + process[sortedby][1] -
                                    process[sortedby][3],
                                    reverse=sortedreverse)
            except Exception:
                listsorted = sorted(self.processlist,
                                    key=lambda process: process['cpu_percent'],
                                    reverse=sortedreverse)
        else:
            # Others sorts
            listsorted = sorted(self.processlist,
                                key=lambda process: process[sortedby],
                                reverse=sortedreverse)

        self.processlist = listsorted

        return self.processlist
