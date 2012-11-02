#!/usr/bin/env python
#
# Glances is a simple textual monitoring tool
#
# Copyright (C) Nicolargo 2012 <nicolas@nicolargo.com>
#
# Glances is distributed
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Glances is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.";
#

__appname__ = 'glances'
__version__ = "1.5b"
__author__ = "Nicolas Hennion <nicolas@nicolargo.com>"
__licence__ = "LGPL"

# Libraries
#==========

import os
import sys
import platform
import getopt
import signal
import time
from datetime import datetime, timedelta
import gettext
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler        

# International
#==============

gettext.install(__appname__)

# Classes
#========

class Timer:
    """
    The timer class
    """

    def __init__(self, duration):
        self.started(duration)

    def started(self, duration):
        self.target = time.time() + duration

    def finished(self):
        return time.time() > self.target


class glancesLimits:
    """
    Manage the limit OK,CAREFUL,WARNING,CRITICAL for each stats
    """

    # The limit list is stored in an hash table:
    #  limits_list[STAT] = [CAREFUL, WARNING, CRITICAL]
    # Exemple:
    #  limits_list['STD'] = [50, 70, 90]

    #_______________________________CAREFUL WARNING CRITICAL
    __limits_list = {'STD': [50, 70, 90],
                     'LOAD': [0.7, 1.0, 5.0]}

    def __init__(self, careful=50, warning=70, critical=90):
        self.__limits_list['STD'] = [careful, warning, critical]

    def getSTDCareful(self):
        return self.__limits_list['STD'][0]

    def getSTDWarning(self):
        return self.__limits_list['STD'][1]

    def getSTDCritical(self):
        return self.__limits_list['STD'][2]

    def getLOADCareful(self, core=1):
        return self.__limits_list['LOAD'][0] * core

    def getLOADWarning(self, core=1):
        return self.__limits_list['LOAD'][1] * core

    def getLOADCritical(self, core=1):
        return self.__limits_list['LOAD'][2] * core


class glancesLogs:
    """
    The main class to manage logs inside the Glances software
    Logs is a list of list:
    [["begin", "end", "WARNING|CRITICAL", "CPU|LOAD|MEM",
      MAX, AVG, MIN, SUM, COUNT],...]
    """

    def __init__(self):
        """
        Init the logs classe
        """
        # Maximum size of the logs list
        self.logs_max = 10

        # Init the logs list
        self.logs_list = []

    def get(self):
        """
        Return the logs list (RAW)
        """
        return self.logs_list

    def len(self):
        """
        Return the number of item in the log list
        """
        return self.logs_list.__len__()

    def __itemexist__(self, item_type):
        """
        An item exist in the list if:
        * end is < 0
        * item_type is matching
        """
        for i in range(self.len()):
            if (self.logs_list[i][1] < 0 and
                self.logs_list[i][3] == item_type):
                return i
        return -1

    def add(self, item_state, item_type, item_value, proc_list = []):
        """
        item_state = "OK|CAREFUL|WARNING|CRITICAL"
        item_type = "CPU*|LOAD|MEM"
        item_value = value
        Item is defined by:
          ["begin", "end", "WARNING|CRITICAL", "CPU|LOAD|MEM",
           MAX, AVG, MIN, SUM, COUNT,
           [top3 process list]]
        If item is a 'new one':
          Add the new item at the beginning of the logs list
        Else:
          Update the existing item
        """
        
        # Add Top process sort depending on alert type
        if (item_type.startswith("MEM")):
            # MEM
            sortby = 'memory_percent'
        else:
            # CPU* and LOAD
            sortby = 'cpu_percent'
        topprocess = sorted(proc_list, key=lambda process: process[sortby], reverse=True)

        # Add or update the log
        item_index = self.__itemexist__(item_type)
        if item_index < 0:
            # Item did not exist, add if WARNING or CRITICAL
            if (item_state == "WARNING" or
                item_state == "CRITICAL"):
                # Time is stored in Epoch format
                # Epoch -> DMYHMS = datetime.fromtimestamp(epoch)
                item = []
                item.append(time.mktime(datetime.now().timetuple()))
                item.append(-1)
                item.append(item_state)     # STATE: WARNING|CRITICAL
                item.append(item_type)      # TYPE: CPU, LOAD, MEM...
                item.append(item_value)     # MAX
                item.append(item_value)     # AVG
                item.append(item_value)     # MIN
                item.append(item_value)     # SUM
                item.append(1)              # COUNT
                item.append(topprocess[0:3]) # TOP 3 PROCESS LIST
                self.logs_list.insert(0, item)
                if self.len() > self.logs_max:
                    self.logs_list.pop()
        else:
            # Item exist, update
            if (item_state == "OK" or
                item_state == "CAREFUL"):
                # Close the item
                self.logs_list[item_index][1] = time.mktime(
                    datetime.now().timetuple())
                # TOP PROCESS LIST
                self.logs_list[item_index][9] = []
            else:
                # Update the item
                # State
                if item_state == "CRITICAL":
                    self.logs_list[item_index][2] = item_state
                # Value
                if item_value > self.logs_list[item_index][4]:
                    # MAX
                    self.logs_list[item_index][4] = item_value
                elif item_value < self.logs_list[item_index][6]:
                    # MIN
                    self.logs_list[item_index][6] = item_value
                # AVG
                self.logs_list[item_index][7] += item_value
                self.logs_list[item_index][8] += 1
                self.logs_list[item_index][5] = (
                    self.logs_list[item_index][7] /
                    self.logs_list[item_index][8])
                # TOP PROCESS LIST
                self.logs_list[item_index][9] = topprocess[0:3]

        return self.len()


class glancesGrabFs:
    """
    Get FS stats
    """

    def __init__(self):
        """
        Init FS stats
        """

        # Ignore the following FS name
        self.ignore_fsname = ('', 'none', 'gvfs-fuse-daemon', 'fusectl',
                              'cgroup')

        # Ignore the following FS type
        self.ignore_fstype = ('binfmt_misc', 'devpts', 'iso9660', 'none',
                              'proc', 'sysfs', 'usbfs', 'rootfs', 'autofs',
                              'devtmpfs')

    def __update__(self):
        """
        Update the stats
        """

        # Reset the list
        self.fs_list = []

        # Open the current mounted FS
        fs_stat = psutil.disk_partitions(True)
        for fs in range(len(fs_stat)):
            fs_current = {}
            fs_current['device_name'] = fs_stat[fs].device
            if fs_current['device_name'] in self.ignore_fsname:
                continue
            fs_current['fs_type'] = fs_stat[fs].fstype
            if fs_current['fs_type'] in self.ignore_fstype:
                continue
            fs_current['mnt_point'] = fs_stat[fs].mountpoint
            try:
                fs_usage = psutil.disk_usage(fs_current['mnt_point'])
            except Exception:
                continue
            fs_current['size'] = fs_usage.total
            fs_current['used'] = fs_usage.used
            fs_current['avail'] = fs_usage.free
            self.fs_list.append(fs_current)

    def get(self):
        self.__update__()
        return self.fs_list


class glancesStats:
    """
    This class store, update and give stats
    """


    def __init__(self, server_tag = False, client_tag = False):
        """
        Init the stats
        """

        self.server_tag = server_tag
        self.client_tag = client_tag

        # Init the fs stats
        try:
            self.glancesgrabfs = glancesGrabFs()
        except Exception:
            self.glancesgrabfs = {}

        # Process list refresh
        self.process_list_refresh = True
        
        # Init the all_stats used by the server
        # all_stats is a dict of dicts filled by the server
        if (self.server_tag):
            self.all_stats = collections.defaultdict(dict)
        
        # Cached informations (no need to be refreshed)
        # Host and OS informations
        if (not self.client_tag):
            self.host = {}
            self.host['os_name'] = platform.system()
            self.host['hostname'] = platform.node()
            self.host['platform'] = platform.architecture()[0]
            is_archlinux = os.path.exists(os.path.join("/", "etc", "arch-release"))
            if self.host['os_name'] == "Linux":
                if is_archlinux:
                    self.host['linux_distro'] = "Arch Linux"
                else:
                    linux_distro = platform.linux_distribution()
                    self.host['linux_distro'] = " ".join(linux_distro[:2])
                self.host['os_version'] = platform.release()
            elif self.host['os_name'] == "FreeBSD":
                self.host['os_version'] = platform.release()
            elif self.host['os_name'] == "Darwin":
                self.host['os_version'] = platform.mac_ver()[0]
            elif self.host['os_name'] == "Windows":
                os_version = platform.win32_ver()
                self.host['os_version'] = " ".join(os_version[::2])
            else:
                self.host['os_version'] = ""
            if (self.server_tag):
                self.all_stats["host"] = self.host

    def __get_process_stats_NEW__(self, proc):
        """
        Get process (proc) statistics
        !!! No performance gap (CPU %)
        !!! Without: 1.5 - 2.0 
        !!! With:    2.0 - 2.2
        
        """
        procstat = proc.as_dict(['get_memory_info', 'get_cpu_percent', 'get_memory_percent',
                                 'pid', 'username', 'get_nice',
                                 'get_cpu_times', 'name', 'status', 'cmdline'])
        if psutil_get_io_counter_tag:
            procstat['io_counters']  = proc.get_io_counters()      
        procstat['status'] = str(procstat['status'])[:1].upper()
        procstat['cmdline'] = " ".join(procstat['cmdline'])
        
        return procstat
        
    def __get_process_stats__(self, proc):
        """
        Get process (proc) statistics
        """
        procstat = {}
        
        procstat['memory_info'] = proc.get_memory_info()
        
        if psutil_get_cpu_percent_tag:
            procstat['cpu_percent'] = \
                proc.get_cpu_percent(interval=0)

        procstat['memory_percent'] = proc.get_memory_percent()

        try:
            if psutil_get_io_counter_tag:
                procstat['io_counters']  = proc.get_io_counters()
        except:
            procstat['io_counters'] = {}

        procstat['pid'] = proc.pid
        procstat['username'] = proc.username

        if hasattr(proc, 'nice'):
            # Deprecated in PsUtil 0.5.0
            procstat['nice'] = proc.nice
        elif hasattr(proc, 'get_nice'):
            # Specific for PsUtil 0.5.0+
            procstat['nice'] = proc.get_nice()
        else:
            # Never here...
            procstat['nice'] = 0

        procstat['status'] = str(proc.status)[:1].upper()
        procstat['cpu_times'] = proc.get_cpu_times()
        procstat['name'] = proc.name
        procstat['cmdline'] = " ".join(proc.cmdline)
        
        return procstat


    def __update__(self, input_stats):
        """
        Update the stats
        """

        # Host information
        # Only for client
        if (self.client_tag):
            self.host = input_stats["host"]

        # CPU
        if (self.client_tag):
            self.cpu = input_stats["cpu"]
        else:
            if not hasattr(self, 'cputime_old'):            
                self.cputime_old = psutil.cpu_times()
                self.cputime_total_old = (self.cputime_old.user +
                                          self.cputime_old.system +
                                          self.cputime_old.idle)
                # Only available on some OS
                if hasattr(self.cputime_old, 'nice'):
                    self.cputime_total_old += self.cputime_old.nice
                if hasattr(self.cputime_old, 'iowait'):
                    self.cputime_total_old += self.cputime_old.iowait
                if hasattr(self.cputime_old, 'irq'):
                    self.cputime_total_old += self.cputime_old.irq
                if hasattr(self.cputime_old, 'softirq'):
                    self.cputime_total_old += self.cputime_old.softirq
                self.cpu = {}
            else:
                try:
                    self.cputime_new = psutil.cpu_times()
                    self.cputime_total_new = (self.cputime_new.user +
                                              self.cputime_new.system +
                                              self.cputime_new.idle)
                    # Only available on some OS
                    if hasattr(self.cputime_new, 'nice'):
                        self.cputime_total_new += self.cputime_new.nice
                    if hasattr(self.cputime_new, 'iowait'):
                        self.cputime_total_new += self.cputime_new.iowait
                    if hasattr(self.cputime_new, 'irq'):
                        self.cputime_total_new += self.cputime_new.irq
                    if hasattr(self.cputime_new, 'softirq'):
                        self.cputime_total_new += self.cputime_new.softirq
                    percent = 100 / (self.cputime_total_new -
                                     self.cputime_total_old)
                    self.cpu = {'kernel':
                                    (self.cputime_new.system -
                                     self.cputime_old.system) * percent,
                                'user':
                                    (self.cputime_new.user -
                                     self.cputime_old.user) * percent,
                                'idle':
                                    (self.cputime_new.idle -
                                     self.cputime_old.idle) * percent}
                    if hasattr(self.cputime_new, 'nice'):
                        self.cpu['nice'] = (self.cputime_new.nice -
                                            self.cputime_old.nice) * percent
                    self.cputime_old = self.cputime_new
                    self.cputime_total_old = self.cputime_total_new
                except Exception:
                    self.cpu = {}
            if (self.server_tag):
                self.all_stats["cpu"] = self.cpu

        # PerCPU
        if (self.client_tag):
            self.percpu = input_stats["percpu"]
        else:
            if not hasattr(self, 'percputime_old'):            
                self.percputime_old = psutil.cpu_times(percpu = True)
                self.percputime_total_old = []
                for i in range(len(self.percputime_old)):                
                    self.percputime_total_old.append(self.percputime_old[i].user +
                                                     self.percputime_old[i].system +
                                                     self.percputime_old[i].idle)
                # Only available on some OS
                for i in range(len(self.percputime_old)):
                    if hasattr(self.percputime_old[i], 'nice'):
                        self.percputime_total_old[i] += self.percputime_old[i].nice
                for i in range(len(self.percputime_old)):                
                    if hasattr(self.percputime_old[i], 'iowait'):
                        self.percputime_total_old[i] += self.percputime_old[i].iowait
                for i in range(len(self.percputime_old)):                                
                    if hasattr(self.percputime_old[i], 'irq'):
                        self.percputime_total_old[i] += self.percputime_old[i].irq
                for i in range(len(self.percputime_old)):                                
                    if hasattr(self.percputime_old[i], 'softirq'):
                        self.percputime_total_old[i] += self.percputime_old[i].softirq
                self.percpu = []
            else:
                try:
                    self.percputime_new = psutil.cpu_times(percpu = True)
                    self.percputime_total_new = []
                    for i in range(len(self.percputime_new)):                
                        self.percputime_total_new.append(self.percputime_new[i].user +
                                                         self.percputime_new[i].system +
                                                         self.percputime_new[i].idle)                    
                    # Only available on some OS
                    for i in range(len(self.percputime_new)):
                        if hasattr(self.percputime_new[i], 'nice'):          
                            self.percputime_total_new[i] += self.percputime_new[i].nice
                    for i in range(len(self.percputime_new)):                
                        if hasattr(self.percputime_new[i], 'iowait'):          
                            self.percputime_total_new[i] += self.percputime_new[i].iowait
                    for i in range(len(self.percputime_new)):                
                        if hasattr(self.percputime_new[i], 'irq'):          
                            self.percputime_total_new[i] += self.percputime_new[i].irq
                    for i in range(len(self.percputime_new)):                
                        if hasattr(self.percputime_new[i], 'softirq'):          
                            self.percputime_total_new[i] += self.percputime_new[i].softirq
                    perpercent = []
                    self.percpu = []
                    for i in range(len(self.percputime_new)):                
                        perpercent.append(100 / (self.percputime_total_new[i] -
                                                 self.percputime_total_old[i]))
                        cpu =  {'kernel':
                                    (self.percputime_new[i].system -
                                     self.percputime_old[i].system) * perpercent[i],
                                'user':
                                    (self.percputime_new[i].user -
                                     self.percputime_old[i].user) * perpercent[i],
                                'idle':
                                    (self.percputime_new[i].idle -
                                     self.percputime_old[i].idle) * perpercent[i]}
                        if hasattr(self.percputime_new[i], 'nice'):
                            cpu['nice'] = (self.percputime_new[i].nice -
                                           self.percputime_old[i].nice) * perpercent[i]
                        self.percpu.append(cpu)                                         
                    self.percputime_old = self.percputime_new
                    self.percputime_total_old = self.percputime_total_new
                except Exception:
                    self.percpu = []
            if (self.server_tag):
                self.all_stats["percpu"] = self.percpu

        # LOAD
        if (self.client_tag):
            self.load = input_stats["load"]
        else:
            if hasattr(os, 'getloadavg'): 
                getload = os.getloadavg()
                self.load = {'min1': getload[0],
                             'min5': getload[1],
                             'min15': getload[2]}
            else:
                self.load = {}
            if (self.server_tag):
                self.all_stats["load"] = self.load

        # MEM
        if (self.client_tag):
            self.mem = input_stats["mem"]
            self.memswap = input_stats["memswap"]
        else:
            if psutil_mem_vm:
                # If PsUtil 0.6+
                phymem = psutil.virtual_memory()
                if (hasattr(phymem, 'cached') and hasattr(phymem, 'buffers')):
                   cachemem = phymem.cached + phymem.buffers
                else:
                   cachemem = 0
                self.mem = {'cache': cachemem,
                            'total': phymem.total,
                            'used': phymem.used,
                            'free': phymem.free,
                            'percent': phymem.percent}
                virtmem = psutil.swap_memory()
                self.memswap = {'total': virtmem.total,
                                'used': virtmem.used,
                                'free': virtmem.free,
                                'percent': virtmem.percent}            
            else:
                # For olders PsUtil version
                # Physical memory (RAM)
                if hasattr(psutil, 'phymem_usage'): 
                    phymem = psutil.phymem_usage()
                    if hasattr(psutil, 'cached_usage') and hasattr(psutil, 'phymem_buffers'): 
                        # Cache stat only available for Linux
                        cachemem = psutil.cached_phymem() + psutil.phymem_buffers()
                    else:
                        cachemem = 0
                    self.mem = {'cache': cachemem,
                                'total': phymem.total,
                                'used': phymem.used,
                                'free': phymem.free,
                                'percent': phymem.percent}
                else:
                    self.mem = {}
                # Virtual memory (SWAP)
                if hasattr(psutil, 'virtmem_usage'): 
                    virtmem = psutil.virtmem_usage()
                    self.memswap = {'total': virtmem.total,
                                    'used': virtmem.used,
                                    'free': virtmem.free,
                                    'percent': virtmem.percent}
                else:
                    self.memswap = {}
            if (self.server_tag):
                self.all_stats["mem"] = self.mem
                self.all_stats["memswap"] = self.memswap

        # NET
        if (self.client_tag):
            self.network = input_stats["network"]
        else:
            if psutil_network_io_tag:
                self.network = []
                if hasattr(psutil, 'network_io_counters'): 
                    if not hasattr(self, 'network_old'): 
                        self.network_old = psutil.network_io_counters(True)
                    else:
                        self.network_new = psutil.network_io_counters(True)
                        for net in self.network_new:
                            try:
                                # Try necessary to manage dynamic network interface
                                netstat = {}
                                netstat['interface_name'] = net
                                netstat['rx'] = (self.network_new[net].bytes_recv -
                                                 self.network_old[net].bytes_recv)
                                netstat['tx'] = (self.network_new[net].bytes_sent -
                                                 self.network_old[net].bytes_sent)
                            except Exception:
                                continue
                            else:
                                self.network.append(netstat)
                        self.network_old = self.network_new
            if (self.server_tag):
                self.all_stats["network"] = self.network

        # DISK I/O
        if (self.client_tag):
            self.diskio = input_stats["diskio"]
        else:
            if psutil_disk_io_tag:
                self.diskio = []
                if psutil_disk_io_tag and hasattr(psutil, 'disk_io_counters'): 
                    if not hasattr(self, 'diskio_old'): 
                        self.diskio_old = psutil.disk_io_counters(True)
                    else:
                        self.diskio_new = psutil.disk_io_counters(True)
                        for disk in self.diskio_new:
                            try:
                                # Try necessary to manage dynamic disk creation/del
                                diskstat = {}
                                diskstat['disk_name'] = disk
                                diskstat['read_bytes'] = (
                                    self.diskio_new[disk].read_bytes -
                                    self.diskio_old[disk].read_bytes)
                                diskstat['write_bytes'] = (
                                    self.diskio_new[disk].write_bytes -
                                    self.diskio_old[disk].write_bytes)
                            except Exception:
                                continue
                            else:
                                self.diskio.append(diskstat)
                        self.diskio_old = self.diskio_new
            if (self.server_tag):
                self.all_stats["diskio"] = self.diskio

        # FILE SYSTEM
        if (self.client_tag):
            self.fs = input_stats["fs"]
        else:
            if psutil_fs_usage_tag:
                self.fs = self.glancesgrabfs.get()
            if (self.server_tag):
                self.all_stats["fs"] = self.fs

        # PROCESS
        # Initialiation of the running processes list
        # Data are refreshed every two cycle (refresh_time * 2)
        if (self.client_tag):
            self.processcount = input_stats["processcount"]
            self.process = input_stats["process"]
            self.process_list_refresh = True
        else:
            if self.process_list_refresh:
                self.process_first_grab = False
                if not hasattr(self, 'process_all'): 
                    self.process_all = [proc for proc in psutil.process_iter()]
                    self.process_first_grab = True
                self.process = []
                self.processcount = {'total': 0, 'running': 0, 'sleeping': 0}
                # Manage new processes
                process_new = [proc.pid for proc in self.process_all]
                for proc in psutil.process_iter():
                    if proc.pid not in process_new:
                        self.process_all.append(proc)
                # Grab stats from process list
                for proc in self.process_all[:]:
                    try:
                        if not proc.is_running():
                            try:
                                self.process_all.remove(proc)
                            except Exception:
                                pass
                    except psutil.error.NoSuchProcess:
                        try:
                            self.process_all.remove(proc)
                        except Exception:
                            pass
                    else:
                        # Global stats
                        try:
                            self.processcount[str(proc.status)] += 1
                        except psutil.error.NoSuchProcess:
                            # Process non longer exist
                            pass
                        except KeyError:
                            # Key did not exist, create it
                            self.processcount[str(proc.status)] = 1
                        finally:
                            self.processcount['total'] += 1
                        # Per process stats
                        try:
                            self.process.append(self.__get_process_stats__(proc))
                        except Exception:
                            pass
                # If it is the first grab then empty process list
                if self.process_first_grab:
                    self.process = []
            self.process_list_refresh = not self.process_list_refresh
            if (self.server_tag):
                self.all_stats["processcount"] = self.processcount
                self.all_stats["process"] = self.process

        # Get the current date/time
        self.now = datetime.now()

        # Get the number of core (CPU) (Used to display load alerts)
        if (self.client_tag):
            self.core_number = input_stats["core_number"]
        else:
            self.core_number = psutil.NUM_CPUS
            if (self.server_tag):
                self.all_stats["core_number"] = self.core_number

    def update(self, input_stats = {}):
        # Update the stats
        self.__update__(input_stats)

    def getAll(self):
        return self.all_stats

    def getHost(self):
        return self.host

    def getSystem(self):
        return self.host

    def getCpu(self):
        return self.cpu

    def getPerCpu(self):
        return self.percpu

    def getCore(self):
        return self.core_number

    def getLoad(self):
        return self.load

    def getMem(self):
        return self.mem

    def getMemSwap(self):
        return self.memswap

    def getNetwork(self):
        if psutil_network_io_tag:
            return sorted(self.network,
                          key=lambda network: network['interface_name'])
        else:
            return 0

    def getDiskIO(self):
        if psutil_disk_io_tag:
            return sorted(self.diskio, key=lambda diskio: diskio['disk_name'])
        else:
            return 0

    def getFs(self):
        if psutil_fs_usage_tag:
            return sorted(self.fs, key=lambda fs: fs['mnt_point'])
        else:
            return 0

    def getProcessCount(self):
        return self.processcount

    def getProcessList(self, sortedby='auto'):
        """
        Return the sorted process list
        """

        sortedReverse = True
        if sortedby == 'auto':
            if psutil_get_cpu_percent_tag:
                sortedby = 'cpu_percent'
            else:
                sortedby = 'memory_percent'
            # Auto selection
            # If global MEM > 70% sort by MEM usage
            # else sort by CPU usage
            if (self.mem['total'] != 0):
                memtotal = ((self.mem['used'] - self.mem['cache']) * 100) / self.mem['total']
                if memtotal > limits.getSTDWarning():
                    sortedby = 'memory_percent'
        elif sortedby == 'name':
            sortedReverse = False

        return sorted(self.process, key=lambda process: process[sortedby],
                      reverse=sortedReverse)

    def getNow(self):
        return self.now


class glancesScreen:
    """
    This class manage the screen (display and key pressed)
    """

    # By default the process list is automatically sorted
    # If global CPU > WANRING => Sorted by CPU usage
    # If global used MEM > WARINING => Sorted by MEM usage
    __process_sortedby = 'auto'

    def __init__(self, refresh_time=1):
        # Global information to display
        self.__version = __version__

        # Init windows positions
        self.term_w = 80
        self.term_h = 24
        self.system_x = 0
        self.system_y = 0
        self.cpu_x = 0
        self.cpu_y = 2
        self.load_x = 19
        self.load_y = 2
        self.mem_x = 39
        self.mem_y = 2
        self.network_x = 0
        self.network_y = 7
        self.diskio_x = 0
        self.diskio_y = -1
        self.fs_x = 0
        self.fs_y = -1
        self.process_x = 29
        self.process_y = 7
        self.log_x = 0
        self.log_y = -1
        self.help_x = 0
        self.help_y = 0
        self.now_x = 79
        self.now_y = 3
        self.caption_x = 0
        self.caption_y = 3

        # Init the curses screen
        self.screen = curses.initscr()
        if not self.screen:
            print(_("Error: Cannot init the curses library.\n"))

        # Set curses options
        if hasattr(curses, 'start_color'):
            curses.start_color()
        if hasattr(curses, 'use_default_colors'):
            curses.use_default_colors()
        if hasattr(curses, 'noecho'):
            curses.noecho()
        if hasattr(curses, 'cbreak'):
            curses.cbreak()
        if hasattr(curses, 'curs_set'):
            curses.curs_set(0)

        # Init colors
        self.hascolors = False
        if curses.has_colors() and curses.COLOR_PAIRS > 8:
            self.hascolors = True
            # FG color, BG color
            curses.init_pair(1, curses.COLOR_WHITE, -1)
            curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_RED)
            curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_GREEN)
            curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLUE)
            curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_MAGENTA)
            curses.init_pair(6, curses.COLOR_RED, -1)
            curses.init_pair(7, curses.COLOR_GREEN, -1)
            curses.init_pair(8, curses.COLOR_BLUE, -1)
            curses.init_pair(9, curses.COLOR_MAGENTA, -1)
        else:
            self.hascolors = False

        self.title_color = curses.A_BOLD | curses.A_UNDERLINE
        self.help_color = curses.A_BOLD
        if self.hascolors:
            # Colors text styles
            self.no_color = curses.color_pair(1)
            self.default_color = curses.color_pair(3) | curses.A_BOLD
            self.ifCAREFUL_color = curses.color_pair(4) | curses.A_BOLD
            self.ifWARNING_color = curses.color_pair(5) | curses.A_BOLD
            self.ifCRITICAL_color = curses.color_pair(2) | curses.A_BOLD
            self.default_color2 = curses.color_pair(7) | curses.A_BOLD
            self.ifCAREFUL_color2 = curses.color_pair(8) | curses.A_BOLD
            self.ifWARNING_color2 = curses.color_pair(9) | curses.A_BOLD
            self.ifCRITICAL_color2 = curses.color_pair(6) | curses.A_BOLD
        else:
            # B&W text styles
            self.no_color = curses.A_NORMAL
            self.default_color = curses.A_NORMAL
            self.ifCAREFUL_color = curses.A_UNDERLINE
            self.ifWARNING_color = curses.A_BOLD
            self.ifCRITICAL_color = curses.A_REVERSE
            self.default_color2 = curses.A_NORMAL
            self.ifCAREFUL_color2 = curses.A_UNDERLINE
            self.ifWARNING_color2 = curses.A_BOLD
            self.ifCRITICAL_color2 = curses.A_REVERSE

        # Define the colors list (hash table) for logged stats
        self.__colors_list = {
            #         CAREFUL WARNING CRITICAL
            'DEFAULT': self.no_color,
            'OK': self.default_color,
            'CAREFUL': self.ifCAREFUL_color,
            'WARNING': self.ifWARNING_color,
            'CRITICAL': self.ifCRITICAL_color
        }

        # Define the colors list (hash table) for non logged stats
        self.__colors_list2 = {
            #         CAREFUL WARNING CRITICAL
            'DEFAULT': self.no_color,
            'OK': self.default_color2,
            'CAREFUL': self.ifCAREFUL_color2,
            'WARNING': self.ifWARNING_color2,
            'CRITICAL': self.ifCRITICAL_color2
        }

        # What are we going to display
        self.network_tag = psutil_network_io_tag
        self.diskio_tag = psutil_disk_io_tag
        self.fs_tag = psutil_fs_usage_tag
        self.log_tag = True
        self.help_tag = False
        self.percpu_tag = True
        self.net_byteps_tag = network_bytepersec_tag

        # Init main window
        self.term_window = self.screen.subwin(0, 0)

        # Init refresh time
        self.__refresh_time = refresh_time

        # Catch key pressed with non blocking mode
        self.term_window.keypad(1)
        self.term_window.nodelay(1)
        self.pressedkey = -1

    def setProcessSortedBy(self, sorted):
        self.__process_sortedautoflag = False
        self.__process_sortedby = sorted

    def getProcessSortedBy(self):
        return self.__process_sortedby

    def __autoUnit(self, val):
        """
        Convert val to string and concatenate the good unit
        Exemples:
            960 -> 960
            142948 -> 143K
            560745673 -> 561M
            ...
        """
        symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
        prefix = {
            'Y': 1208925819614629174706176,
            'Z': 1180591620717411303424,
            'E': 1152921504606846976,
            'P': 1125899906842624,
            'T': 1099511627776,
            'G': 1073741824,
            'M': 1048576,
            'K': 1024
        }

        for key in reversed(symbols):
            if val >= prefix[key]:
                value = float(val) / prefix[key]
                if key == "M" or key == "K":
                    return "{0:.0f}{1}".format(value, key)
                else:
                    return "{0:.1f}{1}".format(value, key)

        return "{0!s}".format(val)

    def __getAlert(self, current=0, max=100):
        # If current < CAREFUL of max then alert = OK
        # If current > CAREFUL of max then alert = CAREFUL
        # If current > WARNING of max then alert = WARNING
        # If current > CRITICAL of max then alert = CRITICAL
        try:
            (current * 100) / max
        except ZeroDivisionError:
            return 'DEFAULT'

        variable = (current * 100) / max

        if variable > limits.getSTDCritical():
            return 'CRITICAL'
        elif variable > limits.getSTDWarning():
            return 'WARNING'
        elif variable > limits.getSTDCareful():
            return 'CAREFUL'

        return 'OK'

    def __getColor(self, current=0, max=100):
        """
        Return colors for logged stats
        """
        return self.__colors_list[self.__getAlert(current, max)]

    def __getColor2(self, current=0, max=100):
        """
        Return colors for non logged stats
        """
        return self.__colors_list2[self.__getAlert(current, max)]

    def __getCpuAlert(self, current=0, max=100):
        return self.__getAlert(current, max)

    def __getCpuColor(self, current=0, max=100):
        return self.__getColor(current, max)

    def __getLoadAlert(self, current=0, core=1):
        # If current < CAREFUL*core of max then alert = OK
        # If current > CAREFUL*core of max then alert = CAREFUL
        # If current > WARNING*core of max then alert = WARNING
        # If current > CRITICAL*core of max then alert = CRITICAL

        if current > limits.getLOADCritical(core):
            return 'CRITICAL'
        elif current > limits.getLOADWarning(core):
            return 'WARNING'
        elif current > limits.getLOADCareful(core):
            return 'CAREFUL'

        return 'OK'

    def __getLoadColor(self, current=0, core=1):
        return self.__colors_list[self.__getLoadAlert(current, core)]

    def __getMemAlert(self, current=0, max=100):
        return self.__getAlert(current, max)

    def __getMemColor(self, current=0, max=100):
        return self.__getColor(current, max)

    def __getNetColor(self, current=0, max=100):
        return self.__getColor2(current, max)

    def __getFsColor(self, current=0, max=100):
        return self.__getColor2(current, max)

    def __getProcessColor(self, current=0, max=100):
        return self.__getColor2(current, max)

    def __catchKey(self):
        # Get key
        self.pressedkey = self.term_window.getch()

        # Actions...
        if (self.pressedkey == 27 or
            self.pressedkey == 113):
            # 'ESC'|'q' > Quit
            end()
        elif self.pressedkey == 49:
            # '1' > Switch between CPU and PerCPU information
            self.percpu_tag = not self.percpu_tag
        elif self.pressedkey == 97:
            # 'a' > Sort processes automatically
            self.setProcessSortedBy('auto')
        elif self.pressedkey == 98:
            # 'b' > Switch between bit/s and byte/s for network IO
            self.net_byteps_tag = not self.net_byteps_tag
        elif self.pressedkey == 99 and psutil_get_cpu_percent_tag:
            # 'c' > Sort processes by CPU usage
            self.setProcessSortedBy('cpu_percent')
        elif self.pressedkey == 100 and psutil_disk_io_tag:
            # 'd' > Show/hide disk I/O stats
            self.diskio_tag = not self.diskio_tag
        elif self.pressedkey == 102 and psutil_fs_usage_tag:
            # 'f' > Show/hide fs stats
            self.fs_tag = not self.fs_tag
        elif self.pressedkey == 104:
            # 'h' > Show/hide help
            self.help_tag = not self.help_tag
        elif self.pressedkey == 108:
            # 'l' > Show/hide log messages
            self.log_tag = not self.log_tag
        elif self.pressedkey == 109:
            # 'm' > Sort processes by MEM usage
            self.setProcessSortedBy('memory_percent')
        elif self.pressedkey == 110 and psutil_network_io_tag:
            # 'n' > Show/hide network stats
            self.network_tag = not self.network_tag
        elif self.pressedkey == 112:
            # 'p' > Sort processes by name
            self.setProcessSortedBy('name')

        # Return the key code
        return self.pressedkey

    def end(self):
        # Shutdown the curses window
        curses.echo()
        curses.nocbreak()
        curses.curs_set(1)
        curses.endwin()

    def display(self, stats):
        # Get stats for processes (used in another functions for logs)
        processcount = stats.getProcessCount()
        processlist = stats.getProcessList(screen.getProcessSortedBy())
        # Display stats
        self.displaySystem(stats.getHost(), stats.getSystem())
        cpu_offset = self.displayCpu(stats.getCpu(), stats.getPerCpu(), processlist)
        self.displayLoad(stats.getLoad(), stats.getCore(), processlist, cpu_offset)
        self.displayMem(stats.getMem(), stats.getMemSwap(), processlist, cpu_offset)
        network_count = self.displayNetwork(stats.getNetwork())
        diskio_count = self.displayDiskIO(stats.getDiskIO(),
                                          self.network_y + network_count)
        fs_count = self.displayFs(stats.getFs(),
                                  self.network_y + network_count +
                                  diskio_count)
        log_count = self.displayLog(self.network_y + network_count +
                                    diskio_count + fs_count)
        self.displayProcess(processcount, processlist, log_count)
        self.displayCaption()
        self.displayNow(stats.getNow())
        self.displayHelp()

    def erase(self):
        # Erase the content of the screen
        self.term_window.erase()

    def flush(self, stats):
        # Flush display
        self.erase()
        self.display(stats)

    def update(self, stats):
        # flush display
        self.flush(stats)

        # Wait
        countdown = Timer(self.__refresh_time)
        while (not countdown.finished()):
            # Getkey
            if self.__catchKey() > -1:
                # flush display
                self.flush(stats)
            # Wait 100ms...
            curses.napms(100)

    def displaySystem(self, host, system):
        # System information
        if not host or not system:
            return 0
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]
        if (screen_y > self.system_y and
            screen_x > self.system_x + 79):
            if host['os_name'] == "Linux":
                system_msg = _("{0} {1} with {2} {3} on {4}").format(
                    system['linux_distro'], system['platform'],
                    system['os_name'], system['os_version'],
                    host['hostname'])
            else:
                system_msg = _("{0} {1} {2} on {3}").format(
                    system['os_name'], system['os_version'],
                    system['platform'], host['hostname'])
            self.term_window.addnstr(self.system_y, self.system_x +
                                     int(screen_x / 2) - len(system_msg) / 2,
                                     system_msg, 80, curses.A_UNDERLINE)

    def displayCpu(self, cpu, percpu, proclist):
        # CPU %
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]
        
        tag_percpu = False
        offset_x = 0
        if screen_x >  self.cpu_x + 79 + (len(percpu)-1)*10:
            tag_percpu = True
            offset_x = (len(percpu)-1)*10
        
        # If space id available (tag_percpu)
        # and global Per CPU tag (percpu_tag)
        # then display detailled informations for CPU
        tag_percpu = tag_percpu and self.percpu_tag
        
        if (screen_y > self.cpu_y + 5 and tag_percpu):
            # Display extended information whenspace is available (perCpu)
            self.term_window.addnstr(self.cpu_y, self.cpu_x, _("PerCPU"), 8,
                                     self.title_color if self.hascolors else
                                     curses.A_UNDERLINE)

            if not percpu:
                self.term_window.addnstr(self.cpu_y + 1, self.cpu_x,
                                         _("Compute data..."), 15)
                return 0

            self.term_window.addnstr(self.cpu_y + 1, self.cpu_x, _("User:"), 8)
            self.term_window.addnstr(self.cpu_y + 2, self.cpu_x, _("Kernel:"), 8)
            self.term_window.addnstr(self.cpu_y + 3, self.cpu_x, _("Nice:"), 8)

            for i in range(len(percpu)):
                self.term_window.addnstr(self.cpu_y, self.cpu_x + 10 + i*10,
                                         "%.1f%%" % (100 - percpu[i]['idle']), 8)

                alert = self.__getCpuAlert(percpu[i]['user'])
                logs.add(alert, "CPU-%d user" % i, percpu[i]['user'], proclist)
                self.term_window.addnstr(self.cpu_y + 1, self.cpu_x + 10 + i*10,
                                         "%.1f" % percpu[i]['user'], 8,
                                         self.__colors_list[alert])

                alert = self.__getCpuAlert(percpu[i]['kernel'])
                logs.add(alert, "CPU-%d kernel" % i, percpu[i]['kernel'], proclist)
                self.term_window.addnstr(self.cpu_y + 2, self.cpu_x + 10 + i*10,
                                         "%.1f" % percpu[i]['kernel'], 8,
                                         self.__colors_list[alert])
                try:
                    alert = self.__getCpuAlert(percpu[i]['nice'])
                    logs.add(alert, "CPU-%d nice" % i, percpu[i]['nice'], proclist)
                    self.term_window.addnstr(self.cpu_y + 3, self.cpu_x + 10 + i*10,
                                             "%.1f" % percpu[i]['nice'], 8,
                                             self.__colors_list[alert])
                except:
                    #~ alert = self.__getCpuAlert(percpu[i]['idle'])
                    #~ logs.add(alert, "CPU-%d idle" % i, percpu[i]['idle'], proclist)
                    self.term_window.addnstr(self.cpu_y + 3, self.cpu_x + 10 + i*10,
                                             "%.1f" % percpu[i]['idle'], 8)
                    

        elif (screen_y > self.cpu_y + 5 and
              screen_x > self.cpu_x + 18):
            # Display summary information
            self.term_window.addnstr(self.cpu_y, self.cpu_x, _("CPU"), 8,
                                     self.title_color if self.hascolors else
                                     curses.A_UNDERLINE)

            if not cpu:
                self.term_window.addnstr(self.cpu_y + 1, self.cpu_x,
                                         _("Compute data..."), 15)
                return 0

            self.term_window.addnstr(self.cpu_y, self.cpu_x + 10,
                                     "%.1f%%" % (100 - cpu['idle']), 8)
            self.term_window.addnstr(self.cpu_y + 1, self.cpu_x, _("User:"), 8)
            self.term_window.addnstr(self.cpu_y + 2, self.cpu_x,
                                     _("Kernel:"), 8)
            self.term_window.addnstr(self.cpu_y + 3, self.cpu_x, _("Nice:"), 8)

            alert = self.__getCpuAlert(cpu['user'])
            logs.add(alert, "CPU user", cpu['user'], proclist)
            self.term_window.addnstr(self.cpu_y + 1, self.cpu_x + 10,
                                     "%.1f" % cpu['user'], 8,
                                     self.__colors_list[alert])

            alert = self.__getCpuAlert(cpu['kernel'])
            logs.add(alert, "CPU kernel", cpu['kernel'], proclist)
            self.term_window.addnstr(self.cpu_y + 2, self.cpu_x + 10,
                                     "%.1f" % cpu['kernel'], 8,
                                     self.__colors_list[alert])
            try:
                alert = self.__getCpuAlert(cpu['nice'])
                logs.add(alert, "CPU nice", cpu['nice'], proclist)
                self.term_window.addnstr(self.cpu_y + 3, self.cpu_x + 10,
                                         "%.1f" % cpu['nice'], 8,
                                         self.__colors_list[alert])
            except:
                #~ alert = self.__getCpuAlert(cpu['idle'])
                #~ logs.add(alert, "CPU idle", cpu['idle'], proclist)
                self.term_window.addnstr(self.cpu_y + 3, self.cpu_x + 10,
                                         "%.1f" % cpu['idle'], 8)
                
        # Return the X offset to display Load and Mem
        return offset_x

    def displayLoad(self, load, core, proclist, offset_x=0):
        # Load %
        if not load:
            return 0
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]
        if (screen_y > self.load_y + 5 and
            screen_x > self.load_x + offset_x + 18):
            self.term_window.addnstr(self.load_y, self.load_x + offset_x, _("Load"), 8,
                                     self.title_color if self.hascolors else
                                     curses.A_UNDERLINE)
            self.term_window.addnstr(self.load_y, self.load_x + offset_x + 10,
                                     str(core) + _("-Core"), 8)
            self.term_window.addnstr(self.load_y + 1, self.load_x + offset_x,
                                     _("1 min:"), 8)
            self.term_window.addnstr(self.load_y + 2, self.load_x + offset_x,
                                     _("5 min:"), 8)
            self.term_window.addnstr(self.load_y + 3, self.load_x + offset_x,
                                     _("15 min:"), 8)

            self.term_window.addnstr(self.load_y + 1, self.load_x + offset_x + 10,
                                     "{0:.2f}".format(load['min1']), 8)

            alert = self.__getLoadAlert(load['min5'], core)
            logs.add(alert, "LOAD 5-min", load['min5'], proclist)
            self.term_window.addnstr(self.load_y + 2, self.load_x + offset_x + 10,
                                     "{0:.2f}".format(load['min5']), 8,
                                     self.__colors_list[alert])

            alert = self.__getLoadAlert(load['min15'], core)
            logs.add(alert, "LOAD 15-min", load['min15'], proclist)
            self.term_window.addnstr(self.load_y + 3, self.load_x + offset_x + 10,
                                     "{0:.2f}".format(load['min15']), 8,
                                     self.__colors_list[alert])

    def displayMem(self, mem, memswap, proclist, offset_x=0):
        # MEM
        if not mem or not memswap:
            return 0
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]
        if (screen_y > self.mem_y + 5 and
            screen_x > self.mem_x + offset_x + 38):
            self.term_window.addnstr(self.mem_y, self.mem_x + offset_x, _("Mem"), 8,
                                     self.title_color if self.hascolors else
                                     curses.A_UNDERLINE)
            self.term_window.addnstr(self.mem_y + 1, self.mem_x + offset_x,
                                     _("Total:"), 6)
            self.term_window.addnstr(self.mem_y + 2, self.mem_x + offset_x, _("Used:"), 6)
            self.term_window.addnstr(self.mem_y + 3, self.mem_x + offset_x, _("Free:"), 6)

            self.term_window.addnstr(self.mem_y, self.mem_x + offset_x + 9,
                                     "{0:.1%}".format(mem['percent'] / 100), 8)
            self.term_window.addnstr(self.mem_y + 1, self.mem_x + offset_x + 9,
                                     self.__autoUnit(mem['total']), 8)
            self.term_window.addnstr(self.mem_y + 2, self.mem_x + offset_x + 9,
                                     self.__autoUnit(mem['used']), 8)
            self.term_window.addnstr(self.mem_y + 3, self.mem_x + offset_x + 9,
                                     self.__autoUnit(mem['free']), 8)

            # real memory usage
            real_used_phymem = mem['used'] - mem['cache']
            real_free_phymem = mem['free'] + mem['cache']
            alert = self.__getMemAlert(real_used_phymem, mem['total'])
            logs.add(alert, "MEM real", real_used_phymem, proclist)
            self.term_window.addnstr(
                self.mem_y + 2, self.mem_x + offset_x + 15,
                "({0})".format(self.__autoUnit(real_used_phymem)), 8,
                self.__colors_list[alert])
            self.term_window.addnstr(
                self.mem_y + 3, self.mem_x + offset_x + 15,
                "({0})".format(self.__autoUnit(real_free_phymem)), 8)

            # Swap
            self.term_window.addnstr(self.mem_y, self.mem_x + offset_x + 25, _("Swap"), 8,
                                     self.title_color if self.hascolors else
                                     curses.A_UNDERLINE)
            self.term_window.addnstr(self.mem_y + 1, self.mem_x + offset_x + 25,
                                     _("Total:"), 6)
            self.term_window.addnstr(self.mem_y + 2, self.mem_x + offset_x + 25,
                                     _("Used:"), 6)
            self.term_window.addnstr(self.mem_y + 3, self.mem_x + offset_x + 25,
                                     _("Free:"), 6)

            self.term_window.addnstr(self.mem_y, self.mem_x + offset_x + 34,
                                     "{0:.1%}".format(memswap['percent'] / 100),
                                     8)
            alert = self.__getMemAlert(memswap['used'], memswap['total'])
            logs.add(alert, "MEM swap", memswap['used'], proclist)
            self.term_window.addnstr(self.mem_y + 1, self.mem_x + offset_x + 34,
                                     self.__autoUnit(memswap['total']), 8)
            self.term_window.addnstr(self.mem_y + 2, self.mem_x + offset_x + 34,
                                     self.__autoUnit(memswap['used']), 8,
                                     self.__colors_list[alert])
            self.term_window.addnstr(self.mem_y + 3, self.mem_x + offset_x + 34,
                                     self.__autoUnit(memswap['free']), 8)

    def displayNetwork(self, network):
        """
        Display the network interface bitrate
        Return the number of interfaces
        """
        # Network interfaces bitrate
        if not self.network_tag:
            return 0
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]
        if (screen_y > self.network_y + 3 and
            screen_x > self.network_x + 28):
            # Network interfaces bitrate
            self.term_window.addnstr(self.network_y, self.network_x,
                                     _("Network"), 8, self.title_color if
                                     self.hascolors else curses.A_UNDERLINE)
            self.term_window.addnstr(self.network_y, self.network_x + 10,
                                     _("Rx/s"), 8)
            self.term_window.addnstr(self.network_y, self.network_x + 19,
                                     _("Tx/s"), 8)

            # If there is no data to display...
            if not network:
                self.term_window.addnstr(self.network_y + 1, self.network_x,
                                         _("Compute data..."), 15)
                return 3

            # Adapt the maximum interface to the screen
            ret = 2
            net_num = min(screen_y - self.network_y - 3, len(network))
            for i in range(0, net_num):
                elapsed_time = max(1, self.__refresh_time)
                self.term_window.addnstr(
                    self.network_y + 1 + i, self.network_x,
                    network[i]['interface_name'] + ':', 8)
                if (self.net_byteps_tag):
                    rx = self.__autoUnit(network[i]['rx'] / elapsed_time)
                    tx = self.__autoUnit(network[i]['tx'] / elapsed_time)
                else:
                    rx = self.__autoUnit(network[i]['rx'] / elapsed_time * 8) + "b"
                    tx = self.__autoUnit(network[i]['tx'] / elapsed_time * 8) + "b"
                self.term_window.addnstr(
                    self.network_y + 1 + i, self.network_x + 10, rx, 8)
                self.term_window.addnstr(
                    self.network_y + 1 + i, self.network_x + 19, tx, 8)
                ret = ret + 1
            return ret
        return 0

    def displayDiskIO(self, diskio, offset_y=0):
        # Disk input/output rate
        if not self.diskio_tag:
            return 0
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]
        self.diskio_y = offset_y
        if (screen_y > self.diskio_y + 3 and
            screen_x > self.diskio_x + 28):
            self.term_window.addnstr(self.diskio_y, self.diskio_x,
                                     _("Disk I/O"), 8,
                                     self.title_color if self.hascolors else
                                     curses.A_UNDERLINE)
            self.term_window.addnstr(self.diskio_y, self.diskio_x + 10,
                                     _("In/s"), 8)
            self.term_window.addnstr(self.diskio_y, self.diskio_x + 19,
                                     _("Out/s"), 8)

            # If there is no data to display...
            if not diskio:
                self.term_window.addnstr(self.diskio_y + 1, self.diskio_x,
                                         _("Compute data..."), 15)
                return 3

            # Adapt the maximum disk to the screen
            disk = 0
            disk_num = min(screen_y - self.diskio_y - 3, len(diskio))
            for disk in range(0, disk_num):
                elapsed_time = max(1, self.__refresh_time)
                self.term_window.addnstr(
                    self.diskio_y + 1 + disk, self.diskio_x,
                    diskio[disk]['disk_name'] + ':', 8)
                self.term_window.addnstr(
                    self.diskio_y + 1 + disk, self.diskio_x + 10,
                    self.__autoUnit(
                        diskio[disk]['write_bytes'] / elapsed_time), 8)
                self.term_window.addnstr(
                    self.diskio_y + 1 + disk, self.diskio_x + 19,
                    self.__autoUnit(
                        diskio[disk]['read_bytes'] / elapsed_time), 8)
            return disk + 3
        return 0

    def displayFs(self, fs, offset_y=0):
        # Filesystem stats
        if not fs or not self.fs_tag:
            return 0
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]
        self.fs_y = offset_y
        if (screen_y > self.fs_y + 3 and
            screen_x > self.fs_x + 28):
            self.term_window.addnstr(self.fs_y, self.fs_x, _("Mount"), 8,
                                     self.title_color if self.hascolors else
                                     curses.A_UNDERLINE)
            self.term_window.addnstr(self.fs_y, self.fs_x + 10, _("Total"), 7)
            self.term_window.addnstr(self.fs_y, self.fs_x + 19, _("Used"), 7)

            # Adapt the maximum disk to the screen
            mounted = 0
            fs_num = min(screen_y - self.fs_y - 3, len(fs))
            for mounted in range(0, fs_num):
                self.term_window.addnstr(
                    self.fs_y + 1 + mounted,
                    self.fs_x, fs[mounted]['mnt_point'], 8)
                self.term_window.addnstr(
                    self.fs_y + 1 + mounted,
                    self.fs_x + 10, self.__autoUnit(fs[mounted]['size']), 8)
                self.term_window.addnstr(
                    self.fs_y + 1 + mounted,
                    self.fs_x + 19, self.__autoUnit(fs[mounted]['used']), 8,
                    self.__getFsColor(fs[mounted]['used'],
                                      fs[mounted]['size']))
            return mounted + 3
        return 0

    def displayLog(self, offset_y=0):
        # Logs
        if logs.len() == 0 or not self.log_tag:
            return 0
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]
        self.log_y = offset_y
        if (screen_y > self.log_y + 3 and
            screen_x > self.log_x + 79):
            self.log_y = max(offset_y, screen_y - 3 -
                             min(offset_y - 3, screen_y - self.log_y,
                                 logs.len()))
            logtodisplay_count = min(screen_y - self.log_y - 3, logs.len())
            logmsg = _("WARNING|CRITICAL logs for CPU|LOAD|MEM")
            if (logtodisplay_count > 1):
                logmsg += (_(" (lasts ") + str(logtodisplay_count) +
                           _(" entries)"))
            else:
                logmsg += _(" (one entry)")
            self.term_window.addnstr(self.log_y, self.log_x, logmsg, 79,
                                     self.title_color if self.hascolors else
                                     curses.A_UNDERLINE)

            # Adapt the maximum log to the screen
            logcount = 0
            log = logs.get()
            for logcount in range(0, logtodisplay_count):
                logmsg = "  " + str(datetime.fromtimestamp(log[logcount][0]))
                if (log[logcount][1] > 0):
                    logmark = ' '
                    logmsg += (" > " +
                               str(datetime.fromtimestamp(log[logcount][1])))
                else:
                    logmark = '~'
                    logmsg += " > " + "%19s" % "___________________"
                if log[logcount][3][:3] == "MEM":
                    logmsg += " {0} ({1}/{2}/{3})".format(
                        log[logcount][3],
                        self.__autoUnit(log[logcount][6]),
                        self.__autoUnit(log[logcount][5]),
                        self.__autoUnit(log[logcount][4]))
                else:
                    logmsg += " {0} ({1:.1f}/{2:.1f}/{3:.1f})".format(
                        log[logcount][3], log[logcount][6],
                        log[logcount][5], log[logcount][4])
                # Add top process
                if (log[logcount][9] != []):
                    logmsg += " - Top process: {0}".format(
                            log[logcount][9][0]['name'])
                # Display the log
                self.term_window.addnstr(self.log_y + 1 + logcount,
                                         self.log_x, logmsg, len(logmsg))
                self.term_window.addnstr(self.log_y + 1 + logcount,
                                         self.log_x, logmark, 1,
                                         self.__colors_list[log[logcount][2]])
            return logcount + 3
        return 0

    def displayProcess(self, processcount, processlist, log_count=0):
        # Process
        if not processcount:
            return 0
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]
        # If there is no network & diskio & fs stats
        # then increase process window
        if (not self.network_tag and
            not self.diskio_tag and
            not self.fs_tag):
            process_x = 0
        else:
            process_x = self.process_x
        # Display the process summary
        if (screen_y > self.process_y + 4 and
            screen_x > process_x + 48):
            # Processes sumary
            self.term_window.addnstr(self.process_y, process_x, _("Processes"),
                                     9, self.title_color if self.hascolors else
                                     curses.A_UNDERLINE)
            other = (processcount['total'] -
                     stats.getProcessCount()['running'] -
                     stats.getProcessCount()['sleeping'])
            self.term_window.addnstr(
                self.process_y, process_x + 10,
                "{0}, {1} {2}, {3} {4}, {5} {6}".format(
                    str(processcount['total']),
                    str(processcount['running']),
                    _("running"),
                    str(processcount['sleeping']),
                    _("sleeping"),
                    str(other),
                    _("other")), 42)

        # Processes detail
        if (screen_y > self.process_y + 4 and
            screen_x > process_x + 49):

            # Display the process detail
            tag_pid = False
            tag_uid = False
            tag_nice = False
            tag_status = False
            tag_proc_time = False
            tag_io = False
            if screen_x > process_x + 55:
                tag_pid = True
            if screen_x > process_x + 64:
                tag_uid = True
            if screen_x > process_x + 70:
                tag_nice = True
            if screen_x > process_x + 74:
                tag_status = True
            if screen_x > process_x + 77:
                tag_proc_time = True
            if screen_x > process_x + 97:
                tag_io = True

            if not psutil_get_io_counter_tag:
                tag_io = False
                
            # VMS
            self.term_window.addnstr(
                self.process_y + 2, process_x,
                _("VIRT"), 5)
            # RSS
            self.term_window.addnstr(
                self.process_y + 2, process_x + 7,
                _("RES"), 5)
            # CPU%
            self.term_window.addnstr(
                self.process_y + 2, process_x + 14,
                _("CPU%"), 5, curses.A_UNDERLINE
                if self.getProcessSortedBy() == 'cpu_percent' else 0)
            # MEM%
            self.term_window.addnstr(
                self.process_y + 2, process_x + 21,
                _("MEM%"), 5, curses.A_UNDERLINE
                if self.getProcessSortedBy() == 'memory_percent' else 0)
            process_name_x = 28
            # If screen space (X) is available then:
            # PID
            if tag_pid:
                self.term_window.addnstr(
                    self.process_y + 2, process_x + process_name_x,
                    _("PID"), 6)
                process_name_x += 7
            # UID
            if tag_uid:
                self.term_window.addnstr(
                    self.process_y + 2, process_x + process_name_x,
                    _("USER"), 8)
                process_name_x += 10
            # NICE
            if tag_nice:
                self.term_window.addnstr(
                    self.process_y + 2, process_x + process_name_x,
                    _("NI"), 3)
                process_name_x += 4
            # STATUS
            if tag_status:
                self.term_window.addnstr(
                    self.process_y + 2, process_x + process_name_x,
                    _("S"), 1)
                process_name_x += 3
            # TIME+
            if tag_proc_time:
                self.term_window.addnstr(
                    self.process_y + 2, process_x + process_name_x,
                    _("TIME+"), 8)
                process_name_x += 10
            # IO
            if tag_io:
                self.term_window.addnstr(
                    self.process_y + 2, process_x + process_name_x,
                    _("IO_R"), 6)
                process_name_x += 8
                self.term_window.addnstr(
                    self.process_y + 2, process_x + process_name_x,
                    _("IO_W"), 6)
                process_name_x += 8               
            # PROCESS NAME
            self.term_window.addnstr(
                self.process_y + 2, process_x + process_name_x,
                _("NAME"), 12, curses.A_UNDERLINE
                if self.getProcessSortedBy() == 'name' else 0)

            # If there is no data to display...
            if not processlist:
                self.term_window.addnstr(self.process_y + 3, self.process_x,
                                         _("Compute data..."), 15)
                return 6

            proc_num = min(screen_y - self.term_h +
                           self.process_y - log_count + 5,
                           len(processlist))
            for processes in range(0, proc_num):
                # VMS
                process_size = processlist[processes]['memory_info'][1]
                self.term_window.addnstr(
                    self.process_y + 3 + processes, process_x,
                    self.__autoUnit(process_size), 5)
                # RSS
                process_resident = processlist[processes]['memory_info'][0]
                self.term_window.addnstr(
                    self.process_y + 3 + processes, process_x + 7,
                    self.__autoUnit(process_resident), 5)
                # CPU%
                cpu_percent = processlist[processes]['cpu_percent']
                if psutil_get_cpu_percent_tag:
                    self.term_window.addnstr(
                        self.process_y + 3 + processes, process_x + 14,
                        "{0:.1f}".format(cpu_percent), 5,
                        self.__getProcessColor(cpu_percent))
                else:
                    self.term_window.addnstr(
                        self.process_y + 3 + processes, process_x, "N/A", 8)
                # MEM%
                memory_percent = processlist[processes]['memory_percent']
                self.term_window.addnstr(
                    self.process_y + 3 + processes, process_x + 21,
                    "{0:.1f}".format(memory_percent), 5,
                    self.__getProcessColor(memory_percent))
                # If screen space (X) is available then:
                # PID
                if tag_pid:
                    pid = processlist[processes]['pid']
                    self.term_window.addnstr(
                        self.process_y + 3 + processes, process_x + 28,
                        str(pid), 6)
                # UID
                if tag_uid:
                    uid = processlist[processes]['username']
                    self.term_window.addnstr(
                        self.process_y + 3 + processes, process_x + 35,
                        str(uid), 8)
                # NICE
                if tag_nice:
                    nice = processlist[processes]['nice']
                    self.term_window.addnstr(
                        self.process_y + 3 + processes, process_x + 45,
                        str(nice), 3)
                # STATUS
                if tag_status:
                    status = processlist[processes]['status']
                    self.term_window.addnstr(
                        self.process_y + 3 + processes, process_x + 49,
                        str(status), 1)
                # TIME+
                if tag_proc_time:
                    process_time = processlist[processes]['cpu_times']
                    dtime = timedelta(seconds=sum(process_time))
                    dtime = "{0}:{1}.{2}".format(
                                str(dtime.seconds // 60 % 60).zfill(2),
                                str(dtime.seconds % 60).zfill(2),
                                str(dtime.microseconds)[:2])
                    self.term_window.addnstr(
                        self.process_y + 3 + processes, process_x + 52,
                        dtime, 8)
                # IO
                if tag_io:
                    if processlist[processes]['io_counters'] == {}:
                        self.term_window.addnstr(
                            self.process_y + 3 + processes, process_x + 62,
                            _("A_DENY"), 6)
                        self.term_window.addnstr(
                            self.process_y + 3 + processes, process_x + 70,
                            _("A_DENY"), 6)
                    else:
                        # Processes are only refresh every 2 refresh_time
                        #~ elapsed_time = max(1, self.__refresh_time) * 2
                        io_read = processlist[processes]['io_counters'][2]
                        self.term_window.addnstr(
                            self.process_y + 3 + processes, process_x + 62,
                            self.__autoUnit(io_read), 6)
                        io_write = processlist[processes]['io_counters'][3]
                        self.term_window.addnstr(
                            self.process_y + 3 + processes, process_x + 70,
                            self.__autoUnit(io_write), 6)
                        
                # display process command line
                max_process_name = screen_x - process_x - process_name_x
                process_name = processlist[processes]['name']
                process_cmdline = processlist[processes]['cmdline']
                if (len(process_cmdline) > max_process_name or
                    len(process_cmdline) == 0):
                    command = process_name
                else:
                    command = process_cmdline
                self.term_window.addnstr(self.process_y + 3 + processes,
                                         process_x + process_name_x,
                                         command, max_process_name)

    def displayCaption(self):
        # Caption
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]
        if (client_tag):
            msg_client = _("Connected to:")+" "+format(server_ip)
        msg_help = _("Press 'h' for help")
        if (client_tag):        
            if (screen_y > self.caption_y and
                screen_x > self.caption_x + len(msg_client)):
                self.term_window.addnstr(max(self.caption_y, screen_y - 1),
                                        self.caption_x, msg_client, len(msg_client),
                                        self.title_color if self.hascolors else
                                        curses.A_UNDERLINE)
            if (screen_x > self.caption_x + len(msg_client)+3+len(msg_help)):
                self.term_window.addnstr(max(self.caption_y, screen_y - 1),
                                        self.caption_x+len(msg_client), " | "+msg_help, 3+len(msg_help))                
        else:
            self.term_window.addnstr(max(self.caption_y, screen_y - 1),
                                    self.caption_x, msg_help, len(msg_help))
                
    def displayHelp(self):
        """
        Show the help panel
        """
        
        if not self.help_tag:
            return 0
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]
        if (screen_y > self.help_y + 23 and
            screen_x > self.help_x + 79):
            # Console 80x24 is mandatory to display the help message
            self.erase()

            try:
                self.term_window.addnstr(
                    self.help_y, self.help_x,
                    _("Glances {0} with PsUtil {1}").format(
                        self.__version, psutil.__version__),
                    79, self.title_color if self.hascolors else 0)
            except:
                self.term_window.addnstr(
                    self.help_y, self.help_x,
                    _("Glances {0}").format(self.__version),
                    79, self.title_color if self.hascolors else 0)

            self.term_window.addnstr(self.help_y + 2, self.help_x,
                                     _("Captions: "), 79)
            self.term_window.addnstr(self.help_y + 2, self.help_x + 10,
                                     _("   OK   "), 8, self.default_color)
            self.term_window.addnstr(self.help_y + 2, self.help_x + 18,
                                     _("CAREFUL "), 8, self.ifCAREFUL_color)
            self.term_window.addnstr(self.help_y + 2, self.help_x + 26,
                                     _("WARNING "), 8, self.ifWARNING_color)
            self.term_window.addnstr(self.help_y + 2, self.help_x + 34,
                                     _("CRITICAL"), 8, self.ifCRITICAL_color)

            width = 5
            self.term_window.addnstr(
                self.help_y + 4, self.help_x,
                "{0:^{width}} {1}".format(
                    _("Key"), _("Function"), width=width),
                79, self.title_color if self.hascolors else 0)
            self.term_window.addnstr(
                self.help_y + 5, self.help_x,
                "{0:^{width}} {1}".format(
                    _("a"), _("Sort processes automatically"), width=width),
                79, self.ifCRITICAL_color2
                    if not psutil_get_cpu_percent_tag else 0)
            self.term_window.addnstr(
                self.help_y + 6, self.help_x,
                "{0:^{width}} {1}".format(
                    _("b"), _("Switch between bit/s or byte/s for network IO"),
                              width=width), 79, self.ifCRITICAL_color2
                    if not psutil_get_cpu_percent_tag else 0)
            self.term_window.addnstr(
                self.help_y + 7, self.help_x,
                "{0:^{width}} {1}".format(
                    _("c"), _("Sort processes by CPU%"), width=width),
                79, self.ifCRITICAL_color2
                    if not psutil_get_cpu_percent_tag else 0)
            self.term_window.addnstr(
                self.help_y + 8, self.help_x,
                "{0:^{width}} {1}".format(
                    _("m"), _("Sort processes by MEM%"), width=width), 79)
            self.term_window.addnstr(
                self.help_y + 9, self.help_x,
                "{0:^{width}} {1}".format(
                    _("p"), _("Sort processes by name"), width=width), 79)
            self.term_window.addnstr(
                self.help_y + 10, self.help_x,
                "{0:^{width}} {1}".format(
                    _("d"), _("Show/hide disk I/O stats"), width=width),
                79, self.ifCRITICAL_color2 if not psutil_disk_io_tag else 0)
            self.term_window.addnstr(
                self.help_y + 11, self.help_x,
                "{0:^{width}} {1}".format(
                    _("f"), _("Show/hide file system stats"), width=width),
                79, self.ifCRITICAL_color2 if not psutil_fs_usage_tag else 0)
            self.term_window.addnstr(
                self.help_y + 12, self.help_x,
                "{0:^{width}} {1}".format(
                    _("n"), _("Show/hide network stats"), width=width),
                79, self.ifCRITICAL_color2 if not psutil_network_io_tag else 0)
            self.term_window.addnstr(
                self.help_y + 13, self.help_x,
                "{0:^{width}} {1}".format(
                    _("l"), _("Show/hide log messages"), width=width), 79)
            self.term_window.addnstr(
                self.help_y + 14, self.help_x,
                "{0:^{width}} {1}".format(
                    _("1"), _("Switch between global CPU and per core stats"), width=width), 79)
            self.term_window.addnstr(
                self.help_y + 15, self.help_x,
                "{0:^{width}} {1}".format(
                    _("h"), _("Show/hide this help message"), width=width), 79)
            self.term_window.addnstr(
                self.help_y + 16, self.help_x,
                "{0:^{width}} {1}".format(
                    _("q"), _("Quit (Esc and Ctrl-C also work)"), width=width),
                79)

    def displayNow(self, now):
        # Display the current date and time (now...) - Center
        if not now:
            return 0
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]
        if (screen_y > self.now_y and
            screen_x > self.now_x):
            now_msg = now.strftime(_("%Y-%m-%d %H:%M:%S"))
            self.term_window.addnstr(
                max(self.now_y, screen_y - 1),
                max(self.now_x, screen_x - 1) - len(now_msg),
                now_msg, len(now_msg))


class glancesHtml:
    """
    This class manages the HTML output
    """

    def __init__(self, htmlfolder="/usr/share", refresh_time=1):
        # Global information to display

        # Init refresh time
        self.__refresh_time = refresh_time
        
        # Set the root path
        self.root_path = htmlfolder + '/'

        # Set the templates path
        environment = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.root_path + 'html'),
            extensions=['jinja2.ext.loopcontrols'])

        # Open the template
        self.template = environment.get_template('default.html')

        # Define the colors list (hash table) for logged stats
        self.__colors_list = {
            #         CAREFUL WARNING CRITICAL
            'DEFAULT': "bgcdefault fgdefault",
            'OK': "bgcok fgok",
            'CAREFUL': "bgccareful fgcareful",
            'WARNING': "bgcwarning fgcwarning",
            'CRITICAL': "bgcritical fgcritical"
        }

    def __getAlert(self, current=0, max=100):
        # If current < CAREFUL of max then alert = OK
        # If current > CAREFUL of max then alert = CAREFUL
        # If current > WARNING of max then alert = WARNING
        # If current > CRITICAL of max then alert = CRITICAL
        if max != 0:
            (current * 100) / max
        else:
            return 'DEFAULT'

        variable = (current * 100) / max

        if variable > limits.getSTDCritical():
            return 'CRITICAL'
        elif variable > limits.getSTDWarning():
            return 'WARNING'
        elif variable > limits.getSTDCareful():
            return 'CAREFUL'

        return 'OK'

    def __getColor(self, current=0, max=100):
        """
        Return colors for logged stats
        """
        return self.__colors_list[self.__getAlert(current, max)]

    def __getCpuColor(self, cpu, max=100):
        cpu['user_color'] = self.__getColor(cpu['user'], max)
        cpu['kernel_color'] = self.__getColor(cpu['kernel'], max)
        cpu['nice_color'] = self.__getColor(cpu['nice'], max)
        return cpu

    def __getLoadAlert(self, current=0, core=1):
        # If current < CAREFUL*core of max then alert = OK
        # If current > CAREFUL*core of max then alert = CAREFUL
        # If current > WARNING*core of max then alert = WARNING
        # If current > CRITICAL*core of max then alert = CRITICAL
        if current > limits.getLOADCritical(core):
            return 'CRITICAL'
        elif current > limits.getLOADWarning(core):
            return 'WARNING'
        elif current > limits.getLOADCareful(core):
            return 'CAREFUL'    
        return 'OK'

    def __getLoadColor(self, load, core=1):
        load['min1_color'] = (
            self.__colors_list[self.__getLoadAlert(load['min1'], core)])
        load['min5_color'] = (
            self.__colors_list[self.__getLoadAlert(load['min5'], core)])
        load['min15_color'] = (
            self.__colors_list[self.__getLoadAlert(load['min15'], core)])
        return load

    def __getMemColor(self, mem):
        real_used_phymem = mem['used'] - mem['cache']
        mem['used_color'] = self.__getColor(real_used_phymem, mem['total'])

        return mem

    def __getMemSwapColor(self, memswap):
        memswap['used_color'] = self.__getColor(memswap['used'],
                                                memswap['total'])
        return memswap

    def __getFsColor(self, fs):
        mounted = 0
        for mounted in range(0, len(fs)):
            fs[mounted]['used_color'] = self.__getColor(fs[mounted]['used'],
                                                        fs[mounted]['size'])
        return fs

    def update(self, stats):
        if stats.getCpu():
            # Open the output file
            f = open(self.root_path + 'glances.html', 'w')

            # Process color

            # Render it
            # HTML Refresh is set to 1.5 * refresh_time
            # ... to avoid display while page rendering
            data = self.template.render(
                refresh=int(self.__refresh_time * 1.5),
                host=stats.getHost(),
                system=stats.getSystem(),
                cpu=self.__getCpuColor(stats.getCpu()),
                load=self.__getLoadColor(stats.getLoad(), stats.getCore()),
                core=stats.getCore(),
                mem=self.__getMemColor(stats.getMem()),
                memswap=self.__getMemSwapColor(stats.getMemSwap()),
                net=stats.getNetwork(),
                diskio=stats.getDiskIO(),
                fs=self.__getFsColor(stats.getFs()),
                proccount=stats.getProcessCount(),
                proclist=stats.getProcessList())

            # Write data into the file
            f.write(data)

            # Close the file
            f.close()


class glancesCsv:
    """
    This class manages the Csv output
    """

    def __init__(self, cvsfile="./glances.csv", refresh_time=1):
        # Global information to display

        # Init refresh time
        self.__refresh_time = refresh_time

        # Set the ouput (CSV) path
        try:
            self.__cvsfile_fd = open("%s" % cvsfile, "wb")
            self.__csvfile = csv.writer(self.__cvsfile_fd)
        except IOError as error:
            print("Can not create the output CSV file: ", error[1])
            sys.exit(0)

    def exit(self):
        self.__cvsfile_fd.close()

    def update(self, stats):
        if stats.getCpu():
            # Update CSV with the CPU stats
            cpu = stats.getCpu()
            self.__csvfile.writerow(["cpu", cpu['user'], cpu['kernel'],
                                     cpu['nice']])
        if stats.getLoad():
            # Update CSV with the LOAD stats
            load = stats.getLoad()
            self.__csvfile.writerow(["load", load['min1'], load['min5'],
                                     load['min15']])
        if (stats.getMem() and
            stats.getMemSwap()):
            # Update CSV with the MEM stats
            mem = stats.getMem()
            self.__csvfile.writerow(["mem", mem['total'], mem['used'],
                                     mem['free']])
            memswap = stats.getMemSwap()
            self.__csvfile.writerow(["swap", memswap['total'], memswap['used'],
                                     memswap['free']])
        self.__cvsfile_fd.flush()


class GlancesHandler(SimpleXMLRPCRequestHandler):
    """
    Main XMLRPC handler
    """
    rpc_paths = ('/RPC2',)


class GlancesInstance():
    """
    All the methods of this class are published as XML RPC methods
    """
    
    def init(self):
        # Return the Glances version
        return __version__ 
    
    def getAll(self):
        # Update and return all the stats
        stats.update()
        return json.dumps(stats.getAll())
    
    def getCpu(self):
        # Update and return CPU stats
        stats.update()
        return json.dumps(stats.getCpu())

    def getLoad(self):
        # Update and return LOAD stats
        stats.update()
        return json.dumps(stats.getLoad())

    def getMem(self):
        # Update and return MEM stats
        stats.update()
        return json.dumps(stats.getMem())

    def getMemSwap(self):
        # Update and return MEMSWAP stats
        stats.update()
        return json.dumps(stats.getMemSwap())


class GlancesServer():
    """
    This class creates and manages the TCP client
    """    

    def __init__(self, bind_address, bind_port = 61209, RequestHandler = GlancesHandler):
        self.server = SimpleXMLRPCServer((bind_address, bind_port),
                                    requestHandler = RequestHandler)
        self.server.register_introspection_functions()
        self.server.register_instance(GlancesInstance())
        return
    
    def serve_forever(self):
        self.server.serve_forever()
        
    def server_close(self):
        self.server.server_close()


class GlancesClient():
    """
    This class creates and manages the TCP client
    """    

    def __init__(self, server_address, server_port = 61209):
        self.client = xmlrpclib.ServerProxy('http://%s:%d' % (server_address, server_port))
        return
            
    def client_init(self):
        return __version__[:3] == self.client.init()[:3]

    def client_get(self):
        return json.loads(self.client.getAll())


# Global def
#===========


def printVersion():
    print(_("Glances version") + (" ") + __version__)


def printSyntax():
    printVersion()
    print(_("Usage: glances [-f file] [-o output] [-t sec] [-h] [-v]"))
    print("")
    print(_("\t-b\t\tDisplay network rate in Byte per second"))
    print(_("\t -B IP|NAME\tBind server to the given IP or host NAME"))
    print(_("\t-c @IP|host\tConnect to a Glances server"))
    print(_("\t-d\t\tDisable disk I/O module"))
    print(_("\t-f file\t\tSet the output folder (HTML) or file (CSV)"))
    print(_("\t-h\t\tDisplay the syntax and exit"))
    print(_("\t-m\t\tDisable mount module"))
    print(_("\t-n\t\tDisable network module"))
    print(_("\t-o output\tDefine additional output (available: HTML or CSV)"))
    print(_("\t-p PORT\t\tDefine the client or server TCP port (default: %d)" %
            server_port))
    print(_("\t-s\t\tRun Glances in server mode"))
    print(_("\t-t sec\t\tSet the refresh time in seconds (default: %d)" %
            refresh_time))
    print(_("\t-v\t\tDisplay the version and exit"))


def end():
    if server_tag:
        # Stop the server loop
        #~ print(_("Stop Glances server"))
        server.server_close()
    else:
        if client_tag:
            # Stop the client loop
            #~ client.client_quit()
            pass
        
        # Stop the classical CLI loop
        screen.end()

        if csv_tag:
            csvoutput.exit()

    sys.exit(0)


def signal_handler(signal, frame):
    end()


# Main
#=====


if __name__ == "__main__":

    # Glances - Init stuff
    ######################

    global network_bytepersec_tag
    global limits, logs, stats, screen
    global htmloutput, csvoutput
    global html_tag, csv_tag, server_tag, client_tag
    global refresh_time, client, server, server_port, server_ip

    # Set default tags
    network_bytepersec_tag = False
    html_tag = False
    csv_tag = False
    client_tag = False
    if os.name == "nt":
        # Force server mode for Windows operating system
        server_tag = True
    else:
        server_tag = False
    
    # Set the default refresh time
    refresh_time = 2
    
    # Set the default TCP port for client and server
    server_port = 61209
    bind_ip = "0.0.0.0"

    # Manage args
    try:
        opts, args = getopt.getopt(sys.argv[1:], "B:bdmnho:f:t:vsc:p:",
                                   ["bind", "bytepersec", "diskio", "mount", 
                                    "netrate", "help", "output", "file",
                                    "time", "version", "server",
                                    "client", "port"])
    except getopt.GetoptError as err:
        # Print help information and exit:
        print(str(err))
        printSyntax()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-v", "--version"):
            printVersion()
            sys.exit(0)
        elif opt in ("-s", "--server"):
            server_tag = True
        elif opt in ("-B", "--bind"):
            try:
                arg
            except NameError:
                print(_("Error: -B flag need an argument (bind IP address)"))
                sys.exit(2)
            bind_ip = arg
        elif opt in ("-c", "--client"):
            client_tag = True
            try:
                arg
            except NameError:
                print(_("Error: -c flag need an argument (server IP address/name"))
                sys.exit(2)
            server_ip = arg
        elif opt in ("-p", "--port"):
            server_port = arg
        elif opt in ("-o", "--output"):
            if arg.lower() == "html":
                try:
                    # HTML output
                    import jinja2
                except ImportError:
                    print(_("Error: Need Jinja2 library to export into HTML"))
                    print()
                    print(_("Try to install the python-jinja2 package"))
                    sys.exit(2)
                else:
                    html_tag = True
            elif arg.lower() == "csv":
                try:
                    # CSV output
                    import csv
                except ImportError:
                    print(_("Error: Need CSV library to export to CSV"))
                    sys.exit(2)
                else:
                    csv_tag = True
            else:
                print(_("Error: Unknown output %s" % arg))
                printSyntax()
                sys.exit(2)
        elif opt in ("-f", "--file"):
            output_file = arg
            output_folder = arg
        elif opt in ("-t", "--time"):
            if int(arg) >= 1:
                refresh_time = int(arg)
            else:
                print(_("Error: Refresh time should be a positive integer"))
                sys.exit(2)
        elif opt in ("-d", "--diskio"):
            psutil_disk_io_tag = False
        elif opt in ("-m", "--mount"):
            psutil_fs_usage_tag = False
        elif opt in ("-n", "--netrate"):
            psutil_network_io_tag = False
        elif opt in ("-b", "--bytepersec"):
            network_bytepersec_tag = True
        else:
            printSyntax()
            sys.exit(0)

    # Check options
    if server_tag:
        if client_tag:
            print(_("Error: Can not use both -s and -c flag"))
            sys.exit(2)
        if html_tag or csv_tag:
            print(_("Error: Can not use both -s and -o flag"))
            sys.exit(2)

    if client_tag:
        if html_tag or csv_tag:
            print(_("Error: Can not use both -c and -o flag"))
            sys.exit(2)
    
    if html_tag:
        try:
            output_folder
        except UnboundLocalError:
            print(_("Error: HTML export (-o html) need"
                    "output folder definition (-f <folder>)"))
            sys.exit(2)

    if csv_tag:
        try:
            output_file
        except UnboundLocalError:
            print(_("Error: CSV export (-o csv) need "
                    "output file definition (-f <file>)"))
            sys.exit(2)

    # Catch CTRL-C
    signal.signal(signal.SIGINT, signal_handler)

    # Optimization of the import step
    # Only usefull lib are imported in order to reduce the memory print
    if not server_tag:
        # Do not load curses lib for server
        try:
            import curses
            import curses.panel
        except ImportError:
            print(_('Curses module not found. Glances cannot start.'))
            print(_('Glances requires at least Python 2.6 or higher.'))
            print()
            sys.exit(1)

    if client_tag:
        psutil_get_cpu_percent_tag = True
        psutil_get_io_counter_tag = True
        psutil_mem_usage_tag = True
        psutil_mem_vm = True
        psutil_fs_usage_tag = True
        psutil_disk_io_tag = True
        psutil_network_io_tag = True
    else:
        # Do not load psutil lib for client
        try:
            import psutil
        except ImportError:
            print(_('PsUtil module not found. Glances cannot start.'))
            print()
            print(_('On Ubuntu 12.04 or higher:'))
            print(_('$ sudo apt-get install python-psutil'))
            print()
            print(_('To install PsUtil using pip (as root):'))
            print(_('# pip install psutil'))
            print()
            sys.exit(1)

        try:
            # get_cpu_percent method only available with PsUtil 0.2.0+
            psutil.Process(os.getpid()).get_cpu_percent(interval=0)
        except Exception:
            psutil_get_cpu_percent_tag = False
        else:
            psutil_get_cpu_percent_tag = True

        try:
            # get_io_counter method only available with PsUtil 0.2.1+
            psutil.Process(os.getpid()).get_io_counters()
        except Exception:
            psutil_get_io_counter_tag = False
        else:
            # get_io_counter only available on Linux
            if sys.platform.startswith("linux"):
                psutil_get_io_counter_tag = True
            else:
                psutil_get_io_counter_tag = False

        try:
            # virtual_memory() is only available with PsUtil 0.6+
            psutil.virtual_memory()
        except:    
            try:
                # (phy|virt)mem_usage methods only available with PsUtil 0.3.0+
                psutil.phymem_usage()
                psutil.virtmem_usage()
            except Exception:
                psutil_mem_usage_tag = False
            else:
                psutil_mem_usage_tag = True
                psutil_mem_vm = False
        else:
            psutil_mem_usage_tag = True
            psutil_mem_vm = True

        try:
            # disk_(partitions|usage) methods only available with PsUtil 0.3.0+
            psutil.disk_partitions()
            psutil.disk_usage('/')
        except Exception:
            psutil_fs_usage_tag = False
        else:
            psutil_fs_usage_tag = True

        try:
            # disk_io_counters method only available with PsUtil 0.4.0+
            psutil.disk_io_counters()
        except Exception:
            psutil_disk_io_tag = False
        else:
            psutil_disk_io_tag = True

        try:
            # network_io_counters method only available with PsUtil 0.4.0+
            psutil.network_io_counters()
        except Exception:
            psutil_network_io_tag = False
        else:
            psutil_network_io_tag = True
        
    # Init Glances depending of the mode (standalone, client, server)    
    if server_tag:
        from SimpleXMLRPCServer import SimpleXMLRPCServer
        import json
        import collections

        # Init the server
        print(_("Glances is listenning on %s:%s") % (bind_ip, server_port))
        server = GlancesServer(bind_ip, server_port, GlancesHandler)

        # Init stats
        stats = glancesStats(server_tag = True) 
    elif client_tag:
        import xmlrpclib
        import json
        import collections

        # Init the client (displaying server stat in the CLI)
        
        client = GlancesClient(server_ip, server_port)

        # Test if client and server are in the same major version
        if not client.client_init():
            print(_("Error: The server version is not compatible"))
            sys.exit(2)
        
        # Init Limits
        limits = glancesLimits()

        # Init Logs
        logs = glancesLogs()

        # Init stats
        stats = glancesStats(client_tag = True)

        # Init screen
        screen = glancesScreen(refresh_time=refresh_time)            
    else:
        # Init the classical CLI
        
        # Init Limits
        limits = glancesLimits()

        # Init Logs
        logs = glancesLogs()

        # Init stats
        stats = glancesStats()

        # Init HTML output
        if html_tag:
            htmloutput = glancesHtml(htmlfolder=output_folder,
                                     refresh_time=refresh_time)

        # Init CSV output
        if csv_tag:
            csvoutput = glancesCsv(cvsfile=output_file,
                                   refresh_time=refresh_time)

        # Init screen
        screen = glancesScreen(refresh_time=refresh_time)

    # Glances - Main loop
    #####################
    
    if server_tag:
        # Start the server loop
        server.serve_forever()
    elif client_tag:
        # Start the client (CLI) loop
        while True:           
            # Get server system informations            
            stats.update(client.client_get())

            # Update the screen
            screen.update(stats)
    else:
        # Start the standalone (CLI) loop
        while True:
            # Get system informations
            stats.update()

            # Update the screen
            screen.update(stats)

            # Update the HTML output
            if html_tag:
                htmloutput.update(stats)

            # Update the CSV output
            if csv_tag:
                csvoutput.update(stats)

# The end...
