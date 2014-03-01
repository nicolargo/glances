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

from datetime import timedelta

from glances_plugin import GlancesPlugin
from _processes import processes


class Plugin(GlancesPlugin):
    """
    Glances's processes Plugin

    stats is a list
    """

    def __init__(self):
        GlancesPlugin.__init__(self)

        # Nothing else to do...
        # 'processes' is already init in the _processes.py script


    def update(self):
        """
        Update processes stats
        """

        # Note: Update is done in the processcount plugin

        self.stats = processes.getlist()
        # We want to display the stat in the curse interface
        self.display_curse = True
        # Set the message position
        # It is NOT the curse position but the Glances column/line
        # Enter -1 to right align 
        self.column_curse = 1
        # Enter -1 to diplay bottom
        self.line_curse = 4


    def msg_curse(self, args=None):
        """
        Return the dict to display in the curse interface
        """

        # Init the return message
        ret = []

        # Header
        msg="{0:15}".format(_(""))
        ret.append(self.curse_add_line(msg))
        msg="{0:>6}".format(_("CPU%"))
        ret.append(self.curse_add_line(msg))
        msg="{0:>6}".format(_("MEM%"))
        ret.append(self.curse_add_line(msg))
        msg="{0:>6}".format(_("VIRT"))
        ret.append(self.curse_add_line(msg, optional=True))
        msg="{0:>6}".format(_("RES"))
        ret.append(self.curse_add_line(msg, optional=True))
        msg="{0:>6}".format(_("PID"))
        ret.append(self.curse_add_line(msg, optional=True))
        msg=" {0:10}".format(_("USER"))
        ret.append(self.curse_add_line(msg, optional=True))
        msg="{0:>3}".format(_("NI"))
        ret.append(self.curse_add_line(msg, optional=True))
        msg=" {0:1}".format(_("S"))
        ret.append(self.curse_add_line(msg, optional=True))
        msg="{0:>9}".format(_("TIME+"))
        ret.append(self.curse_add_line(msg, optional=True))
        msg="{0:>6}".format(_("IOr/s"))
        ret.append(self.curse_add_line(msg, optional=True))
        msg="{0:>6}".format(_("IOw/s"))
        ret.append(self.curse_add_line(msg, optional=True))
        msg=" {0:8}".format(_("Command"))
        ret.append(self.curse_add_line(msg, optional=True))
 
        # Trying to display proc time
        tag_proc_time = True

        # Loop over processes (sorted by args.process_sorted_by)
        for p in sorted(self.stats, key=lambda process: process['cpu_percent'], reverse=True):
            ret.append(self.curse_new_line())
            # Name
            msg="{0:15}".format(p['name'][:15])
            ret.append(self.curse_add_line(msg))
            # CPU
            msg = "{0:>6}".format(format(p['cpu_percent'], '>5.1f'))
            ret.append(self.curse_add_line(msg, 
                                           self.get_alert(p['cpu_percent'], header="cpu")))
            # MEM
            msg = "{0:>6}".format(format(p['memory_percent'], '>5.1f'))
            ret.append(self.curse_add_line(msg, 
                                           self.get_alert(p['memory_percent'], header="mem")))
            # VMS
            msg = "{0:>6}".format(self.auto_unit(p['memory_info'][1], low_precision=False))
            ret.append(self.curse_add_line(msg, optional=True))
            # RSS
            msg = "{0:>6}".format(self.auto_unit(p['memory_info'][0], low_precision=False))
            ret.append(self.curse_add_line(msg, optional=True))
            # PID
            msg = "{0:>6}".format(p['pid'])
            ret.append(self.curse_add_line(msg, optional=True))
            # USER
            msg = " {0:9}".format(p['username'][:9])
            ret.append(self.curse_add_line(msg, optional=True))
            # NICE
            msg = " {0:>3}".format(p['nice'])
            ret.append(self.curse_add_line(msg, optional=True))
            # STATUS
            msg = " {0:>1}".format(p['status'])
            ret.append(self.curse_add_line(msg, optional=True))
            # TIME+
            if (tag_proc_time):
                try:
                    dtime = timedelta(seconds=sum(p['cpu_times']))
                except Exception:
                    # Catched on some Amazon EC2 server
                    # See https://github.com/nicolargo/glances/issues/87
                    tag_proc_time = False
                else:
                    msg = "{0}:{1}.{2}".format(
                            str(dtime.seconds // 60 % 60),
                            str(dtime.seconds % 60).zfill(2),
                            str(dtime.microseconds)[:2].zfill(2))
            else:
                msg = " "
            msg = "{0:>9}".format(msg)
            ret.append(self.curse_add_line(msg, optional=True))
            # IO read
            io_rs = (p['io_counters'][0] - p['io_counters'][2]) / p['time_since_update']
            msg = "{0:>6}".format(self.auto_unit(io_rs, low_precision=False))
            ret.append(self.curse_add_line(msg, optional=True))
            # IO write
            io_ws = (p['io_counters'][1] - p['io_counters'][3]) / p['time_since_update']
            msg = "{0:>6}".format(self.auto_unit(io_ws, low_precision=False))
            ret.append(self.curse_add_line(msg, optional=True))
            msg = " {0}".format(p['cmdline'])
            ret.append(self.curse_add_line(msg, optional=True))

        # Return the message with decoration 
        return ret
