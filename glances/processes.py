# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2017 Nicolargo <nicolas@nicolargo.com>
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

import operator
import os

from glances.compat import iteritems, itervalues, listitems, iterkeys
from glances.globals import BSD, LINUX, MACOS, SUNOS, WINDOWS
from glances.timer import Timer, getTimeSinceLastUpdate
from glances.filter import GlancesFilter
from glances.logger import logger

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

        # Wether or not to enable process tree
        self._enable_tree = False
        self.process_tree = None

        # Init stats
        self.auto_sort = True
        self._sort_key = 'cpu_percent'
        self.processlist = []
        self.reset_processcount()

        # Tag to enable/disable the processes stats (to reduce the Glances CPU consumption)
        # Default is to enable the processes stats
        self.disable_tag = False

        # Extended stats for top process is enable by default
        self.disable_extended_tag = False

        # Maximum number of processes showed in the UI (None if no limit)
        self._max_processes = None

        # Process filter is a regular expression
        self._filter = GlancesFilter()

        # Whether or not to hide kernel threads
        self.no_kernel_threads = False

        # Store maximums values in a dict
        # Used in the UI to highlight the maximum value
        self._max_values_list = ('cpu_percent', 'memory_percent')
        # { 'cpu_percent': 0.0, 'memory_percent': 0.0 }
        self._max_values = {}
        self.reset_max_values()

    def reset_processcount(self):
        """Reset the global process count"""
        self.processcount = {'total': 0,
                             'running': 0,
                             'sleeping': 0,
                             'thread': 0,
                             'pid_max': None}

    def update_processcount(self, plist):
        """Update the global process count from the current processes list"""
        # Update the maximum process ID (pid) number
        self.processcount['pid_max'] = self.pid_max
        # For each key in the processcount dict
        # count the number of processes with the same status
        for k in iterkeys(self.processcount):
            self.processcount[k] = len(list(filter(lambda v: v['status'] is k,
                                                   plist)))
        # Compute thread
        self.processcount['thread'] = sum(i['num_threads'] for i in plist)
        # Compute total
        self.processcount['total'] = len(plist)

    def enable(self):
        """Enable process stats."""
        self.disable_tag = False
        self.update()

    def disable(self):
        """Disable process stats."""
        self.disable_tag = True

    def enable_extended(self):
        """Enable extended process stats."""
        self.disable_extended_tag = False
        self.update()

    def disable_extended(self):
        """Disable extended process stats."""
        self.disable_extended_tag = True

    @property
    def pid_max(self):
        """
        Get the maximum PID value.

        On Linux, the value is read from the `/proc/sys/kernel/pid_max` file.

        From `man 5 proc`:
        The default value for this file, 32768, results in the same range of
        PIDs as on earlier kernels. On 32-bit platfroms, 32768 is the maximum
        value for pid_max. On 64-bit systems, pid_max can be set to any value
        up to 2^22 (PID_MAX_LIMIT, approximately 4 million).

        If the file is unreadable or not available for whatever reason,
        returns None.

        Some other OSes:
        - On FreeBSD and macOS the maximum is 99999.
        - On OpenBSD >= 6.0 the maximum is 99999 (was 32766).
        - On NetBSD the maximum is 30000.

        :returns: int or None
        """
        if LINUX:
            # XXX: waiting for https://github.com/giampaolo/psutil/issues/720
            try:
                with open('/proc/sys/kernel/pid_max', 'rb') as f:
                    return int(f.read())
            except (OSError, IOError):
                return None
        else:
            return None

    @property
    def max_processes(self):
        """Get the maximum number of processes showed in the UI."""
        return self._max_processes

    @max_processes.setter
    def max_processes(self, value):
        """Set the maximum number of processes showed in the UI."""
        self._max_processes = value

    @property
    def process_filter_input(self):
        """Get the process filter (given by the user)."""
        return self._filter.filter_input

    @property
    def process_filter(self):
        """Get the process filter (current apply filter)."""
        return self._filter.filter

    @process_filter.setter
    def process_filter(self, value):
        """Set the process filter."""
        self._filter.filter = value

    @property
    def process_filter_key(self):
        """Get the process filter key."""
        return self._filter.filter_key

    @property
    def process_filter_re(self):
        """Get the process regular expression compiled."""
        return self._filter.filter_re

    def disable_kernel_threads(self):
        """Ignore kernel threads in process list."""
        self.no_kernel_threads = True

    def enable_tree(self):
        """Enable process tree."""
        self._enable_tree = True

    def is_tree_enabled(self):
        """Return True if process tree is enabled, False instead."""
        return self._enable_tree

    @property
    def sort_reverse(self):
        """Return True to sort processes in reverse 'key' order, False instead."""
        if self.sort_key == 'name' or self.sort_key == 'username':
            return False

        return True

    def max_values(self):
        """Return the max values dict."""
        return self._max_values

    def get_max_values(self, key):
        """Get the maximum values of the given stat (key)."""
        return self._max_values[key]

    def set_max_values(self, key, value):
        """Set the maximum value for a specific stat (key)."""
        self._max_values[key] = value

    def reset_max_values(self):
        """Reset the maximum values dict."""
        self._max_values = {}
        for k in self._max_values_list:
            self._max_values[k] = 0.0

    def __get_extended_stats(self, proc, procstat):
        """
        Get extended stats, only for top processes (see issue #403).

        - cpu_affinity (Linux, Windows, FreeBSD)
        - ionice (Linux and Windows > Vista)
        - memory_full_info (Linux)
        - num_ctx_switches (not available on Illumos/Solaris)
        - num_fds (Unix-like)
        - num_handles (Windows)
        - num_threads (not available on *BSD)
        - memory_maps (only swap, Linux)
          https://www.cyberciti.biz/faq/linux-which-process-is-using-swap/
        - connections (TCP and UDP)
        """
        procstat['extended_stats'] = True

        for stat in ['cpu_affinity', 'ionice', 'memory_full_info',
                     'num_ctx_switches', 'num_fds', 'num_handles',
                     'num_threads']:
            try:
                procstat.update(proc.as_dict(attrs=[stat]))
            except psutil.NoSuchProcess:
                pass
            # XXX: psutil>=4.3.1 raises ValueError while <4.3.1 raises AttributeError
            except (ValueError, AttributeError):
                procstat[stat] = None

        if LINUX:
            try:
                procstat['memory_swap'] = sum([v.swap for v in proc.memory_maps()])
            except psutil.NoSuchProcess:
                pass
            except (psutil.AccessDenied, TypeError, NotImplementedError):
                # NotImplementedError: /proc/${PID}/smaps file doesn't exist
                # on kernel < 2.6.14 or CONFIG_MMU kernel configuration option
                # is not enabled (see psutil #533/glances #413).
                # XXX: Remove TypeError once we'll drop psutil < 3.0.0.
                procstat['memory_swap'] = None

        try:
            procstat['tcp'] = len(proc.connections(kind="tcp"))
            procstat['udp'] = len(proc.connections(kind="udp"))
        except psutil.AccessDenied:
            procstat['tcp'] = None
            procstat['udp'] = None

        return procstat

    def update(self):
        """Update the processes stats."""
        # Reset the stats
        self.processlist = []
        self.reset_processcount()

        # Do not process if disable tag is set
        if self.disable_tag:
            return

        # Time since last update (for disk_io rate computation)
        time_since_update = getTimeSinceLastUpdate('process_disk')

        # Grab the stats
        mandatories_attr = ['cmdline', 'cpu_percent', 'cpu_times',
                            'memory_info', 'memory_percent',
                            'name', 'nice', 'pid',
                            'ppid', 'status', 'username',
                            'status', 'num_threads', 'gids']
        # io_counters availability: Linux, BSD, Windows, AIX
        if LINUX or BSD or WINDOWS:
            mandatories_attr += ['io_counters']

        # and build the processes stats list
        self.processlist = [p.info for p in psutil.process_iter(attrs=mandatories_attr,
                                                                ad_value=None)
                            # OS specifics processes filter
                            if not (BSD and p.info['name'] == 'idle') and
                            not (WINDOWS and p.info['name'] == 'System Idle Process') and
                            not (MACOS and p.info['name'] == 'kernel_task') and
                            # Kernel threads filter
                            not (self.no_kernel_threads and LINUX and p.info['gids'].real == 0) and
                            # User filter
                            not (self._filter.is_filtered(p.info))
                            ]

        # Sort the processes list by the current sort_key
        self.processlist = sorted(self.processlist,
                                  key=lambda p: p[self.sort_key],
                                  reverse=True)

        # Update the processcount
        self.update_processcount(self.processlist)

        # Loop over processes and add metadata
        first = True
        for proc in self.processlist:
            if first and not self.disable_extended_tag:
                # Get extended stats, only for top processes (see issue #403).
                # - cpu_affinity (Linux, Windows, FreeBSD)
                # - ionice (Linux and Windows > Vista)
                # - memory_full_info (Linux)
                # - num_ctx_switches (not available on Illumos/Solaris)
                # - num_fds (Unix-like)
                # - num_handles (Windows)
                # - num_threads (not available on *BSD)
                # - memory_maps (only swap, Linux)
                #   https://www.cyberciti.biz/faq/linux-which-process-is-using-swap/
                # - connections (TCP and UDP)
                extended = {}
                try:
                    top_process = psutil.Process(proc['pid'])
                    extended_stats = ['cpu_affinity', 'ionice',
                                      'memory_full_info', 'num_ctx_switches',
                                      'num_fds', 'num_threads']
                    if WINDOWS:
                        extended_stats += ['num_handles']
                    extended = top_process.as_dict(attrs=extended_stats)
                    # !!! TODO
                    # if LINUX:
                    #     try:
                    #         procstat['memory_swap'] = sum([v.swap for v in proc.memory_maps()])
                    #     except psutil.NoSuchProcess:
                    #         pass
                    #     except (psutil.AccessDenied, TypeError, NotImplementedError):
                    #         # NotImplementedError: /proc/${PID}/smaps file doesn't exist
                    #         # on kernel < 2.6.14 or CONFIG_MMU kernel configuration option
                    #         # is not enabled (see psutil #533/glances #413).
                    #         # XXX: Remove TypeError once we'll drop psutil < 3.0.0.
                    #         procstat['memory_swap'] = None
                    # try:
                    #     procstat['tcp'] = len(proc.connections(kind="tcp"))
                    #     procstat['udp'] = len(proc.connections(kind="udp"))
                    # except psutil.AccessDenied:
                    #     procstat['tcp'] = None
                    #     procstat['udp'] = None
                except (psutil.NoSuchProcess, ValueError, AttributeError) as e:
                    logger.error('Can not grab extended stats ({})'.format(e))
                    extended['extended_stats'] = False
                else:
                    logger.debug('Grab extended stats for process {}'.format(proc['pid']))
                    extended['extended_stats'] = True
                proc.update(extended)
            first = False

            # Time since last update (for disk_io rate computation)
            proc['time_since_update'] = time_since_update

            # Process status (only keep the first char)
            proc['status'] = str(proc['status'])[:1].upper()

            # Process IO
            # procstat['io_counters'] is a list:
            # [read_bytes, write_bytes, read_bytes_old, write_bytes_old, io_tag]
            # If io_tag = 0 > Access denied or first time (display "?")
            # If io_tag = 1 > No access denied (display the IO rate)
            if 'io_counters' in proc and proc['io_counters'] is not None:
                io_new = [proc['io_counters'].read_bytes,
                          proc['io_counters'].write_bytes]
                # For IO rate computation
                # Append saved IO r/w bytes
                try:
                    proc['io_counters'] = io_new + self.io_old[proc['pid']]
                    io_tag = 1
                except KeyError:
                    proc['io_counters'] = io_new + [0, 0]
                    io_tag = 0
                # then save the IO r/w bytes
                self.io_old[proc['pid']] = io_new
            else:
                proc['io_counters'] = [0, 0] + [0, 0]
                io_tag = 0
            # Append the IO tag (for display)
            proc['io_counters'] += [io_tag]

        # Compute the maximum value for keys in self._max_values_list (CPU, MEM)
        for k in self._max_values_list:
            if self.processlist != []:
                self.set_max_values(k, max(i[k] for i in self.processlist))

    def getcount(self):
        """Get the number of processes."""
        return self.processcount

    def getlist(self, sortedby=None):
        """Get the processlist."""
        return self.processlist

    def gettree(self):
        """Get the process tree."""
        return self.process_tree

    @property
    def sort_key(self):
        """Get the current sort key."""
        return self._sort_key

    @sort_key.setter
    def sort_key(self, key):
        """Set the current sort key."""
        self._sort_key = key


# TODO: move this global function (also used in glances_processlist
#       and logs) inside the GlancesProcesses class
def sort_stats(stats, sortedby=None, tree=False, reverse=True):
    """Return the stats (dict) sorted by (sortedby)
    Reverse the sort if reverse is True."""
    if sortedby is None:
        # No need to sort...
        return stats

    if sortedby == 'io_counters' and not tree:
        # Specific case for io_counters
        # Sum of io_r + io_w
        try:
            # Sort process by IO rate (sum IO read + IO write)
            stats.sort(key=lambda process: process[sortedby][0] -
                       process[sortedby][2] + process[sortedby][1] -
                       process[sortedby][3],
                       reverse=reverse)
        except Exception:
            stats.sort(key=operator.itemgetter('cpu_percent'),
                       reverse=reverse)
    else:
        # Others sorts
        if tree:
            stats.set_sorting(sortedby, reverse)
        else:
            try:
                stats.sort(key=operator.itemgetter(sortedby),
                           reverse=reverse)
            except (KeyError, TypeError):
                stats.sort(key=operator.itemgetter('name'),
                           reverse=False)

    return stats


glances_processes = GlancesProcesses()
