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

"""Process list plugin."""

import os
import shlex
import copy
from datetime import timedelta

from glances.logger import logger
from glances.globals import WINDOWS
from glances.processes import glances_processes, sort_stats
from glances.plugins.glances_core import Plugin as CorePlugin
from glances.plugins.glances_plugin import GlancesPlugin


def seconds_to_hms(input_seconds):
    """Convert seconds to human-readable time."""
    minutes, seconds = divmod(input_seconds, 60)
    hours, minutes = divmod(minutes, 60)

    hours = int(hours)
    minutes = int(minutes)
    seconds = str(int(seconds)).zfill(2)

    return hours, minutes, seconds


def split_cmdline(cmdline):
    """Return path, cmd and arguments for a process cmdline."""
    path, cmd = os.path.split(cmdline[0])
    arguments = ' '.join(cmdline[1:])
    return path, cmd, arguments


class Plugin(GlancesPlugin):
    """Glances' processes plugin.

    stats is a list
    """

    # Define the header layout of the processes list columns
    layout_header = {
        'cpu': '{:<6} ',
        'mem': '{:<5} ',
        'virt': '{:<5} ',
        'res': '{:<5} ',
        'pid': '{:>{width}} ',
        'user': '{:<10} ',
        'time': '{:>8} ',
        'thread': '{:<3} ',
        'nice': '{:>3} ',
        'status': '{:>1} ',
        'ior': '{:>4} ',
        'iow': '{:<4} ',
        'command': '{}',
    }

    # Define the stat layout of the processes list columns
    layout_stat = {
        'cpu': '{:<6.1f} ',
        'mem': '{:<5.1f} ',
        'virt': '{:<5} ',
        'res': '{:<5} ',
        'pid': '{:>{width}} ',
        'user': '{:<10} ',
        'time': '{:>8} ',
        'thread': '{:<3} ',
        'nice': '{:>3} ',
        'status': '{:>1} ',
        'ior': '{:>4} ',
        'iow': '{:<4} ',
        'command': '{}',
        'name': '[{}]'
    }

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super(Plugin, self).__init__(args=args,
                                     config=config,
                                     stats_init_value=[])

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Trying to display proc time
        self.tag_proc_time = True

        # Call CorePlugin to get the core number (needed when not in IRIX mode / Solaris mode)
        try:
            self.nb_log_core = CorePlugin(args=self.args).update()["log"]
        except Exception:
            self.nb_log_core = 0

        # Get the max values (dict)
        self.max_values = copy.deepcopy(glances_processes.max_values())

        # Get the maximum PID number
        # Use to optimize space (see https://github.com/nicolargo/glances/issues/959)
        self.pid_max = glances_processes.pid_max

        # Set the default sort key if it is defined in the configuration file
        if config is not None:
            if 'processlist' in config.as_dict() and 'sort_key' in config.as_dict()['processlist']:
                logger.debug('Configuration overwrites processes sort key by {}'.format(config.as_dict()['processlist']['sort_key']))
                glances_processes.set_sort_key(config.as_dict()['processlist']['sort_key'], False)

        # Note: 'glances_processes' is already init in the processes.py script

    def get_key(self):
        """Return the key of the list."""
        return 'pid'

    def update(self):
        """Update processes stats using the input method."""
        # Init new stats
        stats = self.get_init_value()

        if self.input_method == 'local':
            # Update stats using the standard system lib
            # Note: Update is done in the processcount plugin
            # Just return the processes list
            stats = glances_processes.getlist()

        elif self.input_method == 'snmp':
            # No SNMP grab for processes
            pass

        # Update the stats
        self.stats = stats

        # Get the max values (dict)
        # Use Deep copy to avoid change between update and display
        self.max_values = copy.deepcopy(glances_processes.max_values())

        return self.stats

    def get_nice_alert(self, value):
        """Return the alert relative to the Nice configuration list"""
        value = str(value)
        try:
            if value in self.get_limit('nice_critical'):
                return 'CRITICAL'
        except KeyError:
            pass
        try:
            if value in self.get_limit('nice_warning'):
                return 'WARNING'
        except KeyError:
            pass
        try:
            if value in self.get_limit('nice_careful'):
                return 'CAREFUL'
        except KeyError:
            pass
        return 'DEFAULT'

    def get_process_curses_data(self, p, first, args):
        """Get curses data to display for a process.

        - p is the process to display
        - first is a tag=True if the process is the first on the list
        """
        ret = [self.curse_new_line()]
        # CPU
        if 'cpu_percent' in p and p['cpu_percent'] is not None and p['cpu_percent'] != '':
            if args.disable_irix and self.nb_log_core != 0:
                msg = self.layout_stat['cpu'].format(p['cpu_percent'] / float(self.nb_log_core))
            else:
                msg = self.layout_stat['cpu'].format(p['cpu_percent'])
            alert = self.get_alert(p['cpu_percent'],
                                   highlight_zero=False,
                                   is_max=(p['cpu_percent'] == self.max_values['cpu_percent']),
                                   header="cpu")
            ret.append(self.curse_add_line(msg, alert))
        else:
            msg = self.layout_header['cpu'].format('?')
            ret.append(self.curse_add_line(msg))
        # MEM
        if 'memory_percent' in p and p['memory_percent'] is not None and p['memory_percent'] != '':
            msg = self.layout_stat['mem'].format(p['memory_percent'])
            alert = self.get_alert(p['memory_percent'],
                                   highlight_zero=False,
                                   is_max=(p['memory_percent'] == self.max_values['memory_percent']),
                                   header="mem")
            ret.append(self.curse_add_line(msg, alert))
        else:
            msg = self.layout_header['mem'].format('?')
            ret.append(self.curse_add_line(msg))
        # VMS/RSS
        if 'memory_info' in p and p['memory_info'] is not None and p['memory_info'] != '':
            # VMS
            msg = self.layout_stat['virt'].format(self.auto_unit(p['memory_info'][1], low_precision=False))
            ret.append(self.curse_add_line(msg, optional=True))
            # RSS
            msg = self.layout_stat['res'].format(self.auto_unit(p['memory_info'][0], low_precision=False))
            ret.append(self.curse_add_line(msg, optional=True))
        else:
            msg = self.layout_header['virt'].format('?')
            ret.append(self.curse_add_line(msg))
            msg = self.layout_header['res'].format('?')
            ret.append(self.curse_add_line(msg))
        # PID
        msg = self.layout_stat['pid'].format(p['pid'], width=self.__max_pid_size())
        ret.append(self.curse_add_line(msg))
        # USER
        if 'username' in p:
            # docker internal users are displayed as ints only, therefore str()
            # Correct issue #886 on Windows OS
            msg = self.layout_stat['user'].format(str(p['username'])[:9])
            ret.append(self.curse_add_line(msg))
        else:
            msg = self.layout_header['user'].format('?')
            ret.append(self.curse_add_line(msg))
        # TIME+
        try:
            # Sum user and system time
            user_system_time = p['cpu_times'][0] + p['cpu_times'][1]
        except (OverflowError, TypeError) as e:
            # Catch OverflowError on some Amazon EC2 server
            # See https://github.com/nicolargo/glances/issues/87
            # Also catch TypeError on macOS
            # See: https://github.com/nicolargo/glances/issues/622
            # logger.debug("Cannot get TIME+ ({})".format(e))
            msg = self.layout_header['time'].format('?')
            ret.append(self.curse_add_line(msg, optional=True))
        else:
            hours, minutes, seconds = seconds_to_hms(user_system_time)
            if hours > 99:
                msg = '{:<7}h'.format(hours)
            elif 0 < hours < 100:
                msg = '{}h{}:{}'.format(hours, minutes, seconds)
            else:
                msg = '{}:{}'.format(minutes, seconds)
            msg = self.layout_stat['time'].format(msg)
            if hours > 0:
                ret.append(self.curse_add_line(msg,
                                               decoration='CPU_TIME',
                                               optional=True))
            else:
                ret.append(self.curse_add_line(msg, optional=True))
        # THREAD
        if 'num_threads' in p:
            num_threads = p['num_threads']
            if num_threads is None:
                num_threads = '?'
            msg = self.layout_stat['thread'].format(num_threads)
            ret.append(self.curse_add_line(msg))
        else:
            msg = self.layout_header['thread'].format('?')
            ret.append(self.curse_add_line(msg))
        # NICE
        if 'nice' in p:
            nice = p['nice']
            if nice is None:
                nice = '?'
            msg = self.layout_stat['nice'].format(nice)
            ret.append(self.curse_add_line(msg,
                                           decoration=self.get_nice_alert(nice)))
        else:
            msg = self.layout_header['nice'].format('?')
            ret.append(self.curse_add_line(msg))
        # STATUS
        if 'status' in p:
            status = p['status']
            msg = self.layout_stat['status'].format(status)
            if status == 'R':
                ret.append(self.curse_add_line(msg, decoration='STATUS'))
            else:
                ret.append(self.curse_add_line(msg))
        else:
            msg = self.layout_header['status'].format('?')
            ret.append(self.curse_add_line(msg))
        # IO read/write
        if 'io_counters' in p and p['io_counters'][4] == 1 and p['time_since_update'] != 0:
            # Display rate if stats is available and io_tag ([4]) == 1
            # IO read
            io_rs = int((p['io_counters'][0] - p['io_counters'][2]) / p['time_since_update'])
            if io_rs == 0:
                msg = self.layout_stat['ior'].format("0")
            else:
                msg = self.layout_stat['ior'].format(self.auto_unit(io_rs,
                                                                    low_precision=True))
            ret.append(self.curse_add_line(msg, optional=True, additional=True))
            # IO write
            io_ws = int((p['io_counters'][1] - p['io_counters'][3]) / p['time_since_update'])
            if io_ws == 0:
                msg = self.layout_stat['iow'].format("0")
            else:
                msg = self.layout_stat['iow'].format(self.auto_unit(io_ws,
                                                                    low_precision=True))
            ret.append(self.curse_add_line(msg, optional=True, additional=True))
        else:
            msg = self.layout_header['ior'].format("?")
            ret.append(self.curse_add_line(msg, optional=True, additional=True))
            msg = self.layout_header['iow'].format("?")
            ret.append(self.curse_add_line(msg, optional=True, additional=True))

        # Command line
        # If no command line for the process is available, fallback to
        # the bare process name instead
        if 'cmdline' in p:
            cmdline = p['cmdline']
        else:
            cmdline = '?'
        try:
            if cmdline:
                path, cmd, arguments = split_cmdline(cmdline)
                if os.path.isdir(path) and not args.process_short_name:
                    msg = self.layout_stat['command'].format(path) + os.sep
                    ret.append(self.curse_add_line(msg, splittable=True))
                    ret.append(self.curse_add_line(cmd, decoration='PROCESS', splittable=True))
                else:
                    msg = self.layout_stat['command'].format(cmd)
                    ret.append(self.curse_add_line(msg, decoration='PROCESS', splittable=True))
                if arguments:
                    msg = ' ' + self.layout_stat['command'].format(arguments)
                    ret.append(self.curse_add_line(msg, splittable=True))
            else:
                msg = self.layout_stat['name'].format(p['name'])
                ret.append(self.curse_add_line(msg, splittable=True))
        except (TypeError, UnicodeEncodeError) as e:
            # Avoid crach after running fine for several hours #1335
            logger.debug("Can not decode command line '{}' ({})".format(cmdline, e))
            ret.append(self.curse_add_line('', splittable=True))

        # Add extended stats but only for the top processes
        if first and 'extended_stats' in p and args.enable_process_extended:
            # Left padding
            xpad = ' ' * 13
            # First line is CPU affinity
            if 'cpu_affinity' in p and p['cpu_affinity'] is not None:
                ret.append(self.curse_new_line())
                msg = xpad + 'CPU affinity: ' + str(len(p['cpu_affinity'])) + ' cores'
                ret.append(self.curse_add_line(msg, splittable=True))
            # Second line is memory info
            if 'memory_info' in p and \
               p['memory_info'] is not None:
                ret.append(self.curse_new_line())
                msg = '{}Memory info: {}'.format(xpad, p['memory_info'])
                if 'memory_swap' in p and p['memory_swap'] is not None:
                    msg += ' swap ' + self.auto_unit(p['memory_swap'], low_precision=False)
                ret.append(self.curse_add_line(msg, splittable=True))
            # Third line is for open files/network sessions
            msg = ''
            if 'num_threads' in p and p['num_threads'] is not None:
                msg += str(p['num_threads']) + ' threads '
            if 'num_fds' in p and p['num_fds'] is not None:
                msg += str(p['num_fds']) + ' files '
            if 'num_handles' in p and p['num_handles'] is not None:
                msg += str(p['num_handles']) + ' handles '
            if 'tcp' in p and p['tcp'] is not None:
                msg += str(p['tcp']) + ' TCP '
            if 'udp' in p and p['udp'] is not None:
                msg += str(p['udp']) + ' UDP'
            if msg != '':
                ret.append(self.curse_new_line())
                msg = xpad + 'Open: ' + msg
                ret.append(self.curse_add_line(msg, splittable=True))
            # Fouth line is IO nice level (only Linux and Windows OS)
            if 'ionice' in p and \
               p['ionice'] is not None \
               and hasattr(p['ionice'], 'ioclass'):
                ret.append(self.curse_new_line())
                msg = xpad + 'IO nice: '
                k = 'Class is '
                v = p['ionice'].ioclass
                # Linux: The scheduling class. 0 for none, 1 for real time, 2 for best-effort, 3 for idle.
                # Windows: On Windows only ioclass is used and it can be set to 2 (normal), 1 (low) or 0 (very low).
                if WINDOWS:
                    if v == 0:
                        msg += k + 'Very Low'
                    elif v == 1:
                        msg += k + 'Low'
                    elif v == 2:
                        msg += 'No specific I/O priority'
                    else:
                        msg += k + str(v)
                else:
                    if v == 0:
                        msg += 'No specific I/O priority'
                    elif v == 1:
                        msg += k + 'Real Time'
                    elif v == 2:
                        msg += k + 'Best Effort'
                    elif v == 3:
                        msg += k + 'IDLE'
                    else:
                        msg += k + str(v)
                #  value is a number which goes from 0 to 7.
                # The higher the value, the lower the I/O priority of the process.
                if hasattr(p['ionice'], 'value') and p['ionice'].value != 0:
                    msg += ' (value %s/7)' % str(p['ionice'].value)
                ret.append(self.curse_add_line(msg, splittable=True))

        return ret

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if not self.stats or args.disable_process:
            return ret

        # Compute the sort key
        process_sort_key = glances_processes.sort_key

        # Header
        self.__msg_curse_header(ret, process_sort_key, args)

        # Process list
        # Loop over processes (sorted by the sort key previously compute)
        first = True
        for p in self.__sort_stats(process_sort_key):
            ret.extend(self.get_process_curses_data(p, first, args))
            # End of extended stats
            first = False
        if glances_processes.process_filter is not None:
            if args.reset_minmax_tag:
                args.reset_minmax_tag = not args.reset_minmax_tag
                self.__mmm_reset()
            self.__msg_curse_sum(ret, args=args)
            self.__msg_curse_sum(ret, mmm='min', args=args)
            self.__msg_curse_sum(ret, mmm='max', args=args)

        # Return the message with decoration
        return ret

    def __msg_curse_header(self, ret, process_sort_key, args=None):
        """Build the header and add it to the ret dict."""
        sort_style = 'SORT'

        if args.disable_irix and 0 < self.nb_log_core < 10:
            msg = self.layout_header['cpu'].format('CPU%/' + str(self.nb_log_core))
        elif args.disable_irix and self.nb_log_core != 0:
            msg = self.layout_header['cpu'].format('CPU%/C')
        else:
            msg = self.layout_header['cpu'].format('CPU%')
        ret.append(self.curse_add_line(msg, sort_style if process_sort_key == 'cpu_percent' else 'DEFAULT'))
        msg = self.layout_header['mem'].format('MEM%')
        ret.append(self.curse_add_line(msg, sort_style if process_sort_key == 'memory_percent' else 'DEFAULT'))
        msg = self.layout_header['virt'].format('VIRT')
        ret.append(self.curse_add_line(msg, optional=True))
        msg = self.layout_header['res'].format('RES')
        ret.append(self.curse_add_line(msg, optional=True))
        msg = self.layout_header['pid'].format('PID', width=self.__max_pid_size())
        ret.append(self.curse_add_line(msg))
        msg = self.layout_header['user'].format('USER')
        ret.append(self.curse_add_line(msg, sort_style if process_sort_key == 'username' else 'DEFAULT'))
        msg = self.layout_header['time'].format('TIME+')
        ret.append(self.curse_add_line(msg, sort_style if process_sort_key == 'cpu_times' else 'DEFAULT', optional=True))
        msg = self.layout_header['thread'].format('THR')
        ret.append(self.curse_add_line(msg))
        msg = self.layout_header['nice'].format('NI')
        ret.append(self.curse_add_line(msg))
        msg = self.layout_header['status'].format('S')
        ret.append(self.curse_add_line(msg))
        msg = self.layout_header['ior'].format('R/s')
        ret.append(self.curse_add_line(msg, sort_style if process_sort_key == 'io_counters' else 'DEFAULT', optional=True, additional=True))
        msg = self.layout_header['iow'].format('W/s')
        ret.append(self.curse_add_line(msg, sort_style if process_sort_key == 'io_counters' else 'DEFAULT', optional=True, additional=True))
        msg = self.layout_header['command'].format('Command')
        ret.append(self.curse_add_line(msg, sort_style if process_sort_key == 'name' else 'DEFAULT'))

    def __msg_curse_sum(self, ret, sep_char='_', mmm=None, args=None):
        """
        Build the sum message (only when filter is on) and add it to the ret dict.

        * ret: list of string where the message is added
        * sep_char: define the line separation char
        * mmm: display min, max, mean or current (if mmm=None)
        * args: Glances args
        """
        ret.append(self.curse_new_line())
        if mmm is None:
            ret.append(self.curse_add_line(sep_char * 69))
            ret.append(self.curse_new_line())
        # CPU percent sum
        msg = self.layout_stat['cpu'].format(self.__sum_stats('cpu_percent', mmm=mmm))
        ret.append(self.curse_add_line(msg,
                                       decoration=self.__mmm_deco(mmm)))
        # MEM percent sum
        msg = self.layout_stat['mem'].format(self.__sum_stats('memory_percent', mmm=mmm))
        ret.append(self.curse_add_line(msg,
                                       decoration=self.__mmm_deco(mmm)))
        # VIRT and RES memory sum
        if 'memory_info' in self.stats[0] and self.stats[0]['memory_info'] is not None and self.stats[0]['memory_info'] != '':
            # VMS
            msg = self.layout_stat['virt'].format(self.auto_unit(self.__sum_stats('memory_info', indice=1, mmm=mmm), low_precision=False))
            ret.append(self.curse_add_line(msg,
                                           decoration=self.__mmm_deco(mmm),
                                           optional=True))
            # RSS
            msg = self.layout_stat['res'].format(self.auto_unit(self.__sum_stats('memory_info', indice=0, mmm=mmm), low_precision=False))
            ret.append(self.curse_add_line(msg,
                                           decoration=self.__mmm_deco(mmm),
                                           optional=True))
        else:
            msg = self.layout_header['virt'].format('')
            ret.append(self.curse_add_line(msg))
            msg = self.layout_header['res'].format('')
            ret.append(self.curse_add_line(msg))
        # PID
        msg = self.layout_header['pid'].format('', width=self.__max_pid_size())
        ret.append(self.curse_add_line(msg))
        # USER
        msg = self.layout_header['user'].format('')
        ret.append(self.curse_add_line(msg))
        # TIME+
        msg = self.layout_header['time'].format('')
        ret.append(self.curse_add_line(msg, optional=True))
        # THREAD
        msg = self.layout_header['thread'].format('')
        ret.append(self.curse_add_line(msg))
        # NICE
        msg = self.layout_header['nice'].format('')
        ret.append(self.curse_add_line(msg))
        # STATUS
        msg = self.layout_header['status'].format('')
        ret.append(self.curse_add_line(msg))
        # IO read/write
        if 'io_counters' in self.stats[0] and mmm is None:
            # IO read
            io_rs = int((self.__sum_stats('io_counters', 0) - self.__sum_stats('io_counters', indice=2, mmm=mmm)) / self.stats[0]['time_since_update'])
            if io_rs == 0:
                msg = self.layout_stat['ior'].format('0')
            else:
                msg = self.layout_stat['ior'].format(self.auto_unit(io_rs, low_precision=True))
            ret.append(self.curse_add_line(msg,
                                           decoration=self.__mmm_deco(mmm),
                                           optional=True, additional=True))
            # IO write
            io_ws = int((self.__sum_stats('io_counters', 1) - self.__sum_stats('io_counters', indice=3, mmm=mmm)) / self.stats[0]['time_since_update'])
            if io_ws == 0:
                msg = self.layout_stat['iow'].format('0')
            else:
                msg = self.layout_stat['iow'].format(self.auto_unit(io_ws, low_precision=True))
            ret.append(self.curse_add_line(msg,
                                           decoration=self.__mmm_deco(mmm),
                                           optional=True, additional=True))
        else:
            msg = self.layout_header['ior'].format('')
            ret.append(self.curse_add_line(msg, optional=True, additional=True))
            msg = self.layout_header['iow'].format('')
            ret.append(self.curse_add_line(msg, optional=True, additional=True))
        if mmm is None:
            msg = ' < {}'.format('current')
            ret.append(self.curse_add_line(msg, optional=True))
        else:
            msg = ' < {}'.format(mmm)
            ret.append(self.curse_add_line(msg, optional=True))
            msg = ' (\'M\' to reset)'
            ret.append(self.curse_add_line(msg, optional=True))

    def __mmm_deco(self, mmm):
        """Return the decoration string for the current mmm status."""
        if mmm is not None:
            return 'DEFAULT'
        else:
            return 'FILTER'

    def __mmm_reset(self):
        """Reset the MMM stats."""
        self.mmm_min = {}
        self.mmm_max = {}

    def __sum_stats(self, key, indice=None, mmm=None):
        """Return the sum of the stats value for the given key.

        * indice: If indice is set, get the p[key][indice]
        * mmm: display min, max, mean or current (if mmm=None)
        """
        # Compute stats summary
        ret = 0
        for p in self.stats:
            if key not in p:
                # Correct issue #1188
                continue
            if p[key] is None:
                # Correct https://github.com/nicolargo/glances/issues/1105#issuecomment-363553788
                continue
            if indice is None:
                ret += p[key]
            else:
                ret += p[key][indice]

        # Manage Min/Max/Mean
        mmm_key = self.__mmm_key(key, indice)
        if mmm == 'min':
            try:
                if self.mmm_min[mmm_key] > ret:
                    self.mmm_min[mmm_key] = ret
            except AttributeError:
                self.mmm_min = {}
                return 0
            except KeyError:
                self.mmm_min[mmm_key] = ret
            ret = self.mmm_min[mmm_key]
        elif mmm == 'max':
            try:
                if self.mmm_max[mmm_key] < ret:
                    self.mmm_max[mmm_key] = ret
            except AttributeError:
                self.mmm_max = {}
                return 0
            except KeyError:
                self.mmm_max[mmm_key] = ret
            ret = self.mmm_max[mmm_key]

        return ret

    def __mmm_key(self, key, indice):
        ret = key
        if indice is not None:
            ret += str(indice)
        return ret

    def __sort_stats(self, sortedby=None):
        """Return the stats (dict) sorted by (sortedby)."""
        return sort_stats(self.stats, sortedby,
                          reverse=glances_processes.sort_reverse)

    def __max_pid_size(self):
        """Return the maximum PID size in number of char."""
        if self.pid_max is not None:
            return len(str(self.pid_max))
        else:
            # By default return 5 (corresponding to 99999 PID number)
            return 5
