#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

import os

import psutil

from glances.filter import GlancesFilter, GlancesFilterList
from glances.globals import BSD, LINUX, MACOS, WINDOWS, iterkeys, list_of_namedtuple_to_list_of_dict, namedtuple_to_dict
from glances.logger import logger
from glances.programs import processes_to_programs
from glances.timer import Timer, getTimeSinceLastUpdate

psutil_version_info = tuple([int(num) for num in psutil.__version__.split('.')])

# This constant defines the list of mandatory processes stats. Thoses stats can not be disabled by the user
mandatory_processes_stats_list = ['pid', 'name']

# This constant defines the list of available processes sort key
sort_processes_stats_list = ['cpu_percent', 'memory_percent', 'username', 'cpu_times', 'io_counters', 'name']

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


class GlancesProcesses:
    """Get processed stats using the psutil library."""

    def __init__(self, cache_timeout=60):
        """Init the class to collect stats about processes."""
        # Init the args, coming from the classes derived from GlancesMode
        # Should be set by the set_args method
        self.args = None

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

        # List of processes stats to export
        # Only process matching one of the filter will be exported
        self._filter_export = GlancesFilterList()
        self.processlist_export = []

        # Tag to enable/disable the processes stats (to reduce the Glances CPU consumption)
        # Default is to enable the processes stats
        self.disable_tag = False

        # Extended stats for top process is enable by default
        self.disable_extended_tag = False
        self.extended_process = None

        # Tests (and disable if not available) optionals features
        self._test_grab()

        # Maximum number of processes showed in the UI (None if no limit)
        self._max_processes = None

        # Process filter
        self._filter = GlancesFilter()

        # Whether or not to hide kernel threads
        self.no_kernel_threads = False

        # Store maximums values in a dict
        # Used in the UI to highlight the maximum value
        self._max_values_list = ('cpu_percent', 'memory_percent')
        # { 'cpu_percent': 0.0, 'memory_percent': 0.0 }
        self._max_values = {}
        self.reset_max_values()

        # Set the key's list be disabled in order to only display specific attribute in the process list
        self.disable_stats = []

    def _test_grab(self):
        """Test somes optionals features"""
        # Test if the system can grab io_counters
        try:
            p = psutil.Process()
            p.io_counters()
        except Exception as e:
            logger.warning(f'PsUtil can not grab processes io_counters ({e})')
            self.disable_io_counters = True
        else:
            logger.debug('PsUtil can grab processes io_counters')
            self.disable_io_counters = False

        # Test if the system can grab gids
        try:
            p = psutil.Process()
            p.gids()
        except Exception as e:
            logger.warning(f'PsUtil can not grab processes gids ({e})')
            self.disable_gids = True
        else:
            logger.debug('PsUtil can grab processes gids')
            self.disable_gids = False

    def set_args(self, args):
        """Set args."""
        self.args = args

    def reset_internal_cache(self):
        """Reset the internal cache."""
        self.cache_timer = Timer(0)
        self.processlist_cache = {}
        if hasattr(psutil.process_iter, 'cache_clear'):
            # Cache clear only available in PsUtil 6 or higher
            psutil.process_iter.cache_clear()

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
            self.processcount[k] = len(list(filter(lambda v: v.get('status', '?') is k, plist)))
        # Compute thread
        try:
            self.processcount['thread'] = sum(i['num_threads'] for i in plist if i['num_threads'] is not None)
        except KeyError:
            self.processcount['thread'] = None
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
            except OSError:
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
    def disable_stats(self):
        """Set disable_stats list"""
        return self._disable_stats

    @disable_stats.setter
    def disable_stats(self, stats_list):
        """Set disable_stats list"""
        self._disable_stats = [i for i in stats_list if i not in mandatory_processes_stats_list]

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

    # Export filter

    @property
    def export_process_filter(self):
        """Get the export process filter (current export process filter list)."""
        return self._filter_export.filter

    @export_process_filter.setter
    def export_process_filter(self, value):
        """Set the export process filter list."""
        self._filter_export.filter = value

    # Kernel threads

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

        # Set the extended stats list (OS dependent)
        extended_stats = ['cpu_affinity', 'ionice', 'num_ctx_switches']
        if LINUX:
            # num_fds only available on Unix system (see issue #1351)
            extended_stats += ['num_fds']
        if WINDOWS:
            extended_stats += ['num_handles']

        ret = {}
        try:
            logger.debug('Grab extended stats for process {}'.format(proc['pid']))

            # Get PID of the selected process
            selected_process = psutil.Process(proc['pid'])

            # Get the extended stats for the selected process
            ret = selected_process.as_dict(attrs=extended_stats, ad_value=None)

            # Get memory swap for the selected process (Linux Only)
            ret['memory_swap'] = self.__get_extended_memory_swap(selected_process)

            # Get number of TCP and UDP network connections for the selected process
            ret['tcp'], ret['udp'] = self.__get_extended_connections(selected_process)
        except (psutil.NoSuchProcess, ValueError, AttributeError) as e:
            logger.error(f'Can not grab extended stats ({e})')
            self.extended_process = None
            ret['extended_stats'] = False
        else:
            # Compute CPU and MEM min/max/mean
            # Merge the returned dict with the current on
            ret.update(self.__get_min_max_mean(proc))
            self.extended_process = ret
            ret['extended_stats'] = True
        return namedtuple_to_dict(ret)

    def __get_min_max_mean(self, proc, prefix=['cpu', 'memory']):
        """Return the min/max/mean for the given process"""
        ret = {}
        for stat_prefix in prefix:
            min_key = stat_prefix + '_min'
            max_key = stat_prefix + '_max'
            mean_sum_key = stat_prefix + '_mean_sum'
            mean_counter_key = stat_prefix + '_mean_counter'
            if min_key not in self.extended_process:
                ret[min_key] = proc[stat_prefix + '_percent']
            else:
                ret[min_key] = min(proc[stat_prefix + '_percent'], self.extended_process[min_key])
            if max_key not in self.extended_process:
                ret[max_key] = proc[stat_prefix + '_percent']
            else:
                ret[max_key] = max(proc[stat_prefix + '_percent'], self.extended_process[max_key])
            if mean_sum_key not in self.extended_process:
                ret[mean_sum_key] = proc[stat_prefix + '_percent']
            else:
                ret[mean_sum_key] = self.extended_process[mean_sum_key] + proc[stat_prefix + '_percent']
            if mean_counter_key not in self.extended_process:
                ret[mean_counter_key] = 1
            else:
                ret[mean_counter_key] = self.extended_process[mean_counter_key] + 1
            ret[stat_prefix + '_mean'] = ret[mean_sum_key] / ret[mean_counter_key]
        return ret

    def __get_extended_memory_swap(self, process):
        """Return the memory swap for the given process"""
        if not LINUX:
            return None
        try:
            memory_swap = sum([v.swap for v in process.memory_maps()])
        except (psutil.NoSuchProcess, KeyError):
            # (KeyError catch for issue #1551)
            pass
        except (psutil.AccessDenied, NotImplementedError):
            # NotImplementedError: /proc/${PID}/smaps file doesn't exist
            # on kernel < 2.6.14 or CONFIG_MMU kernel configuration option
            # is not enabled (see psutil #533/glances #413).
            memory_swap = None
        return memory_swap

    def __get_extended_connections(self, process):
        """Return a tuple with (tcp, udp) connections count
        The code is compliant with both PsUtil<6 and Psutil>=6
        """
        try:
            # Hack for issue #2754 (PsUtil 6+)
            if psutil_version_info[0] >= 6:
                tcp = len(process.net_connections(kind="tcp"))
                udp = len(process.net_connections(kind="udp"))
            else:
                tcp = len(process.connections(kind="tcp"))
                udp = len(process.connections(kind="udp"))
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            # Manage issue1283 (psutil.AccessDenied)
            tcp = None
            udp = None
        return tcp, udp

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

    def build_process_list(self, sorted_attrs):
        # Build the processes stats list (it is why we need psutil>=5.3.0) (see issue #2755)
        processlist = list(
            filter(
                lambda p: not (BSD and p.info['name'] == 'idle')
                and not (WINDOWS and p.info['name'] == 'System Idle Process')
                and not (MACOS and p.info['name'] == 'kernel_task')
                and not (self.no_kernel_threads and LINUX and p.info['gids'].real == 0),
                psutil.process_iter(attrs=sorted_attrs, ad_value=None),
            )
        )

        # Only get the info key
        # PsUtil 6+ no longer check PID reused #2755 so use is_running in the loop
        # Note: not sure it is realy needed but CPU consumption look the same with or without it
        processlist = [p.info for p in processlist if p.is_running()]

        # Sort the processes list by the current sort_key
        return sort_stats(processlist, sorted_by=self.sort_key, reverse=True)

    def get_sorted_attrs(self):
        defaults = ['cpu_percent', 'cpu_times', 'memory_percent', 'name', 'status', 'num_threads']
        optional = ['io_counters'] if not self.disable_io_counters else []

        return defaults + optional

    def get_displayed_attr(self):
        defaults = ['memory_info', 'nice', 'pid']
        optional = ['gids'] if not self.disable_gids else []

        return defaults + optional

    def get_cached_attrs(self):
        return ['cmdline', 'username']

    def maybe_add_cached_attrs(self, sorted_attrs, cached_attrs):
        # Some stats are not sort key
        # An optimisation can be done be only grabbed displayed_attr
        # for displayed processes (but only in standalone mode...)
        sorted_attrs.extend(self.get_displayed_attr())
        # Some stats are cached (not necessary to be refreshed every time)
        if self.cache_timer.finished():
            sorted_attrs += cached_attrs
            self.cache_timer.set(self.cache_timeout)
            self.cache_timer.reset()
            is_cached = False
        else:
            is_cached = True

        return is_cached, sorted_attrs

    def get_pid_time_and_status(self, time_since_update, proc):
        # PID is the key
        proc['key'] = 'pid'

        # Time since last update (for disk_io rate computation)
        proc['time_since_update'] = time_since_update

        # Process status (only keep the first char)
        proc['status'] = str(proc.get('status', '?'))[:1].upper()

        return proc

    def get_io_counters(self, proc):
        # procstat['io_counters'] is a list:
        # [read_bytes, write_bytes, read_bytes_old, write_bytes_old, io_tag]
        # If io_tag = 0 > Access denied or first time (display "?")
        # If io_tag = 1 > No access denied (display the IO rate)
        if 'io_counters' in proc and proc['io_counters'] is not None:
            io_new = [proc['io_counters'][2], proc['io_counters'][3]]
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

        return proc

    def maybe_add_cached_stats(self, is_cached, cached_attrs, proc):
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
            try:
                self.processlist_cache[proc['pid']] = {cached: proc[cached] for cached in cached_attrs}
            except KeyError:
                pass

        return proc

    def update(self):
        """Update the processes stats."""
        # Init new processes stats
        processlist = []

        # Do not process if disable tag is set
        if self.disable_tag:
            return processlist

        # Time since last update (for disk_io rate computation)
        time_since_update = getTimeSinceLastUpdate('process_disk')

        # Grab standard stats
        #####################
        sorted_attrs = self.get_sorted_attrs()

        # The following attributes are cached and only retrieve every self.cache_timeout seconds
        # Warning: 'name' can not be cached because it is used for filtering
        cached_attrs = self.get_cached_attrs()

        is_cached, sorted_attrs = self.maybe_add_cached_attrs(sorted_attrs, cached_attrs)

        # Remove attributes set by the user in the config file (see #1524)
        sorted_attrs = [i for i in sorted_attrs if i not in self.disable_stats]
        processlist = self.build_process_list(sorted_attrs)

        # Update the processcount
        self.update_processcount(processlist)

        # Loop over processes and :
        # - add extended stats for selected process
        # - add metadata
        for position, proc in enumerate(processlist):
            # Extended stats
            ################

            # Get the selected process when the 'e' key is pressed
            if self.is_selected_extended_process(position):
                self.extended_process = proc

            # Grab extended stats only for the selected process (see issue #2225)
            if self.extended_process is not None and proc['pid'] == self.extended_process['pid']:
                proc.update(self.get_extended_stats(self.extended_process))
                self.extended_process = namedtuple_to_dict(proc)

            # Meta data
            ###########
            proc = self.get_pid_time_and_status(time_since_update, proc)

            # Process IO
            proc = self.get_io_counters(proc)

            # Manage cached information
            proc = self.maybe_add_cached_stats(is_cached, cached_attrs, proc)

        # Remove non running process from the cache (avoid issue #2976)
        self.remove_non_running_procs(processlist)

        # Filter and transform process export list
        self.processlist_export = self.update_export_list(processlist)

        # Filter and transform process list
        processlist = self.update_list(processlist)

        # Compute the maximum value for keys in self._max_values_list: CPU, MEM
        # Useful to highlight the processes with maximum values
        self.compute_max_value(processlist)

        # Update the stats
        self.processlist = processlist

        return self.processlist

    def compute_max_value(self, processlist):
        for k in [i for i in self._max_values_list if i not in self.disable_stats]:
            values_list = [i[k] for i in processlist if i[k] is not None]
            if values_list:
                self.set_max_values(k, max(values_list))

    def remove_non_running_procs(self, processlist):
        pids_running = [p['pid'] for p in processlist]
        pids_cached = list(self.processlist_cache.keys()).copy()
        for pid in pids_cached:
            if pid not in pids_running:
                self.processlist_cache.pop(pid, None)

    def update_list(self, processlist):
        """Return the process list after filtering and transformation (namedtuple to dict)."""
        if self._filter.filter is None:
            return list_of_namedtuple_to_list_of_dict(processlist)
        ret = list(filter(lambda p: self._filter.is_filtered(p), processlist))
        return list_of_namedtuple_to_list_of_dict(ret)

    def update_export_list(self, processlist):
        """Return the process export list after filtering and transformation (namedtuple to dict)."""
        if self._filter_export.filter == []:
            return []
        ret = list(filter(lambda p: self._filter_export.is_filtered(p), processlist))
        return list_of_namedtuple_to_list_of_dict(ret)

    def get_count(self):
        """Get the number of processes."""
        return self.processcount

    def get_list(self, sorted_by=None, as_programs=False):
        """Get the processlist.
        By default, return the list of threads.
        If as_programs is True, return the list of programs."""
        if as_programs:
            return processes_to_programs(self.processlist)
        return self.processlist

    def get_export(self):
        """Return the processlist for export."""
        return self.processlist_export

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
            logger.info(f'Set nice level of process {pid} to {p.nice()} (higher the priority)')
        except psutil.AccessDenied:
            logger.warning(f'Can not decrease (higher the priority) the nice level of process {pid} (access denied)')

    def nice_increase(self, pid):
        """Increase nice level
        On UNIX this is a number which usually goes from -20 to 20.
        The higher the nice value, the lower the priority of the process."""
        p = psutil.Process(pid)
        try:
            p.nice(p.nice() + 1)
            logger.info(f'Set nice level of process {pid} to {p.nice()} (lower the priority)')
        except psutil.AccessDenied:
            logger.warning(f'Can not increase (lower the priority) the nice level of process {pid} (access denied)')

    def kill(self, pid, timeout=3):
        """Kill process with pid"""
        assert pid != os.getpid(), "Glances can kill itself..."
        p = psutil.Process(pid)
        logger.debug(f'Send kill signal to process: {p}')
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
    A secondary sort key should be specified.

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
