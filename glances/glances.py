#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Glances - An eye on your system
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

__appname__ = 'glances'
__version__ = "1.7.4"
__author__ = "Nicolas Hennion <nicolas@nicolargo.com>"
__licence__ = "LGPL"

# Libraries
#==========

# Standards libs
import os
import sys
import platform
import getopt
import signal
import time
from datetime import datetime, timedelta
import re
import subprocess
import locale
import gettext
import socket

# Specifics libs
import json
import collections

# For client/server authentication
from base64 import b64decode
from hashlib import md5

# Somes libs depends of OS
is_BSD = sys.platform.find('bsd') != -1
is_Linux = sys.platform.startswith('linux')
is_Mac = sys.platform.startswith('darwin')
is_Windows = sys.platform.startswith('win')

try:
    # Python 2
    from ConfigParser import RawConfigParser
    from ConfigParser import NoOptionError
except ImportError:
    # Python 3
    from configparser import RawConfigParser
    from configparser import NoOptionError

try:
    # Python 2
    from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler
    from SimpleXMLRPCServer import SimpleXMLRPCServer
except ImportError:
    # Python 3
    from xmlrpc.server import SimpleXMLRPCRequestHandler
    from xmlrpc.server import SimpleXMLRPCServer

try:
    # Python 2
    from xmlrpclib import ServerProxy, ProtocolError
except ImportError:
    # Python 3
    from xmlrpc.client import ServerProxy, ProtocolError

if not is_Windows:
    # curses did not exist on Windows (shame on it)
    try:
        import curses
        import curses.panel
    except ImportError:
        print('Curses module not found. Glances cannot start.')
        sys.exit(1)

if is_Windows:
    try:
        import colorconsole
        import colorconsole.terminal
    except ImportError:
        is_colorConsole = False
    else:
        is_colorConsole = True

try:
    # psutil is the main library used to grab stats
    import psutil
except ImportError:
    print('PsUtil module not found. Glances cannot start.')
    sys.exit(1)

psutil_version = tuple([int(num) for num in psutil.__version__.split('.')])
# this is not a mistake: psutil 0.5.1 is detected as 0.5.0
if psutil_version < (0, 5, 0):
    print('PsUtil version %s detected.' % psutil.__version__)
    print('PsUtil 0.5.1 or higher is needed. Glances cannot start.')
    sys.exit(1)

try:
    # psutil.virtual_memory() only available from psutil >= 0.6
    psutil.virtual_memory()
except Exception:
    psutil_mem_vm = False
else:
    psutil_mem_vm = True

try:
    # psutil.net_io_counters() only available from psutil >= 1.0.0
    psutil.net_io_counters()
except Exception:
    psutil_net_io_counters = False
else:
    psutil_net_io_counters = True

if not is_Mac:
    psutil_get_io_counter_tag = True
else:
    # get_io_counters() not available on OS X
    psutil_get_io_counter_tag = False

# sensors library (optional; Linux-only)
if is_Linux:
    try:
        import sensors
    except ImportError:
        sensors_lib_tag = False
    else:
        sensors_lib_tag = True
else:
    sensors_lib_tag = False

# batinfo library (optional; Linux-only)
if is_Linux:
    try:
        import batinfo
    except ImportError:
        batinfo_lib_tag = False
    else:
        batinfo_lib_tag = True
else:
    batinfo_lib_tag = False

try:
    # HTML output (optional)
    import jinja2
except ImportError:
    html_lib_tag = False
else:
    html_lib_tag = True

try:
    # CSV output (optional)
    import csv
except ImportError:
    cvs_lib_tag = False
else:
    csv_lib_tag = True

# path definitions
work_path = os.path.realpath(os.path.dirname(__file__))
appname_path = os.path.split(sys.argv[0])[0]
sys_prefix = os.path.realpath(os.path.dirname(appname_path))

# i18n
locale.setlocale(locale.LC_ALL, '')
gettext_domain = __appname__

# get locale directory
i18n_path = os.path.realpath(os.path.join(work_path, '..', 'i18n'))
sys_i18n_path = os.path.join(sys_prefix, 'share', 'locale')

if os.path.exists(i18n_path):
    locale_dir = i18n_path
elif os.path.exists(sys_i18n_path):
    locale_dir = sys_i18n_path
else:
    locale_dir = None
gettext.install(gettext_domain, locale_dir)

# Default tag
sensors_tag = False
hddtemp_tag = False
network_tag = True
diskio_tag = True
fs_tag = True
process_tag = True

# Global moved outside main for unit tests
last_update_times = {}


# Classes
#========
if is_Windows and is_colorConsole:
    import msvcrt
    import threading
    try:
        import Queue as queue
    except ImportError:
        import queue

    class ListenGetch(threading.Thread):

        def __init__(self, nom=''):
            threading.Thread.__init__(self)
            self.Terminated = False
            self.q = queue.Queue()

        def run(self):
            while not self.Terminated:
                char = msvcrt.getch()
                self.q.put(char)

        def stop(self):
            self.Terminated = True
            while not self.q.empty():
                self.q.get()

        def get(self, default=None):
            try:
                return ord(self.q.get_nowait())
            except Exception:
                return default

    class Screen():

        COLOR_DEFAULT_WIN = '0F'  # 07'#'0F'
        COLOR_BK_DEFAULT = colorconsole.terminal.colors["BLACK"]
        COLOR_FG_DEFAULT = colorconsole.terminal.colors["WHITE"]

        def __init__(self, nc):
            self.nc = nc
            self.term = colorconsole.terminal.get_terminal()
            # os.system('color %s' % self.COLOR_DEFAULT_WIN)
            self.listen = ListenGetch()
            self.listen.start()

            self.term.clear()

        def subwin(self, x, y):
            return self

        def keypad(self, id):
            return None

        def nodelay(self, id):
            return None

        def getch(self):
            return self.listen.get(27)

        def erase(self):
            self.reset()
            return None

        def addnstr(self, y, x, msg, ln, typo=0):
            try:
                fgs, bks = self.nc.colors[typo]
            except Exception:
                fgs, bks = self.COLOR_FG_DEFAULT, self.COLOR_BK_DEFAULT
            self.term.set_color(fg=fgs, bk=bks)
            self.term.print_at(x, y, msg.ljust(ln))
            self.term.set_color(fg=self.COLOR_FG_DEFAULT, bk=self.COLOR_BK_DEFAULT)

        def getmaxyx(self):
            x = (self.term._Terminal__get_console_info().srWindow.Right -
                 self.term._Terminal__get_console_info().srWindow.Left + 1)
            y = (self.term._Terminal__get_console_info().srWindow.Bottom -
                 self.term._Terminal__get_console_info().srWindow.Top + 1)
            return [y, x]

        def reset(self):
            self.term.clear()
            self.term.reset()
            return None

        def restore_buffered_mode(self):
            self.term.restore_buffered_mode()
            return None

    class WCurseLight():

        COLOR_WHITE = colorconsole.terminal.colors["WHITE"]
        COLOR_RED = colorconsole.terminal.colors["RED"]
        COLOR_GREEN = colorconsole.terminal.colors["GREEN"]
        COLOR_BLUE = colorconsole.terminal.colors["LBLUE"]
        COLOR_MAGENTA = colorconsole.terminal.colors["LPURPLE"]
        COLOR_BLACK = colorconsole.terminal.colors["BLACK"]
        A_UNDERLINE = 0
        A_BOLD = 0
        COLOR_PAIRS = 9
        colors = {}

        def __init__(self):
            self.term = Screen(self)

        def initscr(self):
            return self.term

        def start_color(self):
            return None

        def use_default_colors(self):
            return None

        def noecho(self):
            return None

        def cbreak(self):
            return None

        def curs_set(self, y):
            return None

        def has_colors(self):
            return True

        def echo(self):
            return None

        def nocbreak(self):
            return None

        def endwin(self):
            self.term.reset()
            self.term.restore_buffered_mode()
            self.term.listen.stop()

        def napms(self, t):
            time.sleep(t / 1000 if t > 1000 else 1)

        def init_pair(self, id, fg, bk):
            self.colors[id] = [max(fg, 0), max(bk, 0)]

        def color_pair(self, id):
            return id

    curses = WCurseLight()


class Timer:
    """
    The timer class
    """

    def __init__(self, duration):
        self.duration = duration
        self.start()

    def start(self):
        self.target = time.time() + self.duration

    def reset(self):
        self.start()

    def set(self, duration):
        self.duration = duration

    def finished(self):
        return time.time() > self.target


class Config:
    """
    This class is used to access/read config file, if it exists

    :param location: the custom path to search for config file
    :type location: str or None
    """

    def __init__(self, location=None):
        self.location = location
        self.filename = 'glances.conf'

        self.parser = RawConfigParser()
        self.load()

    def load(self):
        """
        Load a config file from the list of paths, if it exists
        """
        for path in self.get_paths_list():
            if os.path.isfile(path) and os.path.getsize(path) > 0:
                try:
                    if sys.version_info >= (3, 2):
                        self.parser.read(path, encoding='utf-8')
                    else:
                        self.parser.read(path)
                except UnicodeDecodeError as e:
                    print(_("Error decoding config file '%s': %s") % (path, e))
                    sys.exit(1)

                break

    def get_paths_list(self):
        """
        Get a list of config file paths, taking into account of the OS,
        priority and location.

        * running from source: /path/to/glances/conf
        * Linux: ~/.config/glances, /etc/glances
        * BSD: ~/.config/glances, /usr/local/etc/glances
        * Mac: ~/Library/Application Support/glances, /usr/local/etc/glances
        * Windows: %APPDATA%\glances

        The config file will be searched in the following order of priority:
            * /path/to/file (via -C flag)
            * /path/to/glances/conf
            * user's home directory (per-user settings)
            * {/usr/local,}/etc directory (system-wide settings)
        """
        paths = []
        conf_path = os.path.realpath(os.path.join(work_path, '..', 'conf'))

        if self.location is not None:
            paths.append(self.location)

        if os.path.exists(conf_path):
            paths.append(os.path.join(conf_path, self.filename))

        if is_Linux or is_BSD:
            paths.append(os.path.join(
                os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config'),
                __appname__, self.filename))
        elif is_Mac:
            paths.append(os.path.join(
                os.path.expanduser('~/Library/Application Support/'),
                __appname__, self.filename))
        elif is_Windows:
            paths.append(os.path.join(
                os.environ.get('APPDATA'), __appname__, self.filename))

        if is_Linux:
            paths.append(os.path.join('/etc', __appname__, self.filename))
        elif is_BSD:
            paths.append(os.path.join(
                sys.prefix, 'etc', __appname__, self.filename))
        elif is_Mac:
            paths.append(os.path.join(
                sys_prefix, 'etc', __appname__, self.filename))

        return paths

    def has_section(self, section):
        """
        Return info about the existence of a section
        """
        return self.parser.has_section(section)

    def get_option(self, section, option):
        """
        Get the float value of an option, if it exists
        """
        try:
            value = self.parser.getfloat(section, option)
        except NoOptionError:
            return
        else:
            return value

    def get_raw_option(self, section, option):
        """
        Get the raw value of an option, if it exists
        """
        try:
            value = self.parser.get(section, option)
        except NoOptionError:
            return
        else:
            return value


class monitorList:
    """
    This class describes the optionnal monitored processes list
    A list of 'important' processes to monitor.

    The list (Python list) is composed of items (Python dict)
    An item is defined (Dict keys'):
    * description: Description of the processes (max 16 chars)
    * regex: regular expression of the processes to monitor
    * command: (optional) shell command for extended stat
    * countmin: (optional) minimal number of processes
    * countmax: (optional) maximum number of processes
    """
    # Maximum number of items in the list
    __monitor_list_max_size = 10
    # The list
    __monitor_list = []

    def __init__(self):
        if config.has_section('monitor'):
            # Process monitoring list
            self.__setMonitorList('monitor', 'list')

    def __setMonitorList(self, section, key):
        """
        Init the monitored processes list
        The list is defined in the Glances configuration file
        """
        for l in range(1, self.__monitor_list_max_size + 1):
            value = {}
            key = "list_" + str(l) + "_"
            try:
                description = config.get_raw_option(section, key + "description")
                regex = config.get_raw_option(section, key + "regex")
                command = config.get_raw_option(section, key + "command")
                countmin = config.get_raw_option(section, key + "countmin")
                countmax = config.get_raw_option(section, key + "countmax")
            except Exception:
                pass
            else:
                if description is not None and regex is not None:
                    # Build the new item
                    value["description"] = description
                    value["regex"] = regex
                    value["command"] = command
                    value["countmin"] = countmin
                    value["countmax"] = countmax
                    # Add the item to the list
                    self.__monitor_list.append(value)

    def __str__(self):
        return str(self.__monitor_list)

    def __repr__(self):
        return self.__monitor_list

    def __getitem__(self, item):
        return self.__monitor_list[item]

    def __len__(self):
        return len(self.__monitor_list)

    def __get__(self, item, key):
        """
        Meta function to return key value of item
        None if not defined or item > len(list)
        """
        if item < len(self.__monitor_list):
            try:
                return self.__monitor_list[item][key]
            except Exception:
                return None
        else:
            return None

    def getAll(self):
        return self.__monitor_list

    def setAll(self, newlist):
        self.__monitor_list = newlist

    def description(self, item):
        """
        Return the description of the item number (item)
        """
        return self.__get__(item, "description")

    def regex(self, item):
        """
        Return the regular expression of the item number (item)
        """
        return self.__get__(item, "regex")

    def command(self, item):
        """
        Return the stats command of the item number (item)
        """
        return self.__get__(item, "command")

    def countmin(self, item):
        """
        Return the minimum number of processes of the item number (item)
        """
        return self.__get__(item, "countmin")

    def countmax(self, item):
        """
        Return the maximum number of processes of the item number (item)
        """
        return self.__get__(item, "countmax")


class glancesLimits:
    """
    Manage limits for each stats. A limit can be:
    * a set of careful, warning and critical values
    * a filter (for example: hide some network interfaces)

    The limit list is stored in an hash table:
    __limits_list[STAT] = [CAREFUL, WARNING, CRITICAL]

    STD is for defaults limits (CPU/MEM/SWAP/FS)
    CPU_IOWAIT limits (iowait in %)
    CPU_STEAL limits (steal in %)
    LOAD is for LOAD limits (5 min/15 min)
    TEMP is for sensors limits (temperature in °C)
    HDDTEMP is for hddtemp limits (temperature in °C)
    FS is for partitions space limits
    IODISK_HIDE is a list of disk (name) to hide
    NETWORK_HIDE is a list of network interface (name) to hide
    """
    __limits_list = {'STD': [50, 70, 90],
                     'CPU_USER': [50, 70, 90],
                     'CPU_SYSTEM': [50, 70, 90],
                     'CPU_IOWAIT': [40, 60, 80],
                     'CPU_STEAL': [10, 15, 20],
                     'LOAD': [0.7, 1.0, 5.0],
                     'MEM': [50, 70, 90],
                     'SWAP': [50, 70, 90],
                     'TEMP': [60, 70, 80],
                     'HDDTEMP': [45, 52, 60],
                     'FS': [50, 70, 90],
                     'PROCESS_CPU': [50, 70, 90],
                     'PROCESS_MEM': [50, 70, 90],
                     'IODISK_HIDE': [],
                     'NETWORK_HIDE': []}

    def __init__(self):
        # Test if the configuration file has a limits section
        if config.has_section('global'):
            # Read STD limits
            self.__setLimits('STD', 'global', 'careful')
            self.__setLimits('STD', 'global', 'warning')
            self.__setLimits('STD', 'global', 'critical')
        if config.has_section('cpu'):
            # Read CPU limits
            self.__setLimits('CPU_USER', 'cpu', 'user_careful')
            self.__setLimits('CPU_USER', 'cpu', 'user_warning')
            self.__setLimits('CPU_USER', 'cpu', 'user_critical')
            self.__setLimits('CPU_SYSTEM', 'cpu', 'system_careful')
            self.__setLimits('CPU_SYSTEM', 'cpu', 'system_warning')
            self.__setLimits('CPU_SYSTEM', 'cpu', 'system_critical')
            self.__setLimits('CPU_IOWAIT', 'cpu', 'iowait_careful')
            self.__setLimits('CPU_IOWAIT', 'cpu', 'iowait_warning')
            self.__setLimits('CPU_IOWAIT', 'cpu', 'iowait_critical')
            self.__setLimits('CPU_STEAL', 'cpu', 'steal_careful')
            self.__setLimits('CPU_STEAL', 'cpu', 'steal_warning')
            self.__setLimits('CPU_STEAL', 'cpu', 'steal_critical')
        if config.has_section('load'):
            # Read LOAD limits
            self.__setLimits('LOAD', 'load', 'careful')
            self.__setLimits('LOAD', 'load', 'warning')
            self.__setLimits('LOAD', 'load', 'critical')
        if config.has_section('memory'):
            # Read MEM limits
            self.__setLimits('MEM', 'memory', 'careful')
            self.__setLimits('MEM', 'memory', 'warning')
            self.__setLimits('MEM', 'memory', 'critical')
        if config.has_section('swap'):
            # Read MEM limits
            self.__setLimits('SWAP', 'swap', 'careful')
            self.__setLimits('SWAP', 'swap', 'warning')
            self.__setLimits('SWAP', 'swap', 'critical')
        if config.has_section('temperature'):
            # Read TEMP limits
            self.__setLimits('TEMP', 'temperature', 'careful')
            self.__setLimits('TEMP', 'temperature', 'warning')
            self.__setLimits('TEMP', 'temperature', 'critical')
        if config.has_section('hddtemperature'):
            # Read HDDTEMP limits
            self.__setLimits('HDDTEMP', 'hddtemperature', 'careful')
            self.__setLimits('HDDTEMP', 'hddtemperature', 'warning')
            self.__setLimits('HDDTEMP', 'hddtemperature', 'critical')
        if config.has_section('filesystem'):
            # Read FS limits
            self.__setLimits('FS', 'filesystem', 'careful')
            self.__setLimits('FS', 'filesystem', 'warning')
            self.__setLimits('FS', 'filesystem', 'critical')
        if config.has_section('process'):
            # Process limits
            self.__setLimits('PROCESS_CPU', 'process', 'cpu_careful')
            self.__setLimits('PROCESS_CPU', 'process', 'cpu_warning')
            self.__setLimits('PROCESS_CPU', 'process', 'cpu_critical')
            self.__setLimits('PROCESS_MEM', 'process', 'mem_careful')
            self.__setLimits('PROCESS_MEM', 'process', 'mem_warning')
            self.__setLimits('PROCESS_MEM', 'process', 'mem_critical')
        if config.has_section('iodisk'):
            # Hidden disks' list
            self.__setHidden('IODISK_HIDE', 'iodisk', 'hide')
        if config.has_section('network'):
            # Network interfaces' list
            self.__setHidden('NETWORK_HIDE', 'network', 'hide')

    def __setHidden(self, stat, section, alert='hide'):
        """
        stat: 'IODISK', 'NETWORK'
        section: 'iodisk', 'network'
        alert: 'hide'
        """
        value = config.get_raw_option(section, alert)

        # print("%s / %s = %s -> %s" % (section, alert, value, stat))
        if (value is not None):
            self.__limits_list[stat] = value.split(",")

    def __setLimits(self, stat, section, alert):
        """
        stat: 'CPU', 'LOAD', 'MEM', 'SWAP', 'TEMP', etc.
        section: 'cpu', 'load', 'memory', 'swap', 'temperature', etc.
        alert: 'careful', 'warning', 'critical'
        """
        value = config.get_option(section, alert)

        # print("%s / %s = %s -> %s" % (section, alert, value, stat))
        if alert.endswith('careful'):
            self.__limits_list[stat][0] = value
        elif alert.endswith('warning'):
            self.__limits_list[stat][1] = value
        elif alert.endswith('critical'):
            self.__limits_list[stat][2] = value

    def setAll(self, newlimits):
        self.__limits_list = newlimits
        return True

    def getAll(self):
        return self.__limits_list

    def getHide(self, stat):
        try:
            self.__limits_list[stat]
        except KeyError:
            return []
        else:
            return self.__limits_list[stat]

    def getCareful(self, stat):
        return self.__limits_list[stat][0]

    def getWarning(self, stat):
        return self.__limits_list[stat][1]

    def getCritical(self, stat):
        return self.__limits_list[stat][2]

    # TO BE DELETED AFTER THE HTML output refactoring
    def getSTDCareful(self):
        return self.getCareful('STD')

    def getSTDWarning(self):
        return self.getWarning('STD')

    def getSTDCritical(self):
        return self.getCritical('STD')
    # /TO BE DELETED AFTER THE HTML output refactoring

    def getCPUCareful(self, stat):
        return self.getCareful('CPU_' + stat.upper())

    def getCPUWarning(self, stat):
        return self.getWarning('CPU_' + stat.upper())

    def getCPUCritical(self, stat):
        return self.getCritical('CPU_' + stat.upper())

    def getLOADCareful(self, core=1):
        return self.getCareful('LOAD') * core

    def getLOADWarning(self, core=1):
        return self.getWarning('LOAD') * core

    def getLOADCritical(self, core=1):
        return self.getCritical('LOAD') * core

    def getMEMCareful(self):
        return self.getCareful('MEM')

    def getMEMWarning(self):
        return self.getWarning('MEM')

    def getMEMCritical(self):
        return self.getCritical('MEM')

    def getSWAPCareful(self):
        return self.getCareful('SWAP')

    def getSWAPWarning(self):
        return self.getWarning('SWAP')

    def getSWAPCritical(self):
        return self.getCritical('SWAP')

    def getTEMPCareful(self):
        return self.getCareful('TEMP')

    def getTEMPWarning(self):
        return self.getWarning('TEMP')

    def getTEMPCritical(self):
        return self.getCritical('TEMP')

    def getHDDTEMPCareful(self):
        return self.getCareful('HDDTEMP')

    def getHDDTEMPWarning(self):
        return self.getWarning('HDDTEMP')

    def getHDDTEMPCritical(self):
        return self.getCritical('HDDTEMP')

    def getFSCareful(self):
        return self.getCareful('FS')

    def getFSWarning(self):
        return self.getWarning('FS')

    def getFSCritical(self):
        return self.getCritical('FS')

    def getProcessCareful(self, stat='', core=1):
        if stat.upper() != 'CPU':
            # Use core only for CPU
            core = 1
        return self.getCareful('PROCESS_' + stat.upper()) * core

    def getProcessWarning(self, stat='', core=1):
        if stat.upper() != 'CPU':
            # Use core only for CPU
            core = 1
        return self.getWarning('PROCESS_' + stat.upper()) * core

    def getProcessCritical(self, stat='', core=1):
        if stat.upper() != 'CPU':
            # Use core only for CPU
            core = 1
        return self.getCritical('PROCESS_' + stat.upper()) * core


class glancesLogs:
    """
    The main class to manage logs inside the Glances software
    Logs is a list of list (stored in the self.logs_list var)
    See item description in the add function
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
            if self.logs_list[i][1] < 0 and self.logs_list[i][3] == item_type:
                return i
        return -1

    def add(self, item_state, item_type, item_value, proc_list=[], proc_desc=""):
        """
        item_state = "OK|CAREFUL|WARNING|CRITICAL"
        item_type = "CPU*|LOAD|MEM|MON"
        item_value = value
        Item is defined by:
          ["begin", "end", "WARNING|CRITICAL", "CPU|LOAD|MEM",
           MAX, AVG, MIN, SUM, COUNT,
           [top3 process list],
           "Processes description"]
        If item is a 'new one':
          Add the new item at the beginning of the logs list
        Else:
          Update the existing item
        """
        # Add Top process sort depending on alert type
        sortby = 'none'
        if item_type.startswith("MEM"):
            # Sort TOP process by memory_percent
            sortby = 'memory_percent'
        elif item_type.startswith("CPU IO") and is_Linux:
            # Sort TOP process by io_counters (only for Linux OS)
            sortby = 'io_counters'
        elif item_type.startswith("MON"):
            # Do no sort process for monitored prcesses list
            sortby = 'none'
        else:
            # Default TOP process sort is cpu_percent
            sortby = 'cpu_percent'

        # Sort processes
        if sortby != 'none':
            topprocess = sorted(proc_list, key=lambda process: process[sortby],
                                reverse=True)
        else:
            topprocess = proc_list

        # Add or update the log
        item_index = self.__itemexist__(item_type)
        if item_index < 0:
            # Item did not exist, add if WARNING or CRITICAL
            if item_state == "WARNING" or item_state == "CRITICAL":
                # Time is stored in Epoch format
                # Epoch -> DMYHMS = datetime.fromtimestamp(epoch)
                item = []
                # START DATE
                item.append(time.mktime(datetime.now().timetuple()))
                # END DATE
                item.append(-1)
                item.append(item_state)       # STATE: WARNING|CRITICAL
                item.append(item_type)        # TYPE: CPU, LOAD, MEM...
                item.append(item_value)       # MAX
                item.append(item_value)       # AVG
                item.append(item_value)       # MIN
                item.append(item_value)       # SUM
                item.append(1)                # COUNT
                item.append(topprocess[0:3])  # TOP 3 PROCESS LIST
                item.append(proc_desc)        # MONITORED PROCESSES DESC
                self.logs_list.insert(0, item)
                if self.len() > self.logs_max:
                    self.logs_list.pop()
        else:
            # Item exist, update
            if item_state == "OK" or item_state == "CAREFUL":
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
                self.logs_list[item_index][5] = (self.logs_list[item_index][7] /
                                                 self.logs_list[item_index][8])
                # TOP PROCESS LIST
                self.logs_list[item_index][9] = topprocess[0:3]
                # MONITORED PROCESSES DESC
                self.logs_list[item_index][10] = proc_desc

        return self.len()

    def clean(self, critical=False):
        """
        Clean the log list by deleting finished item
        By default, only delete WARNING message
        If critical = True, also delete CRITICAL message
        """
        # Create a new clean list
        clean_logs_list = []
        while self.len() > 0:
            item = self.logs_list.pop()
            if item[1] < 0 or (not critical and item[2] == "CRITICAL"):
                clean_logs_list.insert(0, item)
        # The list is now the clean one
        self.logs_list = clean_logs_list
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
        self.ignore_fsname = ('', 'cgroup', 'fusectl', 'gvfs-fuse-daemon',
                              'gvfsd-fuse', 'none')

        # Ignore the following FS type
        self.ignore_fstype = ('autofs', 'binfmt_misc', 'configfs', 'debugfs',
                              'devfs', 'devpts', 'devtmpfs', 'hugetlbfs',
                              'iso9660', 'linprocfs', 'mqueue', 'none',
                              'proc', 'procfs', 'pstore', 'rootfs',
                              'securityfs', 'sysfs', 'usbfs')

        # ignore FS by mount point
        self.ignore_mntpoint = ('', '/dev/shm', '/lib/init/rw', '/sys/fs/cgroup')

    def __update__(self):
        """
        Update the stats
        """
        # Reset the list
        self.fs_list = []

        # Open the current mounted FS
        fs_stat = psutil.disk_partitions(all=True)
        for fs in range(len(fs_stat)):
            fs_current = {}
            fs_current['device_name'] = fs_stat[fs].device
            if fs_current['device_name'] in self.ignore_fsname:
                continue
            fs_current['fs_type'] = fs_stat[fs].fstype
            if fs_current['fs_type'] in self.ignore_fstype:
                continue
            fs_current['mnt_point'] = fs_stat[fs].mountpoint
            if fs_current['mnt_point'] in self.ignore_mntpoint:
                continue
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


class glancesGrabSensors:
    """
    Get sensors stats using the PySensors library
    """

    def __init__(self):
        """
        Init sensors stats
        """
        try:
            sensors.init()
        except Exception:
            self.initok = False
        else:
            self.initok = True

    def __update__(self):
        """
        Update the stats
        """
        # Reset the list
        self.sensors_list = []

        # grab only temperature stats
        if self.initok:
            for chip in sensors.iter_detected_chips():
                for feature in chip:
                    sensors_current = {}
                    if feature.name.startswith('temp'):
                        sensors_current['label'] = feature.label[:20]
                        sensors_current['value'] = int(feature.get_value())
                        self.sensors_list.append(sensors_current)

    def get(self):
        self.__update__()
        return self.sensors_list

    def quit(self):
        if self.initok:
            sensors.cleanup()


class glancesGrabHDDTemp:
    """
    Get hddtemp stats using a socket connection
    """
    cache = ""
    address = "127.0.0.1"
    port = 7634

    def __init__(self):
        """
        Init hddtemp stats
        """
        try:
            sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sck.connect((self.address, self.port))
            sck.close()
        except Exception:
            self.initok = False
        else:
            self.initok = True

    def __update__(self):
        """
        Update the stats
        """
        # Reset the list
        self.hddtemp_list = []

        if self.initok:
            data = ""
            # Taking care of sudden deaths/stops of hddtemp daemon
            try:
                sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sck.connect((self.address, self.port))
                data = sck.recv(4096)
                sck.close()
            except Exception:
                hddtemp_current = {}
                hddtemp_current['label'] = "hddtemp is gone"
                hddtemp_current['value'] = 0
                self.hddtemp_list.append(hddtemp_current)
                return
            else:
                # Considering the size of "|/dev/sda||0||" as the minimum
                if len(data) < 14:
                    if len(self.cache) == 0:
                        data = "|hddtemp error||0||"
                    else:
                        data = self.cache
                self.cache = data
                fields = data.decode('utf-8').split("|")
                devices = (len(fields) - 1) // 5
                for i in range(0, devices):
                    offset = i * 5
                    hddtemp_current = {}
                    temperature = fields[offset + 3]
                    if temperature == "ERR":
                        hddtemp_current['label'] = _("hddtemp error")
                        hddtemp_current['value'] = 0
                    elif temperature == "SLP":
                        hddtemp_current['label'] = fields[offset + 1].split("/")[-1] + " is sleeping"
                        hddtemp_current['value'] = 0
                    elif temperature == "UNK":
                        hddtemp_current['label'] = fields[offset + 1].split("/")[-1] + " is unknown"
                        hddtemp_current['value'] = 0
                    else:
                        hddtemp_current['label'] = fields[offset + 1].split("/")[-1]
                        try:
                            hddtemp_current['value'] = int(temperature)
                        except TypeError:
                            hddtemp_current['label'] = fields[offset + 1].split("/")[-1] + " is unknown"
                            hddtemp_current['value'] = 0
                    self.hddtemp_list.append(hddtemp_current)

    def get(self):
        self.__update__()
        return self.hddtemp_list


class GlancesGrabProcesses:
    """
    Get processed stats using the PsUtil lib
    """

    def __init__(self, cache_timeout = 60):
        """
        Init the class to collect stats about processes
        """
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

    def __get_process_stats(self, proc):
        """
        Get process statistics
        """
        procstat = {}

        # Process ID
        procstat['pid'] = proc.pid

        # Process name (cached by PSUtil)
        procstat['name'] = proc.name

        # Process username (cached with internal cache)
        try:
            self.username_cache[procstat['pid']]
        except:
            try:
                self.username_cache[procstat['pid']] = proc.username
            except KeyError:
                try:
                    self.username_cache[procstat['pid']] = proc.uids.real
                except KeyError:
                    self.username_cache[procstat['pid']] = "?"
        procstat['username'] = self.username_cache[procstat['pid']]

        # Process command line (cached with internal cache)
        try:
            self.cmdline_cache[procstat['pid']]
        except:
            self.cmdline_cache[procstat['pid']] = ' '.join(proc.cmdline)
        procstat['cmdline'] = self.cmdline_cache[procstat['pid']]

        # Process status
        procstat['status'] = str(proc.status)[:1].upper()

        # Process nice
        procstat['nice'] = proc.get_nice()

        # Process memory
        procstat['memory_info'] = proc.get_memory_info()
        procstat['memory_percent'] = proc.get_memory_percent()

        # Process CPU
        procstat['cpu_times'] = proc.get_cpu_times()
        procstat['cpu_percent'] = proc.get_cpu_percent(interval=0)

        # Process network connections (TCP and UDP) (Experimental)
        # !!! High CPU consumption
        # try:
        #     procstat['tcp'] = len(proc.get_connections(kind="tcp"))
        #     procstat['udp'] = len(proc.get_connections(kind="udp"))
        # except:
        #     procstat['tcp'] = 0
        #     procstat['udp'] = 0

        # Process IO
        # procstat['io_counters'] is a list:
        # [read_bytes, write_bytes, read_bytes_old, write_bytes_old, io_tag]
        # If io_tag = 0 > Access denied (display "?")
        # If io_tag = 1 > No access denied (display the IO rate)
        if psutil_get_io_counter_tag:
            try:
                # Get the process IO counters
                proc_io = proc.get_io_counters()
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
        self.processlist = []
        self.processcount = {'total': 0, 'running': 0, 'sleeping': 0, 'thread': 0}

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
                if (is_BSD and procstat['name'] == 'idle' or
                    is_Windows and procstat['name'] == 'System Idle Process' or
                    is_Mac and procstat['name'] == 'kernel_task'):
                    continue
                # Update processcount (global statistics)
                try:
                    self.processcount[str(proc.status)] += 1
                except KeyError:
                    # Key did not exist, create it
                    self.processcount[str(proc.status)] = 1
                else:
                    self.processcount['total'] += 1
                # Update thread number (global statistics)
                try:
                    self.processcount['thread'] += proc.get_num_threads()
                except:
                    pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            else:
                # Update processlist
                self.processlist.append(procstat)

        # Clean internals caches if timeout is reached
        if (self.cache_timer.finished()):
            self.username_cache = {}
            self.cmdline_cache = {}
            # Restart the timer
            self.cache_timer.reset()

    def getcount(self):
        return self.processcount

    def getlist(self):
        return self.processlist


class glancesGrabBat:
    """
    Get batteries stats using the Batinfo librairie
    """

    def __init__(self):
        """
        Init batteries stats
        """
        if batinfo_lib_tag:
            try:
                self.bat = batinfo.batteries()
                self.initok = True
                self.__update__()
            except Exception:
                self.initok = False
        else:
            self.initok = False

    def __update__(self):
        """
        Update the stats
        """
        if self.initok:
            try:
                self.bat.update()
            except Exception:
                self.bat_list = []
            else:
                self.bat_list = self.bat.stat
        else:
            self.bat_list = []

    def get(self):
        # Update the stats
        self.__update__()
        return self.bat_list

    def getcapacitypercent(self):
        if not self.initok or self.bat_list == []:
            return []
        # Init the bsum (sum of percent) and bcpt (number of batteries)
        # and Loop over batteries (yes a computer could have more than 1 battery)
        bsum = 0
        for bcpt in range(len(self.get())):
            try:
                bsum = bsum + int(self.bat_list[bcpt].capacity)
            except ValueError:
                return []
        bcpt = bcpt + 1
        # Return the global percent
        return int(bsum / bcpt)


class GlancesStats:
    """
    This class store, update and give stats
    """

    def __init__(self):
        """
        Init the stats
        """
        self._init_host()

        # Init the grab error tags
        # for managing error during stats grab
        # By default, we *hope* that there is no error
        self.network_error_tag = False
        self.diskio_error_tag = False

        # Init the fs stats
        try:
            self.glancesgrabfs = glancesGrabFs()
        except Exception:
            self.glancesgrabfs = {}

        # Init the sensors stats (optional)
        if sensors_tag:
            try:
                self.glancesgrabsensors = glancesGrabSensors()
            except Exception:
                self.sensors_tag = False

        # Init the hddtemp stats (optional)
        if hddtemp_tag:
            try:
                self.glancesgrabhddtemp = glancesGrabHDDTemp()
            except Exception:
                self.hddtemp_tag = False

        if batinfo_lib_tag:
            self.glancesgrabbat = glancesGrabBat()

        # Init the process list
        self.process_list_refresh = True
        self.process_list_sortedby = ''
        self.glancesgrabprocesses = GlancesGrabProcesses()

    def _init_host(self):
        self.host = {}
        self.host['os_name'] = platform.system()
        self.host['hostname'] = platform.node()
        # More precise but not user friendly
        #~ if platform.uname()[4]:
            #~ self.host['platform'] = platform.uname()[4]
        #~ else:
            #~ self.host['platform'] = platform.architecture()[0]
        # This one is better
        self.host['platform'] = platform.architecture()[0]
        is_archlinux = os.path.exists(os.path.join("/", "etc", "arch-release"))
        if self.host['os_name'] == "Linux":
            if is_archlinux:
                self.host['linux_distro'] = "Arch Linux"
            else:
                linux_distro = platform.linux_distribution()
                self.host['linux_distro'] = ' '.join(linux_distro[:2])
            self.host['os_version'] = platform.release()
        elif self.host['os_name'] == "FreeBSD":
            self.host['os_version'] = platform.release()
        elif self.host['os_name'] == "Darwin":
            self.host['os_version'] = platform.mac_ver()[0]
        elif self.host['os_name'] == "Windows":
            os_version = platform.win32_ver()
            self.host['os_version'] = ' '.join(os_version[::2])
        else:
            self.host['os_version'] = ""

    def __update__(self, input_stats):
        """
        Update the stats
        """
        # CPU
        cputime = psutil.cpu_times(percpu=False)
        cputime_total = cputime.user + cputime.system + cputime.idle
        # Only available on some OS
        if hasattr(cputime, 'nice'):
            cputime_total += cputime.nice
        if hasattr(cputime, 'iowait'):
            cputime_total += cputime.iowait
        if hasattr(cputime, 'irq'):
            cputime_total += cputime.irq
        if hasattr(cputime, 'softirq'):
            cputime_total += cputime.softirq
        if hasattr(cputime, 'steal'):
            cputime_total += cputime.steal
        if not hasattr(self, 'cputime_old'):
            self.cputime_old = cputime
            self.cputime_total_old = cputime_total
            self.cpu = {}
        else:
            self.cputime_new = cputime
            self.cputime_total_new = cputime_total
            try:
                percent = 100 / (self.cputime_total_new -
                                 self.cputime_total_old)
                self.cpu = {'user': (self.cputime_new.user -
                                     self.cputime_old.user) * percent,
                            'system': (self.cputime_new.system -
                                       self.cputime_old.system) * percent,
                            'idle': (self.cputime_new.idle -
                                     self.cputime_old.idle) * percent}
                if hasattr(self.cputime_new, 'nice'):
                    self.cpu['nice'] = (self.cputime_new.nice -
                                        self.cputime_old.nice) * percent
                if hasattr(self.cputime_new, 'iowait'):
                    self.cpu['iowait'] = (self.cputime_new.iowait -
                                          self.cputime_old.iowait) * percent
                if hasattr(self.cputime_new, 'irq'):
                    self.cpu['irq'] = (self.cputime_new.irq -
                                       self.cputime_old.irq) * percent
                if hasattr(self.cputime_new, 'softirq'):
                    self.cpu['softirq'] = (self.cputime_new.softirq -
                                           self.cputime_old.softirq) * percent
                if hasattr(self.cputime_new, 'steal'):
                    self.cpu['steal'] = (self.cputime_new.steal -
                                         self.cputime_old.steal) * percent
                self.cputime_old = self.cputime_new
                self.cputime_total_old = self.cputime_total_new
            except Exception:
                self.cpu = {}

        # Per-CPU
        percputime = psutil.cpu_times(percpu=True)
        percputime_total = []
        for i in range(len(percputime)):
            percputime_total.append(percputime[i].user +
                                    percputime[i].system +
                                    percputime[i].idle)
        # Only available on some OS
        for i in range(len(percputime)):
            if hasattr(percputime[i], 'nice'):
                percputime_total[i] += percputime[i].nice
        for i in range(len(percputime)):
            if hasattr(percputime[i], 'iowait'):
                percputime_total[i] += percputime[i].iowait
        for i in range(len(percputime)):
            if hasattr(percputime[i], 'irq'):
                percputime_total[i] += percputime[i].irq
        for i in range(len(percputime)):
            if hasattr(percputime[i], 'softirq'):
                percputime_total[i] += percputime[i].softirq
        for i in range(len(percputime)):
            if hasattr(percputime[i], 'steal'):
                percputime_total[i] += percputime[i].steal
        if not hasattr(self, 'percputime_old'):
            self.percputime_old = percputime
            self.percputime_total_old = percputime_total
            self.percpu = []
        else:
            self.percputime_new = percputime
            self.percputime_total_new = percputime_total
            perpercent = []
            self.percpu = []
            try:
                for i in range(len(self.percputime_new)):
                    perpercent.append(100 / (self.percputime_total_new[i] -
                                             self.percputime_total_old[i]))
                    cpu = {'user': (self.percputime_new[i].user -
                                    self.percputime_old[i].user) * perpercent[i],
                           'system': (self.percputime_new[i].system -
                                      self.percputime_old[i].system) * perpercent[i],
                           'idle': (self.percputime_new[i].idle -
                                    self.percputime_old[i].idle) * perpercent[i]}
                    if hasattr(self.percputime_new[i], 'nice'):
                        cpu['nice'] = (self.percputime_new[i].nice -
                                       self.percputime_old[i].nice) * perpercent[i]
                    if hasattr(self.percputime_new[i], 'iowait'):
                        cpu['iowait'] = (self.percputime_new[i].iowait -
                                         self.percputime_old[i].iowait) * perpercent[i]
                    if hasattr(self.percputime_new[i], 'irq'):
                        cpu['irq'] = (self.percputime_new[i].irq -
                                      self.percputime_old[i].irq) * perpercent[i]
                    if hasattr(self.percputime_new[i], 'softirq'):
                        cpu['softirq'] = (self.percputime_new[i].softirq -
                                          self.percputime_old[i].softirq) * perpercent[i]
                    if hasattr(self.percputime_new[i], 'steal'):
                        cpu['steal'] = (self.percputime_new[i].steal -
                                        self.percputime_old[i].steal) * perpercent[i]
                    self.percpu.append(cpu)
                self.percputime_old = self.percputime_new
                self.percputime_total_old = self.percputime_total_new
            except Exception:
                self.percpu = []

        # LOAD
        if hasattr(os, 'getloadavg'):
            getload = os.getloadavg()
            self.load = {'min1': getload[0],
                         'min5': getload[1],
                         'min15': getload[2]}
        else:
            self.load = {}

        # MEM
        # psutil >= 0.6
        if psutil_mem_vm:
            # RAM
            phymem = psutil.virtual_memory()

            # buffers and cached (Linux, BSD)
            buffers = getattr(phymem, 'buffers', 0)
            cached = getattr(phymem, 'cached', 0)

            # active and inactive not available on Windows
            active = getattr(phymem, 'active', 0)
            inactive = getattr(phymem, 'inactive', 0)

            # phymem free and usage
            total = phymem.total
            free = phymem.available  # phymem.free + buffers + cached
            used = total - free

            self.mem = {'total': total,
                        'percent': phymem.percent,
                        'used': used,
                        'free': free,
                        'active': active,
                        'inactive': inactive,
                        'buffers': buffers,
                        'cached': cached}

            # Swap
            # try... is an hack for issue #152
            try:
                virtmem = psutil.swap_memory()
            except Exception:
                self.memswap = {}
            else:
                self.memswap = {'total': virtmem.total,
                                'used': virtmem.used,
                                'free': virtmem.free,
                                'percent': virtmem.percent}
        else:
            # psutil < 0.6
            # RAM
            if hasattr(psutil, 'phymem_usage'):
                phymem = psutil.phymem_usage()

                # buffers and cached (Linux, BSD)
                buffers = getattr(psutil, 'phymem_buffers', 0)()
                cached = getattr(psutil, 'cached_phymem', 0)()

                # phymem free and usage
                total = phymem.total
                free = phymem.free + buffers + cached
                used = total - free

                # active and inactive not available for psutil < 0.6
                self.mem = {'total': total,
                            'percent': phymem.percent,
                            'used': used,
                            'free': free,
                            'buffers': buffers,
                            'cached': cached}
            else:
                self.mem = {}

            # Swap
            if hasattr(psutil, 'virtmem_usage'):
                virtmem = psutil.virtmem_usage()
                self.memswap = {'total': virtmem.total,
                                'used': virtmem.used,
                                'free': virtmem.free,
                                'percent': virtmem.percent}
            else:
                self.memswap = {}

        # NET
        if network_tag and not self.network_error_tag:
            self.network = []

            # By storing time data we enable Rx/s and Tx/s calculations in the
            # XML/RPC API, which would otherwise be overly difficult work
            # for users of the API
            time_since_update = getTimeSinceLastUpdate('net')

            if psutil_net_io_counters:
                # psutil >= 1.0.0
                try:
                    get_net_io_counters = psutil.net_io_counters(pernic=True)
                except IOError:
                    self.network_error_tag = True
            else:
                # psutil < 1.0.0
                try:
                    get_net_io_counters = psutil.network_io_counters(pernic=True)
                except IOError:
                    self.network_error_tag = True

            if not hasattr(self, 'network_old'):
                try:
                    self.network_old = get_net_io_counters
                except (IOError, UnboundLocalError):
                    self.network_error_tag = True
            else:
                self.network_new = get_net_io_counters
                for net in self.network_new:
                    try:
                        # Try necessary to manage dynamic network interface
                        netstat = {}
                        netstat['time_since_update'] = time_since_update
                        netstat['interface_name'] = net
                        netstat['cumulative_rx'] = self.network_new[net].bytes_recv
                        netstat['rx'] = (self.network_new[net].bytes_recv -
                                         self.network_old[net].bytes_recv)
                        netstat['cumulative_tx'] = self.network_new[net].bytes_sent
                        netstat['tx'] = (self.network_new[net].bytes_sent -
                                         self.network_old[net].bytes_sent)
                        netstat['cumulative_cx'] = (netstat['cumulative_rx'] +
                                                    netstat['cumulative_tx'])
                        netstat['cx'] = netstat['rx'] + netstat['tx']
                    except Exception:
                        continue
                    else:
                        self.network.append(netstat)
                self.network_old = self.network_new

        # SENSORS
        if sensors_tag:
            self.sensors = self.glancesgrabsensors.get()

        # HDDTEMP
        if hddtemp_tag:
            self.hddtemp = self.glancesgrabhddtemp.get()

        # BATERRIES INFORMATION
        if batinfo_lib_tag:
            self.batpercent = self.glancesgrabbat.getcapacitypercent()

        # DISK I/O
        if diskio_tag and not self.diskio_error_tag:
            time_since_update = getTimeSinceLastUpdate('disk')
            self.diskio = []
            if not hasattr(self, 'diskio_old'):
                try:
                    self.diskio_old = psutil.disk_io_counters(perdisk=True)
                except IOError:
                    self.diskio_error_tag = True
            else:
                self.diskio_new = psutil.disk_io_counters(perdisk=True)
                for disk in self.diskio_new:
                    try:
                        # Try necessary to manage dynamic disk creation/del
                        diskstat = {}
                        diskstat['time_since_update'] = time_since_update
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

        # FILE SYSTEM
        if fs_tag:
            self.fs = self.glancesgrabfs.get()

        # PROCESS
        if process_tag:
            self.glancesgrabprocesses.update()
            processcount = self.glancesgrabprocesses.getcount()
            process = self.glancesgrabprocesses.getlist()
            if not hasattr(self, 'process'):
                self.processcount = {}
                self.process = []
            else:
                self.processcount = processcount
                self.process = process

        # Uptime
        try:
            # For PsUtil >= 0.7.0
            self.uptime = datetime.now() - datetime.fromtimestamp(psutil.get_boot_time())
        except:
            self.uptime = datetime.now() - datetime.fromtimestamp(psutil.BOOT_TIME)
        # Convert uptime to string (because datetime is not JSONifi)
        self.uptime = str(self.uptime).split('.')[0]

        # Get the current date/time
        self.now = datetime.now()

        # Get the number of core (CPU) (Used to display load alerts)
        self.core_number = psutil.NUM_CPUS

        # get psutil version
        self.psutil_version = psutil.__version__

    def update(self, input_stats={}):
        # Update the stats
        self.__update__(input_stats)

    def getSortedBy(self):
        return self.process_list_sortedby

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
        if network_tag:
            return sorted(self.network, key=lambda network: network['interface_name'])
        else:
            return []

    def getSensors(self):
        if sensors_tag:
            return sorted(self.sensors, key=lambda sensors: sensors['label'])
        else:
            return []

    def getHDDTemp(self):
        if hddtemp_tag:
            return sorted(self.hddtemp, key=lambda hddtemp: hddtemp['label'])
        else:
            return []

    def getBatPercent(self):
        if batinfo_lib_tag:
            return self.batpercent
        else:
            return []

    def getDiskIO(self):
        if diskio_tag:
            return sorted(self.diskio, key=lambda diskio: diskio['disk_name'])
        else:
            return []

    def getFs(self):
        if fs_tag:
            return sorted(self.fs, key=lambda fs: fs['mnt_point'])
        else:
            return []

    def getProcessCount(self):
        if process_tag:
            return self.processcount
        else:
            return 0

    def getProcessList(self, sortedby='auto'):
        """
        Return the sorted process list
        """
        if not process_tag:
            return []
        if self.process == {} or 'limits' not in globals():
            return self.process

        sortedReverse = True
        if sortedby == 'auto':
            # Auto selection (default: sort by CPU%)
            sortedby = 'cpu_percent'
            # Dynamic choice
            if ('iowait' in self.cpu and
                self.cpu['iowait'] > limits.getCPUWarning(stat='iowait')):
                # If CPU IOWait > 70% sort by IORATE usage
                sortedby = 'io_counters'
            elif (self.mem['total'] != 0 and
                  self.mem['used'] * 100 / self.mem['total'] > limits.getMEMWarning()):
                # If global MEM > 70% sort by MEM usage
                sortedby = 'memory_percent'
        elif sortedby == 'name':
            sortedReverse = False

        if sortedby == 'io_counters':
            try:
                # Sort process by IO rate (sum IO read + IO write)
                listsorted = sorted(self.process,
                                    key=lambda process: process[sortedby][0] -
                                    process[sortedby][2] + process[sortedby][1] -
                                    process[sortedby][3], reverse=sortedReverse)
            except Exception:
                listsorted = sorted(self.process, key=lambda process: process['cpu_percent'],
                                    reverse=sortedReverse)
        else:
            # Others sorts
            listsorted = sorted(self.process, key=lambda process: process[sortedby],
                                reverse=sortedReverse)

        # Save the latest sort type in a global var
        self.process_list_sortedby = sortedby

        # Return the sorted list
        return listsorted

    def getPsutilVersion(self):
        return self.psutil_version

    def getNow(self):
        return self.now

    def getUptime(self):
        return self.uptime


class GlancesStatsServer(GlancesStats):

    def __init__(self):
        GlancesStats.__init__(self)

        # Init the all_stats used by the server
        # all_stats is a dict of dicts filled by the server
        self.all_stats = collections.defaultdict(dict)
        self._init_host()
        self.all_stats["host"] = self.host

    def __update__(self, input_stats):
        """
        Update the stats
        """
        GlancesStats.__update__(self, input_stats)

        self.all_stats["cpu"] = self.cpu
        self.all_stats["percpu"] = self.percpu
        self.all_stats["load"] = self.load
        self.all_stats["mem"] = self.mem
        self.all_stats["memswap"] = self.memswap
        self.all_stats["network"] = self.network if network_tag else []
        self.all_stats["sensors"] = self.sensors if sensors_tag else []
        self.all_stats["hddtemp"] = self.hddtemp if hddtemp_tag else []
        self.all_stats["batpercent"] = self.batpercent if batinfo_lib_tag else []
        self.all_stats["diskio"] = self.diskio if diskio_tag else []
        self.all_stats["fs"] = self.fs if fs_tag else []
        self.all_stats["processcount"] = self.processcount if process_tag else 0
        self.all_stats["process"] = self.process if process_tag else []
        self.all_stats["core_number"] = self.core_number
        self.all_stats["psutil_version"] = self.psutil_version
        self.all_stats["uptime"] = self.uptime

        # Get the current date/time
        self.now = datetime.now()

    def getAll(self):
        return self.all_stats


class GlancesStatsClient(GlancesStats):

    def __init__(self):
        GlancesStats.__init__(self)

    def __update__(self, input_stats):
        """
        Update the stats
        """
        if input_stats != {}:
            self.host = input_stats["host"]
            self.cpu = input_stats["cpu"]
            self.percpu = input_stats["percpu"]
            self.load = input_stats["load"]
            self.mem = input_stats["mem"]
            self.memswap = input_stats["memswap"]
            try:
                self.network = input_stats["network"]
            except Exception:
                self.network = []
            try:
                self.sensors = input_stats["sensors"]
            except Exception:
                self.sensors = []
            try:
                self.hddtemp = input_stats["hddtemp"]
            except Exception:
                self.hddtemp = []
            try:
                self.batpercent = input_stats["batpercent"]
            except Exception:
                self.batpercent = []
            try:
                self.diskio = input_stats["diskio"]
            except Exception:
                self.diskio = []
            try:
                self.fs = input_stats["fs"]
            except Exception:
                self.fs = []
            self.processcount = input_stats["processcount"]
            self.process = input_stats["process"]
            self.core_number = input_stats["core_number"]
            self.psutil_version = input_stats["psutil_version"]
            try:
                self.uptime = input_stats["uptime"]
            except Exception:
                self.uptime = None

        # Get the current date/time
        self.now = datetime.now()


class glancesScreen:
    """
    This class manage the screen (display and key pressed)
    """
    # By default the process list is automatically sorted
    # If global CPU > WANRING => Sorted by CPU usage
    # If global used MEM > WARINING => Sorted by MEM usage
    __process_sortedby = 'auto'

    def __init__(self, refresh_time=1, use_bold=1):
        # Global information to display
        self.__version = __version__

        # Init windows positions
        self.term_w = 80
        self.term_h = 24
        self.system_x = 0
        self.system_y = 0
        self.uptime_x = 79
        self.uptime_y = 0
        self.cpu_x = 0
        self.cpu_y = 2
        self.load_x = 17
        self.load_y = 2
        self.mem_x = 33
        self.mem_y = 2
        self.network_x = 0
        self.network_y = 7
        self.sensors_x = 0
        self.sensors_y = -1
        self.hddtemp_x = 0
        self.hddtemp_y = -1
        self.diskio_x = 0
        self.diskio_y = -1
        self.fs_x = 0
        self.fs_y = -1
        self.process_x = 26
        self.process_y = 7
        self.log_x = 0
        self.log_y = -1
        self.help_x = 0
        self.help_y = 0
        self.now_x = 79
        self.now_y = 3
        self.bat_x = 0
        self.bat_y = 3
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
            try:
                curses.curs_set(0)
            except Exception:
                pass

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

        if use_bold:
            A_BOLD = curses.A_BOLD
        else:
            A_BOLD = 0

        self.title_color = A_BOLD
        self.title_underline_color = A_BOLD | curses.A_UNDERLINE
        self.help_color = A_BOLD
        if self.hascolors:
            # Colors text styles
            self.no_color = curses.color_pair(1)
            self.default_color = curses.color_pair(3) | A_BOLD
            self.ifCAREFUL_color = curses.color_pair(4) | A_BOLD
            self.ifWARNING_color = curses.color_pair(5) | A_BOLD
            self.ifCRITICAL_color = curses.color_pair(2) | A_BOLD
            self.default_color2 = curses.color_pair(7) | A_BOLD
            self.ifCAREFUL_color2 = curses.color_pair(8) | A_BOLD
            self.ifWARNING_color2 = curses.color_pair(9) | A_BOLD
            self.ifCRITICAL_color2 = curses.color_pair(6) | A_BOLD
        else:
            # B&W text styles
            self.no_color = curses.A_NORMAL
            self.default_color = curses.A_NORMAL
            self.ifCAREFUL_color = curses.A_UNDERLINE
            self.ifWARNING_color = A_BOLD
            self.ifCRITICAL_color = curses.A_REVERSE
            self.default_color2 = curses.A_NORMAL
            self.ifCAREFUL_color2 = curses.A_UNDERLINE
            self.ifWARNING_color2 = A_BOLD
            self.ifCRITICAL_color2 = curses.A_REVERSE

        # Define the colors list (hash table) for logged stats
        self.__colors_list = {
            'DEFAULT': self.no_color,
            'OK': self.default_color,
            'CAREFUL': self.ifCAREFUL_color,
            'WARNING': self.ifWARNING_color,
            'CRITICAL': self.ifCRITICAL_color
        }

        # Define the colors list (hash table) for non logged stats
        self.__colors_list2 = {
            'DEFAULT': self.no_color,
            'OK': self.default_color2,
            'CAREFUL': self.ifCAREFUL_color2,
            'WARNING': self.ifWARNING_color2,
            'CRITICAL': self.ifCRITICAL_color2
        }

        # What are we going to display
        self.network_tag = network_tag
        self.sensors_tag = sensors_tag
        self.hddtemp_tag = hddtemp_tag
        self.diskio_tag = diskio_tag
        self.fs_tag = fs_tag
        self.log_tag = True
        self.help_tag = False
        self.percpu_tag = percpu_tag
        self.process_tag = process_tag
        self.net_byteps_tag = network_bytepersec_tag
        self.network_stats_combined = False
        self.network_stats_cumulative = False

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

    def __autoUnit(self, val, low_precision=False):
        """
        Make a nice human readable string out of val
        Number of decimal places increases as quantity approaches 1

        examples:
        CASE: 613421788        RESULT:       585M low_precision:       585M
        CASE: 5307033647       RESULT:      4.94G low_precision:       4.9G
        CASE: 44968414685      RESULT:      41.9G low_precision:      41.9G
        CASE: 838471403472     RESULT:       781G low_precision:       781G
        CASE: 9683209690677    RESULT:      8.81T low_precision:       8.8T
        CASE: 1073741824       RESULT:      1024M low_precision:      1024M
        CASE: 1181116006       RESULT:      1.10G low_precision:       1.1G

        parameter 'low_precision=True' returns less decimal places.
        potentially sacrificing precision for more readability
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
            value = float(val) / prefix[key]
            if value > 1:
                fixed_decimal_places = 0
                if value < 10:
                    fixed_decimal_places = 2
                elif value < 100:
                    fixed_decimal_places = 1
                if low_precision:
                    if key in 'MK':
                        fixed_decimal_places = 0
                    else:
                        fixed_decimal_places = min(1, fixed_decimal_places)
                elif key in 'K':
                    fixed_decimal_places = 0
                formatter = "{0:.%df}{1}" % fixed_decimal_places
                return formatter.format(value, key)
        return "{0!s}".format(val)

    def __getCpuAlert(self, current=0, max=100, stat=''):
        # If current < CAREFUL of max then alert = OK
        # If current > CAREFUL of max then alert = CAREFUL
        # If current > WARNING of max then alert = WARNING
        # If current > CRITICAL of max then alert = CRITICAL
        # stat is USER, SYSTEM, IOWAIT or STEAL
        try:
            variable = (current * 100) / max
        except ZeroDivisionError:
            return 'DEFAULT'

        if variable > limits.getCPUCritical(stat=stat):
            return 'CRITICAL'
        elif variable > limits.getCPUWarning(stat=stat):
            return 'WARNING'
        elif variable > limits.getCPUCareful(stat=stat):
            return 'CAREFUL'

        return 'OK'

    def __getCpuColor(self, current=0, max=100, stat=''):
        return self.__colors_list[self.__getCpuAlert(current, max, stat)]

    def __getCpuColor2(self, current=0, max=100, stat=''):
        return self.__colors_list2[self.__getCpuAlert(current, max, stat)]

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

    def __getLoadColor2(self, current=0, core=1):
        return self.__colors_list2[self.__getLoadAlert(current, core)]

    def __getMemAlert(self, current=0, max=100):
        # If current < CAREFUL of max then alert = OK
        # If current > CAREFUL of max then alert = CAREFUL
        # If current > WARNING of max then alert = WARNING
        # If current > CRITICAL of max then alert = CRITICAL
        try:
            variable = (current * 100) / max
        except ZeroDivisionError:
            return 'DEFAULT'

        if variable > limits.getMEMCritical():
            return 'CRITICAL'
        elif variable > limits.getMEMWarning():
            return 'WARNING'
        elif variable > limits.getMEMCareful():
            return 'CAREFUL'

        return 'OK'

    def __getMemColor(self, current=0, max=100):
        return self.__colors_list[self.__getMemAlert(current, max)]

    def __getMemColor2(self, current=0, max=100):
        return self.__colors_list2[self.__getMemAlert(current, max)]

    def __getSwapAlert(self, current=0, max=100):
        # If current < CAREFUL of max then alert = OK
        # If current > CAREFUL of max then alert = CAREFUL
        # If current > WARNING of max then alert = WARNING
        # If current > CRITICAL of max then alert = CRITICAL
        try:
            variable = (current * 100) / max
        except ZeroDivisionError:
            return 'DEFAULT'

        if variable > limits.getSWAPCritical():
            return 'CRITICAL'
        elif variable > limits.getSWAPWarning():
            return 'WARNING'
        elif variable > limits.getSWAPCareful():
            return 'CAREFUL'

        return 'OK'

    def __getSwapColor(self, current=0, max=100):
        return self.__colors_list[self.__getSwapAlert(current, max)]

    def __getSwapColor2(self, current=0, max=100):
        return self.__colors_list2[self.__getSwapAlert(current, max)]

    def __getFsAlert(self, current=0, max=100):
        # If current < CAREFUL of max then alert = OK
        # If current > CAREFUL of max then alert = CAREFUL
        # If current > WARNING of max then alert = WARNING
        # If current > CRITICAL of max then alert = CRITICAL
        try:
            variable = (current * 100) / max
        except ZeroDivisionError:
            return 'DEFAULT'

        if variable > limits.getSWAPCritical():
            return 'CRITICAL'
        elif variable > limits.getSWAPWarning():
            return 'WARNING'
        elif variable > limits.getSWAPCareful():
            return 'CAREFUL'

        return 'OK'

    def __getFsColor(self, current=0, max=100):
        return self.__colors_list[self.__getFsAlert(current, max)]

    def __getFsColor2(self, current=0, max=100):
        return self.__colors_list2[self.__getFsAlert(current, max)]

    def __getSensorsAlert(self, current=0):
        # Alert for Sensors (temperature in degre)
        # If current < CAREFUL then alert = OK
        # If current > CAREFUL then alert = CAREFUL
        # If current > WARNING then alert = WARNING
        # If current > CRITICALthen alert = CRITICAL

        if current > limits.getTEMPCritical():
            return 'CRITICAL'
        elif current > limits.getTEMPWarning():
            return 'WARNING'
        elif current > limits.getTEMPCareful():
            return 'CAREFUL'

        return 'OK'

    def __getSensorsColor(self, current=0):
        """
        Return color for Sensors temperature
        """
        return self.__colors_list[self.__getSensorsAlert(current)]

    def __getSensorsColor2(self, current=0):
        """
        Return color for Sensors temperature
        """
        return self.__colors_list2[self.__getSensorsAlert(current)]

    def __getHDDTempAlert(self, current=0):
        # Alert for HDDTemp (temperature in degre)
        # If current < CAREFUL then alert = OK
        # If current > CAREFUL then alert = CAREFUL
        # If current > WARNING then alert = WARNING
        # If current > CRITICALthen alert = CRITICAL
        if current > limits.getHDDTEMPCritical():
            return 'CRITICAL'
        elif current > limits.getHDDTEMPWarning():
            return 'WARNING'
        elif current > limits.getHDDTEMPCareful():
            return 'CAREFUL'

        return 'OK'

    def __getHDDTempColor(self, current=0):
        """
        Return color for HDDTemp temperature
        """
        return self.__colors_list[self.__getHDDTempAlert(current)]

    def __getHDDTempColor2(self, current=0):
        """
        Return color for HDDTemp temperature
        """
        return self.__colors_list2[self.__getHDDTempAlert(current)]

    def __getProcessAlert(self, current=0, max=100, stat='', core=1):
        # If current < CAREFUL of max then alert = OK
        # If current > CAREFUL of max then alert = CAREFUL
        # If current > WARNING of max then alert = WARNING
        # If current > CRITICAL of max then alert = CRITICAL
        # If stat == 'CPU', get core into account...
        try:
            variable = (current * 100) / max
        except ZeroDivisionError:
            return 'DEFAULT'

        if variable > limits.getProcessCritical(stat=stat, core=core):
            return 'CRITICAL'
        elif variable > limits.getProcessWarning(stat=stat, core=core):
            return 'WARNING'
        elif variable > limits.getProcessCareful(stat=stat, core=core):
            return 'CAREFUL'

        return 'OK'

    def __getProcessCpuColor(self, current=0, max=100, core=1):
        return self.__colors_list[self.__getProcessAlert(current, max, 'CPU', core)]

    def __getProcessCpuColor2(self, current=0, max=100, core=1):
        return self.__colors_list2[self.__getProcessAlert(current, max, 'CPU', core)]

    def __getProcessMemColor(self, current=0, max=100):
        return self.__colors_list[self.__getProcessAlert(current, max, 'MEM')]

    def __getProcessMemColor2(self, current=0, max=100):
        return self.__colors_list2[self.__getProcessAlert(current, max, 'MEM')]

    def __getMonitoredAlert(self, nbprocess=0, countmin=None, countmax=None):
        # If count is not defined, not monitoring the number of processes
        if countmin is None:
            countmin = nbprocess
        if countmax is None:
            countmax = nbprocess
        if nbprocess > 0:
            if int(countmin) <= int(nbprocess) <= int(countmax):
                return 'OK'
            else:
                return 'WARNING'
        else:
            if int(countmin) == 0:
                return 'OK'
            else:
                return 'CRITICAL'

    def __getMonitoredColor(self, nbprocess=0, countmin=1, countmax=1):
        return self.__colors_list2[self.__getMonitoredAlert(nbprocess, countmin, countmax)]

    def __getkey(self, window):
        """
        A getKey function to catch ESC key AND Numlock key (issue #163)
        """
        keycode = [0, 0]
        keycode[0] = window.getch()
        keycode[1] = window.getch()

        if keycode[0] == 27 and keycode[1] != -1:
            # Do not escape on specials keys
            return -1
        else:
            return keycode[0]

    def __catchKey(self):
        # Get key
        #~ self.pressedkey = self.term_window.getch()
        self.pressedkey = self.__getkey(self.term_window)

        # Actions...
        if self.pressedkey == ord('\x1b') or self.pressedkey == ord('q'):
            # 'ESC'|'q' > Quit
            end()
        elif self.pressedkey == ord('1'):
            # '1' > Switch between CPU and PerCPU information
            self.percpu_tag = not self.percpu_tag
        elif self.pressedkey == ord('a'):
            # 'a' > Sort processes automatically
            self.setProcessSortedBy('auto')
        elif self.pressedkey == ord('b'):
            # 'b' > Switch between bit/s and Byte/s for network IO
            self.net_byteps_tag = not self.net_byteps_tag
        elif self.pressedkey == ord('c'):
            # 'c' > Sort processes by CPU usage
            self.setProcessSortedBy('cpu_percent')
        elif self.pressedkey == ord('d') and diskio_tag:
            # 'd' > Show/hide disk I/O stats
            self.diskio_tag = not self.diskio_tag
        elif self.pressedkey == ord('f') and fs_tag:
            # 'f' > Show/hide fs stats
            self.fs_tag = not self.fs_tag
        elif self.pressedkey == ord('h'):
            # 'h' > Show/hide help
            self.help_tag = not self.help_tag
        elif self.pressedkey == ord('i') and psutil_get_io_counter_tag:
            # 'i' > Sort processes by IO rate (not available on OS X)
            self.setProcessSortedBy('io_counters')
        elif self.pressedkey == ord('l'):
            # 'l' > Show/hide log messages
            self.log_tag = not self.log_tag
        elif self.pressedkey == ord('m'):
            # 'm' > Sort processes by MEM usage
            self.setProcessSortedBy('memory_percent')
        elif self.pressedkey == ord('n') and network_tag:
            # 'n' > Show/hide network stats
            self.network_tag = not self.network_tag
        elif self.pressedkey == ord('p'):
            # 'p' > Sort processes by name
            self.setProcessSortedBy('name')
        elif self.pressedkey == ord('s'):
            # 's' > Show/hide sensors stats (Linux-only)
            self.sensors_tag = not self.sensors_tag
        elif self.pressedkey == ord('t'):
            # 't' > View network traffic as combination
            self.network_stats_combined = not self.network_stats_combined
        elif self.pressedkey == ord('u'):
            # 'u' > View cumulative network IO
            self.network_stats_cumulative = not self.network_stats_cumulative
        elif self.pressedkey == ord('w'):
            # 'w' > Delete finished warning logs
            logs.clean()
        elif self.pressedkey == ord('x'):
            # 'x' > Delete finished warning and critical logs
            logs.clean(critical=True)
        elif self.pressedkey == ord('y'):
            # 'y' > Show/hide hddtemp stats
            self.hddtemp_tag = not self.hddtemp_tag

        # Return the key code
        return self.pressedkey

    def end(self):
        # Shutdown the curses window
        curses.echo()
        curses.nocbreak()
        curses.curs_set(1)
        curses.endwin()

    def display(self, stats, cs_status="None"):
        """
        Display stats on the screen
        cs_status:
            "None": standalone or server mode
            "Connected": Client is connected to the server
            "Disconnected": Client is disconnected from the server
        """
        # Get stats for processes (used in another functions for logs)
        processcount = stats.getProcessCount()
        processlist = stats.getProcessList(screen.getProcessSortedBy())

        if not self.help_tag:
            # Display stats
            self.displaySystem(stats.getHost(), stats.getSystem(), stats.getUptime())
            cpu_offset = self.displayCpu(stats.getCpu(), stats.getPerCpu(), processlist)
            self.displayLoad(stats.getLoad(), stats.getCore(), processlist, cpu_offset)
            self.displayMem(stats.getMem(), stats.getMemSwap(), processlist, cpu_offset)
            network_count = self.displayNetwork(stats.getNetwork(),
                                                error=stats.network_error_tag)
            sensors_count = self.displaySensors(stats.getSensors(),
                                                self.network_y + network_count)
            hddtemp_count = self.displayHDDTemp(stats.getHDDTemp(),
                                                self.network_y + network_count + sensors_count)
            diskio_count = self.displayDiskIO(stats.getDiskIO(), offset_y=self.network_y +
                                              sensors_count + network_count + hddtemp_count,
                                              error=stats.diskio_error_tag)
            fs_count = self.displayFs(stats.getFs(), self.network_y + sensors_count +
                                      network_count + diskio_count + hddtemp_count)
            log_count = self.displayLog(self.network_y + sensors_count + network_count +
                                        diskio_count + fs_count + hddtemp_count)
            self.displayProcess(processcount, processlist, stats.getSortedBy(),
                                log_count=log_count, core=stats.getCore(), cs_status=cs_status)
            self.displayCaption(cs_status=cs_status)
        self.displayHelp(core=stats.getCore())
        self.displayBat(stats.getBatPercent())
        self.displayNow(stats.getNow())

    def erase(self):
        # Erase the content of the screen
        self.term_window.erase()

    def flush(self, stats, cs_status="None"):
        """
        Clear and update screen
        cs_status:
            "None": standalone or server mode
            "Connected": Client is connected to the server
            "Disconnected": Client is disconnected from the server
        """
        self.erase()
        self.display(stats, cs_status=cs_status)

    def update(self, stats, cs_status="None"):
        """
        Update the screen and wait __refresh_time sec / catch key every 100 ms
        cs_status:
            "None": standalone or server mode
            "Connected": Client is connected to the server
            "Disconnected": Client is disconnected from the server
        """
        # Flush display
        self.flush(stats, cs_status=cs_status)

        # Wait
        countdown = Timer(self.__refresh_time)
        while not countdown.finished():
            # Getkey
            if self.__catchKey() > -1:
                # flush display
                self.flush(stats, cs_status=cs_status)
            # Wait 100ms...
            curses.napms(100)

    def displaySystem(self, host, system, uptime):
        # System information
        if not host or not system:
            return 0
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]
        # Host + OS informations
        if host['os_name'] == "Linux":
            system_msg = _("{0} ({1} {2} / {3} {4})").format(
                host['hostname'],
                system['linux_distro'], system['platform'],
                system['os_name'], system['os_version'])
        else:
            system_msg = _("{0} ({1} {2} {3})").format(
                host['hostname'],
                system['os_name'], system['os_version'],
                system['platform'])
        # System uptime
        if uptime:
            uptime_msg = _("Uptime: {0}").format(uptime)
        else:
            uptime_msg = ""
        # Display
        if (screen_y > self.system_y):
            if (screen_x > self.system_x + len(system_msg) + len(uptime_msg)):
                center = ((screen_x - len(uptime_msg)) // 2) - len(system_msg) // 2
                self.term_window.addnstr(self.system_y, self.system_x + center,
                                         system_msg, 80, curses.A_UNDERLINE)
                try:
                    self.term_window.addnstr(self.uptime_y, screen_x - len(uptime_msg),
                                             uptime_msg, 80)
                except:
                    return len(system_msg)
                else:
                    return len(system_msg) + len(uptime_msg)
            elif (screen_x > self.system_x + len(system_msg)):
                center = (screen_x // 2) - len(system_msg) // 2
                self.term_window.addnstr(self.system_y, self.system_x + center,
                                         system_msg, 80, curses.A_UNDERLINE)
                return len(system_msg)
            else:
                return 0

    def displayCpu(self, cpu, percpu, proclist):
        # Get screen size
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]

        # Is it possible to display extended stats ?
        # If yes then tag_extendedcpu = True
        tag_extendedcpu = screen_x > self.cpu_x + 79 + 14

        # Is it possible to display per-CPU stats ? Do you want it ?
        # If yes then tag_percpu = True
        if self.percpu_tag:
            tag_percpu = screen_x > self.cpu_x + 79 + (len(percpu) - 1) * 10
        else:
            tag_percpu = False

        # compute x offset
        if tag_percpu:
            offset_x = (len(percpu) - 1) * 8
        elif tag_extendedcpu:
            offset_x = 16
        else:
            offset_x = 0

        # Log
        if cpu:
            logs.add(self.__getCpuAlert(cpu['user'], stat="USER"), "CPU user",
                     cpu['user'], proclist)
            logs.add(self.__getCpuAlert(cpu['system'], stat="SYSTEM"), "CPU system",
                     cpu['system'], proclist)
            if 'iowait' in cpu:
                logs.add(self.__getCpuAlert(cpu['iowait'], stat="IOWAIT"), "CPU IOwait",
                         cpu['iowait'], proclist)
            if 'steal' in cpu:
                logs.add(self.__getCpuAlert(cpu['steal'], stat="STEAL"), "CPU steal",
                         cpu['steal'], proclist)

        # Display per-CPU stats
        if screen_y > self.cpu_y + 5 and tag_percpu:
            self.term_window.addnstr(self.cpu_y, self.cpu_x, _("PerCPU"), 6,
                                     self.title_color if self.hascolors else
                                     curses.A_UNDERLINE)

            if not percpu:
                self.term_window.addnstr(self.cpu_y + 1, self.cpu_x,
                                         _("Compute data..."), 15)
                return 0

            self.term_window.addnstr(self.cpu_y + 1, self.cpu_x,
                                     _("user:"), 7)
            self.term_window.addnstr(self.cpu_y + 2, self.cpu_x,
                                     _("system:"), 7)
            if 'iowait' in percpu[0]:
                self.term_window.addnstr(self.cpu_y + 3, self.cpu_x,
                                         _("iowait:"), 7)
            else:
                self.term_window.addnstr(self.cpu_y + 3, self.cpu_x,
                                         _("idle:"), 7)

            for i in range(len(percpu)):
                # percentage of usage
                self.term_window.addnstr(
                    self.cpu_y, self.cpu_x + 8 + i * 8,
                    format((100 - percpu[i]['idle']) / 100, '>6.1%'), 6)

                # user
                self.term_window.addnstr(
                    self.cpu_y + 1, self.cpu_x + 8 + i * 8,
                    format(percpu[i]['user'] / 100, '>6.1%'), 6,
                    self.__getCpuColor2(percpu[i]['user'], stat='user'))

                # system
                self.term_window.addnstr(
                    self.cpu_y + 2, self.cpu_x + 8 + i * 8,
                    format(percpu[i]['system'] / 100, '>6.1%'), 6,
                    self.__getCpuColor2(percpu[i]['system'], stat='system'))

                # If the IOWait stat is available then display it
                # else display the IDLE stat
                if 'iowait' in percpu[i]:
                    # iowait
                    self.term_window.addnstr(
                        self.cpu_y + 3, self.cpu_x + 8 + i * 8,
                        format(percpu[i]['iowait'] / 100, '>6.1%'), 6,
                        self.__getCpuColor2(percpu[i]['iowait'], stat='iowait'))
                else:
                    # idle
                    self.term_window.addnstr(
                        self.cpu_y + 3, self.cpu_x + 8 + i * 8,
                        format(percpu[i]['idle'] / 100, '>6.1%'), 6)

        # display CPU summary information
        elif screen_y > self.cpu_y + 5 and screen_x > self.cpu_x + 18:
            self.term_window.addnstr(self.cpu_y, self.cpu_x, _("CPU"), 3,
                                     self.title_color if self.hascolors else
                                     curses.A_UNDERLINE)

            if not cpu:
                self.term_window.addnstr(self.cpu_y + 1, self.cpu_x,
                                         _("Compute data..."), 15)
                return 0

            # percentage of usage
            cpu_percent = (100 - cpu['idle']) / 100
            self.term_window.addnstr(self.cpu_y, self.cpu_x + 8,
                                     format(cpu_percent, '>6.1%'), 6)

            y = 1
            # user
            self.term_window.addnstr(self.cpu_y + y, self.cpu_x, _("user:"), 5)
            self.term_window.addnstr(self.cpu_y + y, self.cpu_x + 8,
                                     format(cpu['user'] / 100, '>6.1%'), 6,
                                     self.__getCpuColor(cpu['user'], stat='user'))
            y += 1

            # system
            if 'system' in cpu:
                self.term_window.addnstr(self.cpu_y + y, self.cpu_x,
                                         _("system:"), 7)
                self.term_window.addnstr(self.cpu_y + y, self.cpu_x + 8,
                                         format(cpu['system'] / 100, '>6.1%'), 6,
                                         self.__getCpuColor(cpu['system'], stat='system'))
                y += 1

            # idle
            self.term_window.addnstr(self.cpu_y + y, self.cpu_x, _("idle:"), 5)
            self.term_window.addnstr(self.cpu_y + y, self.cpu_x + 8,
                                     format(cpu['idle'] / 100, '>6.1%'), 6)
            y += 1

            # display extended CPU stats when space is available
            if screen_y > self.cpu_y + 5 and tag_extendedcpu:
                y = 0
                if 'steal' in cpu:
                    # Steal time (Linux) for VM guests
                    self.term_window.addnstr(self.cpu_y + y, self.cpu_x + 16,
                                             _("steal:"), 6)
                    self.term_window.addnstr(
                        self.cpu_y + y, self.cpu_x + 24,
                        format(cpu['steal'] / 100, '>6.1%'), 6,
                        self.__getCpuColor(cpu['steal'], stat='steal'))

                y += 1
                if 'nice' in cpu:
                    # nice
                    self.term_window.addnstr(self.cpu_y + y, self.cpu_x + 16,
                                             _("nice:"), 5)
                    self.term_window.addnstr(
                        self.cpu_y + y, self.cpu_x + 24,
                        format(cpu['nice'] / 100, '>6.1%'), 6)
                    y += 1

                if 'iowait' in cpu:
                    # iowait (Linux)
                    self.term_window.addnstr(self.cpu_y + y, self.cpu_x + 16,
                                             _("iowait:"), 7)
                    self.term_window.addnstr(
                        self.cpu_y + y, self.cpu_x + 24,
                        format(cpu['iowait'] / 100, '>6.1%'), 6,
                        self.__getCpuColor(cpu['iowait'], stat='iowait'))
                    y += 1

                if 'irq' in cpu:
                    # irq (Linux, FreeBSD)
                    self.term_window.addnstr(self.cpu_y + y, self.cpu_x + 16,
                                             _("irq:"), 4)
                    self.term_window.addnstr(
                        self.cpu_y + y, self.cpu_x + 24,
                        format(cpu['irq'] / 100, '>6.1%'), 6)
                    y += 1

        # return the x offset to display load
        return offset_x

    def displayLoad(self, load, core, proclist, offset_x=0):
        # Load %
        if not load:
            return 0
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]

        loadblocksize = 15

        if (screen_y > self.load_y + 5 and
            screen_x > self.load_x + offset_x + loadblocksize):

            self.term_window.addnstr(self.load_y,
                                     self.load_x + offset_x, _("Load"), 4,
                                     self.title_color if self.hascolors else
                                     curses.A_UNDERLINE)
            self.term_window.addnstr(self.load_y, self.load_x + offset_x + 7,
                                     str(core) + _("-core"), 7)

            # 1 min
            self.term_window.addnstr(self.load_y + 1,
                                     self.load_x + offset_x, _("1 min:"), 6)
            self.term_window.addnstr(self.load_y + 1,
                                     self.load_x + offset_x + 8,
                                     format(load['min1'], '>5.2f'), 5)

            # 5 min
            self.term_window.addnstr(self.load_y + 2,
                                     self.load_x + offset_x, _("5 min:"), 6)
            alert = self.__getLoadAlert(load['min5'], core)
            logs.add(alert, "LOAD 5-min", load['min5'], proclist)
            self.term_window.addnstr(self.load_y + 2,
                                     self.load_x + offset_x + 8,
                                     format(load['min5'], '>5.2f'), 5,
                                     self.__getLoadColor(load['min5'], core))

            # 15 min
            self.term_window.addnstr(self.load_y + 3,
                                     self.load_x + offset_x, _("15 min:"), 7)
            alert = self.__getLoadAlert(load['min15'], core)
            logs.add(alert, "LOAD 15-min", load['min15'], proclist)
            self.term_window.addnstr(self.load_y + 3,
                                     self.load_x + offset_x + 8,
                                     format(load['min15'], '>5.2f'), 5,
                                     self.__getLoadColor(load['min15'], core))

        # return the x offset to display mem
        return offset_x

    def displayMem(self, mem, memswap, proclist, offset_x=0):
        # Memory
        if not mem:
            return 0
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]

        memblocksize = 45
        extblocksize = 15

        # get the psutil version installed on the server, if in client mode
        if client_tag:
            server_psutil_version = stats.getPsutilVersion()
        else:
            server_psutil_version = ""

        if (screen_y > self.mem_y + 5 and
            screen_x > self.mem_x + offset_x + memblocksize - extblocksize):

            # RAM
            self.term_window.addnstr(self.mem_y,
                                     self.mem_x + offset_x, _("Mem"), 8,
                                     self.title_color if self.hascolors else
                                     curses.A_UNDERLINE)

            # percentage of usage
            self.term_window.addnstr(self.mem_y, self.mem_x + offset_x + 6,
                                     format(mem['percent'] / 100, '>6.1%'), 6)

            # total
            self.term_window.addnstr(self.mem_y + 1, self.mem_x + offset_x,
                                     _("total:"), 6)
            self.term_window.addnstr(
                self.mem_y + 1, self.mem_x + offset_x + 7,
                format(self.__autoUnit(mem['total']), '>5'), 5)

            # used
            alert = self.__getMemAlert(mem['used'], mem['total'])
            logs.add(alert, "MEM real", mem['used'], proclist)
            self.term_window.addnstr(self.mem_y + 2, self.mem_x + offset_x,
                                     _("used:"), 5)
            self.term_window.addnstr(
                self.mem_y + 2, self.mem_x + offset_x + 7,
                format(self.__autoUnit(mem['used']), '>5'), 5,
                self.__getMemColor(mem['used'], mem['total']))

            # free
            self.term_window.addnstr(self.mem_y + 3, self.mem_x + offset_x,
                                     _("free:"), 5)
            self.term_window.addnstr(
                self.mem_y + 3, self.mem_x + offset_x + 7,
                format(self.__autoUnit(mem['free']), '>5'), 5)

            # Display extended informations if space is available
            y = 0
            if screen_x > self.mem_x + offset_x + memblocksize:
                # active and inactive (UNIX; only available for psutil >= 0.6)
                if not is_Windows:
                    if server_psutil_version >= '0.6.0' or psutil_mem_vm:
                        self.term_window.addnstr(self.mem_y + y,
                                                 self.mem_x + offset_x + 14,
                                                 _("active:"), 7)
                        self.term_window.addnstr(
                            self.mem_y + y, self.mem_x + offset_x + 24,
                            format(self.__autoUnit(mem['active']), '>5'), 5)
                        y += 1

                        self.term_window.addnstr(self.mem_y + y,
                                                 self.mem_x + offset_x + 14,
                                                 _("inactive:"), 9)
                        self.term_window.addnstr(
                            self.mem_y + y, self.mem_x + offset_x + 24,
                            format(self.__autoUnit(mem['inactive']), '>5'), 5)
                        y += 1

                # buffers & cached (Linux, BSD)
                if is_Linux or is_BSD:
                    self.term_window.addnstr(self.mem_y + y,
                                             self.mem_x + offset_x + 14,
                                             _("buffers:"), 8)
                    self.term_window.addnstr(
                        self.mem_y + y, self.mem_x + offset_x + 24,
                        format(self.__autoUnit(mem['buffers']), '>5'), 5)
                    y += 1

                    self.term_window.addnstr(self.mem_y + y,
                                             self.mem_x + offset_x + 14,
                                             _("cached:"), 7)
                    self.term_window.addnstr(
                        self.mem_y + y, self.mem_x + offset_x + 24,
                        format(self.__autoUnit(mem['cached']), '>5'), 5)
                    y += 1
            else:
                # If space is NOT available then mind the gap...
                offset_x -= extblocksize

            if not memswap:
                # If there is no swap stat, then do not display it
                return 0
            if memswap['total'] == 0:
                # If swap is null, then do not display it
                return 0

            # Swap
            self.term_window.addnstr(self.mem_y,
                                     self.mem_x + offset_x + 32, _("Swap"), 4,
                                     self.title_color if self.hascolors else
                                     curses.A_UNDERLINE)

            # percentage of usage
            self.term_window.addnstr(
                self.mem_y, self.mem_x + offset_x + 38,
                format(memswap['percent'] / 100, '>6.1%'), 6)

            # total
            self.term_window.addnstr(self.mem_y + 1,
                                     self.mem_x + offset_x + 32,
                                     _("total:"), 6)
            self.term_window.addnstr(
                self.mem_y + 1, self.mem_x + offset_x + 39,
                format(self.__autoUnit(memswap['total']), '>5'), 8)

            # used
            alert = self.__getSwapAlert(memswap['used'], memswap['total'])
            logs.add(alert, "MEM swap", memswap['used'], proclist)
            self.term_window.addnstr(self.mem_y + 2,
                                     self.mem_x + offset_x + 32,
                                     _("used:"), 5)
            self.term_window.addnstr(
                self.mem_y + 2, self.mem_x + offset_x + 39,
                format(self.__autoUnit(memswap['used']), '>5'), 8,
                self.__getSwapColor(memswap['used'], memswap['total']))

            # free
            self.term_window.addnstr(self.mem_y + 3,
                                     self.mem_x + offset_x + 32,
                                     _("free:"), 5)
            self.term_window.addnstr(
                self.mem_y + 3, self.mem_x + offset_x + 39,
                format(self.__autoUnit(memswap['free']), '>5'), 8)

    def displayNetwork(self, network, error=False):
        """
        Display the network interface bitrate
        If error = True, then display a grab error message
        Return the number of interfaces
        """
        if not self.network_tag:
            return 0
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]
        if screen_y > self.network_y + 3 and screen_x > self.network_x + 28:
            self.term_window.addnstr(self.network_y, self.network_x,
                                     _("Network"), 7, self.title_color if
                                     self.hascolors else curses.A_UNDERLINE)

            if self.network_stats_combined:
                column_name = "Rx+Tx"
                if not self.network_stats_cumulative:
                    column_name += "/s"
                self.term_window.addnstr(self.network_y, self.network_x + 10,
                                         format(_(column_name), '>13'), 13)
            else:
                rx_column_name = "Rx"
                tx_column_name = "Tx"
                if not self.network_stats_cumulative:
                    rx_column_name += "/s"
                    tx_column_name += "/s"
                self.term_window.addnstr(self.network_y, self.network_x + 10,
                                         format(_(rx_column_name), '>5'), 5)
                self.term_window.addnstr(self.network_y, self.network_x + 18,
                                         format(_(tx_column_name), '>5'), 5)

            if error:
                # If there is a grab error
                self.term_window.addnstr(self.network_y + 1, self.network_x,
                                         _("Cannot grab data..."), 20)
                return 3
            elif not network:
                # or no data to display...
                self.term_window.addnstr(self.network_y + 1, self.network_x,
                                         _("Compute data..."), 15)
                return 3

            # Adapt the maximum interface to the screen
            net_max = min(screen_y - self.network_y - 3, len(network))
            net_count = 0
            for i in range(0, net_max):
                elapsed_time = max(1, self.__refresh_time)

                # network interface name
                #~ ifname = network[i]['interface_name'].encode('ascii', 'ignore').split(':')[0]
                ifname = network[i]['interface_name'].split(':')[0]

                if (ifname not in limits.getHide('NETWORK_HIDE')):
                    net_count += 1

                    if len(ifname) > 8:
                        ifname = '_' + ifname[-8:]
                    self.term_window.addnstr(self.network_y + net_count,
                                             self.network_x, ifname, 8)

                    # Byte/s or bit/s
                    if self.net_byteps_tag:
                        rx_per_sec = self.__autoUnit(network[i]['rx'] // elapsed_time)
                        tx_per_sec = self.__autoUnit(network[i]['tx'] // elapsed_time)
                        # Combined, or total network traffic
                        # cx is combined rx + tx
                        cx_per_sec = self.__autoUnit(network[i]['cx'] // elapsed_time)
                        cumulative_rx = self.__autoUnit(network[i]['cumulative_rx'])
                        cumulative_tx = self.__autoUnit(network[i]['cumulative_tx'])
                        cumulative_cx = self.__autoUnit(network[i]['cumulative_cx'])

                    else:
                        rx_per_sec = self.__autoUnit(
                            network[i]['rx'] // elapsed_time * 8) + "b"
                        tx_per_sec = self.__autoUnit(
                            network[i]['tx'] // elapsed_time * 8) + "b"
                        # cx is combined rx + tx
                        cx_per_sec = self.__autoUnit(
                            network[i]['cx'] // elapsed_time * 8) + "b"
                        cumulative_rx = self.__autoUnit(
                            network[i]['cumulative_rx'] * 8) + "b"
                        cumulative_tx = self.__autoUnit(
                            network[i]['cumulative_tx'] * 8) + "b"
                        cumulative_cx = self.__autoUnit(
                            network[i]['cumulative_cx'] * 8) + "b"

                    if self.network_stats_cumulative:
                        rx = cumulative_rx
                        tx = cumulative_tx
                        cx = cumulative_cx
                    else:
                        rx = rx_per_sec
                        tx = tx_per_sec
                        cx = cx_per_sec

                    if not self.network_stats_combined:
                        # rx/s
                        self.term_window.addnstr(self.network_y + net_count,
                                                 self.network_x + 8,
                                                 format(rx, '>7'), 7)
                        # tx/s
                        self.term_window.addnstr(self.network_y + net_count,
                                                 self.network_x + 16,
                                                 format(tx, '>7'), 7)
                    else:
                        # cx/s (Combined, or total)
                        self.term_window.addnstr(self.network_y + net_count,
                                                 self.network_x + 16,
                                                 format(cx, '>7'), 7)
            return net_count +2
        return 0

    def displaySensors(self, sensors, offset_y=0):
        """
        Display the sensors stats (Linux-only)
        Return the number of sensors stats
        """
        if not self.sensors_tag or not sensors:
            return 0
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]
        self.sensors_y = offset_y
        if screen_y > self.sensors_y + 3 and screen_x > self.sensors_x + 28:
            # Sensors header
            self.term_window.addnstr(self.sensors_y, self.sensors_x,
                                     _("Sensors"), 7, self.title_color
                                     if self.hascolors else curses.A_UNDERLINE)
            self.term_window.addnstr(self.sensors_y, self.sensors_x + 21,
                                     format(_("°C"), '>3'), 3)

            # Adapt the maximum interface to the screen
            ret = 2
            sensors_num = min(screen_y - self.sensors_y - 3, len(sensors))
            for i in range(0, sensors_num):
                self.term_window.addnstr(
                    self.sensors_y + 1 + i, self.sensors_x,
                    sensors[i]['label'], 21)
                self.term_window.addnstr(
                    self.sensors_y + 1 + i, self.sensors_x + 20,
                    format(sensors[i]['value'], '>3'), 3,
                    self.__getSensorsColor(sensors[i]['value']))
                ret = ret + 1
            return ret
        return 0

    def displayHDDTemp(self, hddtemp, offset_y=0):
        """
        Display the hddtemp stats
        Return the number of hddtemp stats
        """
        if not self.hddtemp_tag or not hddtemp:
            return 0
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]
        self.hddtemp_y = offset_y
        if screen_y > self.hddtemp_y + 3 and screen_x > self.hddtemp_x + 28:
            # hddtemp header
            self.term_window.addnstr(self.hddtemp_y, self.hddtemp_x,
                                     _("HDD Temp"), 8, self.title_color
                                     if self.hascolors else curses.A_UNDERLINE)
            self.term_window.addnstr(self.hddtemp_y, self.hddtemp_x + 21,
                                     format(_("°C"), '>3'), 3)

            # Adapt the maximum interface to the screen
            ret = 2
            hddtemp_num = min(screen_y - self.hddtemp_y - 3, len(hddtemp))
            for i in range(0, hddtemp_num):
                self.term_window.addnstr(
                    self.hddtemp_y + 1 + i, self.hddtemp_x,
                    hddtemp[i]['label'], 21)
                self.term_window.addnstr(
                    self.hddtemp_y + 1 + i, self.hddtemp_x + 20,
                    format(hddtemp[i]['value'], '>3'), 3,
                    self.__getHDDTempColor(hddtemp[i]['value']))
                ret = ret + 1
            return ret
        return 0

    def displayDiskIO(self, diskio, offset_y=0, error=False):
        # Disk input/output rate
        if not self.diskio_tag:
            return 0
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]
        self.diskio_y = offset_y
        if screen_y > self.diskio_y + 3 and screen_x > self.diskio_x + 28:
            self.term_window.addnstr(self.diskio_y, self.diskio_x,
                                     _("Disk I/O"), 8,
                                     self.title_color if self.hascolors else
                                     curses.A_UNDERLINE)
            self.term_window.addnstr(self.diskio_y, self.diskio_x + 10,
                                     format(_("In/s"), '>5'), 5)
            self.term_window.addnstr(self.diskio_y, self.diskio_x + 18,
                                     format(_("Out/s"), '>5'), 5)

            if error:
                # If there is a grab error
                self.term_window.addnstr(self.diskio_y + 1, self.diskio_x,
                                         _("Cannot grab data..."), 20)
                return 3
            elif not diskio:
                # or no data to display...
                self.term_window.addnstr(self.diskio_y + 1, self.diskio_x,
                                         _("Compute data..."), 15)
                return 3

            # Adapt the maximum disk to the screen
            disk_cpt = 0
            disk_max = min(screen_y - self.diskio_y - 3, len(diskio))
            for disk in range(0, disk_max):
                elapsed_time = max(1, self.__refresh_time)

                if (diskio[disk]['disk_name'] not in limits.getHide('IODISK_HIDE')):
                    disk_cpt += 1
                    # partition name
                    self.term_window.addnstr(
                        self.diskio_y + disk_cpt, self.diskio_x,
                        diskio[disk]['disk_name'], 8)
                    # in/s
                    ins = diskio[disk]['write_bytes'] // elapsed_time
                    self.term_window.addnstr(
                        self.diskio_y + disk_cpt, self.diskio_x + 10,
                        format(self.__autoUnit(ins), '>5'), 5)
                    # out/s
                    outs = diskio[disk]['read_bytes'] // elapsed_time
                    self.term_window.addnstr(
                        self.diskio_y + disk_cpt, self.diskio_x + 18,
                        format(self.__autoUnit(outs), '>5'), 5)
            return disk_cpt + 2
        return 0

    def displayFs(self, fs, offset_y=0):
        # Filesystem stats
        if not fs or not self.fs_tag:
            return 0
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]
        self.fs_y = offset_y
        if screen_y > self.fs_y + 3 and screen_x > self.fs_x + 28:
            self.term_window.addnstr(self.fs_y, self.fs_x, _("Mount"), 5,
                                     self.title_color if self.hascolors else
                                     curses.A_UNDERLINE)
            self.term_window.addnstr(self.fs_y, self.fs_x + 9,
                                     format(_("Used"), '>6'), 6)
            self.term_window.addnstr(self.fs_y, self.fs_x + 17,
                                     format(_("Total"), '>6'), 6)

            # Adapt the maximum disk to the screen
            mounted = 0
            fs_num = min(screen_y - self.fs_y - 3, len(fs))
            for mounted in range(0, fs_num):
                # mount point
                if len(fs[mounted]['mnt_point']) > 8:
                    self.term_window.addnstr(
                        self.fs_y + 1 + mounted, self.fs_x,
                        '_' + fs[mounted]['mnt_point'][-7:], 8)
                else:
                    self.term_window.addnstr(
                        self.fs_y + 1 + mounted, self.fs_x,
                        fs[mounted]['mnt_point'], 8)

                # used
                self.term_window.addnstr(
                    self.fs_y + 1 + mounted, self.fs_x + 9,
                    format(self.__autoUnit(fs[mounted]['used']), '>6'), 6,
                    self.__getFsColor2(fs[mounted]['used'], fs[mounted]['size']))

                # total
                self.term_window.addnstr(
                    self.fs_y + 1 + mounted, self.fs_x + 17,
                    format(self.__autoUnit(fs[mounted]['size']), '>6'), 6)

            return mounted + 3
        return 0

    def displayLog(self, offset_y=0):
        # Logs
        if logs.len() == 0 or not self.log_tag:
            return 0
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]
        self.log_y = offset_y
        if screen_y > self.log_y + 3 and screen_x > self.log_x + 79:
            self.log_y = max(offset_y, screen_y - 3 -
                             min(offset_y - 3, screen_y - self.log_y,
                                 logs.len()))
            logtodisplay_count = min(screen_y - self.log_y - 3, logs.len())
            logmsg = _("WARNING|CRITICAL logs")
            if logtodisplay_count > 1:
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
                if log[logcount][1] > 0:
                    logmark = ' '
                    logmsg += (" > " +
                               str(datetime.fromtimestamp(log[logcount][1])))
                else:
                    logmark = '~'
                    logmsg += " > " + "%19s" % "___________________"
                if log[logcount][3][:3] == "MEM":
                    # Special display for MEMORY
                    logmsg += " {0} ({1}/{2}/{3})".format(
                        log[logcount][3],
                        self.__autoUnit(log[logcount][6]),
                        self.__autoUnit(log[logcount][5]),
                        self.__autoUnit(log[logcount][4]))
                elif log[logcount][3][:3] == "MON":
                    # Special display for monitored pocesses list
                    if (log[logcount][5] == 0):
                        logmsg += " No running process"
                    elif (log[logcount][5] == 1):
                        logmsg += " One running process"
                    else:
                        logmsg += " {0} running processes".format(
                            self.__autoUnit(log[logcount][5]))
                else:
                    logmsg += " {0} ({1:.1f}/{2:.1f}/{3:.1f})".format(
                        log[logcount][3], log[logcount][6],
                        log[logcount][5], log[logcount][4])
                # Add the monitored process description
                if log[logcount][10] != "":
                    logmsg += " - {0}".format(log[logcount][10])
                elif log[logcount][9] != []:
                    # Add top processes
                    log_proc_name = log[logcount][9][0]['name']
                    logmsg += " - Top process: {0}".format(log_proc_name)
                # Display the log
                self.term_window.addnstr(self.log_y + 1 + logcount,
                                         self.log_x, logmsg, len(logmsg))
                self.term_window.addnstr(self.log_y + 1 + logcount,
                                         self.log_x, logmark, 1,
                                         self.__colors_list[log[logcount][2]])
            return logcount + 3
        return 0

    def getProcessColumnColor(self, column, sortedby):
        """
        Return the Process title colr depending of:
        self.getProcessSortedBy() -> User sort choice
                         sortedby -> System last sort
        """
        if self.getProcessSortedBy() == 'auto' and sortedby == column:
            return curses.A_UNDERLINE
        elif self.getProcessSortedBy() == column:
            return self.title_color if self.hascolors else curses.A_UNDERLINE
        else:
            return 0

    def displayProcess(self, processcount, processlist, sortedby='',
                       log_count=0, core=1, cs_status="None"):
        """
        Display the processese:
        * summary
        * monitored processes list (optionnal)
        * processes detailed list
        cs_status:
            "None": standalone or server mode
            "Connected": Client is connected to the server
            "Disconnected": Client is disconnected from the server
        """
        # Process
        if not processcount:
            return 0
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]
        # If there is no network & diskio & fs & sensors stats & hddtemp stats
        # then increase process window
        if (not self.network_tag and
            not self.diskio_tag and
            not self.fs_tag and
            not self.sensors_tag and
            not self.hddtemp_tag):
            process_x = 0
        else:
            process_x = self.process_x

        #******************
        # Processes summary
        #******************
        if not self.process_tag:
            self.term_window.addnstr(self.process_y, process_x,
                                     _("Processes (disabled)"),
                                     20, self.title_color if self.hascolors else
                                     curses.A_UNDERLINE)
            return 0
        if screen_y > self.process_y + 4 and screen_x > process_x + 48:
            # Compute others processes
            other = (processcount['total'] -
                     stats.getProcessCount()['running'] -
                     stats.getProcessCount()['sleeping'])
            # Thread is only available in Glances 1.7.4 or higher
            try:
                thread = processcount['thread']
            except KeyError:
                thread = '?'
            # Display the summary
            self.term_window.addnstr(self.process_y, process_x, _("Tasks"),
                                     5, self.title_color if self.hascolors else
                                     curses.A_UNDERLINE)
            self.term_window.addnstr(
                self.process_y, process_x + 7,
                '{0:>3} ({1:>3} {2}), {3:>2} {4}, {5:>3} {6}, {7:>2} {8}'.format(
                    str(processcount['total']),
                    str(thread),
                    _("thr"),
                    str(processcount['running']),
                    _("run"),
                    str(processcount['sleeping']),
                    _("slp"),
                    str(other),
                    _("oth")), 38)

        # Sort info
        # self.getProcessSortedBy() -> User sort choice
        #                  sortedby -> System last sort
        if self.getProcessSortedBy() == 'auto':
            sortmsg = _("sorted automatically")
        else:
            sortmsg = _("sorted by ") + sortedby
        if (screen_y > self.process_y + 4 and
            screen_x > process_x + 48 + len(sortmsg)):
            self.term_window.addnstr(self.process_y, 73, sortmsg, len(sortmsg))

        #*************************
        # Monitored processes list
        #*************************
        monitor_y = self.process_y
        if (len(monitors) > 0 and
            screen_y > self.process_y + 5 + len(monitors) and
            screen_x > process_x + 49):
            # Add space between process summary and monitored processes list
            monitor_y += 1
            item = 0
            for processes in monitors:
                # Display the monitored processes list (one line per monitored processes)
                monitor_y += 1
                # Search monitored processes by a regular expression
                monitoredlist = [p for p in processlist if re.search(monitors.regex(item), p['cmdline']) is not None]
                # Build and print non optional message
                monitormsg1 = "{0:>16} {1:3} {2:13}".format(
                    monitors.description(item)[0:15],
                    len(monitoredlist) if len(monitoredlist) > 1 else "",
                    _("RUNNING") if len(monitoredlist) > 0 else _("NOT RUNNING"))
                self.term_window.addnstr(monitor_y, self.process_x,
                                         monitormsg1, screen_x - process_x,
                                         self.__getMonitoredColor(len(monitoredlist),
                                                                  monitors.countmin(item),
                                                                  monitors.countmax(item)))
                # Build and print optional message
                if len(monitoredlist) > 0:
                    if (cs_status.lower() == "none" and
                        monitors.command(item) is not None):
                        # Execute the user command line
                        try:
                            cmdret = subprocess.check_output(monitors.command(item), shell=True)
                        except subprocess.CalledProcessError:
                            cmdret = _("Error: ") + monitors.command(item)
                        except Exception:
                            cmdret = _("Cannot execute command")
                    else:
                        # By default display CPU and MEM %
                        cmdret = "CPU: {0:.1f}% / MEM: {1:.1f}%".format(
                            sum([p['cpu_percent'] for p in monitoredlist]),
                            sum([p['memory_percent'] for p in monitoredlist]))
                else:
                    cmdret = ""
                    # cmdret = "{0} / {1} / {2}".format(len(monitoredlist),
                    #                                   monitors.countmin(item),
                    #                                   monitors.countmax(item))

                monitormsg2 = "{0}".format(cmdret)
                self.term_window.addnstr(monitor_y, self.process_x + 35,
                                         monitormsg2, screen_x - process_x - 35)

                # Generate log
                logs.add(self.__getMonitoredAlert(len(monitoredlist),
                                                  monitors.countmin(item),
                                                  monitors.countmax(item)),
                         "MON_" + str(item + 1),
                         len(monitoredlist),
                         proc_list=monitoredlist,
                         proc_desc=monitors.description(item))

                # Next...
                item += 1

        #*****************
        # Processes detail
        #*****************
        if screen_y > monitor_y + 4 and screen_x > process_x + 49:
            tag_pid = False
            tag_uid = False
            tag_nice = False
            tag_status = False
            tag_proc_time = False
            tag_io = False
            # tag_tcpudp = False

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
            if screen_x > process_x + 92:
                tag_io = True
            if not psutil_get_io_counter_tag:
                tag_io = False
            # if screen_x > process_x + 107:
            #     tag_tcpudp = True

            # VMS
            self.term_window.addnstr(
                monitor_y + 2, process_x,
                format(_("VIRT"), '>5'), 5)
            # RSS
            self.term_window.addnstr(
                monitor_y + 2, process_x + 6,
                format(_("RES"), '>5'), 5)
            # CPU%
            self.term_window.addnstr(
                monitor_y + 2, process_x + 12,
                format(_("CPU%"), '>5'), 5,
                self.getProcessColumnColor('cpu_percent', sortedby))
            # MEM%
            self.term_window.addnstr(
                monitor_y + 2, process_x + 18,
                format(_("MEM%"), '>5'), 5,
                self.getProcessColumnColor('memory_percent', sortedby))
            process_name_x = 24
            # If screen space (X) is available then:
            # PID
            if tag_pid:
                self.term_window.addnstr(
                    monitor_y + 2, process_x + process_name_x,
                    format(_("PID"), '>5'), 5)
                process_name_x += 6
            # UID
            if tag_uid:
                self.term_window.addnstr(
                    monitor_y + 2, process_x + process_name_x,
                    _("USER"), 4)
                process_name_x += 11
            # NICE
            if tag_nice:
                self.term_window.addnstr(
                    monitor_y + 2, process_x + process_name_x,
                    format(_("NI"), '>3'), 3)
                process_name_x += 4
            # STATUS
            if tag_status:
                self.term_window.addnstr(
                    monitor_y + 2, process_x + process_name_x,
                    _("S"), 1)
                process_name_x += 2
            # TIME+
            if tag_proc_time:
                self.term_window.addnstr(
                    monitor_y + 2, process_x + process_name_x,
                    format(_("TIME+"), '>8'), 8)
                process_name_x += 9
            # IO
            if tag_io:
                self.term_window.addnstr(
                    monitor_y + 2, process_x + process_name_x,
                    format(_("IOR/s"), '>5'), 5,
                    self.getProcessColumnColor('io_counters', sortedby))
                process_name_x += 6
                self.term_window.addnstr(
                    monitor_y + 2, process_x + process_name_x,
                    format(_("IOW/s"), '>5'), 5,
                    self.getProcessColumnColor('io_counters', sortedby))
                process_name_x += 6
            # TCP/UDP
            # if tag_tcpudp:
            #     self.term_window.addnstr(
            #         monitor_y + 2, process_x + process_name_x,
            #         format(_("TCP"), '>5'), 5,
            #         self.getProcessColumnColor('tcp', sortedby))
            #     process_name_x += 6
            #     self.term_window.addnstr(
            #         monitor_y + 2, process_x + process_name_x,
            #         format(_("UDP"), '>5'), 5,
            #         self.getProcessColumnColor('udp', sortedby))
            #     process_name_x += 6
            # PROCESS NAME
            self.term_window.addnstr(
                monitor_y + 2, process_x + process_name_x,
                _("NAME"), 12, curses.A_UNDERLINE
                if sortedby == 'name' else 0)

            # If there is no data to display...
            if not processlist:
                self.term_window.addnstr(monitor_y + 3, self.process_x,
                                         _("Compute data..."), 15)
                return 6

            # Display the processes list
            # How many processes are going to be displayed ?
            proc_num = min(screen_y - monitor_y - log_count - 5,
                           len(processlist))

            # Loop to display processes
            for processes in range(0, proc_num):
                # VMS
                process_size = processlist[processes]['memory_info'][1]
                self.term_window.addnstr(
                    monitor_y + 3 + processes, process_x,
                    format(self.__autoUnit(process_size, low_precision=True),
                           '>5'), 5)
                # RSS
                process_resident = processlist[processes]['memory_info'][0]
                self.term_window.addnstr(
                    monitor_y + 3 + processes, process_x + 6,
                    format(self.__autoUnit(process_resident, low_precision=True),
                           '>5'), 5)
                # CPU%
                cpu_percent = processlist[processes]['cpu_percent']
                self.term_window.addnstr(
                    monitor_y + 3 + processes, process_x + 12,
                    format(cpu_percent, '>5.1f'), 5,
                    self.__getProcessCpuColor2(cpu_percent, core=core))
                # MEM%
                memory_percent = processlist[processes]['memory_percent']
                self.term_window.addnstr(
                    monitor_y + 3 + processes, process_x + 18,
                    format(memory_percent, '>5.1f'), 5,
                    self.__getProcessMemColor2(memory_percent))
                # If screen space (X) is available then:
                # PID
                if tag_pid:
                    pid = processlist[processes]['pid']
                    self.term_window.addnstr(
                        monitor_y + 3 + processes, process_x + 24,
                        format(str(pid), '>5'), 5)
                # UID
                if tag_uid:
                    uid = processlist[processes]['username']
                    self.term_window.addnstr(
                        monitor_y + 3 + processes, process_x + 30,
                        str(uid), 9)
                # NICE
                if tag_nice:
                    nice = processlist[processes]['nice']
                    self.term_window.addnstr(
                        monitor_y + 3 + processes, process_x + 41,
                        format(str(nice), '>3'), 3)
                # STATUS
                if tag_status:
                    status = processlist[processes]['status']
                    self.term_window.addnstr(
                        monitor_y + 3 + processes, process_x + 45,
                        str(status), 1)
                # TIME+
                if tag_proc_time:
                    process_time = processlist[processes]['cpu_times']
                    try:
                        dtime = timedelta(seconds=sum(process_time))
                    except Exception:
                        # Catched on some Amazon EC2 server
                        # See https://github.com/nicolargo/glances/issues/87
                        tag_proc_time = False
                    else:
                        dtime = "{0}:{1}.{2}".format(
                            str(dtime.seconds // 60 % 60),
                            str(dtime.seconds % 60).zfill(2),
                            str(dtime.microseconds)[:2].zfill(2))
                        self.term_window.addnstr(
                            monitor_y + 3 + processes, process_x + 47,
                            format(dtime, '>8'), 8)
                # IO
                # Hack to allow client 1.6 to connect to server 1.5.2
                process_tag_io = True
                try:
                    if processlist[processes]['io_counters'][4] == 0:
                        process_tag_io = True
                except Exception:
                    process_tag_io = False
                if tag_io:
                    if not process_tag_io:
                        # If io_tag == 0 (['io_counters'][4])
                        # then do not diplay IO rate
                        self.term_window.addnstr(
                            monitor_y + 3 + processes, process_x + 56,
                            format("?", '>5'), 5)
                        self.term_window.addnstr(
                            monitor_y + 3 + processes, process_x + 62,
                            format("?", '>5'), 5)
                    else:
                        # If io_tag == 1 (['io_counters'][4])
                        # then diplay IO rate
                        io_read = processlist[processes]['io_counters'][0]
                        io_read_old = processlist[processes]['io_counters'][2]
                        io_write = processlist[processes]['io_counters'][1]
                        io_write_old = processlist[processes]['io_counters'][3]
                        elapsed_time = max(1, self.__refresh_time)
                        io_rs = (io_read - io_read_old) / elapsed_time
                        io_ws = (io_write - io_write_old) / elapsed_time
                        self.term_window.addnstr(
                            monitor_y + 3 + processes, process_x + 56,
                            format(self.__autoUnit(io_rs, low_precision=True),
                                   '>5'), 5)
                        self.term_window.addnstr(
                            monitor_y + 3 + processes, process_x + 62,
                            format(self.__autoUnit(io_ws, low_precision=True),
                                   '>5'), 5)
                # TCP/UDP connexion number
                # if tag_tcpudp:
                #     try:
                #         processlist[processes]['tcp']
                #         processlist[processes]['udp']
                #     except:
                #         pass
                #     else:
                #         self.term_window.addnstr(
                #             monitor_y + 3 + processes, process_x + 68,
                #             format(processlist[processes]['tcp'], '>5'), 5)
                #         self.term_window.addnstr(
                #             monitor_y + 3 + processes, process_x + 74,
                #             format(processlist[processes]['udp'], '>5'), 5)
                # Display process command line
                max_process_name = screen_x - process_x - process_name_x
                process_name = processlist[processes]['name']
                process_cmdline = processlist[processes]['cmdline']
                if (len(process_cmdline) > max_process_name or
                    len(process_cmdline) == 0):
                    command = process_name
                else:
                    command = process_cmdline
                try:
                    self.term_window.addnstr(monitor_y + 3 + processes,
                                             process_x + process_name_x,
                                             command, max_process_name)
                except UnicodeEncodeError:
                    self.term_window.addnstr(monitor_y + 3 + processes,
                                             process_x + process_name_x,
                                             process_name, max_process_name)                    

    def displayCaption(self, cs_status="None"):
        """
        Display the caption (bottom left)
        cs_status:
            "None": standalone or server mode
            "Connected": Client is connected to the server
            "Disconnected": Client is disconnected from the server
        """
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]
        if client_tag:
            if cs_status.lower() == "connected":
                msg_client = _("Connected to ") + format(server_ip)
                msg_client_style = self.default_color2 if self.hascolors else curses.A_UNDERLINE
            elif cs_status.lower() == "disconnected":
                msg_client = _("Disconnected from ") + format(server_ip)
                msg_client_style = self.ifCRITICAL_color2 if self.hascolors else curses.A_UNDERLINE
        msg_help = _("Press 'h' for help")
        if client_tag:
            if (screen_y > self.caption_y and
                screen_x > self.caption_x + len(msg_client)):
                self.term_window.addnstr(max(self.caption_y, screen_y - 1),
                                         self.caption_x, msg_client,
                                         len(msg_client), msg_client_style)
            if screen_x > self.caption_x + len(msg_client) + 3 + len(msg_help):
                self.term_window.addnstr(max(self.caption_y, screen_y - 1),
                                         self.caption_x + len(msg_client),
                                         ' | ' + msg_help, 3 + len(msg_help))
        else:
            if (screen_y > self.caption_y and
                screen_x > self.caption_x + len(msg_help)):
                self.term_window.addnstr(max(self.caption_y, screen_y - 1),
                                         self.caption_x, msg_help, len(msg_help))

    def displayHelp(self, core):
        """
        Show the help panel
        """
        if not self.help_tag:
            return 0
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]
        if screen_y > self.help_y + 23 and screen_x > self.help_x + 79:
            # Console 80x24 is mandatory to display the help message
            self.erase()

            try:
                self.term_window.addnstr(
                    self.help_y, self.help_x,
                    _("Glances {0} with PsUtil {1}").format(
                        self.__version, psutil.__version__),
                    79, self.title_color if self.hascolors else 0)
            except Exception:
                self.term_window.addnstr(
                    self.help_y, self.help_x,
                    _("Glances {0}").format(self.__version),
                    79, self.title_color if self.hascolors else 0)

            # display the limits table
            limits_table_x = self.help_x
            limits_table_y = self.help_y + 2
            self.term_window.addnstr(limits_table_y, limits_table_x + 15,
                                     format(_("CAREFUL"), '7'), 7,
                                     self.ifCAREFUL_color),
            self.term_window.addnstr(limits_table_y, limits_table_x + 22,
                                     format(_("WARNING"), '7'), 7,
                                     self.ifWARNING_color),
            self.term_window.addnstr(limits_table_y, limits_table_x + 29,
                                     format(_("CRITICAL"), '8'), 8,
                                     self.ifCRITICAL_color)

            # stats labels and limit values (left column)
            stats_labels_left = [_("CPU user %"), _("CPU system %"),
                                 _("CPU iowait %"), _("CPU steal %"),
                                 _("Load"), _("RAM %")]
            limits_table_x = self.help_x + 2
            limits_table_y = self.help_y + 3
            for label in stats_labels_left:
                self.term_window.addnstr(limits_table_y, limits_table_x,
                                         format(label, '<13'), 13)
                limits_table_y += 1

            limit_values_left = [[limits.getCPUCareful(stat='user'),
                                  limits.getCPUWarning(stat='user'),
                                  limits.getCPUCritical(stat='user')],
                                 [limits.getCPUCareful(stat='system'),
                                  limits.getCPUWarning(stat='system'),
                                  limits.getCPUCritical(stat='system')],
                                 [limits.getCPUCareful(stat='iowait'),
                                  limits.getCPUWarning(stat='iowait'),
                                  limits.getCPUCritical(stat='iowait')],
                                 [limits.getCPUCareful(stat='steal'),
                                  limits.getCPUWarning(stat='steal'),
                                  limits.getCPUCritical(stat='steal')],
                                 [limits.getLOADCareful() * core,
                                  limits.getLOADWarning() * core,
                                  limits.getLOADCritical() * core],
                                 [limits.getMEMCareful(),
                                  limits.getMEMWarning(),
                                  limits.getMEMCritical()]]
            width = 6
            limits_table_x = self.help_x + 16
            limits_table_y = self.help_y + 3
            for value in limit_values_left:
                self.term_window.addnstr(
                    limits_table_y, limits_table_x,
                    '{0:>{width}}{1:>{width}}{2:>{width}}'.format(
                        *value, width=width), 18)
                limits_table_y += 1

            # stats labels and limit values (right column)
            stats_labels_right = [_("Swap %"), _("Temp °C"),
                                  _("HDD Temp °C"), _("Filesystem %"),
                                  _("CPU process %"), _("MEM process %")]
            limits_table_x = self.help_x + 38
            limits_table_y = self.help_y + 3
            for label in stats_labels_right:
                self.term_window.addnstr(limits_table_y, limits_table_x,
                                         format(label, '<13'), 13)
                limits_table_y += 1

            limit_values_right = [[limits.getSWAPCareful(),
                                   limits.getSWAPWarning(),
                                   limits.getSWAPCritical()],
                                  [limits.getTEMPCareful(),
                                   limits.getTEMPWarning(),
                                   limits.getTEMPCritical()],
                                  [limits.getHDDTEMPCareful(),
                                   limits.getHDDTEMPWarning(),
                                   limits.getHDDTEMPCritical()],
                                  [limits.getFSCareful(),
                                   limits.getFSWarning(),
                                   limits.getFSCritical()],
                                  [limits.getProcessCareful(stat='CPU', core=core),
                                   limits.getProcessWarning(stat='CPU', core=core),
                                   limits.getProcessCritical(stat='CPU', core=core)],
                                  [limits.getProcessCareful(stat='MEM'),
                                   limits.getProcessWarning(stat='MEM'),
                                   limits.getProcessCritical(stat='MEM')]]
            limits_table_x = self.help_x + 53
            limits_table_y = self.help_y + 3
            for value in limit_values_right:
                self.term_window.addnstr(
                    limits_table_y, limits_table_x,
                    '{0:>{width}}{1:>{width}}{2:>{width}}'.format(
                        *value, width=width), 18)
                limits_table_y += 1

            # key table (left column)
            key_col_left = [[_("a"), _("Sort processes automatically")],
                            [_("c"), _("Sort processes by CPU%")],
                            [_("m"), _("Sort processes by MEM%")],
                            [_("p"), _("Sort processes by name")],
                            [_("i"), _("Sort processes by I/O rate")],
                            [_("d"), _("Show/hide disk I/O stats")],
                            [_("f"), _("Show/hide file system stats")],
                            [_("n"), _("Show/hide network stats")],
                            [_("s"), _("Show/hide sensors stats")],
                            [_("y"), _("Show/hide hddtemp stats")]]

            width = 3
            key_table_x = self.help_x + 2
            key_table_y = limits_table_y + 1
            for key in key_col_left:
                self.term_window.addnstr(
                    key_table_y, key_table_x,
                    '{0:{width}}{1}'.format(*key, width=width), 38)
                key_table_y += 1

            # key table (right column)
            key_col_right = [[_("l"), _("Show/hide logs")],
                             [_("b"), _("Bytes or bits for network I/O")],
                             [_("w"), _("Delete warning logs")],
                             [_("x"), _("Delete warning and critical logs")],
                             [_("1"), _("Global CPU or per-CPU stats")],
                             [_("h"), _("Show/hide this help screen")],
                             [_("t"), _("View network I/O as combination")],
                             [_("u"), _("View cumulative network I/O")],
                             [_("q"), _("Quit (Esc and Ctrl-C also work)")]]
            key_table_x = self.help_x + 38
            key_table_y = limits_table_y + 1
            for key in key_col_right:
                self.term_window.addnstr(
                    key_table_y, key_table_x,
                    '{0:{width}}{1}'.format(*key, width=width), 38)
                key_table_y += 1

    def displayBat(self, batpercent):
        # Display the current batteries capacities % - Center
        if not batinfo_lib_tag or batpercent == []:
            return 0
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]
        # Build the message to display
        bat_msg = "%d%%" % batpercent
        # Display the message (if possible)
        if (screen_y > self.bat_y and
            screen_x > self.bat_x + len(bat_msg)):
            center = (screen_x // 2) - len(bat_msg) // 2
            self.term_window.addnstr(
                max(self.bat_y, screen_y - 1),
                self.bat_x + center,
                bat_msg, len(bat_msg))

    def displayNow(self, now):
        # Display the current date and time (now...) - Right
        if not now:
            return 0
        screen_x = self.screen.getmaxyx()[1]
        screen_y = self.screen.getmaxyx()[0]
        if screen_y > self.now_y and screen_x > self.now_x:
            now_msg = now.strftime(_("%Y-%m-%d %H:%M:%S"))
            self.term_window.addnstr(
                max(self.now_y, screen_y - 1),
                max(self.now_x, screen_x - 1) - len(now_msg),
                now_msg, len(now_msg))


class glancesHtml:
    """
    This class manages the HTML output
    """

    def __init__(self, html_path, refresh_time=1):
        html_filename = 'glances.html'
        html_template = 'default.html'
        self.__refresh_time = refresh_time

        # Set the HTML output file
        self.html_file = os.path.join(html_path, html_filename)

        # Get data path
        data_path = os.path.join(work_path, 'data')

        # Set the template path
        template_path = os.path.join(data_path, 'html')
        environment = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_path),
            extensions=['jinja2.ext.loopcontrols'])

        # Open the template
        self.template = environment.get_template(html_template)

        # Define the colors list (hash table) for logged stats
        self.__colors_list = {
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
        cpu['system_color'] = self.__getColor(cpu['system'], max)
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
        mem['used_color'] = self.__getColor(mem['used'], mem['total'])

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
            with open(self.html_file, 'w') as f:
                # HTML refresh is set to 1.5 * refresh_time
                # to avoid display while page rendering
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


class glancesCsv:
    """
    This class manages the CSV output
    """

    def __init__(self, cvsfile="./glances.csv", refresh_time=1):
        # Init refresh time
        self.__refresh_time = refresh_time

        # Set the ouput (CSV) path
        try:
            self.__cvsfile_fd = open("%s" % cvsfile, "wb")
            self.__csvfile = csv.writer(self.__cvsfile_fd)
        except IOError as error:
            print("Cannot create the output CSV file: ", error[1])
            sys.exit(0)

    def exit(self):
        self.__cvsfile_fd.close()

    def update(self, stats):
        if stats.getCpu():
            # Update CSV with the CPU stats
            cpu = stats.getCpu()
            # Standard CPU stats
            l = ["cpu", cpu['user'], cpu['system'], cpu['nice']]
            # Extra CPU stats
            for s in ('idle', 'iowait', 'irq'):
                l.append(cpu[s] if cpu.has_key(s) else None)
            self.__csvfile.writerow(l)
        if stats.getLoad():
            # Update CSV with the LOAD stats
            load = stats.getLoad()
            self.__csvfile.writerow(["load", load['min1'], load['min5'],
                                     load['min15']])
        if stats.getMem() and stats.getMemSwap():
            # Update CSV with the MEM stats
            mem = stats.getMem()
            self.__csvfile.writerow(["mem", mem['total'], mem['used'],
                                     mem['free']])
            memswap = stats.getMemSwap()
            self.__csvfile.writerow(["swap", memswap['total'], memswap['used'],
                                     memswap['free']])
        self.__cvsfile_fd.flush()


class GlancesXMLRPCHandler(SimpleXMLRPCRequestHandler):
    """
    Main XMLRPC handler
    """
    rpc_paths = ('/RPC2', )

    def end_headers(self):
        # Hack to add a specific header
        # Thk to: https://gist.github.com/rca/4063325
        self.send_my_headers()
        SimpleXMLRPCRequestHandler.end_headers(self)

    def send_my_headers(self):
        # Specific header is here (solved the issue #227)
        self.send_header("Access-Control-Allow-Origin", "*")

    def authenticate(self, headers):
        # auth = headers.get('Authorization')
        try:
            (basic, _, encoded) = headers.get('Authorization').partition(' ')
        except Exception:
            # Client did not ask for authentidaction
            # If server need it then exit
            return not self.server.isAuth
        else:
            # Client authentication
            (basic, _, encoded) = headers.get('Authorization').partition(' ')
            assert basic == 'Basic', 'Only basic authentication supported'
            #    Encoded portion of the header is a string
            #    Need to convert to bytestring
            encodedByteString = encoded.encode()
            #    Decode Base64 byte String to a decoded Byte String
            decodedBytes = b64decode(encodedByteString)
            #    Convert from byte string to a regular String
            decodedString = decodedBytes.decode()
            #    Get the username and password from the string
            (username, _, password) = decodedString.partition(':')
            #    Check that username and password match internal global dictionary
            return self.check_user(username, password)

    def check_user(self, username, password):
        # Check username and password in the dictionnary
        if username in self.server.user_dict:
            if self.server.user_dict[username] == md5(password).hexdigest():
                return True
        return False

    def parse_request(self):
        if SimpleXMLRPCRequestHandler.parse_request(self):
            # Next we authenticate
            if self.authenticate(self.headers):
                return True
            else:
                # if authentication fails, tell the client
                self.send_error(401, 'Authentication failed')
        return False

    def log_message(self, format, *args):
        # No message displayed on the server side
        pass


class GlancesXMLRPCServer(SimpleXMLRPCServer):
    """
    Init a SimpleXMLRPCServer instance (IPv6-ready)
    """

    def __init__(self, bind_address, bind_port=61209,
                 requestHandler=GlancesXMLRPCHandler):

        try:
            self.address_family = socket.getaddrinfo(bind_address, bind_port)[0][0]
        except socket.error as e:
            print(_("Couldn't open socket: %s") % e)
            sys.exit(1)

        SimpleXMLRPCServer.__init__(self, (bind_address, bind_port),
                                    requestHandler)


class GlancesInstance():
    """
    All the methods of this class are published as XML RPC methods
    """

    def __init__(self, cached_time=1):
        # cached_time is the minimum time interval between stats updates
        # i.e. XML/RPC calls will not retrieve updated info until the time
        # since last update is passed (will retrieve old cached info instead)
        self.timer = Timer(0)
        self.cached_time = cached_time

    def __update__(self):
        # Never update more than 1 time per cached_time
        if self.timer.finished():
            stats.update()
            self.timer = Timer(self.cached_time)

    def init(self):
        # Return the Glances version
        return __version__

    def getAll(self):
        # Update and return all the stats
        self.__update__()
        return json.dumps(stats.getAll())

    def getAllLimits(self):
        # Return all the limits
        return json.dumps(limits.getAll())

    def getAllMonitored(self):
        # Return the processes monitored list
        return json.dumps(monitors.getAll())

    def getSystem(self):
        # Return operating system info
        # No need to update...
        #~ self.__update__()
        return json.dumps(stats.getSystem())

    def getCore(self):
        # Update and return number of Core
        self.__update__()
        return json.dumps(stats.getCore())

    def getCpu(self):
        # Update and return CPU stats
        self.__update__()
        return json.dumps(stats.getCpu())

    def getLoad(self):
        # Update and return LOAD stats
        self.__update__()
        return json.dumps(stats.getLoad())

    def getMem(self):
        # Update and return MEM stats
        self.__update__()
        return json.dumps(stats.getMem())

    def getMemSwap(self):
        # Update and return MEMSWAP stats
        self.__update__()
        return json.dumps(stats.getMemSwap())

    def getSensors(self):
        # Update and return SENSORS stats
        self.__update__()
        return json.dumps(stats.getSensors())

    def getHDDTemp(self):
        # Update and return HDDTEMP stats
        self.__update__()
        return json.dumps(stats.getHDDTemp())

    def getNetwork(self):
        # Update and return NET stats
        self.__update__()
        return json.dumps(stats.getNetwork())

    def getDiskIO(self):
        # Update and return DISK IO stats
        self.__update__()
        return json.dumps(stats.getDiskIO())

    def getFs(self):
        # Update and return FS stats
        self.__update__()
        return json.dumps(stats.getFs())

    def getProcessCount(self):
        # Update and return ProcessCount stats
        self.__update__()
        return json.dumps(stats.getProcessCount())

    def getProcessList(self):
        # Update and return ProcessList stats
        self.__update__()
        return json.dumps(stats.getProcessList())

    def getBatPercent(self):
        # Update and return total batteries percent stats
        self.__update__()
        return json.dumps(stats.getBatPercent())

    def getNow(self):
        # Update and return current date/hour
        self.__update__()
        return json.dumps(stats.getNow().strftime(_("%Y-%m-%d %H:%M:%S")))

    def getUptime(self):
        # Update and return system uptime
        self.__update__()
        return json.dumps(stats.getUptime().strftime(_("%Y-%m-%d %H:%M:%S")))

    def __getTimeSinceLastUpdate(self, IOType):
        assert(IOType in ['net', 'disk', 'process_disk'])
        return getTimeSinceLastUpdate(IOType)

    def getNetTimeSinceLastUpdate(self):
        return getTimeSinceLastUpdate('net')

    def getDiskTimeSinceLastUpdate(self):
        return getTimeSinceLastUpdate('net')

    def getProcessDiskTimeSinceLastUpdate(self):
        return getTimeSinceLastUpdate('process_disk')


class GlancesServer():
    """
    This class creates and manages the TCP client
    """

    def __init__(self, bind_address, bind_port=61209,
                 requestHandler=GlancesXMLRPCHandler, cached_time=1):
        self.server = GlancesXMLRPCServer(bind_address, bind_port, requestHandler)

        # The users dict
        # username / MD5 password couple
        # By default, no auth is needed
        self.server.user_dict = {}
        self.server.isAuth = False
        # Register functions
        self.server.register_introspection_functions()
        self.server.register_instance(GlancesInstance(cached_time))

    def add_user(self, username, password):
        """
        Add an user to the dictionnary
        """
        self.server.user_dict[username] = md5(password).hexdigest()
        self.server.isAuth = True

    def serve_forever(self):
        self.server.serve_forever()

    def server_close(self):
        self.server.server_close()


class GlancesClient():
    """
    This class creates and manages the TCP client
    """

    def __init__(self, server_address, server_port=61209,
                 username="glances", password=""):
        # Build the URI
        if password != "":
            uri = 'http://%s:%s@%s:%d' % (username, password, server_address, server_port)
        else:
            uri = 'http://%s:%d' % (server_address, server_port)

        # Try to connect to the URI
        try:
            self.client = ServerProxy(uri)
        except Exception:
            print(_("Error: creating client socket") + " %s" % uri)
            pass
        return

    def client_init(self):
        try:
            client_version = self.client.init()
        except ProtocolError as err:
            if str(err).find(" 401 ") > 0:
                print(_("Error: Connection to server failed. Bad password."))
                sys.exit(-1)
            else:
                print(_("Error: Connection to server failed. Unknown error."))
                sys.exit(-1)
        return __version__[:3] == client_version[:3]

    def client_get_limits(self):
        try:
            serverlimits = json.loads(self.client.getAllLimits())
        except Exception:
            return {}
        else:
            return serverlimits

    def client_get_monitored(self):
        try:
            servermonitored = json.loads(self.client.getAllMonitored())
        except Exception:
            return []
        else:
            return servermonitored

    def client_get(self):
        try:
            stats = json.loads(self.client.getAll())
        except Exception:
            return {}
        else:
            return stats

# Global def
#===========


def printVersion():
    print(_("Glances version ") + __version__ + _(" with PsUtil ") + psutil.__version__)


def printSyntax():
    printVersion()
    print(_("Usage: glances [options]"))
    print(_("\nOptions:"))
    print(_("\t-b\t\tDisplay network rate in Byte per second"))
    print(_("\t-B @IP|HOST\tBind server to the given IPv4/IPv6 address or hostname"))
    print(_("\t-c @IP|HOST\tConnect to a Glances server by IPv4/IPv6 address or hostname"))
    print(_("\t-C FILE\t\tPath to the configuration file"))
    print(_("\t-d\t\tDisable disk I/O module"))
    print(_("\t-e\t\tEnable sensors module"))
    print(_("\t-f FILE\t\tSet the HTML output folder or CSV file"))
    print(_("\t-h\t\tDisplay the help and exit"))
    print(_("\t-m\t\tDisable mount module"))
    print(_("\t-n\t\tDisable network module"))
    print(_("\t-o OUTPUT\tDefine additional output (available: HTML or CSV)"))
    print(_("\t-p PORT\t\tDefine the client/server TCP port (default: %d)" %
            server_port))
    print(_("\t-P PASSWORD\tDefine a client/server password"))
    print(_("\t--password\tDefine a client/server password from the prompt"))
    print(_("\t-r\t\tDisable process list"))
    print(_("\t-s\t\tRun Glances in server mode"))
    print(_("\t-t SECONDS\tSet refresh time in seconds (default: %d sec)" %
            refresh_time))
    print(_("\t-v\t\tDisplay the version and exit"))
    print(_("\t-y\t\tEnable hddtemp module"))
    print(_("\t-z\t\tDo not use the bold color attribute"))
    print(_("\t-1\t\tStart Glances in per CPU mode"))


def end():
    if server_tag:
        # Stop the server loop
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


def get_password(description='', confirm=False):
    """
    Read a password from the command line (with confirmation if confirm = True)
    """
    import getpass

    if description != '':
        sys.stdout.write("%s\n" % description)

    password1 = getpass.getpass(_("Password: "))
    if confirm:
        password2 = getpass.getpass(_("Password (confirm): "))
    else:
        return password1

    if password1 == password2:
        return password1
    else:
        sys.stdout.write(_("[Warning] Passwords did not match, please try again...\n"))
        return get_password(description=description, confirm=confirm)


def main():
    # Glances - Init stuff
    ######################

    global config, limits, monitors, logs, stats, screen
    global htmloutput, csvoutput
    global html_tag, csv_tag, server_tag, client_tag
    global psutil_get_io_counter_tag, psutil_mem_vm
    global percpu_tag, fs_tag, diskio_tag, network_tag, network_bytepersec_tag
    global sensors_tag, hddtemp_tag, process_tag
    global refresh_time, client, server, server_port, server_ip
    global last_update_times

    # create update times dict
    last_update_times = {}

    # Set default tags
    percpu_tag = False
    fs_tag = True
    diskio_tag = True
    network_tag = True
    network_bytepersec_tag = False
    sensors_tag = False
    hddtemp_tag = False
    process_tag = True
    html_tag = False
    csv_tag = False
    client_tag = False
    password_tag = False
    password_prompt = False
    if is_Windows and not is_colorConsole:
        # Force server mode for Windows OS without colorconsole
        server_tag = True
    else:
        server_tag = False

    # Configuration file stuff
    conf_file = ""
    conf_file_tag = False

    # Set the default refresh time
    refresh_time = 3

    # Set the default cache lifetime (for server)
    cached_time = 1

    # Use curses.A_BOLD by default
    use_bold = True

    # Set the default TCP port for client and server
    server_port = 61209
    bind_ip = "0.0.0.0"

    # Default username/password
    username = "glances"
    password = ""

    # Manage args
    try:
        opts, args = getopt.getopt(sys.argv[1:], "B:bdeymnho:f:t:vsc:p:C:P:zr1",
                                   ["bind", "bytepersec", "diskio", "mount",
                                    "sensors", "hddtemp", "netrate", "help", "output",
                                    "file", "time", "version", "server",
                                    "client", "port", "config", "password",
                                    "nobold", "noproc", "percpu"])
    except getopt.GetoptError as err:
        # Print help information and exit:
        if (err.opt == 'P') and ('requires argument' in err.msg):
            print(_("Error: -P flag need an argument (password)"))
        elif (err.opt == 'B') and ('requires argument' in err.msg):
            print(_("Error: -B flag need an argument (bind IP address)"))
        elif (err.opt == 'c') and ('requires argument' in err.msg):
            print(_("Error: -c flag need an argument (server IP address/name)"))
        elif (err.opt == 'p') and ('requires argument' in err.msg):
            print(_("Error: -p flag need an argument (port number)"))
        elif (err.opt == 'o') and ('requires argument' in err.msg):
            print(_("Error: -o flag need an argument (HTML or CSV)"))
        elif (err.opt == 't') and ('requires argument' in err.msg):
            print(_("Error: -t flag need an argument (refresh time)"))
        else:
            print(str(err))
        print
        printSyntax()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-v", "--version"):
            printVersion()
            sys.exit(0)
        elif opt in ("-s", "--server"):
            server_tag = True
        elif opt in ("-P"):
            password_tag = True
            password = arg
        elif opt in ("--password", "--password"):
            password_prompt = True
        elif opt in ("-B", "--bind"):
            bind_ip = arg
        elif opt in ("-c", "--client"):
            client_tag = True
            server_ip = arg
        elif opt in ("-p", "--port"):
            server_port = arg
        elif opt in ("-o", "--output"):
            if arg.lower() == "html":
                html_tag = True
            elif arg.lower() == "csv":
                csv_tag = True
            else:
                print(_("Error: Unknown output %s" % arg))
                sys.exit(2)
        elif opt in ("-e", "--sensors"):
            if is_Linux:
                if not sensors_lib_tag:
                    print(_("Error: PySensors library not found"))
                    sys.exit(2)
                else:
                    sensors_tag = True
            else:
                print(_("Error: Sensors module is only available on Linux"))
                sys.exit(2)
        elif opt in ("-y", "--hddtemp"):
            hddtemp_tag = True
        elif opt in ("-f", "--file"):
            output_file = arg
            output_folder = arg
        elif opt in ("-t", "--time"):
            try:
                refresh_time = int(arg)
            except:
                print("Error: Invalid refresh time (%s)" % arg)
                sys.exit(2)
            if (refresh_time < 1):
                print(_("Error: Refresh time should be a positive integer"))
                sys.exit(2)
        elif opt in ("-d", "--diskio"):
            diskio_tag = False
        elif opt in ("-m", "--mount"):
            fs_tag = False
        elif opt in ("-n", "--netrate"):
            network_tag = False
        elif opt in ("-b", "--bytepersec"):
            network_bytepersec_tag = True
        elif opt in ("-C", "--config"):
            conf_file = arg
            conf_file_tag = True
        elif opt in ("-z", "--nobold"):
            use_bold = False
        elif opt in ("-r", "--noproc"):
            process_tag = False
        elif opt in ("-1", "--percpu"):
            percpu_tag = True
        else:
            printSyntax()
            sys.exit(0)

    # Check options
    if password_tag and password_prompt:
        print(_("Error: Cannot use both -P and --password flag"))
        sys.exit(2)

    if server_tag:
        if client_tag:
            print(_("Error: Cannot use both -s and -c flag"))
            sys.exit(2)
        if html_tag or csv_tag:
            print(_("Error: Cannot use both -s and -o flag"))
            sys.exit(2)
        if password_prompt:
            password = get_password(description=_("Define the password for the Glances server"), confirm=True)

    if client_tag:
        if html_tag or csv_tag:
            print(_("Error: Cannot use both -c and -o flag"))
            sys.exit(2)
        if conf_file_tag:
            print(_("Error: Cannot use both -c and -C flag"))
            print(_("       Limits are set based on the server ones"))
            sys.exit(2)
        if password_prompt:
            password = get_password(description=_("Enter the Glances server password"), confirm=False)

    if html_tag:
        if not html_lib_tag:
            print(_("Error: Need Jinja2 library to export into HTML"))
            print(_("Try to install the python-jinja2 package"))
            sys.exit(2)
        try:
            output_folder
        except UnboundLocalError:
            print(_("Error: HTML export (-o html) need "
                    "output folder definition (-f <folder>)"))
            sys.exit(2)

    if csv_tag:
        if not csv_lib_tag:
            print(_("Error: Need CSV library to export into CSV"))
            sys.exit(2)
        try:
            output_file
        except UnboundLocalError:
            print(_("Error: CSV export (-o csv) need "
                    "output file definition (-f <file>)"))
            sys.exit(2)

    # Catch CTRL-C
    signal.signal(signal.SIGINT, signal_handler)

    if conf_file_tag:
        config = Config(conf_file)
    else:
        config = Config()

    if client_tag:
        psutil_get_io_counter_tag = True
        psutil_mem_vm = False
        fs_tag = True
        diskio_tag = True
        network_tag = True
        sensors_tag = True
        hddtemp_tag = True
    elif server_tag:
        sensors_tag = True
        hddtemp_tag = True

    # Init Glances depending of the mode (standalone, client, server)
    if server_tag:
        # Init the server
        try:
            server = GlancesServer(bind_ip, int(server_port), GlancesXMLRPCHandler, cached_time)
        except (ValueError, socket.error) as err:
            print(_("Error: Invalid port number: %s") % err)
            sys.exit(2)
        print(_("Glances server is running on") + " %s:%s" % (bind_ip, server_port))

        # Set the server login/password (if -P/--password tag)
        if password != "":
            server.add_user(username, password)

        # Init Limits
        limits = glancesLimits()

        # Init monitor list
        monitors = monitorList()

        # Init stats
        stats = GlancesStatsServer()
        stats.update({})
    elif client_tag:
        # Init the client (displaying server stat in the CLI)
        try:
            client = GlancesClient(server_ip, int(server_port), username, password)
        except (ValueError, socket.error) as err:
            print(_("Error: Invalid port number: %s") % err)
            sys.exit(2)

        # Test if client and server are in the same major version
        if not client.client_init():
            print(_("Error: The server version is not compatible"))
            sys.exit(2)

        # Init Limits
        limits = glancesLimits()

        # Init monitor list
        monitors = monitorList()

        # Init Logs
        logs = glancesLogs()

        # Init stats
        stats = GlancesStatsClient()

        # Init screen
        screen = glancesScreen(refresh_time=refresh_time,
                               use_bold=use_bold)
    else:
        # Init the classical CLI

        # Init Limits
        limits = glancesLimits()

        # Init monitor list
        monitors = monitorList()

        # Init Logs
        logs = glancesLogs()

        # Init stats
        stats = GlancesStats()

        # Init HTML output
        if html_tag:
            htmloutput = glancesHtml(html_path=output_folder,
                                     refresh_time=refresh_time)

        # Init CSV output
        if csv_tag:
            csvoutput = glancesCsv(cvsfile=output_file,
                                   refresh_time=refresh_time)

        # Init screen
        screen = glancesScreen(refresh_time=refresh_time,
                               use_bold=use_bold)

    # Glances - Main loop
    #####################

    if server_tag:
        # Start the server loop
        server.serve_forever()
    elif client_tag:
        # Set the limits to the server ones
        server_limits = client.client_get_limits()
        if server_limits != {}:
            limits.setAll(server_limits)

        # Set the monitored pocesses list to the server one
        server_monitored = client.client_get_monitored()
        if server_monitored != []:
            monitors.setAll(server_monitored)

        # Start the client (CLI) loop
        while True:
            # Get server system informations
            server_stats = client.client_get()
            if server_stats == {}:
                server_status = "Disconnected"
            else:
                server_status = "Connected"
                stats.update(server_stats)
            # Update the screen
            screen.update(stats, cs_status=server_status)
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


def getTimeSinceLastUpdate(IOType):
    global last_update_times
    assert(IOType in ['net', 'disk', 'process_disk'])
    current_time = time.time()
    last_time = last_update_times.get(IOType)
    if not last_time:
        time_since_update = 1
    else:
        time_since_update = current_time - last_time
    last_update_times[IOType] = current_time
    return time_since_update

# Main
#=====

if __name__ == "__main__":
    main()


# The end...
