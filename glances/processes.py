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

from glances.compat import iteritems, itervalues, listitems
from glances.globals import BSD, LINUX, MACOS, WINDOWS
from glances.timer import Timer, getTimeSinceLastUpdate
from glances.processes_tree import ProcessTreeNode
from glances.filter import GlancesFilter
from glances.logger import logger

import psutil


def is_kernel_thread(proc):
    """Return True if proc is a kernel thread, False instead."""
    try:
        return os.getpgid(proc.pid) == 0
    # Python >= 3.3 raises ProcessLookupError, which inherits OSError
    except OSError:
        # return False is process is dead
        return False


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
        self.allprocesslist = []
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
        self.processcount = {'total': 0,
                             'running': 0,
                             'sleeping': 0,
                             'thread': 0,
                             'pid_max': None}

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

    def __get_mandatory_stats(self, proc, procstat):
        """
        Get mandatory_stats: for all processes.
        Needed for the sorting/filter step.

        Stats grabbed inside this method:
        * 'name', 'cpu_times', 'status', 'ppid'
        * 'username', 'cpu_percent', 'memory_percent'
        """
        procstat['mandatory_stats'] = True

        # Name, cpu_times, status and ppid stats are in the same /proc file
        # Optimisation fir issue #958
        try:
            procstat.update(proc.as_dict(
                attrs=['name', 'cpu_times', 'status', 'ppid'],
                ad_value=''))
        except psutil.NoSuchProcess:
            # Try/catch for issue #432 (process no longer exist)
            return None
        else:
            procstat['status'] = str(procstat['status'])[:1].upper()

        try:
            procstat.update(proc.as_dict(
                attrs=['username', 'cpu_percent', 'memory_percent'],
                ad_value=''))
        except psutil.NoSuchProcess:
            # Try/catch for issue #432 (process no longer exist)
            return None

        if procstat['cpu_percent'] == '' or procstat['memory_percent'] == '':
            # Do not display process if we cannot get the basic
            # cpu_percent or memory_percent stats
            return None

        # Compute the maximum value for cpu_percent and memory_percent
        for k in self._max_values_list:
            if procstat[k] > self.get_max_values(k):
                self.set_max_values(k, procstat[k])

        # Process command line (cached with internal cache)
        if procstat['pid'] not in self.cmdline_cache:
            # Patch for issue #391
            try:
                self.cmdline_cache[procstat['pid']] = proc.cmdline()
            except (AttributeError, UnicodeDecodeError, psutil.AccessDenied, psutil.NoSuchProcess, psutil.WindowsError):
                self.cmdline_cache[procstat['pid']] = ""
        procstat['cmdline'] = self.cmdline_cache[procstat['pid']]

        # Process IO
        # procstat['io_counters'] is a list:
        # [read_bytes, write_bytes, read_bytes_old, write_bytes_old, io_tag]
        # If io_tag = 0 > Access denied (display "?")
        # If io_tag = 1 > No access denied (display the IO rate)
        # Availability: all platforms except macOS and Illumos/Solaris
        try:
            # Get the process IO counters
            proc_io = proc.io_counters()
            io_new = [proc_io.read_bytes, proc_io.write_bytes]
        except (psutil.AccessDenied, psutil.NoSuchProcess, NotImplementedError):
            # Access denied to process IO (no root account)
            # NoSuchProcess (process die between first and second grab)
            # Put 0 in all values (for sort) and io_tag = 0 (for display)
            procstat['io_counters'] = [0, 0] + [0, 0]
            io_tag = 0
        except AttributeError:
            return procstat
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

    def __get_standard_stats(self, proc, procstat):
        """
        Get standard_stats: only for displayed processes.

        Stats grabbed inside this method:
        * nice and memory_info
        """
        procstat['standard_stats'] = True

        # Process nice and memory_info (issue #926)
        try:
            procstat.update(
                proc.as_dict(attrs=['nice', 'memory_info']))
        except psutil.NoSuchProcess:
            pass

        return procstat

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

    def __get_process_stats(self, proc,
                            mandatory_stats=True,
                            standard_stats=True,
                            extended_stats=False):
        """Get stats of a running processes."""
        # Process ID (always)
        procstat = proc.as_dict(attrs=['pid'])

        if mandatory_stats:
            procstat = self.__get_mandatory_stats(proc, procstat)

        if procstat is not None and standard_stats:
            procstat = self.__get_standard_stats(proc, procstat)

        if procstat is not None and extended_stats and not self.disable_extended_tag:
            procstat = self.__get_extended_stats(proc, procstat)

        return procstat

    def update(self):
        """Update the processes stats."""
        # Reset the stats
        self.processlist = []
        self.reset_processcount()

        # Do not process if disable tag is set
        if self.disable_tag:
            return

        # Get the time since last update
        time_since_update = getTimeSinceLastUpdate('process_disk')

        # Reset the max dict
        self.reset_max_values()

        # Update the maximum process ID (pid) number
        self.processcount['pid_max'] = self.pid_max

        # Build an internal dict with only mandatories stats (sort keys)
        processdict = {}
        excluded_processes = set()
        for proc in psutil.process_iter():
            # Ignore kernel threads if needed
            if self.no_kernel_threads and not WINDOWS and is_kernel_thread(proc):
                continue

            # If self.max_processes is None: Only retrieve mandatory stats
            # Else: retrieve mandatory and standard stats
            s = self.__get_process_stats(proc,
                                         mandatory_stats=True,
                                         standard_stats=self.max_processes is None)
            # Check if s is note None (issue #879)
            # ignore the 'idle' process on Windows and *BSD
            # ignore the 'kernel_task' process on macOS
            # waiting for upstream patch from psutil
            if (s is None or
                    BSD and s['name'] == 'idle' or
                    WINDOWS and s['name'] == 'System Idle Process' or
                    MACOS and s['name'] == 'kernel_task'):
                continue
            # Continue to the next process if it has to be filtered
            if self._filter.is_filtered(s):
                excluded_processes.add(proc)
                continue

            # Ok add the process to the list
            processdict[proc] = s
            # Update processcount (global statistics)
            try:
                self.processcount[str(proc.status())] += 1
            except KeyError:
                # Key did not exist, create it
                try:
                    self.processcount[str(proc.status())] = 1
                except psutil.NoSuchProcess:
                    pass
            except psutil.NoSuchProcess:
                pass
            else:
                self.processcount['total'] += 1
            # Update thread number (global statistics)
            try:
                self.processcount['thread'] += proc.num_threads()
            except Exception:
                pass

        if self._enable_tree:
            self.process_tree = ProcessTreeNode.build_tree(processdict,
                                                           self.sort_key,
                                                           self.sort_reverse,
                                                           self.no_kernel_threads,
                                                           excluded_processes)

            for i, node in enumerate(self.process_tree):
                # Only retreive stats for visible processes (max_processes)
                if self.max_processes is not None and i >= self.max_processes:
                    break

                # add standard stats
                new_stats = self.__get_process_stats(node.process,
                                                     mandatory_stats=False,
                                                     standard_stats=True,
                                                     extended_stats=False)
                if new_stats is not None:
                    node.stats.update(new_stats)

                # Add a specific time_since_update stats for bitrate
                node.stats['time_since_update'] = time_since_update

        else:
            # Process optimization
            # Only retreive stats for visible processes (max_processes)
            if self.max_processes is not None:
                # Sort the internal dict and cut the top N (Return a list of tuple)
                # tuple=key (proc), dict (returned by __get_process_stats)
                try:
                    processiter = sorted(iteritems(processdict),
                                         key=lambda x: x[1][self.sort_key],
                                         reverse=self.sort_reverse)
                except (KeyError, TypeError) as e:
                    logger.error("Cannot sort process list by {}: {}".format(self.sort_key, e))
                    logger.error('{}'.format(listitems(processdict)[0]))
                    # Fallback to all process (issue #423)
                    processloop = iteritems(processdict)
                    first = False
                else:
                    processloop = processiter[0:self.max_processes]
                    first = True
            else:
                # Get all processes stats
                processloop = iteritems(processdict)
                first = False

            for i in processloop:
                # Already existing mandatory stats
                procstat = i[1]
                if self.max_processes is not None:
                    # Update with standard stats
                    # and extended stats but only for TOP (first) process
                    s = self.__get_process_stats(i[0],
                                                 mandatory_stats=False,
                                                 standard_stats=True,
                                                 extended_stats=first)
                    if s is None:
                        continue
                    procstat.update(s)
                # Add a specific time_since_update stats for bitrate
                procstat['time_since_update'] = time_since_update
                # Update process list
                self.processlist.append(procstat)
                # Next...
                first = False

        # Build the all processes list used by the AMPs
        self.allprocesslist = [p for p in itervalues(processdict)]

        # Clean internals caches if timeout is reached
        if self.cache_timer.finished():
            self.username_cache = {}
            self.cmdline_cache = {}
            # Restart the timer
            self.cache_timer.reset()

    def getcount(self):
        """Get the number of processes."""
        return self.processcount

    def getalllist(self):
        """Get the allprocesslist."""
        return self.allprocesslist

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
