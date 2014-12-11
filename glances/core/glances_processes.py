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

# Import Python lib
import collections
import operator
import re

# Import psutil
import psutil

# Import Glances lib
from glances.core.glances_globals import is_bsd, is_linux, is_mac, is_windows, logger
from glances.core.glances_timer import getTimeSinceLastUpdate, Timer


class ProcessTreeNode(object):

    """
    Represent a process tree.

    We avoid recursive algorithm to manipulate the tree because function calls are expensive with CPython.
    """

    def __init__(self, process=None, stats=None, sort_key=None, root=False):
        self.process = process
        self.stats = stats
        self.children = []
        self.children_sorted = False
        self.sort_key = sort_key
        self.reverse_sorting = (self.sort_key != "name")
        self.is_root = root

    def __str__(self):
        """ Return the tree as a string for debugging. """
        lines = []
        nodes_to_print = collections.deque([collections.deque([("#", self)])])
        while nodes_to_print:
            indent_str, current_node = nodes_to_print[-1].pop()
            if not nodes_to_print[-1]:
                nodes_to_print.pop()
            if current_node.is_root:
                lines.append(indent_str)
            else:
                lines.append("%s[%s]" % (indent_str, current_node.process.name()))
            indent_str = " " * (len(lines[-1]) - 1)
            children_nodes_to_print = collections.deque()
            for child in current_node.children:
                if child is current_node.children[-1]:
                    tree_char = "└─"
                else:
                    tree_char = "├─"
                children_nodes_to_print.appendleft((indent_str + tree_char, child))
            if children_nodes_to_print:
                nodes_to_print.append(children_nodes_to_print)
        return "\n".join(lines)

    def set_sorting(self, key, reverse):
        """ Set sorting key or func for user with __iter__ (affects the whole tree from this node). """
        if (self.sort_key != key) or (self.reverse_sorting != reverse):
            nodes_to_flag_unsorted = collections.deque([self])
            while nodes_to_flag_unsorted:
                current_node = nodes_to_flag_unsorted.pop()
                current_node.children_sorted = False
                current_node.sort_key = key
                current_node.reverse_sorting = reverse
                nodes_to_flag_unsorted.extend(current_node.children)

    def get_weight(self):
        """ Return "weight" of a process and all its children for sorting. """
        if self.sort_key == "name":
            return self.stats[self.sort_key]

        # sum ressource usage for self and children
        total = 0
        nodes_to_sum = collections.deque([self])
        while nodes_to_sum:
            current_node = nodes_to_sum.pop()
            if callable(self.sort_key):
                total += self.sort_key(current_node.stats)
            elif self.sort_key == "io_counters":
                stats = current_node.stats[self.sort_key]
                total += stats[0] - stats[2] + stats[1] - stats[3]
            elif self.sort_key == "cpu_times":
                total += sum(current_node.stats[self.sort_key])
            else:
                total += current_node.stats[self.sort_key]
            nodes_to_sum.extend(current_node.children)

        return total

    def __len__(self):
        """Return the number of nodes in the tree."""
        total = 0
        nodes_to_sum = collections.deque([self])
        while nodes_to_sum:
            current_node = nodes_to_sum.pop()
            if not current_node.is_root:
                total += 1
            nodes_to_sum.extend(current_node.children)
        return total

    def __iter__(self):
        """ Iterator returning ProcessTreeNode in sorted order, recursively. """
        if not self.is_root:
            yield self
        if not self.children_sorted:
            # optimization to avoid sorting twice (once when limiting the maximum processes to grab stats for,
            # and once before displaying)
            self.children.sort(key=self.__class__.get_weight, reverse=self.reverse_sorting)
            self.children_sorted = True
        for child in self.children:
            for n in iter(child):
                yield n

    def iter_children(self, exclude_incomplete_stats=True):
        """
        Iterator returning ProcessTreeNode in sorted order (only children of this node, non recursive).

        If exclude_incomplete_stats is True, exclude processes not having full statistics.
        It can happen after a resort (change of sort key) because process stats are not grabbed immediately,
        but only at next full update.
        """
        if not self.children_sorted:
            # optimization to avoid sorting twice (once when limiting the maximum processes to grab stats for,
            # and once before displaying)
            self.children.sort(key=self.__class__.get_weight, reverse=self.reverse_sorting)
            self.children_sorted = True
        for child in self.children:
            if (not exclude_incomplete_stats) or ("time_since_update" in child.stats):
                yield child

    def find_process(self, process):
        """ Search in tree for the ProcessTreeNode owning process, return it or None if not found. """
        nodes_to_search = collections.deque([self])
        while nodes_to_search:
            current_node = nodes_to_search.pop()
            if (not current_node.is_root) and (current_node.process.pid == process.pid):
                return current_node
            nodes_to_search.extend(current_node.children)

    @staticmethod
    def build_tree(process_dict, sort_key, hide_kernel_threads):
        """ Build a process tree using using parent/child relationships, and return the tree root node. """
        tree_root = ProcessTreeNode(root=True)
        nodes_to_add_last = collections.deque()

        # first pass: add nodes whose parent are in the tree
        for process, stats in process_dict.items():
            new_node = ProcessTreeNode(process, stats, sort_key)
            try:
                parent_process = process.parent()
            except psutil.NoSuchProcess:
                # parent is dead, consider no parent
                parent_process = None
            if parent_process is None:
                # no parent, add this node at the top level
                tree_root.children.append(new_node)
            elif hide_kernel_threads and (not is_windows) and (parent_process.gids().real == 0):
                # parent is a kernel thread, add this node at the top level
                tree_root.children.append(new_node)
            else:
                parent_node = tree_root.find_process(parent_process)
                if parent_node is not None:
                    # parent is already in the tree, add a new child
                    parent_node.children.append(new_node)
                else:
                    # parent is not in tree, add this node later
                    nodes_to_add_last.append(new_node)

        # next pass(es): add nodes to their parents if it could not be done in previous pass
        while nodes_to_add_last:
            node_to_add = nodes_to_add_last.popleft()  # pop from left and append to right to avoid infinite loop
            try:
                parent_process = node_to_add.process.parent()
            except psutil.NoSuchProcess:
                # parent is dead, consider no parent, add this node at the top level
                tree_root.children.append(node_to_add)
            else:
                if parent_process is None:
                    # parent is None now, but was not at previous pass (can occur on Windows only)
                    # consider no parent, add this node at the top level
                    tree_root.children.append(node_to_add)
                else:
                    parent_node = tree_root.find_process(parent_process)
                    if parent_node is not None:
                        # parent is already in the tree, add a new child
                        parent_node.children.append(node_to_add)
                    else:
                        # parent is not in tree, add this node later
                        nodes_to_add_last.append(node_to_add)

        return tree_root


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
        self.resetsort()
        self.processlist = []
        self.processcount = {
            'total': 0, 'running': 0, 'sleeping': 0, 'thread': 0}

        # Tag to enable/disable the processes stats (to reduce the Glances CPU consumption)
        # Default is to enable the processes stats
        self.disable_tag = False

        # Extended stats for top process is enable by default
        self.disable_extended_tag = False

        # Maximum number of processes showed in the UI interface
        # None if no limit
        self.max_processes = None

        # Process filter is a regular expression
        self.process_filter = None
        self.process_filter_re = None

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

    def set_max_processes(self, value):
        """Set the maximum number of processes showed in the UI interfaces"""
        self.max_processes = value
        return self.max_processes

    def get_max_processes(self):
        """Get the maximum number of processes showed in the UI interfaces"""
        return self.max_processes

    def set_process_filter(self, value):
        """Set the process filter"""
        logger.info("Set process filter to {0}".format(value))
        self.process_filter = value
        if value is not None:
            try:
                self.process_filter_re = re.compile(value)
                logger.debug("Process filter regex compilation OK: {0}".format(self.get_process_filter()))
            except Exception:
                logger.error("Cannot compile process filter regex: {0}".format(value))
                self.process_filter_re = None
        else:
            self.process_filter_re = None
        return self.process_filter

    def get_process_filter(self):
        """Get the process filter"""
        return self.process_filter

    def get_process_filter_re(self):
        """Get the process regular expression compiled"""
        return self.process_filter_re

    def is_filtered(self, value):
        """Return True if the value should be filtered"""
        if self.get_process_filter() is None:
            # No filter => Not filtered
            return False
        else:
            # logger.debug(self.get_process_filter() + " <> " + value + " => " + str(self.get_process_filter_re().match(value) is None))
            return self.get_process_filter_re().match(value) is None

    def disable_kernel_threads(self):
        """ Ignore kernel threads in process list. """
        self.no_kernel_threads = True

    def enable_tree(self):
        """ Enable process tree. """
        self._enable_tree = True

    def is_tree_enabled(self):
        """ Return True if process tree is enabled, False instead. """
        return self._enable_tree

    def __get_process_stats(self, proc,
                            mandatory_stats=True,
                            standard_stats=True,
                            extended_stats=False):
        """
        Get process stats of the proc processes (proc is returned psutil.process_iter())
        mandatory_stats: need for the sorting/filter step
        => cpu_percent, memory_percent, io_counters, name, cmdline
        standard_stats: for all the displayed processes
        => username, status, memory_info, cpu_times
        extended_stats: only for top processes (see issue #403)
        => connections (UDP/TCP), memory_swap...
        """

        # Process ID (always)
        procstat = proc.as_dict(attrs=['pid'])

        if mandatory_stats:
            procstat['mandatory_stats'] = True

            # Process CPU, MEM percent and name
            try:
                procstat.update(
                    proc.as_dict(attrs=['cpu_percent', 'memory_percent', 'name', 'cpu_times'], ad_value=''))
            except psutil.NoSuchProcess:
                # Correct issue #414
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
                    self.cmdline_cache[
                        procstat['pid']] = ' '.join(proc.cmdline())
                except (AttributeError, UnicodeDecodeError, psutil.AccessDenied, psutil.NoSuchProcess):
                    self.cmdline_cache[procstat['pid']] = ""
            procstat['cmdline'] = self.cmdline_cache[procstat['pid']]

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
                except (psutil.AccessDenied, psutil.NoSuchProcess):
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

        if standard_stats:
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

        if extended_stats and not self.disable_extended_tag:
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
            if is_windows:
                try:
                    procstat.update(proc.as_dict(attrs=['num_handles']))
                except psutil.NoSuchProcess:
                    pass
            else:
                procstat['num_handles'] = None

            # SWAP memory (Only on Linux based OS)
            # http://www.cyberciti.biz/faq/linux-which-process-is-using-swap/
            if is_linux:
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
            if is_linux or is_windows:
                try:
                    procstat.update(proc.as_dict(attrs=['ionice']))
                except psutil.NoSuchProcess:
                    pass
            else:
                procstat['ionice'] = None

            # logger.debug(procstat)

        return procstat

    def update(self):
        """
        Update the processes stats
        """
        # Reset the stats
        self.processlist = []
        self.processcount = {
            'total': 0, 'running': 0, 'sleeping': 0, 'thread': 0}

        # Do not process if disable tag is set
        if self.disable_tag:
            return

        # Get the time since last update
        time_since_update = getTimeSinceLastUpdate('process_disk')

        # Build an internal dict with only mandatories stats (sort keys)
        processdict = {}
        for proc in psutil.process_iter():
            # Ignore kernel threads if needed
            if (self.no_kernel_threads and (not is_windows)  # gids() is only available on unix
                    and (proc.gids().real == 0)):
                continue

            # If self.get_max_processes() is None: Only retreive mandatory stats
            # Else: retreive mandatory and standard stats
            s = self.__get_process_stats(proc,
                                         mandatory_stats=True,
                                         standard_stats=self.get_max_processes() is None)
            # Continue to the next process if it has to be filtered
            if s is None or (self.is_filtered(s['cmdline']) and self.is_filtered(s['name'])):
                continue
            # Ok add the process to the list
            processdict[proc] = s
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
                                                           self.getsortkey(),
                                                           self.no_kernel_threads)

            for i, node in enumerate(self.process_tree):
                # Only retreive stats for visible processes (get_max_processes)
                if (self.get_max_processes() is not None) and (i >= self.get_max_processes()):
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
            # Only retreive stats for visible processes (get_max_processes)
            if self.get_max_processes() is not None:
                # Sort the internal dict and cut the top N (Return a list of tuple)
                # tuple=key (proc), dict (returned by __get_process_stats)
                try:
                    processiter = sorted(
                        processdict.items(), key=lambda x: x[1][self.getsortkey()], reverse=True)
                except (KeyError, TypeError) as e:
                    logger.error("Cannot sort process list by %s (%s)" % (self.getsortkey(), e))
                    logger.error("%s" % str(processdict.items()[0]))
                    # Fallback to all process (issue #423)
                    processloop = processdict.items()
                    first = False
                else:
                    processloop = processiter[0:self.get_max_processes()]
                    first = True
            else:
                # Get all processes stats
                processloop = processdict.items()
                first = False
            for i in processloop:
                # Already existing mandatory stats
                procstat = i[1]
                if self.get_max_processes() is not None:
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

    def gettree(self):
        """Get the process tree."""
        return self.process_tree

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
        if self._enable_tree and (self.process_tree is not None):
            self.process_tree.set_sorting(sortedby, sortedby != "name")
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
                self.processlist.sort(key=lambda process: process[sortedby][0] -
                                      process[sortedby][2] + process[sortedby][1] -
                                      process[sortedby][3],
                                      reverse=sortedreverse)
            except Exception:
                self.processlist.sort(key=operator.itemgetter('cpu_percent'),
                                      reverse=sortedreverse)
        else:
            # Others sorts
            self.processlist.sort(key=operator.itemgetter(sortedby),
                                  reverse=sortedreverse)

        return self.processlist
