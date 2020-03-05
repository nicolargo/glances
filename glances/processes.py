# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2019 Nicolargo <nicolas@nicolargo.com>
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
from glances.globals import BSD, LINUX, MACOS, SUNOS, WINDOWS, WSL
from glances.timer import Timer, getTimeSinceLastUpdate
from glances.filter import GlancesFilter
from glances.logger import logger

import psutil


class GlancesProcesses(object):
    """Get processed stats using the psutil library."""

    def __init__(self, cache_timeout=60):
        """Init the class to collect stats about processes."""
        # Add internals caches because psutil do not cache all the stats
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
        self.auto_sort = None
        self._sort_key = None
        # Default processes sort key is 'auto'
        # Can be overwrite from the configuration file (issue#1536) => See glances_processlist.py init
        self.set_sort_key('auto', auto=True)
        self.processlist = []
        self.reset_processcount()

        # Tag to enable/disable the processes stats (to reduce the Glances CPU consumption)
        # Default is to enable the processes stats
        self.disable_tag = False

        # Extended stats for top process is enable by default
        self.disable_extended_tag = False

        # Test if the system can grab io_counters
        try:
            p = psutil.Process()
            p.io_counters()
        except Exception as e:
            logger.warning('PsUtil can not grab processes io_counters ({})'.format(e))
            self.disable_io_counters = True
        else:
            logger.debug('PsUtil can grab processes io_counters')
            self.disable_io_counters = False

        # Test if the system can grab gids
        try:
            p = psutil.Process()
            p.gids()
        except Exception as e:
            logger.warning('PsUtil can not grab processes gids ({})'.format(e))
            self.disable_gids = True
        else:
            logger.debug('PsUtil can grab processes gids')
            self.disable_gids = False

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
        self.processcount['thread'] = sum(i['num_threads'] for i in plist
                                          if i['num_threads'] is not None)
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

        # Grab standard stats
        #####################
        standard_attrs = ['cmdline', 'cpu_percent', 'cpu_times', 'memory_info',
                          'memory_percent', 'name', 'nice', 'pid', 'ppid',
                          'status', 'username', 'status', 'num_threads']
        if not self.disable_io_counters:
            standard_attrs += ['io_counters']
        if not self.disable_gids:
            standard_attrs += ['gids']

        # and build the processes stats list (psutil>=5.3.0)
        self.processlist = [p.info for p in psutil.process_iter(attrs=standard_attrs,
                                                                ad_value=None)
                            # OS-related processes filter
                            if not (BSD and p.info['name'] == 'idle') and
                            not (WINDOWS and p.info['name'] == 'System Idle Process') and
                            not (MACOS and p.info['name'] == 'kernel_task') and
                            # Kernel threads filter
                            not (self.no_kernel_threads and LINUX and p.info['gids'].real == 0) and
                            # User filter
                            not (self._filter.is_filtered(p.info))]

        # Sort the processes list by the current sort_key
        self.processlist = sort_stats(self.processlist,
                                      sortedby=self.sort_key,
                                      reverse=True)

        # Update the processcount
        self.update_processcount(self.processlist)

        # Loop over processes and add metadata
        first = True
        for proc in self.processlist:
            # Get extended stats, only for top processes (see issue #403).
            if first and not self.disable_extended_tag:
                # - cpu_affinity (Linux, Windows, FreeBSD)
                # - ionice (Linux and Windows > Vista)
                # - num_ctx_switches (not available on Illumos/Solaris)
                # - num_fds (Unix-like)
                # - num_handles (Windows)
                # - memory_maps (only swap, Linux)
                #   https://www.cyberciti.biz/faq/linux-which-process-is-using-swap/
                # - connections (TCP and UDP)
                extended = {}
                try:
                    top_process = psutil.Process(proc['pid'])
                    extended_stats = ['cpu_affinity', 'ionice',
                                      'num_ctx_switches']
                    if LINUX:
                        # num_fds only avalable on Unix system (see issue #1351)
                        extended_stats += ['num_fds']
                    if WINDOWS:
                        extended_stats += ['num_handles']

                    # Get the extended stats
                    extended = top_process.as_dict(attrs=extended_stats,
                                                   ad_value=None)

                    if LINUX:
                        try:
                            extended['memory_swap'] = sum([v.swap for v in top_process.memory_maps()])
                        except (psutil.NoSuchProcess, KeyError):
                            # KeyError catch for issue #1551)
                            pass
                        except (psutil.AccessDenied, NotImplementedError):
                            # NotImplementedError: /proc/${PID}/smaps file doesn't exist
                            # on kernel < 2.6.14 or CONFIG_MMU kernel configuration option
                            # is not enabled (see psutil #533/glances #413).
                            extended['memory_swap'] = None
                    try:
                        extended['tcp'] = len(top_process.connections(kind="tcp"))
                        extended['udp'] = len(top_process.connections(kind="udp"))
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        # Manage issue1283 (psutil.AccessDenied)
                        extended['tcp'] = None
                        extended['udp'] = None
                except (psutil.NoSuchProcess, ValueError, AttributeError) as e:
                    logger.error('Can not grab extended stats ({})'.format(e))
                    extended['extended_stats'] = False
                else:
                    logger.debug('Grab extended stats for process {}'.format(proc['pid']))
                    extended['extended_stats'] = True
                proc.update(extended)
            first = False
            # /End of extended stats

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

        # Compute the maximum value for keys in self._max_values_list: CPU, MEM
        # Usefull to highlight the processes with maximum values
        for k in self._max_values_list:
            values_list = [i[k] for i in self.processlist if i[k] is not None]
            if values_list != []:
                self.set_max_values(k, max(values_list))

    def getcount(self):
        """Get the number of processes."""
        return self.processcount

    def getlist(self, sortedby=None):
        """Get the processlist."""
        return self.processlist

    @property
    def sort_key(self):
        """Get the current sort key."""
        return self._sort_key

    def set_sort_key(self, key, auto=True):
        """Set the current sort key."""
        if key == 'auto':
            self.auto_sort = True
            self._sort_key = 'cpu_percent'
        else:
            self.auto_sort = auto
            self._sort_key = key


def weighted(value):
    """Manage None value in dict value."""
    return -float('inf') if value is None else value


def _sort_io_counters(process,
                      sortedby='io_counters',
                      sortedby_secondary='memory_percent'):
    """Specific case for io_counters
    Sum of io_r + io_w"""
    return process[sortedby][0] - process[sortedby][2] + process[sortedby][1] - process[sortedby][3]


def _sort_cpu_times(process,
                    sortedby='cpu_times',
                    sortedby_secondary='memory_percent'):
    """ Specific case for cpu_times
    Patch for "Sorting by process time works not as expected #1321"
    By default PsUtil only takes user time into account
    see (https://github.com/giampaolo/psutil/issues/1339)
    The following implementation takes user and system time into account"""
    return process[sortedby][0] + process[sortedby][1]


def _sort_lambda(sortedby='cpu_percent',
                 sortedby_secondary='memory_percent'):
    """Return a sort lambda function for the sortedbykey"""
    ret = None
    if sortedby == 'io_counters':
        ret = _sort_io_counters
    elif sortedby == 'cpu_times':
        ret = _sort_cpu_times
    return ret


def sort_stats(stats,
               sortedby='cpu_percent',
               sortedby_secondary='memory_percent',
               reverse=True):
    """Return the stats (dict) sorted by (sortedby).

    Reverse the sort if reverse is True.
    """
    if sortedby is None and sortedby_secondary is None:
        # No need to sort...
        return stats

    # Check if a specific sort should be done
    sort_lambda = _sort_lambda(sortedby=sortedby,
                               sortedby_secondary=sortedby_secondary)

    if sort_lambda is not None:
        # Specific sort
        try:
            stats.sort(key=sort_lambda, reverse=reverse)
        except Exception:
            # If an error is detected, fallback to cpu_percent
            stats.sort(key=lambda process: (weighted(process['cpu_percent']),
                                            weighted(process[sortedby_secondary])),
                       reverse=reverse)
    else:
        # Standard sort
        try:
            stats.sort(key=lambda process: (weighted(process[sortedby]),
                                            weighted(process[sortedby_secondary])),
                       reverse=reverse)
        except (KeyError, TypeError):
            # Fallback to name
            stats.sort(key=lambda process: process['name'] if process['name'] is not None else '~',
                       reverse=False)

    return stats


glances_processes = GlancesProcesses()
