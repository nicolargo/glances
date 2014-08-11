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

from glances.core.glances_globals import is_linux, is_bsd, is_mac, is_windows, logger
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
        self.resetsort()
        self.processlist = []
        self.processcount = {'total': 0, 'running': 0, 'sleeping': 0, 'thread': 0}

        # Tag to enable/disable the processes stats (to reduce the Glances CPU comsumption)
        # Default is to enable the processes stats
        self.disable_tag = False

        # Maximum number of processes showed in the UI interface
        # None if no limit
        self.max_processes = None

    def enable(self):
        """Enable process stats."""
        self.disable_tag = False
        self.update()

    def disable(self):
        """Disable process stats."""
        self.disable_tag = True

    def set_max_processes(self, value):
        """Set the maximum number of processes showed in the UI interfaces"""
        self.max_processes = value
        return self.max_processes

    def get_max_processes(self):
        """Get the maximum number of processes showed in the UI interfaces"""
        return self.max_processes

    def __get_process_stats(self, proc,
                            mandatory_stats=True,
                            standard_stats=True, 
                            extended_stats=False):
        """
        Get process stats of the proc processes (proc is returned psutil.process_iter())
        mandatory_stats: need for the sorting step  
        => cpu_percent, memory_percent, io_counters, name
        standard_stats: for all the displayed processes
        => username, cmdline, status, memory_info, cpu_times
        extended_stats: only for top processes (see issue #403)
        => connections (UDP/TCP), memory_swap...
        """

        # Process ID (always)
        procstat = proc.as_dict(attrs=['pid'])

        if mandatory_stats:
            procstat['mandatory_stats'] = True 

            # Process CPU, MEM percent and name
            procstat.update(proc.as_dict(attrs=['cpu_percent', 'memory_percent', 'name'], ad_value=''))

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

        if standard_stats:
            procstat['standard_stats'] = True 

            # Process username (cached with internal cache)
            try:
                self.username_cache[procstat['pid']]
            except KeyError:
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
            except KeyError:
                # Patch for issue #391
                try:
                    self.cmdline_cache[procstat['pid']] = ' '.join(proc.cmdline())
                except (AttributeError, psutil.AccessDenied, UnicodeDecodeError):
                    self.cmdline_cache[procstat['pid']] = ""
            procstat['cmdline'] = self.cmdline_cache[procstat['pid']]

            # Process status, nice, memory_info and cpu_times
            procstat.update(proc.as_dict(attrs=['status', 'nice', 'memory_info', 'cpu_times']))
            procstat['status'] = str(procstat['status'])[:1].upper()

        if extended_stats:
            procstat['extended_stats'] = True 

            # CPU affinity
            # Memory extended
            # Number of context switch
            # Number of file descriptors (Unix only)
            # Threads number
            procstat.update(proc.as_dict(attrs=['cpu_affinity', 
                                                'memory_info_ex',
                                                'num_ctx_switches',
                                                'num_fds',
                                                'num_threads']))

            # Number of handles (Windows only)
            if is_windows:
                procstat.update(proc.as_dict(attrs=['num_handles']))

            # SWAP memory (Only on Linux based OS)
            # http://www.cyberciti.biz/faq/linux-which-process-is-using-swap/
            if is_linux:
                try:
                    procstat['memory_swap'] = sum([v.swap for v in proc.memory_maps()])
                except psutil.AccessDenied:
                    procstat['memory_swap'] = None

            # Process network connections (TCP and UDP)
            try:
                procstat['tcp'] = len(proc.connections(kind="tcp"))
                procstat['udp'] = len(proc.connections(kind="udp"))
            except:
                procstat['tcp'] = None
                procstat['udp'] = None

            # IO Nice
            # http://pythonhosted.org/psutil/#psutil.Process.ionice
            if is_linux or is_windows:
                procstat.update(proc.as_dict(attrs=['ionice']))

            # !!! Only for dev
            logger.debug("EXTENDED STATS: %s" % procstat)

        return procstat

    def update(self):
        """
        Update the processes stats
        """
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
        for proc in psutil.process_iter():
            # If self.get_max_processes() is None: Only retreive mandatory stats
            # Else: retreive mandatoryadn standard stast
            processdict[proc] = self.__get_process_stats(proc, 
                                                         mandatory_stats=True, 
                                                         standard_stats=self.get_max_processes() is None)
            # ignore the 'idle' process on Windows and *BSD
            # ignore the 'kernel_task' process on OS X
            # waiting for upstream patch from psutil
            if (is_bsd and processdict[proc]['name'] == 'idle' or
                is_windows and processdict[proc]['name'] == 'System Idle Process' or
                is_mac and processdict[proc]['name'] == 'kernel_task'):
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

        if self.get_max_processes() is not None:
            # Sort the internal dict and cut the top N (Return a list of tuple)
            # tuple=key (proc), dict (returned by __get_process_stats)
            processiter = sorted(processdict.items(), key=lambda x: x[1][self.getsortkey()], reverse=True)
            first = True
            for i in processiter[0:self.get_max_processes()]:
                # Already existing mandatory stats
                procstat = i[1]
                # Update with standard stats
                # and extended stats but only for TOP (first) process
                procstat.update(self.__get_process_stats(i[0], 
                                                         mandatory_stats=False, 
                                                         standard_stats=True,
                                                         extended_stats=first))
                # Add a specific time_since_update stats for bitrate
                procstat['time_since_update'] = time_since_update
                # Update process list
                self.processlist.append(procstat)
                # Next...
                first = False
        else:
            # Get all the processes
            for i in processdict.items():
                # Already existing mandatory and standard stats
                procstat = i[1]
                # Add a specific time_since_update stats for bitrate
                procstat['time_since_update'] = time_since_update
                # Update process list
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
        """Get the current sort key"""
        if self.getmanualsortkey() is not None:
            return self.getmanualsortkey()
        else:
            return self.getautosortkey()

    def getmanualsortkey(self):
        """Get the current sort key for manual sort."""
        return self.processmanualsort

    def getautosortkey(self):
        """Get the current sort key for automatic sort."""
        return self.processautosort

    def setmanualsortkey(self, sortedby):
        """Set the current sort key for manual sort."""
        self.processmanualsort = sortedby
        return self.processmanualsort

    def setautosortkey(self, sortedby):
        """Set the current sort key for automatic sort."""
        self.processautosort = sortedby
        return self.processautosort

    def resetsort(self):
        """Set the default sort: Auto"""
        self.setmanualsortkey(None)
        self.setautosortkey('cpu_percent')

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
