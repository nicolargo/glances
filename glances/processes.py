# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2023 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

import os

from glances.globals import BSD, LINUX, MACOS, WINDOWS, iterkeys
from glances.timer import Timer, getTimeSinceLastUpdate
from glances.filter import GlancesFilter
from glances.programs import processes_to_programs
from glances.logger import logger

import psutil

# This constant defines the list of available processes sort key
sort_processes_key_list = ['cpu_percent', 'memory_percent', 'username', 'cpu_times', 'io_counters', 'name']

# Sort dictionary for human
sort_for_human = {
    'io_counters': 'disk IO',
    'cpu_percent': 'CPU consumption',
    'memory_percent': 'memory consumption',
    'cpu_times': 'process time',
    'username': 'user name',
    'name': 'processs name',
    None: 'None',
}


class GlancesProcesses(object):
    """Get processed stats using the psutil library."""

    def __init__(self, cache_timeout=60):
        """Init the class to collect stats about processes."""
        # Init the args, coming from the GlancesStandalone class
        # Should be set by the set_args method
        self.args = None

        # Add internals caches because psutil do not cache all the stats
        # See: https://github.com/giampaolo/psutil/issues/462
        self.username_cache = {}
        self.cmdline_cache = {}

        # The internals caches will be cleaned each 'cache_timeout' seconds
        self.cache_timeout = cache_timeout
        # First iteration, no cache
        self.cache_timer = Timer(0)

        # Init the io_old dict used to compute the IO bitrate
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

        # Cache is a dict with key=pid and value = dict of cached value
        self.processlist_cache = {}

        # Tag to enable/disable the processes stats (to reduce the Glances CPU consumption)
        # Default is to enable the processes stats
        self.disable_tag = False

        # Extended stats for top process is enable by default
        self.disable_extended_tag = False
        self.extended_process = None

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

    def set_args(self, args):
        """Set args."""
        self.args = args

    def reset_processcount(self):
        """Reset the global process count"""
        self.processcount = {'total': 0, 'running': 0, 'sleeping': 0, 'thread': 0, 'pid_max': None}

    def update_processcount(self, plist):
        """Update the global process count from the current processes list"""
        # Update the maximum process ID (pid) number
        self.processcount['pid_max'] = self.pid_max
        # For each key in the processcount dict
        # count the number of processes with the same status
        for k in iterkeys(self.processcount):
            self.processcount[k] = len(list(filter(lambda v: v['status'] is k, plist)))
        # Compute thread
        self.processcount['thread'] = sum(i['num_threads'] for i in plist if i['num_threads'] is not None)
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
        PIDs as on earlier kernels. On 32-bit platforms, 32768 is the maximum
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
    def processes_count(self):
        """Get the current number of processes showed in the UI."""
        return min(self._max_processes - 2, glances_processes.processcount['total'] - 1)

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

    def get_extended_stats(self, proc):
        """Get the extended stats for the given PID."""
        # - cpu_affinity (Linux, Windows, FreeBSD)
        # - ionice (Linux and Windows > Vista)
        # - num_ctx_switches (not available on Illumos/Solaris)
        # - num_fds (Unix-like)
        # - num_handles (Windows)
        # - memory_maps (only swap, Linux)
        #   https://www.cyberciti.biz/faq/linux-which-process-is-using-swap/
        # - connections (TCP and UDP)
        # - CPU min/max/mean

        # Set the extended stats list (OS dependant)
        extended_stats = ['cpu_affinity', 'ionice', 'num_ctx_switches']
        if LINUX:
            # num_fds only available on Unix system (see issue #1351)
            extended_stats += ['num_fds']
        if WINDOWS:
            extended_stats += ['num_handles']

        ret = {}
        try:
            # Get the extended stats
            selected_process = psutil.Process(proc['pid'])
            ret = selected_process.as_dict(attrs=extended_stats, ad_value=None)

            if LINUX:
                try:
                    ret['memory_swap'] = sum([v.swap for v in selected_process.memory_maps()])
                except (psutil.NoSuchProcess, KeyError):
                    # (KeyError catch for issue #1551)
                    pass
                except (psutil.AccessDenied, NotImplementedError):
                    # NotImplementedError: /proc/${PID}/smaps file doesn't exist
                    # on kernel < 2.6.14 or CONFIG_MMU kernel configuration option
                    # is not enabled (see psutil #533/glances #413).
                    ret['memory_swap'] = None
            try:
                ret['tcp'] = len(selected_process.connections(kind="tcp"))
                ret['udp'] = len(selected_process.connections(kind="udp"))
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                # Manage issue1283 (psutil.AccessDenied)
                ret['tcp'] = None
                ret['udp'] = None
        except (psutil.NoSuchProcess, ValueError, AttributeError) as e:
            logger.error('Can not grab extended stats ({})'.format(e))
            self.extended_process = None
            ret['extended_stats'] = False
        else:
            logger.debug('Grab extended stats for process {}'.format(proc['pid']))

            # Compute CPU and MEM min/max/mean
            for stat_prefix in ['cpu', 'memory']:
                if stat_prefix + '_min' not in self.extended_process:
                    ret[stat_prefix + '_min'] = proc[stat_prefix + '_percent']
                else:
                    ret[stat_prefix + '_min'] = (
                        proc[stat_prefix + '_percent']
                        if proc[stat_prefix + '_min'] > proc[stat_prefix + '_percent']
                        else proc[stat_prefix + '_min']
                    )
                if stat_prefix + '_max' not in self.extended_process:
                    ret[stat_prefix + '_max'] = proc[stat_prefix + '_percent']
                else:
                    ret[stat_prefix + '_max'] = (
                        proc[stat_prefix + '_percent']
                        if proc[stat_prefix + '_max'] < proc[stat_prefix + '_percent']
                        else proc[stat_prefix + '_max']
                    )
                if stat_prefix + '_mean_sum' not in self.extended_process:
                    ret[stat_prefix + '_mean_sum'] = proc[stat_prefix + '_percent']
                else:
                    ret[stat_prefix + '_mean_sum'] = proc[stat_prefix + '_mean_sum'] + proc[stat_prefix + '_percent']
                if stat_prefix + '_mean_counter' not in self.extended_process:
                    ret[stat_prefix + '_mean_counter'] = 1
                else:
                    ret[stat_prefix + '_mean_counter'] = proc[stat_prefix + '_mean_counter'] + 1
                ret[stat_prefix + '_mean'] = ret[stat_prefix + '_mean_sum'] / ret[stat_prefix + '_mean_counter']

            ret['extended_stats'] = True
        return ret

    def is_selected_extended_process(self, position):
        """Return True if the process is the selected one for extended stats."""
        return (
            hasattr(self.args, 'programs')
            and not self.args.programs
            and hasattr(self.args, 'enable_process_extended')
            and self.args.enable_process_extended
            and not self.disable_extended_tag
            and hasattr(self.args, 'cursor_position')
            and position == self.args.cursor_position
            and not self.args.disable_cursor
        )

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
        sorted_attrs = ['cpu_percent', 'cpu_times', 'memory_percent', 'name', 'status', 'num_threads']
        displayed_attr = ['memory_info', 'nice', 'pid']
        # 'name' can not be cached because it is used for filtering
        cached_attrs = ['cmdline', 'username']

        # Some stats are optional
        if not self.disable_io_counters:
            sorted_attrs.append('io_counters')
        if not self.disable_gids:
            displayed_attr.append('gids')
        # Some stats are not sort key
        # An optimisation can be done be only grabbed displayed_attr
        # for displayed processes (but only in standalone mode...)
        sorted_attrs.extend(displayed_attr)
        # Some stats are cached (not necessary to be refreshed every time)
        if self.cache_timer.finished():
            sorted_attrs += cached_attrs
            self.cache_timer.set(self.cache_timeout)
            self.cache_timer.reset()
            is_cached = False
        else:
            is_cached = True

        # Build the processes stats list (it is why we need psutil>=5.3.0)
        # This is one of the main bottleneck of Glances (see flame graph)
        # Filter processes
        self.processlist = list(
            filter(
                lambda p: not (BSD and p.info['name'] == 'idle')
                and not (WINDOWS and p.info['name'] == 'System Idle Process')
                and not (MACOS and p.info['name'] == 'kernel_task')
                and not (self.no_kernel_threads and LINUX and p.info['gids'].real == 0),
                psutil.process_iter(attrs=sorted_attrs, ad_value=None),
            )
        )
        # Only get the info key
        self.processlist = [p.info for p in self.processlist]
        # Sort the processes list by the current sort_key
        self.processlist = sort_stats(self.processlist, sorted_by=self.sort_key, reverse=True)

        # Update the processcount
        self.update_processcount(self.processlist)

        # Loop over processes and :
        # - add extended stats for selected process
        # - add metadata
        for position, proc in enumerate(self.processlist):
            # Extended stats
            ################

            # Get the selected process when the 'e' key is pressed
            if self.is_selected_extended_process(position):
                self.extended_process = proc

            # Grab extended stats only for the selected process (see issue #2225)
            if self.extended_process is not None and proc['pid'] == self.extended_process['pid']:
                proc.update(self.get_extended_stats(self.extended_process))
                self.extended_process = proc

            # Meta data
            ###########

            # PID is the key
            proc['key'] = 'pid'

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
                io_new = [proc['io_counters'].read_bytes, proc['io_counters'].write_bytes]
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

            # Manage cached information
            if is_cached:
                # Grab cached values (in case of a new incoming process)
                if proc['pid'] not in self.processlist_cache:
                    try:
                        self.processlist_cache[proc['pid']] = psutil.Process(pid=proc['pid']).as_dict(
                            attrs=cached_attrs, ad_value=None
                        )
                    except psutil.NoSuchProcess:
                        pass
                # Add cached value to current stat
                try:
                    proc.update(self.processlist_cache[proc['pid']])
                except KeyError:
                    pass
            else:
                # Save values to cache
                self.processlist_cache[proc['pid']] = {cached: proc[cached] for cached in cached_attrs}

        # Apply user filter
        self.processlist = list(filter(lambda p: not self._filter.is_filtered(p), self.processlist))

        # Compute the maximum value for keys in self._max_values_list: CPU, MEM
        # Useful to highlight the processes with maximum values
        for k in self._max_values_list:
            values_list = [i[k] for i in self.processlist if i[k] is not None]
            if values_list:
                self.set_max_values(k, max(values_list))

    def get_count(self):
        """Get the number of processes."""
        return self.processcount

    def getlist(self, sorted_by=None, as_programs=False):
        """Get the processlist.
        By default, return the list of threads.
        If as_programs is True, return the list of programs."""
        if as_programs:
            return processes_to_programs(self.processlist)
        else:
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

    def nice_decrease(self, pid):
        """Decrease nice level
        On UNIX this is a number which usually goes from -20 to 20.
        The higher the nice value, the lower the priority of the process."""
        p = psutil.Process(pid)
        try:
            p.nice(p.nice() - 1)
            logger.info('Set nice level of process {} to {} (higher the priority)'.format(pid, p.nice()))
        except psutil.AccessDenied:
            logger.warning(
                'Can not decrease (higher the priority) the nice level of process {} (access denied)'.format(pid)
            )

    def nice_increase(self, pid):
        """Increase nice level
        On UNIX this is a number which usually goes from -20 to 20.
        The higher the nice value, the lower the priority of the process."""
        p = psutil.Process(pid)
        try:
            p.nice(p.nice() + 1)
            logger.info('Set nice level of process {} to {} (lower the priority)'.format(pid, p.nice()))
        except psutil.AccessDenied:
            logger.warning(
                'Can not increase (lower the priority) the nice level of process {} (access denied)'.format(pid)
            )

    def kill(self, pid, timeout=3):
        """Kill process with pid"""
        assert pid != os.getpid(), "Glances can kill itself..."
        p = psutil.Process(pid)
        logger.debug('Send kill signal to process: {}'.format(p))
        p.kill()
        return p.wait(timeout)


def weighted(value):
    """Manage None value in dict value."""
    return -float('inf') if value is None else value


def _sort_io_counters(process, sorted_by='io_counters', sorted_by_secondary='memory_percent'):
    """Specific case for io_counters

    :return: Sum of io_r + io_w
    """
    return process[sorted_by][0] - process[sorted_by][2] + process[sorted_by][1] - process[sorted_by][3]


def _sort_cpu_times(process, sorted_by='cpu_times', sorted_by_secondary='memory_percent'):
    """Specific case for cpu_times

    Patch for "Sorting by process time works not as expected #1321"
    By default PsUtil only takes user time into account
    see (https://github.com/giampaolo/psutil/issues/1339)
    The following implementation takes user and system time into account
    """
    return process[sorted_by][0] + process[sorted_by][1]


def _sort_lambda(sorted_by='cpu_percent', sorted_by_secondary='memory_percent'):
    """Return a sort lambda function for the sorted_by key"""
    ret = None
    if sorted_by == 'io_counters':
        ret = _sort_io_counters
    elif sorted_by == 'cpu_times':
        ret = _sort_cpu_times
    return ret


def sort_stats(stats, sorted_by='cpu_percent', sorted_by_secondary='memory_percent', reverse=True):
    """Return the stats (dict) sorted by (sorted_by).

    Reverse the sort if reverse is True.
    """
    if sorted_by is None and sorted_by_secondary is None:
        # No need to sort...
        return stats

    # Check if a specific sort should be done
    sort_lambda = _sort_lambda(sorted_by=sorted_by, sorted_by_secondary=sorted_by_secondary)

    if sort_lambda is not None:
        # Specific sort
        try:
            stats.sort(key=sort_lambda, reverse=reverse)
        except Exception:
            # If an error is detected, fallback to cpu_percent
            stats.sort(
                key=lambda process: (weighted(process['cpu_percent']), weighted(process[sorted_by_secondary])),
                reverse=reverse,
            )
    else:
        # Standard sort
        try:
            stats.sort(
                key=lambda process: (weighted(process[sorted_by]), weighted(process[sorted_by_secondary])),
                reverse=reverse,
            )
        except (KeyError, TypeError):
            # Fallback to name
            stats.sort(key=lambda process: process['name'] if process['name'] is not None else '~', reverse=False)

    return stats


glances_processes = GlancesProcesses()
