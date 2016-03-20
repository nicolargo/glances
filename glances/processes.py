# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2016 Nicolargo <nicolas@nicolargo.com>
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

import os
import re

from glances.compat import iteritems, itervalues, listitems
from glances.globals import BSD, LINUX, OSX, WINDOWS
from glances.logger import logger
from glances.timer import Timer, getTimeSinceLastUpdate
from glances.processes_tree import ProcessTreeNode

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
        self.processcount = {'total': 0, 'running': 0, 'sleeping': 0, 'thread': 0}

        # Tag to enable/disable the processes stats (to reduce the Glances CPU consumption)
        # Default is to enable the processes stats
        self.disable_tag = False

        # Extended stats for top process is enable by default
        self.disable_extended_tag = False

        # Maximum number of processes showed in the UI (None if no limit)
        self._max_processes = None

        # Process filter is a regular expression
        self._process_filter = None
        self._process_filter_re = None

        # Whether or not to hide kernel threads
        self.no_kernel_threads = False

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
    def max_processes(self):
        """Get the maximum number of processes showed in the UI."""
        return self._max_processes

    @max_processes.setter
    def max_processes(self, value):
        """Set the maximum number of processes showed in the UI."""
        self._max_processes = value

    @property
    def process_filter(self):
        """Get the process filter."""
        return self._process_filter

    @process_filter.setter
    def process_filter(self, value):
        """Set the process filter."""
        logger.info("Set process filter to {0}".format(value))
        self._process_filter = value
        if value is not None:
            try:
                self._process_filter_re = re.compile(value)
                logger.debug("Process filter regex compilation OK: {0}".format(self.process_filter))
            except Exception:
                logger.error("Cannot compile process filter regex: {0}".format(value))
                self._process_filter_re = None
        else:
            self._process_filter_re = None

    @property
    def process_filter_re(self):
        """Get the process regular expression compiled."""
        return self._process_filter_re

    def is_filtered(self, value):
        """Return True if the value should be filtered."""
        if self.process_filter is None:
            # No filter => Not filtered
            return False
        else:
            try:
                return self.process_filter_re.match(' '.join(value)) is None
            except AttributeError:
                #  Filter processes crashs with a bad regular expression pattern (issue #665)
                return False

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

    def __get_mandatory_stats(self, proc, procstat):
        """
        Get mandatory_stats: need for the sorting/filter step.

        => cpu_percent, memory_percent, io_counters, name, cmdline
        """
        procstat['mandatory_stats'] = True

        # Process CPU, MEM percent and name
        try:
            procstat.update(proc.as_dict(
                attrs=['username', 'cpu_percent', 'memory_percent',
                       'name', 'cpu_times'], ad_value=''))
        except psutil.NoSuchProcess:
            # Try/catch for issue #432
            return None
        if procstat['cpu_percent'] == '' or procstat['memory_percent'] == '':
            # Do not display process if we cannot get the basic
            # cpu_percent or memory_percent stats
            return None

        # Process command line (cached with internal cache)
        try:
            self.cmdline_cache[procstat['pid']]
        except KeyError:
            # Patch for issue #391
            try:
                self.cmdline_cache[procstat['pid']] = proc.cmdline()
            except (AttributeError, UnicodeDecodeError, psutil.AccessDenied, psutil.NoSuchProcess):
                self.cmdline_cache[procstat['pid']] = ""
        procstat['cmdline'] = self.cmdline_cache[procstat['pid']]

        # Process IO
        # procstat['io_counters'] is a list:
        # [read_bytes, write_bytes, read_bytes_old, write_bytes_old, io_tag]
        # If io_tag = 0 > Access denied (display "?")
        # If io_tag = 1 > No access denied (display the IO rate)
        # Note Disk IO stat not available on Mac OS
        if not OSX:
            try:
                # Get the process IO counters
                proc_io = proc.io_counters()
                io_new = [proc_io.read_bytes, proc_io.write_bytes]
            except (psutil.AccessDenied, psutil.NoSuchProcess, NotImplementedError):
                # Access denied to process IO (no root account)
                # NoSuchProcess (process die between first and second grab)
                # Put 0 in all values (for sort) and io_tag = 0 (for
                # display)
                procstat['io_counters'] = [0, 0] + [0, 0]
                io_tag = 0
            else:
                # For IO rate computation
                # Append saved IO r/w bytes
                try:
                    procstat['io_counters'] = io_new + \
                        self.io_old[procstat['pid']]
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
        Get standard_stats: for all the displayed processes.

        => username, status, memory_info, cpu_times
        """
        procstat['standard_stats'] = True

        # Process username (cached with internal cache)
        try:
            self.username_cache[procstat['pid']]
        except KeyError:
            try:
                self.username_cache[procstat['pid']] = proc.username()
            except psutil.NoSuchProcess:
                self.username_cache[procstat['pid']] = "?"
            except (KeyError, psutil.AccessDenied):
                try:
                    self.username_cache[procstat['pid']] = proc.uids().real
                except (KeyError, AttributeError, psutil.AccessDenied):
                    self.username_cache[procstat['pid']] = "?"
        procstat['username'] = self.username_cache[procstat['pid']]

        # Process status, nice, memory_info and cpu_times
        try:
            procstat.update(
                proc.as_dict(attrs=['status', 'nice', 'memory_info', 'cpu_times']))
        except psutil.NoSuchProcess:
            pass
        else:
            procstat['status'] = str(procstat['status'])[:1].upper()

        return procstat

    def __get_extended_stats(self, proc, procstat):
        """
        Get extended_stats: only for top processes (see issue #403).

        => connections (UDP/TCP), memory_swap...
        """
        procstat['extended_stats'] = True

        # CPU affinity (Windows and Linux only)
        try:
            procstat.update(proc.as_dict(attrs=['cpu_affinity']))
        except psutil.NoSuchProcess:
            pass
        except AttributeError:
            procstat['cpu_affinity'] = None
        # Memory extended
        try:
            procstat.update(proc.as_dict(attrs=['memory_info_ex']))
        except psutil.NoSuchProcess:
            pass
        except AttributeError:
            procstat['memory_info_ex'] = None
        # Number of context switch
        try:
            procstat.update(proc.as_dict(attrs=['num_ctx_switches']))
        except psutil.NoSuchProcess:
            pass
        except AttributeError:
            procstat['num_ctx_switches'] = None
        # Number of file descriptors (Unix only)
        try:
            procstat.update(proc.as_dict(attrs=['num_fds']))
        except psutil.NoSuchProcess:
            pass
        except AttributeError:
            procstat['num_fds'] = None
        # Threads number
        try:
            procstat.update(proc.as_dict(attrs=['num_threads']))
        except psutil.NoSuchProcess:
            pass
        except AttributeError:
            procstat['num_threads'] = None

        # Number of handles (Windows only)
        if WINDOWS:
            try:
                procstat.update(proc.as_dict(attrs=['num_handles']))
            except psutil.NoSuchProcess:
                pass
        else:
            procstat['num_handles'] = None

        # SWAP memory (Only on Linux based OS)
        # http://www.cyberciti.biz/faq/linux-which-process-is-using-swap/
        if LINUX:
            try:
                procstat['memory_swap'] = sum(
                    [v.swap for v in proc.memory_maps()])
            except psutil.NoSuchProcess:
                pass
            except psutil.AccessDenied:
                procstat['memory_swap'] = None
            except Exception:
                # Add a dirty except to handle the PsUtil issue #413
                procstat['memory_swap'] = None

        # Process network connections (TCP and UDP)
        try:
            procstat['tcp'] = len(proc.connections(kind="tcp"))
            procstat['udp'] = len(proc.connections(kind="udp"))
        except Exception:
            procstat['tcp'] = None
            procstat['udp'] = None

        # IO Nice
        # http://pythonhosted.org/psutil/#psutil.Process.ionice
        if LINUX or WINDOWS:
            try:
                procstat.update(proc.as_dict(attrs=['ionice']))
            except psutil.NoSuchProcess:
                pass
        else:
            procstat['ionice'] = None

        return procstat

    def __get_process_stats(self, proc,
                            mandatory_stats=True,
                            standard_stats=True,
                            extended_stats=False):
        """Get stats of running processes."""
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
        self.processcount = {'total': 0, 'running': 0, 'sleeping': 0, 'thread': 0}

        # Do not process if disable tag is set
        if self.disable_tag:
            return

        # Get the time since last update
        time_since_update = getTimeSinceLastUpdate('process_disk')

        # Build an internal dict with only mandatories stats (sort keys)
        processdict = {}
        excluded_processes = set()
        for proc in psutil.process_iter():
            # Ignore kernel threads if needed
            if self.no_kernel_threads and not WINDOWS and is_kernel_thread(proc):
                continue

            # If self.max_processes is None: Only retreive mandatory stats
            # Else: retreive mandatory and standard stats
            s = self.__get_process_stats(proc,
                                         mandatory_stats=True,
                                         standard_stats=self.max_processes is None)
            # Continue to the next process if it has to be filtered
            if s is None or (self.is_filtered(s['cmdline']) and self.is_filtered(s['name'])):
                excluded_processes.add(proc)
                continue
            # Ok add the process to the list
            processdict[proc] = s
            # ignore the 'idle' process on Windows and *BSD
            # ignore the 'kernel_task' process on OS X
            # waiting for upstream patch from psutil
            if (BSD and processdict[proc]['name'] == 'idle' or
                    WINDOWS and processdict[proc]['name'] == 'System Idle Process' or
                    OSX and processdict[proc]['name'] == 'kernel_task'):
                continue
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
                    logger.error("Cannot sort process list by {0}: {1}".format(self.sort_key, e))
                    logger.error('{0}'.format(listitems(processdict)[0]))
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

        # Build the all processes list used by the monitored list
        self.allprocesslist = itervalues(processdict)

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

glances_processes = GlancesProcesses()
