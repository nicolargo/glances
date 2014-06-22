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

"""Process list plugin."""

# Import sys libs
import os
from datetime import timedelta

# Import Glances libs
from glances.core.glances_globals import glances_processes, is_windows
from glances.plugins.glances_plugin import GlancesPlugin


class Plugin(GlancesPlugin):

    """Glances' processes plugin.

    stats is a list
    """

    def __init__(self, args=None):
        """Init the plugin."""
        GlancesPlugin.__init__(self, args=args)

        # We want to display the stat in the curse interface
        self.display_curse = True
        # Set the message position
        # It is NOT the curse position but the Glances column/line
        # Enter -1 to right align
        self.column_curse = 1
        # Enter -1 to diplay bottom
        self.line_curse = 4

        # Note: 'glances_processes' is already init in the glances_processes.py script

    def reset(self):
        """Reset/init the stats."""
        self.stats = []

    def update(self):
        """Update processes stats using the input method."""
        # Reset stats
        self.reset()

        if self.get_input() == 'local':
            # Update stats using the standard system lib
            # Note: Update is done in the processcount plugin
            # Just return the processes list
            self.stats = glances_processes.getlist()
        elif self.get_input() == 'snmp':
            # Update stats using SNMP
            # !!! TODO
            pass

        return self.stats

    def msg_curse(self, args=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if self.stats == [] or args.disable_process:
            return ret

        # Compute the sort key
        try:
            args.process_sorted_by
        except AttributeError:
            args.process_sorted_by = glances_processes.getsortkey()
        if args.process_sorted_by == 'auto':
            process_sort_key = glances_processes.getsortkey()
        else:
            process_sort_key = args.process_sorted_by
        sort_style = 'SORT'

        # Header
        msg = '{0:>6}'.format(_("CPU%"))
        ret.append(self.curse_add_line(msg, sort_style if process_sort_key == 'cpu_percent' else 'DEFAULT'))
        msg = '{0:>6}'.format(_("MEM%"))
        ret.append(self.curse_add_line(msg, sort_style if process_sort_key == 'memory_percent' else 'DEFAULT'))
        msg = '{0:>6}'.format(_("VIRT"))
        ret.append(self.curse_add_line(msg, optional=True))
        msg = '{0:>6}'.format(_("RES"))
        ret.append(self.curse_add_line(msg, optional=True))
        msg = '{0:>6}'.format(_("PID"))
        ret.append(self.curse_add_line(msg))
        msg = ' {0:10}'.format(_("USER"))
        ret.append(self.curse_add_line(msg))
        msg = '{0:>4}'.format(_("NI"))
        ret.append(self.curse_add_line(msg))
        msg = '{0:>2}'.format(_("S"))
        ret.append(self.curse_add_line(msg))
        msg = '{0:>9}'.format(_("TIME+"))
        ret.append(self.curse_add_line(msg, optional=True))
        msg = '{0:>6}'.format(_("IOR/s"))
        ret.append(self.curse_add_line(msg, sort_style if process_sort_key == 'io_counters' else 'DEFAULT', optional=True))
        msg = '{0:>6}'.format(_("IOW/s"))
        ret.append(self.curse_add_line(msg, sort_style if process_sort_key == 'io_counters' else 'DEFAULT', optional=True))
        msg = ' {0:8}'.format(_("Command"))
        ret.append(self.curse_add_line(msg))

        # Trying to display proc time
        tag_proc_time = True

        # Loop over processes (sorted by the sort key previously compute)
        for p in self.sortlist(process_sort_key):
            ret.append(self.curse_new_line())
            # CPU
            msg = '{0:>6.1f}'.format(p['cpu_percent'])
            ret.append(self.curse_add_line(msg,
                                           self.get_alert(p['cpu_percent'], header="cpu")))
            # MEM
            msg = '{0:>6.1f}'.format(p['memory_percent'])
            ret.append(self.curse_add_line(msg,
                                           self.get_alert(p['memory_percent'], header="mem")))
            # VMS
            msg = '{0:>6}'.format(self.auto_unit(p['memory_info'][1], low_precision=False))
            ret.append(self.curse_add_line(msg, optional=True))
            # RSS
            msg = '{0:>6}'.format(self.auto_unit(p['memory_info'][0], low_precision=False))
            ret.append(self.curse_add_line(msg, optional=True))
            # PID
            msg = '{0:>6}'.format(p['pid'])
            ret.append(self.curse_add_line(msg))
            # USER
            # docker internal users are displayed as ints only, therefore str()
            msg = ' {0:9}'.format(str(p['username'])[:9])
            ret.append(self.curse_add_line(msg))
            # NICE
            nice = p['nice']
            if nice is None:
                nice = '?'
            msg = '{0:>5}'.format(nice)
            if isinstance(nice, int) and ((is_windows and nice != 32) or
                                          (not is_windows and nice != 0)):
                ret.append(self.curse_add_line(msg, decoration='NICE'))
            else:
                ret.append(self.curse_add_line(msg))
            # STATUS
            status = p['status']
            msg = '{0:>2}'.format(status)
            if status == 'R':
                ret.append(self.curse_add_line(msg, decoration='STATUS'))
            else:
                ret.append(self.curse_add_line(msg))
            # TIME+
            if tag_proc_time:
                try:
                    dtime = timedelta(seconds=sum(p['cpu_times']))
                except Exception:
                    # Catched on some Amazon EC2 server
                    # See https://github.com/nicolargo/glances/issues/87
                    tag_proc_time = False
                else:
                    msg = '{0}:{1}.{2}'.format(str(dtime.seconds // 60 % 60),
                                               str(dtime.seconds % 60).zfill(2),
                                               str(dtime.microseconds)[:2].zfill(2))
            else:
                msg = ' '
            msg = '{0:>9}'.format(msg)
            ret.append(self.curse_add_line(msg, optional=True))
            # IO read/write
            if 'io_counters' in p:
                # IO read
                io_rs = (p['io_counters'][0] - p['io_counters'][2]) / p['time_since_update']
                if io_rs == 0:
                    msg = '{0:>6}'.format("0")
                else:
                    msg = '{0:>6}'.format(self.auto_unit(io_rs, low_precision=False))
                ret.append(self.curse_add_line(msg, optional=True))
                # IO write
                io_ws = (p['io_counters'][1] - p['io_counters'][3]) / p['time_since_update']
                if io_ws == 0:
                    msg = '{0:>6}'.format("0")
                else:
                    msg = '{0:>6}'.format(self.auto_unit(io_ws, low_precision=False))
                ret.append(self.curse_add_line(msg, optional=True))
            else:
                msg = '{0:>6}'.format("?")
                ret.append(self.curse_add_line(msg, optional=True))
                ret.append(self.curse_add_line(msg, optional=True))
            # Command line
            # If no command line for the process is available, fallback to
            # the bare process name instead
            cmdline = p['cmdline']
            if cmdline == "":
                msg = ' {0}'.format(p['name'])
                ret.append(self.curse_add_line(msg, splittable=True))
            else:
                try:
                    cmd = cmdline.split()[0]
                    args = ' '.join(cmdline.split()[1:])
                    path, basename = os.path.split(cmd)
                    if os.path.isdir(path):
                        msg = ' {0}'.format(path) + os.sep
                        ret.append(self.curse_add_line(msg, splittable=True))
                        ret.append(self.curse_add_line(basename, decoration='PROCESS', splittable=True))
                    else:
                        msg = ' {0}'.format(basename)
                        ret.append(self.curse_add_line(msg, decoration='PROCESS', splittable=True))
                    msg = " {0}".format(args)
                    ret.append(self.curse_add_line(msg, splittable=True))
                except UnicodeEncodeError:
                    ret.append(self.curse_add_line("", splittable=True))

        # Return the message with decoration
        return ret

    def sortlist(self, sortedby=None):
        """Return the stats sorted by sortedby variable."""
        if sortedby is None:
            # No need to sort...
            return self.stats

        sortedreverse = True
        if sortedby == 'name':
            sortedreverse = False

        if sortedby == 'io_counters':
            # Specific case for io_counters
            # Sum of io_r + io_w
            try:
                # Sort process by IO rate (sum IO read + IO write)
                listsorted = sorted(self.stats,
                                    key=lambda process: process[sortedby][0] -
                                    process[sortedby][2] + process[sortedby][1] -
                                    process[sortedby][3],
                                    reverse=sortedreverse)
            except Exception:
                listsorted = sorted(self.stats,
                                    key=lambda process: process['cpu_percent'],
                                    reverse=sortedreverse)
        else:
            # Others sorts
            listsorted = sorted(self.stats,
                                key=lambda process: process[sortedby],
                                reverse=sortedreverse)

        self.stats = listsorted

        return self.stats
